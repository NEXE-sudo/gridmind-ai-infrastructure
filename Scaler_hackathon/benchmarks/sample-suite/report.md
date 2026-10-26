# GridMind scenario suite 1.1.0

- Suite: `gridmind-operations-scenarios`
- Seeds: `1, 2, 3, 4, 5`
- Scenario count: `10`
- Run count: `200`
- Live inference enabled: `False`

All workload, topology, power, energy, and price data are synthetic. A completed run means the simulator reached its fixed horizon without an exception; it does not mean the workload queue drained.
Primary horizons are fixed per scenario version and are not extended for a favored policy. Descriptive bootstrap intervals use matched independent scenario-seed runs; they are omitted below five valid pairs.

## Balanced baseline (`balanced`)

Baseline capacity and deadline trade-offs.

Horizon: 60 steps. Fixed 60-minute primary evaluation window; the staggered arrivals and 18-minute maximum nominal duration leave substantial service margin, but the horizon is not a drain-to-empty guarantee.

| Policy | Run status (complete/failed/incomplete) | Completed / all workloads | Operational failures | Cancelled | Permanently infeasible | Unresolved at horizon | Full-set completion | Feasible completion | Deadline misses / due | Deadline attained | Starved | Node failures / recoveries / requeues / preemptions | Resource / power rejections | Throughput jobs/hour | Queue wait min | Turnaround min | Energy kWh / estimated cost | Paired n vs resource-aware |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fifo | 5/0/0 | 50/50 | 0 | 0 | 0 | 0 | 50/50 (100.0%) | 50/50 (100.0%) | 0/50 (0.0%) | 50/50 (100.0%) | 0 | 4/4/2/0 | 0/0 | 10.0 | 2.32 | 11.66 | 2.820167 / 0.225613 | 5 |
| priority | 5/0/0 | 50/50 | 0 | 0 | 0 | 0 | 50/50 (100.0%) | 50/50 (100.0%) | 0/50 (0.0%) | 50/50 (100.0%) | 0 | 4/4/2/0 | 0/0 | 10.0 | 2.24 | 11.58 | 2.837667 / 0.227013 | 5 |
| resource_aware | 5/0/0 | 50/50 | 0 | 0 | 0 | 0 | 50/50 (100.0%) | 50/50 (100.0%) | 0/50 (0.0%) | 50/50 (100.0%) | 0 | 4/4/2/0 | 0/0 | 10.0 | 2.24 | 11.58 | 2.837667 / 0.227013 | — |
| nemotron | 5/0/0 | 50/50 | 0 | 0 | 0 | 0 | 50/50 (100.0%) | 50/50 (100.0%) | 0/50 (0.0%) | 50/50 (100.0%) | 0 | 4/4/2/0 | 0/0 | 10.0 | 2.24 | 11.58 | 2.837667 / 0.227013 | 5 |

Workload totals in this table pool successful fixed-horizon runs; failed simulation records and their partial state remain available in JSON/CSV. Run-status counts are separate from workload statuses. The full-set completion denominator includes every materialized workload, including infeasible and not-yet-arrived jobs. Feasible completion uses all structurally placeable scenario workloads. Deadline-miss denominator counts deadlines that elapsed or completed late; deadline attainment uses all submitted workloads with deadlines. Post-deadline work remains eligible. Cost is an estimate from the configured synthetic energy rate.

| Policy | Primary unresolved outcome classification (count) |
|---|---|
| fifo | none |
| priority | none |
| resource_aware | none |
| nemotron | none |

| Policy | Last actionable blocker for unresolved workloads (count) |
|---|---|
| fifo | none |
| priority | none |
| resource_aware | none |
| nemotron | none |

| Policy vs resource-aware | Valid paired n | Throughput delta (95% descriptive CI) | Deadline-attainment delta (95% descriptive CI) | Energy delta kWh (95% descriptive CI) |
|---|---:|---|---|---|
| fifo | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | -0.0175 (-0.0525, 0.0) |
| priority | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |
| nemotron | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |

## Burst arrivals (`burst_arrivals`)

Queue contention and burst recovery.

Horizon: 75 steps. Fixed 75-minute primary evaluation window preserves three burst waves and a long post-arrival service window; it measures backlog recovery without extending selectively for any policy.

