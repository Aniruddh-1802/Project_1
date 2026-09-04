# DE4 — Batch vs Streaming Decision Workshop

For each scenario: source, arrival pattern, required latency, decision, and why.

## 1. Daily usage summary
- **Source:** `sms-call-internet-mi-YYYY-MM-DD.csv`, one file per day.
- **Arrival pattern:** batch, once every 24 hours, in `data/landing/`.
- **Required latency:** hours — the summary is consumed the next business day.
- **Decision: BATCH.** The source itself is a daily file drop; there is no per-event data to stream. Airflow triggered once per arrival is the natural fit.

## 2. Hypothetical live activity events
- **Source:** per-cell-tower event stream (not present in this training dataset).
- **Arrival pattern:** continuous, sub-second events.
- **Required latency:** seconds, if it existed — an operator watching a live dashboard needs current state, not yesterday's file.
- **Decision: STREAMING, conceptually only.** This dataset does not contain live events, so nothing is built for it. See §2 below for where Kafka would enter if it did exist.

## 3. Billing report
- **Source:** aggregated usage over a billing period (derived from the same daily activity data).
- **Arrival pattern:** batch, monthly.
- **Required latency:** days — billing runs on a fixed cycle, not on demand.
- **Decision: BATCH.** A monthly cycle has no latency pressure; recomputing from the warehouse fact table on a schedule is simpler and more auditable than a streaming aggregate.

## 4. Hotspot alerts
- **Source:** `hourly_grid_summary`, scanned for activity spikes (`spark/alert_generator.py`).
- **Arrival pattern:** currently batch, evaluated after each DE3 run (per file, i.e., daily).
- **Required latency:** ideally minutes, so operators can react to genuine spikes while they're happening.
- **Decision: BATCH today, candidate for STREAMING later.** With daily-file arrival, alerts can only ever be as fresh as the last batch. If sub-hour event data existed, this is the first candidate to move to streaming — it is the scenario where latency has real operational cost (a live network issue, not a historical one).

## 5. Executive dashboard refresh
- **Source:** warehouse tables (`dim_grid`, `dim_time`, `fact_network_activity`) and `analytics/dashboard_summary`.
- **Arrival pattern:** batch, refreshed after each successful pipeline run.
- **Required latency:** hours — an executive dashboard reviewed once or twice a day does not need sub-minute freshness.
- **Decision: BATCH.** Freshness requirement is low and the data underneath it (daily files) is already batch; a streaming refresh here would add complexity with no latency benefit.

## 6. Model training and scoring
- **Source:** warehouse / analytics layer, accumulated history.
- **Arrival pattern:** training is a scheduled batch job over historical data; scoring could run per new day of data.
- **Required latency:** training — none (offline); scoring — hours is acceptable given the source data is daily.
- **Decision: BATCH for both.** Training needs the full accumulated history, which is inherently batch. Scoring inherits the daily cadence of its input, so there is no latency reason to score more often than new data arrives.

## Where Kafka would conceptually enter

Without changing this training dataset, Kafka has no real entry point — every source here is a daily file. If the hypothetical live activity events in scenario 2 existed, Kafka would sit between the event source and a streaming consumer that writes micro-batches into `data/raw/` (or a parallel `data/streaming_raw/`), so DE3's Spark job could keep reading from one consistent zone regardless of how data arrived. Hotspot alerting (scenario 4) is the first workload that would actually benefit from that change, because it is the only one where minutes of latency have an operational cost.

## Summary table

| Scenario | Source | Arrival | Latency need | Decision |
|---|---|---|---|---|
| Daily usage summary | Daily CSV | Batch (daily) | Hours | Batch |
| Live activity events (hypothetical) | Event stream | Continuous | Seconds | Streaming (not built — no such source exists here) |
| Billing report | Warehouse | Batch (monthly) | Days | Batch |
| Hotspot alerts | `hourly_grid_summary` | Batch (daily) | Minutes (ideal) | Batch now; streaming candidate if event data existed |
| Executive dashboard | Warehouse | Batch (per run) | Hours | Batch |
| Model training / scoring | Warehouse / analytics | Batch | None / hours | Batch |
