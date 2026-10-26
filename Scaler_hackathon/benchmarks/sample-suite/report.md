# GridMind scenario suite 1.0.0

- Suite: `gridmind-operations-scenarios`
- Seeds: `1, 2, 3, 4, 5`
- Scenario count: `10`
- Run count: `200`
- Live inference enabled: `False`

All energy and cost figures are synthetic; policies are paired by seed and scenario hash.
Intervals are descriptive bootstrap summaries over independent scenario-seed runs, not jobs or ticks.

## Balanced baseline (`balanced`)

Baseline capacity and deadline trade-offs.

| Policy | Runs | Completed | Failed | Incomplete | Throughput jobs/hour | SLA attainment | Energy kWh |
|---|---:|---:|---:|---:|---:|---:|---:|
| fifo | 5 | 5 | 0 | 0 | 15.42834 | 1.0 | 2.645833 |
| priority | 5 | 5 | 0 | 0 | 15.83486 | 1.0 | 2.655 |
| resource_aware | 5 | 5 | 0 | 0 | 15.83486 | 1.0 | 2.655 |
| nemotron | 5 | 5 | 0 | 0 | 15.83486 | 1.0 | 2.655 |

Paired mean deltas use only successfully completed matching seed/hash pairs; failed and incomplete runs are listed above and retained in JSON/CSV.

| Policy vs resource-aware | Paired n | Throughput delta (95% CI) | SLA delta (95% CI) | Energy delta kWh (95% CI) |
|---|---:|---|---|---|
| fifo | 5 | -0.40652 (-1.2196, 0.0) | 0.0 (0.0, 0.0) | -0.009167 (-0.0275, 0.0) |
| priority | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |
| nemotron | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |

## Burst arrivals (`burst_arrivals`)

Queue contention and burst recovery.

| Policy | Runs | Completed | Failed | Incomplete | Throughput jobs/hour | SLA attainment | Energy kWh |
|---|---:|---:|---:|---:|---:|---:|---:|
| fifo | 5 | 5 | 0 | 0 | 15.10072 | 0.88888 | 5.5405 |
| priority | 5 | 5 | 0 | 0 | 14.85616 | 0.9 | 5.5855 |
| resource_aware | 5 | 5 | 0 | 0 | 14.85616 | 0.9 | 5.5855 |
| nemotron | 5 | 5 | 0 | 0 | 14.85616 | 0.9 | 5.5855 |

Paired mean deltas use only successfully completed matching seed/hash pairs; failed and incomplete runs are listed above and retained in JSON/CSV.

| Policy vs resource-aware | Paired n | Throughput delta (95% CI) | SLA delta (95% CI) | Energy delta kWh (95% CI) |
|---|---:|---|---|---|
| fifo | 5 | 0.24456 (-0.5456, 0.99) | -0.01112 (-0.0667, 0.0333) | -0.045 (-0.0865, -0.0117) |
| priority | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |
| nemotron | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |

## Mixed priorities and tight deadlines (`mixed_priority_deadlines`)

Priority ordering versus deadline and throughput trade-offs.

| Policy | Runs | Completed | Failed | Incomplete | Throughput jobs/hour | SLA attainment | Energy kWh |
|---|---:|---:|---:|---:|---:|---:|---:|
| fifo | 5 | 5 | 0 | 0 | 13.3915 | 0.97144 | 4.587333 |
| priority | 5 | 5 | 0 | 0 | 12.92752 | 1.0 | 4.651 |
| resource_aware | 5 | 5 | 0 | 0 | 12.92752 | 1.0 | 4.651 |
| nemotron | 5 | 5 | 0 | 0 | 12.92752 | 1.0 | 4.651 |

Paired mean deltas use only successfully completed matching seed/hash pairs; failed and incomplete runs are listed above and retained in JSON/CSV.

| Policy vs resource-aware | Paired n | Throughput delta (95% CI) | SLA delta (95% CI) | Energy delta kWh (95% CI) |
|---|---:|---|---|---|
| fifo | 5 | 0.46398 (-0.7022, 1.667) | -0.02856 (-0.0571, 0.0) | -0.063667 (-0.1903, 0.0743) |
| priority | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |
| nemotron | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |

## Heterogeneous GPU requirements (`heterogeneous_gpu_types`)

GPU-type compatibility and capacity-aware placement.