| Policy | Run status (complete/failed/incomplete) | Completed / all workloads | Operational failures | Cancelled | Permanently infeasible | Unresolved at horizon | Full-set completion | Feasible completion | Deadline misses / due | Deadline attained | Starved | Node failures / recoveries / requeues / preemptions | Resource / power rejections | Throughput jobs/hour | Queue wait min | Turnaround min | Energy kWh / estimated cost | Paired n vs resource-aware |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fifo | 5/0/0 | 90/90 | 0 | 0 | 0 | 0 | 90/90 (100.0%) | 90/90 (100.0%) | 10/90 (11.1%) | 80/90 (88.9%) | 0 | 0/0/0/0 | 0/0 | 14.4 | 9.69998 | 20.25556 | 5.567167 / 0.445373 | 5 |
| priority | 5/0/0 | 90/90 | 0 | 0 | 0 | 0 | 90/90 (100.0%) | 90/90 (100.0%) | 9/90 (10.0%) | 81/90 (90.0%) | 0 | 0/0/0/0 | 0/0 | 14.4 | 9.45556 | 20.0111 | 5.603834 / 0.448306 | 5 |
| resource_aware | 5/0/0 | 90/90 | 0 | 0 | 0 | 0 | 90/90 (100.0%) | 90/90 (100.0%) | 9/90 (10.0%) | 81/90 (90.0%) | 0 | 0/0/0/0 | 0/0 | 14.4 | 9.45556 | 20.0111 | 5.603834 / 0.448306 | — |
| nemotron | 5/0/0 | 90/90 | 0 | 0 | 0 | 0 | 90/90 (100.0%) | 90/90 (100.0%) | 9/90 (10.0%) | 81/90 (90.0%) | 0 | 0/0/0/0 | 0/0 | 14.4 | 9.45556 | 20.0111 | 5.603834 / 0.448306 | 5 |

Workload totals in this table pool successful fixed-horizon runs; failed simulation records and their partial state remain available in JSON/CSV. Run-status counts are separate from workload statuses. The full-set completion denominator includes every materialized workload, including infeasible and not-yet-arrived jobs. Feasible completion uses all structurally placeable scenario workloads. Deadline-miss denominator counts deadlines that elapsed or completed late; deadline attainment uses all submitted workloads with deadlines. Post-deadline work remains eligible. Cost is an estimate from the configured synthetic energy rate.

| Policy | Primary unresolved outcome classification (count) |
|---|---|
| fifo | none |
| priority | none |
| resource_aware | none |
| nemotron | none |

| Policy | Last actionable blocker for unresolved workloads (count) |
|---|---|
| fifo | none |
| priority | none |
| resource_aware | none |
| nemotron | none |

| Policy vs resource-aware | Valid paired n | Throughput delta (95% descriptive CI) | Deadline-attainment delta (95% descriptive CI) | Energy delta kWh (95% descriptive CI) |
|---|---:|---|---|---|
| fifo | 5 | 0.0 (0.0, 0.0) | -0.01112 (-0.0667, 0.0333) | -0.036667 (-0.0668, -0.0065) |
| priority | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |
| nemotron | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |

## Mixed priorities and tight deadlines (`mixed_priority_deadlines`)

Priority ordering versus deadline and throughput trade-offs.

Horizon: 70 steps. Fixed 70-minute primary evaluation window spans the staggered queue and 65-minute maximum nominal deadline; it evaluates deadline outcomes rather than promising that all jobs drain.

| Policy | Run status (complete/failed/incomplete) | Completed / all workloads | Operational failures | Cancelled | Permanently infeasible | Unresolved at horizon | Full-set completion | Feasible completion | Deadline misses / due | Deadline attained | Starved | Node failures / recoveries / requeues / preemptions | Resource / power rejections | Throughput jobs/hour | Queue wait min | Turnaround min | Energy kWh / estimated cost | Paired n vs resource-aware |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fifo | 5/0/0 | 70/70 | 0 | 0 | 0 | 0 | 70/70 (100.0%) | 70/70 (100.0%) | 2/65 (3.1%) | 68/70 (97.1%) | 0 | 0/0/0/0 | 0/0 | 12.0 | 5.85714 | 16.14286 | 4.645667 / 0.371653 | 5 |
| priority | 5/0/0 | 70/70 | 0 | 0 | 0 | 0 | 70/70 (100.0%) | 70/70 (100.0%) | 0/65 (0.0%) | 70/70 (100.0%) | 0 | 0/0/0/0 | 0/0 | 12.0 | 5.88572 | 16.17144 | 4.691 / 0.37528 | 5 |
| resource_aware | 5/0/0 | 70/70 | 0 | 0 | 0 | 0 | 70/70 (100.0%) | 70/70 (100.0%) | 0/65 (0.0%) | 70/70 (100.0%) | 0 | 0/0/0/0 | 0/0 | 12.0 | 5.88572 | 16.17144 | 4.691 / 0.37528 | — |
| nemotron | 5/0/0 | 70/70 | 0 | 0 | 0 | 0 | 70/70 (100.0%) | 70/70 (100.0%) | 0/65 (0.0%) | 70/70 (100.0%) | 0 | 0/0/0/0 | 0/0 | 12.0 | 5.88572 | 16.17144 | 4.691 / 0.37528 | 5 |

