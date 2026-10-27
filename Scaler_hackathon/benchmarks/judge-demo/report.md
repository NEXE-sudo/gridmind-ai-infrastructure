# GridMind focused demo: node failure and recovery

Generated from a fresh offline simulator execution by `python -m server.judge_demo`.
All power, energy, workloads, and failures are synthetic. This one-seed demonstration is descriptive, not a statistically supported policy ranking.

## Reproduction and provenance

- Scenario: `node_failure_recovery` (`Node failure and recovery`)
- Seed: `7`; fixed horizon: `90` one-minute steps
- Scenario suite: `gridmind-operations-scenarios@1.1.0`
- Materialized workload hash: `7493efa9cd0de8c69ec4af2d751e77930611e9dbd46082dfae50b87a2949bb0f`
- Shared failure-trace hash: `58d4da2fbb1af547264dc64b31c02a2910ccf6a4a480f951939890c6ab39620a`
- Manifest hash: `d3caf6448c90ab18582a17475a467380ac92c8830d3d04e18c16da7d05350002`
- Live inference: **not attempted**. The Nemotron row uses deterministic resource-aware fallback.

## Initial state

| Node | GPU model | GPUs | Memory (GB) | Node power limit (kW) |
|---|---|---:|---:|---:|
| gpu-a100 | NVIDIA A100 | 4 | 80 | 3.5 |
| gpu-l40s | NVIDIA L40S | 4 | 48 | 3.0 |
| gpu-t4 | NVIDIA T4 | 2 | 24 | 1.8 |

Facility power budget: **7.8 kW**; per-step node-failure probability: **16%**; node recovery delay: **3 steps**.

| Workload | Arrival step | Priority | GPUs | Memory (GB) | Duration (steps) | Deadline step |
|---|---:|---:|---:|---:|---:|---:|
| node_failure_recovery-001 | 1 | 4 | 1 | 12 | 8 | 31 |
| node_failure_recovery-002 | 1 | 3 | 2 | 40 | 18 | 56 |
| node_failure_recovery-003 | 3 | 2 | 4 | 44 | 28 | 83 |
| node_failure_recovery-004 | 5 | 4 | 1 | 12 | 8 | 35 |
| node_failure_recovery-005 | 4 | 3 | 2 | 40 | 18 | 59 |
| node_failure_recovery-006 | 5 | 2 | 4 | 44 | 28 | 85 |
| node_failure_recovery-007 | 8 | 4 | 1 | 12 | 8 | 38 |
| node_failure_recovery-008 | 7 | 3 | 2 | 40 | 18 | 62 |
| node_failure_recovery-009 | 1 | 2 | 4 | 44 | 28 | 81 |
| node_failure_recovery-010 | 3 | 4 | 1 | 12 | 8 | 33 |
| node_failure_recovery-011 | 2 | 3 | 2 | 40 | 18 | 57 |
| node_failure_recovery-012 | 5 | 2 | 4 | 44 | 28 | 85 |

## Scheduler decision trace

The resource-aware policy placed **node_failure_recovery-001** on **gpu-t4** at queue rank 1. It selected the candidate with the greatest post-placement GPU fill; ties use the lexicographically largest node ID.

| Feasible candidate | Projected GPU fill | GPUs free before | Memory free before (GB) | Power delta (kW) | Selected |
|---|---:|---:|---:|---:|:---:|
| gpu-a100 | 0.250 | 4 | 80 | 0.650 | no |
| gpu-l40s | 0.250 | 4 | 48 | 0.550 | no |
| gpu-t4 | 0.500 | 2 | 24 | 0.400 | yes |

An actual deferred-work diagnostic for **node_failure_recovery-011** at step 2 reported `temporary_capacity_contention`. Per-node checks: `{"gpu-a100":"temporary_gpu_capacity_contention","gpu-l40s":"temporary_memory_capacity_contention","gpu-t4":"memory_insufficient"}`. This is a point-in-time reason, not a claim that the workload was infeasible forever.

## Fixed-horizon operational outcomes

Each policy receives the same materialized workload set and exogenous failure trace and runs all 90 steps. Each status cell counts all 12 scenario workloads. `Completed run` means the simulation reached its horizon; it does not mean every workload completed.

| Policy | Execution | Workload status counts | Completed / all | Deadline misses / due | Deadline attained / all deadlines | Mean queue wait (minutes / samples) | Throughput (jobs/hour) |
|---|---|---|---:|---:|---:|---:|---:|
| fifo (`baseline_scheduler`) | completed 90/90 steps | completed 9, failed 2, cancelled 0, pending 0, running 1 (12 total) | 9/12 (75.0%) | 4/12 (33.3%) | 8/12 (66.7%) | 18.2222 (9 samples) | 6.0 |
| resource_aware (`baseline_scheduler`) | completed 90/90 steps | completed 9, failed 2, cancelled 0, pending 0, running 1 (12 total) | 9/12 (75.0%) | 3/12 (25.0%) | 9/12 (75.0%) | 14.5556 (9 samples) | 6.0 |
| nemotron (`deterministic_fallback`) | completed 90/90 steps | completed 9, failed 2, cancelled 0, pending 0, running 1 (12 total) | 9/12 (75.0%) | 3/12 (25.0%) | 9/12 (75.0%) | 14.5556 (9 samples) | 6.0 |