| Policy | Runs | Completed | Failed | Incomplete | Throughput jobs/hour | SLA attainment | Energy kWh |
|---|---:|---:|---:|---:|---:|---:|---:|
| fifo | 5 | 0 | 0 | 5 | 7.3846 | 0.6667 | 1.841333 |
| priority | 5 | 0 | 0 | 5 | 7.3846 | 0.6667 | 1.84 |
| resource_aware | 5 | 0 | 0 | 5 | 7.3846 | 0.6667 | 1.84 |
| nemotron | 5 | 0 | 0 | 5 | 7.3846 | 0.6667 | 1.84 |

Paired mean deltas use only successfully completed matching seed/hash pairs; failed and incomplete runs are listed above and retained in JSON/CSV.

| Policy vs resource-aware | Paired n | Throughput delta (95% CI) | SLA delta (95% CI) | Energy delta kWh (95% CI) |
|---|---:|---|---|---|
| fifo | 0 | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) |
| priority | 0 | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) |
| nemotron | 0 | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) |

## GPU memory pressure (`gpu_memory_pressure`)

Memory fragmentation and placement rejection.

| Policy | Runs | Completed | Failed | Incomplete | Throughput jobs/hour | SLA attainment | Energy kWh |
|---|---:|---:|---:|---:|---:|---:|---:|
| fifo | 5 | 0 | 0 | 5 | 8.3077 | 0.5 | 1.934167 |
| priority | 5 | 0 | 0 | 5 | 8.3077 | 0.5 | 1.9145 |
| resource_aware | 5 | 0 | 0 | 5 | 8.3077 | 0.5 | 1.9145 |
| nemotron | 5 | 0 | 0 | 5 | 8.3077 | 0.5 | 1.9145 |

Paired mean deltas use only successfully completed matching seed/hash pairs; failed and incomplete runs are listed above and retained in JSON/CSV.

| Policy vs resource-aware | Paired n | Throughput delta (95% CI) | SLA delta (95% CI) | Energy delta kWh (95% CI) |
|---|---:|---|---|---|
| fifo | 0 | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) |
| priority | 0 | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) |
| nemotron | 0 | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) |

## Tight facility power budget (`tight_power_budget`)

Facility-wide power-constrained scheduling.

| Policy | Runs | Completed | Failed | Incomplete | Throughput jobs/hour | SLA attainment | Energy kWh |
|---|---:|---:|---:|---:|---:|---:|---:|
| fifo | 5 | 0 | 0 | 5 | 9.4286 | 0.85002 | 3.2566 |
| priority | 5 | 0 | 0 | 5 | 9.4286 | 0.9167 | 3.2236 |
| resource_aware | 5 | 0 | 0 | 5 | 9.4286 | 0.9167 | 3.2236 |
| nemotron | 5 | 0 | 0 | 5 | 9.4286 | 0.9167 | 3.2236 |

Paired mean deltas use only successfully completed matching seed/hash pairs; failed and incomplete runs are listed above and retained in JSON/CSV.

| Policy vs resource-aware | Paired n | Throughput delta (95% CI) | SLA delta (95% CI) | Energy delta kWh (95% CI) |
|---|---:|---|---|---|
| fifo | 0 | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) |
| priority | 0 | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) |
| nemotron | 0 | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) |

## Node failure and recovery (`node_failure_recovery`)

Failure handling, recovery, and requeue behaviour.

| Policy | Runs | Completed | Failed | Incomplete | Throughput jobs/hour | SLA attainment | Energy kWh |
|---|---:|---:|---:|---:|---:|---:|---:|
| fifo | 5 | 1 | 0 | 4 | 6.13332 | 0.6 | 6.002867 |
| priority | 5 | 1 | 0 | 4 | 6.4 | 0.75 | 5.651367 |
| resource_aware | 5 | 1 | 0 | 4 | 6.4 | 0.75 | 5.651367 |
| nemotron | 5 | 1 | 0 | 4 | 6.4 | 0.75 | 5.651367 |

Paired mean deltas use only successfully completed matching seed/hash pairs; failed and incomplete runs are listed above and retained in JSON/CSV.