Workload totals in this table pool successful fixed-horizon runs; failed simulation records and their partial state remain available in JSON/CSV. Run-status counts are separate from workload statuses. The full-set completion denominator includes every materialized workload, including infeasible and not-yet-arrived jobs. Feasible completion uses all structurally placeable scenario workloads. Deadline-miss denominator counts deadlines that elapsed or completed late; deadline attainment uses all submitted workloads with deadlines. Post-deadline work remains eligible. Cost is an estimate from the configured synthetic energy rate.

| Policy | Primary unresolved outcome classification (count) |
|---|---|
| fifo | none |
| priority | none |
| resource_aware | none |
| nemotron | none |

| Policy | Last actionable blocker for unresolved workloads (count) |
|---|---|
| fifo | none |
| priority | none |
| resource_aware | none |
| nemotron | none |

| Policy vs resource-aware | Valid paired n | Throughput delta (95% descriptive CI) | Deadline-attainment delta (95% descriptive CI) | Energy delta kWh (95% descriptive CI) |
|---|---:|---|---|---|
| fifo | 5 | 0.0 (0.0, 0.0) | -0.02856 (-0.0571, 0.0) | -0.045333 (-0.1303, 0.047) |
| priority | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |
| nemotron | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |

## Heterogeneous GPU requirements (`heterogeneous_gpu_types`)

GPU-type compatibility and capacity-aware placement.

Horizon: 65 steps. Fixed 65-minute primary window exceeds the staggered arrival and maximum nominal service interval; structurally incompatible GPU/memory requests remain visible as infeasible, not as horizon failures.

| Policy | Run status (complete/failed/incomplete) | Completed / all workloads | Operational failures | Cancelled | Permanently infeasible | Unresolved at horizon | Full-set completion | Feasible completion | Deadline misses / due | Deadline attained | Starved | Node failures / recoveries / requeues / preemptions | Resource / power rejections | Throughput jobs/hour | Queue wait min | Turnaround min | Energy kWh / estimated cost | Paired n vs resource-aware |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fifo | 5/0/0 | 40/60 | 0 | 0 | 20 | 0 | 40/60 (66.7%) | 40/40 (100.0%) | 20/60 (33.3%) | 40/60 (66.7%) | 0 | 0/0/0/0 | 0/0 | 7.3846 | 0.375 | 8.375 | 1.841333 / 0.147307 | 5 |
| priority | 5/0/0 | 40/60 | 0 | 0 | 20 | 0 | 40/60 (66.7%) | 40/40 (100.0%) | 20/60 (33.3%) | 40/60 (66.7%) | 0 | 0/0/0/0 | 0/0 | 7.3846 | 0.375 | 8.375 | 1.84 / 0.1472 | 5 |
| resource_aware | 5/0/0 | 40/60 | 0 | 0 | 20 | 0 | 40/60 (66.7%) | 40/40 (100.0%) | 20/60 (33.3%) | 40/60 (66.7%) | 0 | 0/0/0/0 | 0/0 | 7.3846 | 0.375 | 8.375 | 1.84 / 0.1472 | — |
| nemotron | 5/0/0 | 40/60 | 0 | 0 | 20 | 0 | 40/60 (66.7%) | 40/40 (100.0%) | 20/60 (33.3%) | 40/60 (66.7%) | 0 | 0/0/0/0 | 0/0 | 7.3846 | 0.375 | 8.375 | 1.84 / 0.1472 | 5 |

Workload totals in this table pool successful fixed-horizon runs; failed simulation records and their partial state remain available in JSON/CSV. Run-status counts are separate from workload statuses. The full-set completion denominator includes every materialized workload, including infeasible and not-yet-arrived jobs. Feasible completion uses all structurally placeable scenario workloads. Deadline-miss denominator counts deadlines that elapsed or completed late; deadline attainment uses all submitted workloads with deadlines. Post-deadline work remains eligible. Cost is an estimate from the configured synthetic energy rate.

| Policy | Primary unresolved outcome classification (count) |
|---|---|
| fifo | none |
| priority | none |
| resource_aware | none |
| nemotron | none |

| Policy | Last actionable blocker for unresolved workloads (count) |
|---|---|
| fifo | none |
| priority | none |
| resource_aware | none |
| nemotron | none |

