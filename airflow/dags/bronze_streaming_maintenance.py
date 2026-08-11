"""
Modern Data Platform

Bronze Streaming Maintenance: daily OPTIMIZE + VACUUM against every
streaming Bronze Delta table (``bronze/{entity}/``, 16 entities --
``streaming.consumers.bronze_consumer.STREAMING_ENTITIES``).

Not the batch flow's own Bronze table (``bronze_batch/``, 7 entities,
``optimize_bronze.ipynb`` in the Databricks Full Pipeline Job) -- this
DAG only ever touches the append-only table
``streaming.consumers.bronze_consumer.run_bronze_consumer`` itself
writes to, via the same pure-Python ``deltalake`` package (not Spark),
matching that module's own PoC-scope divergence from the Spark-based
batch flow.

Why this exists: the streaming path accumulates one Delta commit (a
data file + a transaction-log entry) per micro-batch flush, with no
compaction of its own (``bronze_consumer.py`` never calls
``optimize``/``vacuum`` -- confirmed by reading it, not assumed). Left
unmanaged, this produces a real, measured disproportion between actual
data volume and S3 object/request count -- 64,549 objects for under
1 GB before this DAG existed. See
docs/architecture/roadmap-next-steps.md for the full investigation,
the one-off manual OPTIMIZE+VACUUM run this DAG supersedes, and why
today's run against a freshly-optimized table reclaims 0 files (a
correct, expected Delta VACUUM safety behavior, not a bug -- see
below).

Schedule: ``timedelta(days=1)``, not an ``@daily``/cron string -- no
cron precedent elsewhere in this project's DAGs, and a plain fixed
interval was already preferred once for exactly this readability
reason (see the reverted ``marketplace_batch_pipeline`` schedule
entry in the roadmap). Both tasks run daily, not weekly: VACUUM's own
``retention_hours=168`` (7 days, Delta's own default, kept as-is) is
what actually protects a concurrent reader from a file being removed
too early -- that safety comes from the retention window being
checked on every run, not from how often the DAG itself fires. Running
daily instead of weekly only changes how long a file that has already
crossed the 7-day mark sits around unreclaimed before the next run
notices -- at most ~1 extra day instead of up to 6.

OPTIMIZE (``DeltaTable.optimize.compact()``) is naturally idempotent:
re-running it against an already-compacted table is a real, confirmed
no-op (``0 added, 0 removed``, see the roadmap entry) -- there is
nothing for it to do until the streaming path's own micro-batch
flushes produce new small files to compact again.

VACUUM runs with ``dry_run=False`` directly, no dry-run task in this
DAG -- the mechanism was already validated manually, end to end,
before this DAG existed (dry-run list captured and reviewed, then a
real ``dry_run=False`` run confirmed identical: 0 files, both times,
because every file OPTIMIZE had just superseded was seconds old, not
7 days old). A day where VACUUM's own log shows 0 files removed is the
*expected* steady state on most days, not a failure -- physical
reclaim only happens for files that have genuinely crossed the
retention window since they were last compacted away.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from typing import Any

from airflow.decorators import dag, task

if "/opt/mdp/src" not in sys.path:
    sys.path.insert(0, "/opt/mdp/src")

_RETENTION_HOURS = 168

# mdp-bronze-maintenance-dev (Terraform module.bronze_maintenance,
# environments/dev/security.tf) -- bronze/ S3 list/get/put/delete
# only, deliberately separate from bronze_consumer's own append-only
# (no delete) credential. Passed explicitly via storage_options to
# each DeltaTable call below rather than exported into the whole
# task's os.environ -- this DAG is the only caller that should ever
# use delete access against this table, so it stays scoped to exactly
# the calls that need it, not ambient for the rest of the process.
_MAINTENANCE_AWS_CREDENTIALS: dict[str, str] = {
    "AWS_ACCESS_KEY_ID": os.environ["MDP_BRONZE_MAINTENANCE_ACCESS_KEY_ID"],
    "AWS_SECRET_ACCESS_KEY": os.environ["MDP_BRONZE_MAINTENANCE_SECRET_ACCESS_KEY"],
    "AWS_REGION": "sa-east-1",
}


@dag(
    dag_id="bronze_streaming_maintenance",
    schedule=timedelta(days=1),
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["maintenance", "bronze", "streaming"],
)
def bronze_streaming_maintenance():

    @task
    def optimize_bronze() -> dict[str, dict[str, Any]]:
        from data_platform.monitoring.logger import get_logger
        from data_platform.observability.logging_config import (
            configure_logging,
        )
        from data_platform.storage.config import StorageConfig

        from deltalake import DeltaTable

        from streaming.consumers.bronze_consumer import STREAMING_ENTITIES

        configure_logging()

        logger = get_logger(__name__)

        results: dict[str, dict[str, Any]] = {}

        errors: dict[str, str] = {}

        for entity in STREAMING_ENTITIES:
            uri = StorageConfig.bronze(entity)

            try:
                dt = DeltaTable(uri, storage_options=_MAINTENANCE_AWS_CREDENTIALS)

                metrics = dt.optimize.compact()

                added = metrics.get("numFilesAdded", 0)
                removed = metrics.get("numFilesRemoved", 0)

                results[entity] = {"filesAdded": added, "filesRemoved": removed}

                logger.info(
                    "OPTIMIZE '%s': %d file(s) added, %d file(s) "
                    "logically removed (not yet physically deleted -- "
                    "see vacuum_bronze).",
                    entity,
                    added,
                    removed,
                )
            except Exception as exc:
                errors[entity] = str(exc)

                logger.exception("OPTIMIZE failed for entity '%s'.", entity)

        if errors:
            summary = "\n".join(
                f"  - {entity}: {message}" for entity, message in errors.items()
            )

            raise RuntimeError(
                f"OPTIMIZE failed for {len(errors)} of "
                f"{len(STREAMING_ENTITIES)} entities:\n{summary}"
            )

        return results

    @task
    def vacuum_bronze(optimize_result: dict[str, dict[str, Any]]) -> None:
        from data_platform.monitoring.logger import get_logger
        from data_platform.observability.logging_config import (
            configure_logging,
        )
        from data_platform.storage.config import StorageConfig

        from deltalake import DeltaTable

        from streaming.consumers.bronze_consumer import STREAMING_ENTITIES

        configure_logging()

        logger = get_logger(__name__)

        errors: dict[str, str] = {}

        total_deleted = 0

        for entity in STREAMING_ENTITIES:
            uri = StorageConfig.bronze(entity)

            try:
                dt = DeltaTable(uri, storage_options=_MAINTENANCE_AWS_CREDENTIALS)

                deleted = dt.vacuum(
                    retention_hours=_RETENTION_HOURS,
                    dry_run=False,
                    enforce_retention_duration=True,
                )

                total_deleted += len(deleted)

                # 0 is the expected, common case -- only files tombstoned
                # more than _RETENTION_HOURS ago are eligible, see this
                # module's own docstring. Logged plainly either way, not
                # treated as a warning or hidden.
                logger.info(
                    "VACUUM '%s': %d file(s) physically deleted "
                    "(retention_hours=%d).",
                    entity,
                    len(deleted),
                    _RETENTION_HOURS,
                )
            except Exception as exc:
                errors[entity] = str(exc)

                logger.exception("VACUUM failed for entity '%s'.", entity)

        if errors:
            summary = "\n".join(
                f"  - {entity}: {message}" for entity, message in errors.items()
            )

            raise RuntimeError(
                f"VACUUM failed for {len(errors)} of "
                f"{len(STREAMING_ENTITIES)} entities:\n{summary}"
            )

        logger.info(
            "VACUUM complete: %d file(s) physically deleted across %d "
            "entities.",
            total_deleted,
            len(STREAMING_ENTITIES),
        )

    # A single optimize_bronze() call, its return value threaded into
    # vacuum_bronze() -- TaskFlow infers the dependency from that data
    # flow alone (an explicit >> alongside it would just be redundant,
    # not wrong, but calling optimize_bronze() a second time to build
    # one would create a second, disconnected task instance instead of
    # reusing the first run's result).
    vacuum_bronze(optimize_bronze())


bronze_streaming_maintenance()
