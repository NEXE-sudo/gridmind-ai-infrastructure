# GridMind experiment report

- Created: `2026-10-26T14:53:16.742161+00:00`
- Seeds: `1, 2, 3`
- Scenario: `GridMind mixed inference and training demo`
- Live model enabled: `False`
- Model ID: `not used`

## All-run policy summaries

| Policy | Runs | Completed | Failed | Incomplete | Throughput jobs/hour | SLA attainment | Deadline miss rate | Energy kWh | Cost estimate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fifo | 3 | 3 | 0 | 0 | 16.380967 | 1.0 | 0.0 | 1.655333 | 0.132427 |
| priority | 3 | 3 | 0 | 0 | 16.487167 | 1.0 | 0.0 | 1.671444 | 0.133716 |
| resource_aware | 3 | 3 | 0 | 0 | 16.487167 | 1.0 | 0.0 | 1.671444 | 0.133716 |
| nemotron | 3 | 3 | 0 | 0 | 16.487167 | 1.0 | 0.0 | 1.671444 | 0.133716 |

Power, energy, and cost are synthetic estimates. Cost uses the scenario's configured energy rate, not a cloud bill. The aggregation includes partial metrics from failed/incomplete records; status counts are reported separately.

## Paired comparison against resource-aware

Only seed pairs where both policy runs completed are used in this paired table. Excluded runs remain visible in the all-run summaries above.

| Policy | Paired seeds | Throughput delta | SLA delta | Deadline miss-rate delta | Energy delta kWh |
|---|---:|---:|---:|---:|---:|
| fifo | 3 | -0.1062 | 0.0 | 0.0 | -0.016111 |
| priority | 3 | 0.0 | 0.0 | 0.0 | 0.0 |
| nemotron | 3 | 0.0 | 0.0 | 0.0 | 0.0 |

## Limitations

- Synthetic one-minute simulation; power and energy are not facility telemetry.
- Results are scenario- and seed-specific; small samples are not statistically conclusive.
- Offline Nemotron policy records fallback execution, not model inference.
- Model-generated explanations are rationales, not causal proof.