| Policy vs resource-aware | Valid paired n | Throughput delta (95% descriptive CI) | Deadline-attainment delta (95% descriptive CI) | Energy delta kWh (95% descriptive CI) |
|---|---:|---|---|---|
| fifo | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.001333 (0.0, 0.004) |
| priority | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |
| nemotron | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |

## GPU memory pressure (`gpu_memory_pressure`)

Memory fragmentation and placement rejection.

Horizon: 65 steps. Fixed 65-minute primary window provides service time beyond the 58-minute maximum nominal deadline while retaining the intentionally skewed memory topology; impossible placements are terminally diagnosed.

| Policy | Run status (complete/failed/incomplete) | Completed / all workloads | Operational failures | Cancelled | Permanently infeasible | Unresolved at horizon | Full-set completion | Feasible completion | Deadline misses / due | Deadline attained | Starved | Node failures / recoveries / requeues / preemptions | Resource / power rejections | Throughput jobs/hour | Queue wait min | Turnaround min | Energy kWh / estimated cost | Paired n vs resource-aware |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fifo | 5/0/0 | 45/70 | 0 | 0 | 20 | 5 | 45/70 (64.3%) | 45/50 (90.0%) | 35/70 (50.0%) | 35/70 (50.0%) | 0 | 0/0/0/0 | 0/0 | 8.3077 | 11.46666 | 19.57776 | 1.934167 / 0.154733 | 5 |
| priority | 5/0/0 | 45/70 | 0 | 0 | 20 | 5 | 45/70 (64.3%) | 45/50 (90.0%) | 35/70 (50.0%) | 35/70 (50.0%) | 0 | 0/0/0/0 | 0/0 | 8.3077 | 11.8222 | 19.93332 | 1.9145 / 0.15316 | 5 |
| resource_aware | 5/0/0 | 45/70 | 0 | 0 | 20 | 5 | 45/70 (64.3%) | 45/50 (90.0%) | 35/70 (50.0%) | 35/70 (50.0%) | 0 | 0/0/0/0 | 0/0 | 8.3077 | 11.8222 | 19.93332 | 1.9145 / 0.15316 | — |
| nemotron | 5/0/0 | 45/70 | 0 | 0 | 20 | 5 | 45/70 (64.3%) | 45/50 (90.0%) | 35/70 (50.0%) | 35/70 (50.0%) | 0 | 0/0/0/0 | 0/0 | 8.3077 | 11.8222 | 19.93332 | 1.9145 / 0.15316 | 5 |

Workload totals in this table pool successful fixed-horizon runs; failed simulation records and their partial state remain available in JSON/CSV. Run-status counts are separate from workload statuses. The full-set completion denominator includes every materialized workload, including infeasible and not-yet-arrived jobs. Feasible completion uses all structurally placeable scenario workloads. Deadline-miss denominator counts deadlines that elapsed or completed late; deadline attainment uses all submitted workloads with deadlines. Post-deadline work remains eligible. Cost is an estimate from the configured synthetic energy rate.

| Policy | Primary unresolved outcome classification (count) |
|---|---|
| fifo | deadline_miss: 5 |
| priority | deadline_miss: 5 |
| resource_aware | deadline_miss: 5 |
| nemotron | deadline_miss: 5 |

| Policy | Last actionable blocker for unresolved workloads (count) |
|---|---|
| fifo | running_work_at_horizon: 5 |
| priority | running_work_at_horizon: 5 |
| resource_aware | running_work_at_horizon: 5 |
| nemotron | running_work_at_horizon: 5 |

| Policy vs resource-aware | Valid paired n | Throughput delta (95% descriptive CI) | Deadline-attainment delta (95% descriptive CI) | Energy delta kWh (95% descriptive CI) |
|---|---:|---|---|---|
| fifo | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.019667 (0.0, 0.059) |
| priority | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |
| nemotron | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |

## Tight facility power budget (`tight_power_budget`)

Facility-wide power-constrained scheduling.

Horizon: 70 steps. Fixed 70-minute primary window includes the 65-minute maximum nominal deadline and leaves time for post-deadline execution; facility power contention is intentionally not removed by extending the horizon.