## Synthetic infrastructure outcomes

| Policy | Estimated energy (kWh) | Estimated energy cost (currency unit unspecified) | Power-budget violations | Node failures / recoveries |
|---|---:|---:|---:|---:|
| fifo | 6.438667 | 0.515093 at configured synthetic tariff 0.08/kWh | 0 | 15 / 14 |
| resource_aware | 6.041167 | 0.483293 at configured synthetic tariff 0.08/kWh | 0 | 15 / 14 |
| nemotron | 6.041167 | 0.483293 at configured synthetic tariff 0.08/kWh | 0 | 15 / 14 |

Offline Nemotron telemetry: **78** scheduler decision attempts, **0** provider invocations, **78** deterministic fallback decisions, **0** provider failures, no provider latency, and no returned token usage. The policy attempted no live inference.

The deadline-miss denominator is workloads whose deadlines were due by the end of the run; deadline attainment uses all workloads with a declared deadline. Queue-wait mean uses completed-workload samples only, with the sample count shown. Energy and its cost estimate use synthetic simulator output and a configured price input whose currency is unspecified; they are neither facility telemetry nor a cloud bill.

### Per-workload outcomes

| Workload | FIFO | Resource-aware | Nemotron (offline fallback) |
|---|---|---|---|
| node_failure_recovery-001 | completed at step 9 | completed at step 9 | completed at step 9 |
| node_failure_recovery-002 | completed at step 19 | completed at step 19 | completed at step 19 |
| node_failure_recovery-003 | completed at step 62; 1 node failure | completed at step 78; 2 node failures | completed at step 78; 2 node failures |
| node_failure_recovery-004 | failed at step 19 (max_retries_exceeded); 3 node failures; deadline missed | failed at step 19 (max_retries_exceeded); 3 node failures; deadline missed | failed at step 19 (max_retries_exceeded); 3 node failures; deadline missed |
| node_failure_recovery-005 | completed at step 41; 1 node failure | completed at step 41; 1 node failure | completed at step 41; 1 node failure |
| node_failure_recovery-006 | completed at step 75; 2 node failures | completed at step 79 | completed at step 79 |
| node_failure_recovery-007 | completed at step 28; 1 node failure | completed at step 27; 2 node failures | completed at step 27; 2 node failures |
| node_failure_recovery-008 | running on gpu-a100 at horizon (3 steps remain); deadline missed | completed at step 44 | completed at step 44 |
| node_failure_recovery-009 | failed at step 28 (max_retries_exceeded); 3 node failures; deadline missed | completed at step 51; 1 node failure | completed at step 51; 1 node failure |
| node_failure_recovery-010 | completed at step 17; 2 node failures | completed at step 17; 2 node failures | completed at step 17; 2 node failures |
| node_failure_recovery-011 | completed at step 41; 1 node failure | failed at step 36 (max_retries_exceeded); 3 node failures; deadline missed | failed at step 36 (max_retries_exceeded); 3 node failures; deadline missed |
| node_failure_recovery-012 | completed at step 90; deadline missed | running on gpu-a100 at horizon (16 steps remain); deadline missed | running on gpu-a100 at horizon (16 steps remain); deadline missed |

### Failure and horizon diagnosis

- **fifo:** 0 permanently infeasible, 0 rejected actions, 0 power-budget violations; operational failures: node_failure_recovery-004 (`max_retries_exceeded`, 3 node failures), node_failure_recovery-009 (`max_retries_exceeded`, 3 node failures); unresolved at step 90: node_failure_recovery-008 (running, 3 steps remain, deadline_miss). Horizon diagnoses: `{"deadline_miss":1}`.
- **resource_aware:** 0 permanently infeasible, 0 rejected actions, 0 power-budget violations; operational failures: node_failure_recovery-004 (`max_retries_exceeded`, 3 node failures), node_failure_recovery-011 (`max_retries_exceeded`, 3 node failures); unresolved at step 90: node_failure_recovery-012 (running, 16 steps remain, deadline_miss). Horizon diagnoses: `{"deadline_miss":1}`.
- **nemotron:** 0 permanently infeasible, 0 rejected actions, 0 power-budget violations; operational failures: node_failure_recovery-004 (`max_retries_exceeded`, 3 node failures), node_failure_recovery-011 (`max_retries_exceeded`, 3 node failures); unresolved at step 90: node_failure_recovery-012 (running, 16 steps remain, deadline_miss). Horizon diagnoses: `{"deadline_miss":1}`.

## What this establishes—and does not

- Establishes that the offline simulator executes the seeded failure/recovery scenario, retains decision diagnostics, and produces reproducible paired policy records.
- The table is one paired seed (`n=1` run per policy). It does not establish a general policy winner, model benefit, real infrastructure behavior, or real-world energy savings.
- The `nemotron` record is **deterministic fallback**, with no live provider call, model identity claim, or provider telemetry.
- Workloads still pending/running at the fixed horizon remain in the results; the horizon is not extended to drain the queue.