| Policy vs resource-aware | Paired n | Throughput delta (95% CI) | SLA delta (95% CI) | Energy delta kWh (95% CI) |
|---|---:|---|---|---|
| fifo | 1 | 0.0 (CI unavailable: insufficient_independent_runs) | 0.0 (CI unavailable: insufficient_independent_runs) | 0.0 (CI unavailable: insufficient_independent_runs) |
| priority | 1 | 0.0 (CI unavailable: insufficient_independent_runs) | 0.0 (CI unavailable: insufficient_independent_runs) | 0.0 (CI unavailable: insufficient_independent_runs) |
| nemotron | 1 | 0.0 (CI unavailable: insufficient_independent_runs) | 0.0 (CI unavailable: insufficient_independent_runs) | 0.0 (CI unavailable: insufficient_independent_runs) |

## Short jobs versus long-running work (`short_long_contention`)

Queue delay and starvation under mixed service times.

| Policy | Runs | Completed | Failed | Incomplete | Throughput jobs/hour | SLA attainment | Energy kWh |
|---|---:|---:|---:|---:|---:|---:|---:|
| fifo | 5 | 0 | 0 | 5 | 8.53332 | 0.8 | 7.419 |
| priority | 5 | 0 | 0 | 5 | 8.53336 | 0.8 | 6.664667 |
| resource_aware | 5 | 0 | 0 | 5 | 8.53336 | 0.8 | 6.664667 |
| nemotron | 5 | 0 | 0 | 5 | 8.53336 | 0.8 | 6.664667 |

Paired mean deltas use only successfully completed matching seed/hash pairs; failed and incomplete runs are listed above and retained in JSON/CSV.

| Policy vs resource-aware | Paired n | Throughput delta (95% CI) | SLA delta (95% CI) | Energy delta kWh (95% CI) |
|---|---:|---|---|---|
| fifo | 0 | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) |
| priority | 0 | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) |
| nemotron | 0 | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) |

## Infeasible workloads (`infeasible_workloads`)

Explicit detection of impossible GPU and memory requests without unsafe placement.

| Policy | Runs | Completed | Failed | Incomplete | Throughput jobs/hour | SLA attainment | Energy kWh |
|---|---:|---:|---:|---:|---:|---:|---:|
| fifo | 5 | 0 | 0 | 5 | 9.3333 | 0.7 | 1.098333 |
| priority | 5 | 0 | 0 | 5 | 9.3333 | 0.7 | 1.118333 |
| resource_aware | 5 | 0 | 0 | 5 | 9.3333 | 0.7 | 1.118333 |
| nemotron | 5 | 0 | 0 | 5 | 9.3333 | 0.7 | 1.118333 |

Paired mean deltas use only successfully completed matching seed/hash pairs; failed and incomplete runs are listed above and retained in JSON/CSV.

| Policy vs resource-aware | Paired n | Throughput delta (95% CI) | SLA delta (95% CI) | Energy delta kWh (95% CI) |
|---|---:|---|---|---|
| fifo | 0 | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) |
| priority | 0 | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) |
| nemotron | 0 | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) |

## Combined operational stress (`combined_stress`)

Compound constraints and policy trade-offs under shared exogenous failures.

| Policy | Runs | Completed | Failed | Incomplete | Throughput jobs/hour | SLA attainment | Energy kWh |
|---|---:|---:|---:|---:|---:|---:|---:|
| fifo | 5 | 0 | 0 | 5 | 8.53332 | 0.45556 | 4.2441 |
| priority | 5 | 0 | 0 | 5 | 9.06666 | 0.56666 | 3.9427 |
| resource_aware | 5 | 0 | 0 | 5 | 9.06666 | 0.56666 | 3.9427 |
| nemotron | 5 | 0 | 0 | 5 | 9.06666 | 0.56666 | 3.9427 |

Paired mean deltas use only successfully completed matching seed/hash pairs; failed and incomplete runs are listed above and retained in JSON/CSV.

| Policy vs resource-aware | Paired n | Throughput delta (95% CI) | SLA delta (95% CI) | Energy delta kWh (95% CI) |
|---|---:|---|---|---|
| fifo | 0 | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) |
| priority | 0 | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) |
| nemotron | 0 | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) | None (CI unavailable: insufficient_independent_runs) |

## Limitations

- All workload, topology, power, failure, and price values are synthetic.
- Each policy is paired by scenario hash and seed; failure traces are exogenous and seeded.
- Uncertainty is summarized over scenario-seed run pairs, not jobs or simulation ticks.
- Offline Nemotron is deterministic resource-aware fallback, not live model inference.
- Scenario aggregates should not be combined into one ranking because scenarios differ.