| Policy | Run status (complete/failed/incomplete) | Completed / all workloads | Operational failures | Cancelled | Permanently infeasible | Unresolved at horizon | Full-set completion | Feasible completion | Deadline misses / due | Deadline attained | Starved | Node failures / recoveries / requeues / preemptions | Resource / power rejections | Throughput jobs/hour | Queue wait min | Turnaround min | Energy kWh / estimated cost | Paired n vs resource-aware |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fifo | 5/0/0 | 55/60 | 0 | 0 | 0 | 5 | 55/60 (91.7%) | 55/60 (91.7%) | 8/55 (14.5%) | 51/60 (85.0%) | 0 | 0/0/0/0 | 0/0 | 9.4286 | 11.81816 | 25.6727 | 3.2566 / 0.260528 | 5 |
| priority | 5/0/0 | 55/60 | 0 | 0 | 0 | 5 | 55/60 (91.7%) | 55/60 (91.7%) | 0/55 (0.0%) | 55/60 (91.7%) | 0 | 0/0/0/0 | 0/0 | 9.4286 | 9.74548 | 23.01818 | 3.2236 / 0.257888 | 5 |
| resource_aware | 5/0/0 | 55/60 | 0 | 0 | 0 | 5 | 55/60 (91.7%) | 55/60 (91.7%) | 0/55 (0.0%) | 55/60 (91.7%) | 0 | 0/0/0/0 | 0/0 | 9.4286 | 9.74548 | 23.01818 | 3.2236 / 0.257888 | — |
| nemotron | 5/0/0 | 55/60 | 0 | 0 | 0 | 5 | 55/60 (91.7%) | 55/60 (91.7%) | 0/55 (0.0%) | 55/60 (91.7%) | 0 | 0/0/0/0 | 0/0 | 9.4286 | 9.74548 | 23.01818 | 3.2236 / 0.257888 | 5 |

Workload totals in this table pool successful fixed-horizon runs; failed simulation records and their partial state remain available in JSON/CSV. Run-status counts are separate from workload statuses. The full-set completion denominator includes every materialized workload, including infeasible and not-yet-arrived jobs. Feasible completion uses all structurally placeable scenario workloads. Deadline-miss denominator counts deadlines that elapsed or completed late; deadline attainment uses all submitted workloads with deadlines. Post-deadline work remains eligible. Cost is an estimate from the configured synthetic energy rate.

| Policy | Primary unresolved outcome classification (count) |
|---|---|
| fifo | deadline_miss: 4, horizon_incomplete: 1 |
| priority | horizon_incomplete: 5 |
| resource_aware | horizon_incomplete: 5 |
| nemotron | horizon_incomplete: 5 |

| Policy | Last actionable blocker for unresolved workloads (count) |
|---|---|
| fifo | running_work_at_horizon: 5 |
| priority | running_work_at_horizon: 5 |
| resource_aware | running_work_at_horizon: 5 |
| nemotron | running_work_at_horizon: 5 |

| Policy vs resource-aware | Valid paired n | Throughput delta (95% descriptive CI) | Deadline-attainment delta (95% descriptive CI) | Energy delta kWh (95% descriptive CI) |
|---|---:|---|---|---|
| fifo | 5 | 0.0 (0.0, 0.0) | -0.06668 (-0.1667, 0.0) | 0.033 (0.0128, 0.057) |
| priority | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |
| nemotron | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |

## Node failure and recovery (`node_failure_recovery`)

Failure handling, recovery, and requeue behaviour.

Horizon: 90 steps. Fixed 90-minute fault-injection window spans the 80-minute maximum nominal deadline and permits repeated three-step recovery cycles; stochastic failures may still leave valid work unresolved.

| Policy | Run status (complete/failed/incomplete) | Completed / all workloads | Operational failures | Cancelled | Permanently infeasible | Unresolved at horizon | Full-set completion | Feasible completion | Deadline misses / due | Deadline attained | Starved | Node failures / recoveries / requeues / preemptions | Resource / power rejections | Throughput jobs/hour | Queue wait min | Turnaround min | Energy kWh / estimated cost | Paired n vs resource-aware |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fifo | 5/0/0 | 48/60 | 6 | 0 | 0 | 6 | 48/60 (80.0%) | 48/60 (80.0%) | 19/60 (31.7%) | 41/60 (68.3%) | 0 | 68/63/51/0 | 0/0 | 6.39998 | 14.42374 | 33.59746 | 6.2302 / 0.498416 | 5 |
| priority | 5/0/0 | 48/60 | 8 | 0 | 0 | 4 | 48/60 (80.0%) | 48/60 (80.0%) | 13/60 (21.7%) | 47/60 (78.3%) | 0 | 68/63/50/0 | 0/0 | 6.4 | 9.2751 | 27.37954 | 5.9127 / 0.473016 | 5 |
| resource_aware | 5/0/0 | 48/60 | 8 | 0 | 0 | 4 | 48/60 (80.0%) | 48/60 (80.0%) | 13/60 (21.7%) | 47/60 (78.3%) | 0 | 68/63/50/0 | 0/0 | 6.4 | 9.2751 | 27.37954 | 5.9127 / 0.473016 | — |
| nemotron | 5/0/0 | 48/60 | 8 | 0 | 0 | 4 | 48/60 (80.0%) | 48/60 (80.0%) | 13/60 (21.7%) | 47/60 (78.3%) | 0 | 68/63/50/0 | 0/0 | 6.4 | 9.2751 | 27.37954 | 5.9127 / 0.473016 | 5 |

