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

HttpSensor(deferrable=True): the wait happens in the triggerer process
(this project already runs a dedicated airflow-triggerer container,
unused by any other DAG until this one) instead of holding a worker
slot for up to 23h -- negligible cost regardless of how the interval
above is tuned later.

schedule=timedelta(days=1) + timeout=23h + soft_fail=True: not a
literal "poke forever in one DagRun" -- each day's DagRun watches for
up to 23h, and either the transition fires (downstream task runs) or
it times out softly (not a failure, nothing happened that day) before
the next day's scheduled run starts a fresh watch. Avoids one DagRun
that in principle never ends, while still checking continuously in
practice. max_active_runs=1 keeps a new day's run from starting before
the previous one has actually finished (fired or timed out).

TriggerDagRunOperator's default wait_for_completion=False is
deliberately left as-is: this task's job is to fire
marketplace_batch_pipeline, not babysit it -- the pipeline's own tasks
already verify their own success (see that DAG's docstring).

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
        deferrable=True,
    )

    trigger_marketplace_batch_pipeline = TriggerDagRunOperator(
        task_id="trigger_marketplace_batch_pipeline",
        trigger_dag_id="marketplace_batch_pipeline",
    )

    sense_new_records_written >> trigger_marketplace_batch_pipeline


order_status_history_lag_watcher()
