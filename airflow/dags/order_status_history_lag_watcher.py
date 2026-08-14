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

**Update, 2026-08-14, real incident: this DAG fired
marketplace_batch_pipeline 188 times in 30 minutes**, 2 of which
reached real Databricks compute (see docs/architecture/
roadmap-next-steps.md for the full incident record). Root cause: the
original design below (increase() over a rolling window) has no
memory of what it already fired on -- restart_watch_cycle creates a
new cycle the instant the current one ends, and if the same real
signal is still inside the new cycle's window (trivially true right
after firing, since the window is 2x poke_interval), every new cycle
re-detects it as "new" and fires again, immediately, forever until
the window ages past the original write. Replaced with a value
watermark (see _new_records_detected below) -- the rest of this
docstring's reasoning about the counter itself (why this metric, not
the Gauge) still holds and is kept as-is; the window/increase()
reasoning that followed it is gone along with the code it justified.

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

(No window anymore, per the 2026-08-14 update above -- the watermark
comparison in _new_records_detected is time-independent: it doesn't
matter how long since the last poke, only whether the counter's raw
value has changed since the last time this DAG consumed it.)

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
_LAST_CONSUMED_VARIABLE = "order_status_history_lag_watcher_last_consumed_count"
_DEFAULT_POKE_INTERVAL_SECONDS = 3600  # 1h

_poke_interval_seconds = int(
    Variable.get(
        _POKE_INTERVAL_VARIABLE,
        default_var=_DEFAULT_POKE_INTERVAL_SECONDS,
    )
)

# Raw instant value, not increase() over a window -- the watermark
# comparison in _new_records_detected is what decides "new", not the
# query itself. See module docstring, 2026-08-14 update.
_PROMQL_QUERY = 'mdp_bronze_records_written_total{entity="order_status_history"}'

_SENSOR_TIMEOUT_SECONDS = int(timedelta(hours=23).total_seconds())


def _new_records_detected(response: Response) -> bool:
    """
    True when the counter's current raw value differs from the last
    value this DAG consumed (Variable _LAST_CONSUMED_VARIABLE,
    default "0"). != rather than > on purpose: an increase means real
    new writes; a decrease means the counter reset (bronze-consumer
    restarted -- it's an in-memory prometheus_client Counter, no
    persistence). Can't tell how much of a post-reset value is
    genuinely new vs. already-seen, so the conservative choice is to
    fire again rather than go silent forever waiting for the value to
    climb back past a now-meaningless old watermark.

    Side effect on True: updates the watermark to the current value,
    right here -- this is the moment "new signal" was actually
    observed, not a downstream task's success (see
    docs/architecture/roadmap-next-steps.md's 2026-08-14 incident
    entry for why increase()-over-a-window had no equivalent of this
    and re-fired on the same already-consumed signal indefinitely).
    """

    payload = response.json()
    results = payload.get("data", {}).get("result", [])

    if not results:
        return False  # metric doesn't exist yet -- nothing ever written

    current_value = float(results[0]["value"][1])
    last_consumed = float(Variable.get(_LAST_CONSUMED_VARIABLE, default_var="0"))

    if current_value == last_consumed:
        return False

    Variable.set(_LAST_CONSUMED_VARIABLE, str(current_value))
    return True


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