Workload totals in this table pool successful fixed-horizon runs; failed simulation records and their partial state remain available in JSON/CSV. Run-status counts are separate from workload statuses. The full-set completion denominator includes every materialized workload, including infeasible and not-yet-arrived jobs. Feasible completion uses all structurally placeable scenario workloads. Deadline-miss denominator counts deadlines that elapsed or completed late; deadline attainment uses all submitted workloads with deadlines. Post-deadline work remains eligible. Cost is an estimate from the configured synthetic energy rate.

| Policy | Primary unresolved outcome classification (count) |
|---|---|
| fifo | deadline_miss: 6 |
| priority | deadline_miss: 4 |
| resource_aware | deadline_miss: 4 |
| nemotron | deadline_miss: 4 |

| Policy | Last actionable blocker for unresolved workloads (count) |
|---|---|
| fifo | node_failure_recovery: 1, running_work_at_horizon: 5 |
| priority | node_failure_recovery: 1, running_work_at_horizon: 3 |
| resource_aware | node_failure_recovery: 1, running_work_at_horizon: 3 |
| nemotron | node_failure_recovery: 1, running_work_at_horizon: 3 |

| Policy vs resource-aware | Valid paired n | Throughput delta (95% descriptive CI) | Deadline-attainment delta (95% descriptive CI) | Energy delta kWh (95% descriptive CI) |
|---|---:|---|---|---|
| fifo | 5 | -2e-05 (-0.6667, 0.5333) | -0.1 (-0.1334, -0.0833) | 0.3175 (-0.0258, 0.6188) |
| priority | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |
| nemotron | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |

## Short jobs versus long-running work (`short_long_contention`)

Queue delay and starvation under mixed service times.

Horizon: 90 steps. Fixed 90-minute contention window exposes the queueing burden of three simultaneous 60-minute, four-GPU jobs on two fitting nodes; the serialized service lower bound exceeds the horizon before later short jobs are included.

| Policy | Run status (complete/failed/incomplete) | Completed / all workloads | Operational failures | Cancelled | Permanently infeasible | Unresolved at horizon | Full-set completion | Feasible completion | Deadline misses / due | Deadline attained | Starved | Node failures / recoveries / requeues / preemptions | Resource / power rejections | Throughput jobs/hour | Queue wait min | Turnaround min | Energy kWh / estimated cost | Paired n vs resource-aware |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fifo | 5/0/0 | 64/80 | 0 | 0 | 0 | 16 | 64/80 (80.0%) | 64/80 (80.0%) | 16/80 (20.0%) | 64/80 (80.0%) | 0 | 0/0/0/0 | 0/0 | 8.53332 | 1.74286 | 13.61192 | 7.419 / 0.59352 | 5 |
| priority | 5/0/0 | 64/80 | 0 | 0 | 0 | 16 | 64/80 (80.0%) | 64/80 (80.0%) | 16/80 (20.0%) | 64/80 (80.0%) | 0 | 0/0/0/0 | 0/0 | 8.53336 | 2.3051 | 13.48462 | 6.664667 / 0.533173 | 5 |
| resource_aware | 5/0/0 | 64/80 | 0 | 0 | 0 | 16 | 64/80 (80.0%) | 64/80 (80.0%) | 16/80 (20.0%) | 64/80 (80.0%) | 0 | 0/0/0/0 | 0/0 | 8.53336 | 2.3051 | 13.48462 | 6.664667 / 0.533173 | — |
| nemotron | 5/0/0 | 64/80 | 0 | 0 | 0 | 16 | 64/80 (80.0%) | 64/80 (80.0%) | 16/80 (20.0%) | 64/80 (80.0%) | 0 | 0/0/0/0 | 0/0 | 8.53336 | 2.3051 | 13.48462 | 6.664667 / 0.533173 | 5 |

Workload totals in this table pool successful fixed-horizon runs; failed simulation records and their partial state remain available in JSON/CSV. Run-status counts are separate from workload statuses. The full-set completion denominator includes every materialized workload, including infeasible and not-yet-arrived jobs. Feasible completion uses all structurally placeable scenario workloads. Deadline-miss denominator counts deadlines that elapsed or completed late; deadline attainment uses all submitted workloads with deadlines. Post-deadline work remains eligible. Cost is an estimate from the configured synthetic energy rate.

