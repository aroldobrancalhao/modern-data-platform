"""
Modern Data Platform

Event-driven trigger for marketplace_batch_pipeline, replacing the
idea of a fixed-interval schedule (already tried once for this same
DAG and reverted -- see the schedule=None decision record in
docs/architecture/roadmap-next-steps.md, driven by a real
AWSDataTransfer cost spike with no matching freshness need). A fixed
interval spends real resources checking even when nothing changed;
this DAG only fires the heavy pipeline when there is real new
order_status_history data to pick up.

Runs forever once started, with no manual re-trigger ever needed in
normal operation: each cycle re-triggers the next one itself
(restart_watch_cycle, see below) the moment it ends, rather than
waiting on schedule=timedelta(days=1) alone -- that schedule is kept
only as a coarse safety net, not the primary mechanism (see below for
why relying on it alone left a real gap). Needs exactly one manual
`airflow dags trigger order_status_history_lag_watcher` to start the
first cycle after this DAG is deployed or has been paused; every cycle
after that starts itself. Before that first (or any manual re-)trigger,
check scripts/check_lag_watcher_would_fire.sh first -- see that
script's own header for why.

Signal used: mdp_bronze_records_written_total{entity="order_status_
history"}, already emitted by bronze_consumer.py (a Prometheus
Counter, scraped directly every 15s per infrastructure/docker/
monitoring/prometheus/prometheus.yml, no new instrumentation needed).

Originally designed against mdp_bronze_consumer_lag (a Gauge) instead,
with a "was > 0 in the lookback window, is 0 now" condition -- found
live, testing this DAG before considering it done, that the Gauge
doesn't work for this: it's only set once per flush, computed *after*
that flush's own commit already landed
(streaming/consumers/bronze_consumer.py's _flush()), so any backlog
that fits inside a single flush round (up to _MAX_BATCH_SIZE, 100
records) never has an observable non-zero sample at all -- confirmed
live with a real 27-message backlog (stopped bronze-consumer, let it
build up, restarted it): mdp_bronze_consumer_lag went straight from no
data to 0, never once reporting the real backlog that objectively sat
there for several minutes. mdp_bronze_records_written_total doesn't
have this gap -- it's a plain monotonic counter, incremented by
exactly the flushed row count on every real flush regardless of how
fast that flush happened, so increase() over any window that spans
the event reliably catches it. Same real backlog, same test: this
counter showed the flush's real 27 immediately, right when the Gauge
showed nothing. The condition is "some records were actually written
in the last <window>" -- 0 at rest (nothing flushed, nothing to see),
> 0 exactly when real new data landed.

    increase(mdp_bronze_records_written_total{entity="order_status_history"}[<window>]) > 0

The window must be >= the poke interval, or a flush that happens
between two pokes could in principle fall entirely outside the
previous poke's lookback range. Set to 2x the poke interval below --
full margin against scheduling jitter, and it scales automatically if
the interval is ever changed, without needing a second number to keep
in sync by hand.

Poke interval is an Airflow Variable
(order_status_history_lag_watcher_poke_interval_seconds, default
3600s/1h), read directly via Variable.get() -- same pattern as
retry_validation.py -- deliberately NOT seeded by AirflowManager.
sync_variables() (airflow/config/bootstrap/airflow.py), unlike this
project's other Variables: those are Terraform-output config,
re-synced (overwritten) on every airflow-bootstrap run by design; this
one is meant to be tuned by a human via the UI/CLI without being
silently reset back to default on the next `docker compose up`. 1h is
deliberately coarse for now -- this phase doesn't expect frequent
events, and checking rarely is the whole point of the event-driven
switch. Lower it (`airflow variables set
order_status_history_lag_watcher_poke_interval_seconds <seconds>`) if
faster reaction is ever needed; no code change required, takes effect
on the DAG's next parse.

HttpSensor(mode="reschedule"), not deferrable=True: originally used
deferrable=True on the assumption the wait would happen in the
triggerer process (this project already runs a dedicated
airflow-triggerer container, unused by any other DAG until this one)
instead of holding a worker slot. Found live, checking the running
task_instance's own state (state='running', pool='default_pool', not
'deferred') that this was never actually true: HttpSensor.execute()
only defers when no response_check is given --
`if not self.deferrable or self.response_check: return
super().execute(...)` -- and this DAG needs response_check to
interpret Prometheus' JSON, so deferrable=True was silently ignored
the entire time, holding a real worker slot for up to 23h per cycle.
mode="reschedule" is the fix that's actually compatible with a custom
response_check: still releases the worker slot between pokes (the
task instance goes to `up_for_reschedule` and the scheduler re-queues
it at the next poke_interval, rather than one process blocking/
sleeping in a loop) -- not literally free like a real deferred wait
would be, but genuinely cheap, and correct about what it's actually
doing.

restart_watch_cycle (TriggerDagRunOperator targeting this same DAG,
trigger_rule="none_failed"): this is what makes the DAG actually
continuous. schedule=timedelta(days=1) alone was a real gap, found
live: the moment sense_new_records_written succeeds (a genuine
transition fires marketplace_batch_pipeline), that DagRun completes
right then -- but the *next* automatic DagRun isn't due until the next
calendar day's schedule slot, so watching stops for up to ~24h
immediately after the one moment it just proved useful. This isn't a
testing artifact -- it's what schedule=timedelta(days=1) does on every
real fire, not just during development. restart_watch_cycle closes
that gap by triggering a fresh instance of this same DAG the moment
the current cycle ends, success or skip, so the next watch starts
immediately instead of waiting for tomorrow.

trigger_rule="none_failed" (not "all_done"): the distinction that
matters is soft_fail's own scope, confirmed by reading
BaseSensorOperator.execute()'s real source -- soft_fail only converts
a *timeout* (run_duration() > self.timeout, or AirflowSensorTimeout/
AirflowTaskTimeout/AirflowFailException) into AirflowSkipException
(task state 'skipped'). Any other exception raised inside poke() --
Prometheus unreachable, a malformed response, a real query error --
is not caught by soft_fail at all; it propagates normally and the task
ends 'failed'. "all_done" would restart the watch cycle in both cases
alike, silently looping forever on a real, persistent failure with
each cycle immediately failing again -- never detecting anything,
never surfacing that anything is wrong. "none_failed" runs on
'success' (fired) and 'skipped' (benign timeout) but not on 'failed'
(a real error) -- the chain keeps itself alive through ordinary
operation and stops, visibly, on a real problem, rather than masking
one. schedule=timedelta(days=1) is still there as a coarse safety
net for exactly that stopped case (and for restarting the chain after
any other reason it might ever break, e.g. an Airflow restart at the
wrong moment) -- it retries automatically within at most 24h even if
nobody notices the failed DagRun right away, without needing the
self-restart chain to be perfectly unbreakable.

max_active_runs=1 keeps the self-triggered next cycle and the daily
schedule's own slot from ever running concurrently against each
other.

TriggerDagRunOperator's default wait_for_completion=False is
deliberately left as-is on both TriggerDagRunOperator tasks: neither
this DAG's job (fire-and-move-on) nor marketplace_batch_pipeline's own
tasks (which already verify their own success, see that DAG's
docstring) need it.

Author: Modern Data Platform
License: MIT
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow.decorators import dag
from airflow.models import Variable
from airflow.providers.http.sensors.http import HttpSensor
from airflow.providers.standard.operators.trigger_dagrun import (
    TriggerDagRunOperator,
)
from requests import Response

_POKE_INTERVAL_VARIABLE = "order_status_history_lag_watcher_poke_interval_seconds"
_DEFAULT_POKE_INTERVAL_SECONDS = 3600  # 1h

_poke_interval_seconds = int(
    Variable.get(
        _POKE_INTERVAL_VARIABLE,
        default_var=_DEFAULT_POKE_INTERVAL_SECONDS,
    )
)

# See module docstring -- must be >= _poke_interval_seconds, 2x for
# full margin, scales automatically with the Variable above.
_window_seconds = _poke_interval_seconds * 2

_PROMQL_QUERY = (
    "increase(mdp_bronze_records_written_total"
    f'{{entity="order_status_history"}}[{_window_seconds}s]) > 0'
)

_SENSOR_TIMEOUT_SECONDS = int(timedelta(hours=23).total_seconds())


def _new_records_detected(response: Response) -> bool:
    """
    True when Prometheus' instant-vector query returned at least one
    time series. The query itself already encodes the full "records
    were actually written recently" condition (see _PROMQL_QUERY
    above) -- a non-empty result IS the event; an empty result just
    means "nothing new yet", and HttpSensor re-pokes at the next
    poke_interval.
    """

    payload = response.json()

    return len(payload.get("data", {}).get("result", [])) > 0


@dag(
    dag_id="order_status_history_lag_watcher",
    schedule=timedelta(days=1),
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["monitoring", "event-driven", "order_status_history"],
)
def order_status_history_lag_watcher():

    sense_new_records_written = HttpSensor(
        task_id="sense_new_records_written",
        http_conn_id="prometheus_default",
        endpoint="/api/v1/query",
        request_params={"query": _PROMQL_QUERY},
        response_check=_new_records_detected,
        poke_interval=_poke_interval_seconds,
        timeout=_SENSOR_TIMEOUT_SECONDS,
        soft_fail=True,
        mode="reschedule",
    )

    trigger_marketplace_batch_pipeline = TriggerDagRunOperator(
        task_id="trigger_marketplace_batch_pipeline",
        trigger_dag_id="marketplace_batch_pipeline",
    )

    # Always restarts the watch cycle -- on 'success' (fired) or
    # 'skipped' (benign timeout) alike -- but not on 'failed' (a real
    # error). See module docstring for why this, not "all_done".
    restart_watch_cycle = TriggerDagRunOperator(
        task_id="restart_watch_cycle",
        trigger_dag_id="order_status_history_lag_watcher",
        trigger_rule="none_failed",
    )

    sense_new_records_written >> trigger_marketplace_batch_pipeline
    sense_new_records_written >> restart_watch_cycle


order_status_history_lag_watcher()