| Policy | Primary unresolved outcome classification (count) |
|---|---|
| fifo | deadline_miss: 16 |
| priority | deadline_miss: 16 |
| resource_aware | deadline_miss: 16 |
| nemotron | deadline_miss: 16 |

| Policy | Last actionable blocker for unresolved workloads (count) |
|---|---|
| fifo | running_work_at_horizon: 12, temporary_capacity_contention: 4 |
| priority | running_work_at_horizon: 11, temporary_capacity_contention: 5 |
| resource_aware | running_work_at_horizon: 11, temporary_capacity_contention: 5 |
| nemotron | running_work_at_horizon: 11, temporary_capacity_contention: 5 |

| Policy vs resource-aware | Valid paired n | Throughput delta (95% descriptive CI) | Deadline-attainment delta (95% descriptive CI) | Energy delta kWh (95% descriptive CI) |
|---|---:|---|---|---|
| fifo | 5 | -4e-05 (-0.5334, 0.5333) | 0.0 (-0.05, 0.05) | 0.754333 (0.2107, 1.2981) |
| priority | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |
| nemotron | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |

## Infeasible workloads (`infeasible_workloads`)

Explicit detection of impossible GPU and memory requests without unsafe placement.

Horizon: 45 steps. Fixed 45-minute primary window is designed to evaluate the feasible portion of the mixed queue; 12-GPU/512-GB requests exceed every node envelope and are reported as permanent infeasibilities.

| Policy | Run status (complete/failed/incomplete) | Completed / all workloads | Operational failures | Cancelled | Permanently infeasible | Unresolved at horizon | Full-set completion | Feasible completion | Deadline misses / due | Deadline attained | Starved | Node failures / recoveries / requeues / preemptions | Resource / power rejections | Throughput jobs/hour | Queue wait min | Turnaround min | Energy kWh / estimated cost | Paired n vs resource-aware |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fifo | 5/0/0 | 35/50 | 0 | 0 | 15 | 0 | 35/50 (70.0%) | 35/35 (100.0%) | 13/48 (27.1%) | 35/50 (70.0%) | 0 | 0/0/0/0 | 0/0 | 9.3333 | 0.31428 | 6.8857 | 1.098333 / 0.087867 | 5 |
| priority | 5/0/0 | 35/50 | 0 | 0 | 15 | 0 | 35/50 (70.0%) | 35/35 (100.0%) | 13/48 (27.1%) | 35/50 (70.0%) | 0 | 0/0/0/0 | 0/0 | 9.3333 | 0.51428 | 7.08572 | 1.118333 / 0.089467 | 5 |
| resource_aware | 5/0/0 | 35/50 | 0 | 0 | 15 | 0 | 35/50 (70.0%) | 35/35 (100.0%) | 13/48 (27.1%) | 35/50 (70.0%) | 0 | 0/0/0/0 | 0/0 | 9.3333 | 0.51428 | 7.08572 | 1.118333 / 0.089467 | — |
| nemotron | 5/0/0 | 35/50 | 0 | 0 | 15 | 0 | 35/50 (70.0%) | 35/35 (100.0%) | 13/48 (27.1%) | 35/50 (70.0%) | 0 | 0/0/0/0 | 0/0 | 9.3333 | 0.51428 | 7.08572 | 1.118333 / 0.089467 | 5 |

Workload totals in this table pool successful fixed-horizon runs; failed simulation records and their partial state remain available in JSON/CSV. Run-status counts are separate from workload statuses. The full-set completion denominator includes every materialized workload, including infeasible and not-yet-arrived jobs. Feasible completion uses all structurally placeable scenario workloads. Deadline-miss denominator counts deadlines that elapsed or completed late; deadline attainment uses all submitted workloads with deadlines. Post-deadline work remains eligible. Cost is an estimate from the configured synthetic energy rate.

| Policy | Primary unresolved outcome classification (count) |
|---|---|
| fifo | none |
| priority | none |
| resource_aware | none |
| nemotron | none |

| Policy | Last actionable blocker for unresolved workloads (count) |
|---|---|
| fifo | none |
| priority | none |
| resource_aware | none |
| nemotron | none |

| Policy vs resource-aware | Valid paired n | Throughput delta (95% descriptive CI) | Deadline-attainment delta (95% descriptive CI) | Energy delta kWh (95% descriptive CI) |
|---|---:|---|---|---|
| fifo | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | -0.02 (-0.03, -0.01) |
| priority | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |
| nemotron | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |

## Combined operational stress (`combined_stress`)

Compound constraints and policy trade-offs under shared exogenous failures.

Horizon: 90 steps. Fixed 90-minute compound-stress window spans the 80-minute maximum nominal deadline while keeping bursts, power limits, model constraints, and seeded failures active; it is not extended to force queue drain.

| Policy | Run status (complete/failed/incomplete) | Completed / all workloads | Operational failures | Cancelled | Permanently infeasible | Unresolved at horizon | Full-set completion | Feasible completion | Deadline misses / due | Deadline attained | Starved | Node failures / recoveries / requeues / preemptions | Resource / power rejections | Throughput jobs/hour | Queue wait min | Turnaround min | Energy kWh / estimated cost | Paired n vs resource-aware |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fifo | 5/0/0 | 64/90 | 2 | 0 | 0 | 24 | 64/90 (71.1%) | 64/90 (71.1%) | 48/90 (53.3%) | 42/90 (46.7%) | 0 | 30/28/32/0 | 0/0 | 8.53334 | 14.48934 | 28.82892 | 4.3699 / 0.349592 | 5 |
| priority | 5/0/0 | 70/90 | 2 | 0 | 0 | 18 | 70/90 (77.8%) | 70/90 (77.8%) | 36/90 (40.0%) | 54/90 (60.0%) | 0 | 30/28/29/0 | 0/0 | 9.33332 | 13.32512 | 26.06546 | 4.0891 / 0.327128 | 5 |
| resource_aware | 5/0/0 | 70/90 | 2 | 0 | 0 | 18 | 70/90 (77.8%) | 70/90 (77.8%) | 36/90 (40.0%) | 54/90 (60.0%) | 0 | 30/28/29/0 | 0/0 | 9.33332 | 13.32512 | 26.06546 | 4.0891 / 0.327128 | — |
| nemotron | 5/0/0 | 70/90 | 2 | 0 | 0 | 18 | 70/90 (77.8%) | 70/90 (77.8%) | 36/90 (40.0%) | 54/90 (60.0%) | 0 | 30/28/29/0 | 0/0 | 9.33332 | 13.32512 | 26.06546 | 4.0891 / 0.327128 | 5 |

Workload totals in this table pool successful fixed-horizon runs; failed simulation records and their partial state remain available in JSON/CSV. Run-status counts are separate from workload statuses. The full-set completion denominator includes every materialized workload, including infeasible and not-yet-arrived jobs. Feasible completion uses all structurally placeable scenario workloads. Deadline-miss denominator counts deadlines that elapsed or completed late; deadline attainment uses all submitted workloads with deadlines. Post-deadline work remains eligible. Cost is an estimate from the configured synthetic energy rate.

| Policy | Primary unresolved outcome classification (count) |
|---|---|
| fifo | deadline_miss: 24 |
| priority | deadline_miss: 18 |
| resource_aware | deadline_miss: 18 |
| nemotron | deadline_miss: 18 |

| Policy | Last actionable blocker for unresolved workloads (count) |
|---|---|
| fifo | node_failure_recovery: 2, power_constrained_waiting: 4, running_work_at_horizon: 6, same_decision_reservation_contention: 2, temporary_capacity_contention: 10 |
| priority | node_failure_recovery: 1, power_constrained_waiting: 3, running_work_at_horizon: 5, same_decision_reservation_contention: 2, temporary_capacity_contention: 7 |
| resource_aware | node_failure_recovery: 1, power_constrained_waiting: 3, running_work_at_horizon: 5, same_decision_reservation_contention: 2, temporary_capacity_contention: 7 |
| nemotron | node_failure_recovery: 1, power_constrained_waiting: 3, running_work_at_horizon: 5, same_decision_reservation_contention: 2, temporary_capacity_contention: 7 |

| Policy vs resource-aware | Valid paired n | Throughput delta (95% descriptive CI) | Deadline-attainment delta (95% descriptive CI) | Energy delta kWh (95% descriptive CI) |
|---|---:|---|---|---|
| fifo | 5 | -0.79998 (-1.2, -0.4) | -0.13334 (-0.2667, -0.0111) | 0.2808 (0.0576, 0.5416) |
| priority | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |
| nemotron | 5 | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) | 0.0 (0.0, 0.0) |

## Limitations

- All workload, topology, power, failure, and price values are synthetic.
- Each policy is paired by seed and scenario hash and executes the entire fixed horizon; recorded exogenous node-failure traces must match.
- Uncertainty is summarized over scenario-seed run pairs, not jobs or simulation ticks.
- Offline Nemotron is deterministic resource-aware fallback, not live model inference.
- Scenario aggregates should not be combined into one ranking because scenarios differ.
- Execution status describes whether the simulation reached its horizon without an exception; it does not imply every workload completed.
