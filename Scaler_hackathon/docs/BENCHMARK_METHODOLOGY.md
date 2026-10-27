# GridMind benchmark methodology

## Reproduction

Run from `Scaler_hackathon/`:

```bash
uv run --locked python -m server.benchmarks \
  --suite configs/scenarios.json --seeds 1,2,3,4,5 \
  --output-dir benchmarks/sample-suite
```

This command emits `results.json`, `runs.csv`, and `report.md`. The checked-in
sample covers ten synthetic scenarios, five seeds, and four policies (200
scenario-seed-policy runs). Primary scenario horizons are fixed in suite
version `1.1.0`; no policy receives a longer primary horizon.

## Optional live Nemotron comparison

Offline runs remain the reproducible default. Offline Nemotron is reported as
`deterministic_fallback`, not as model inference. The live path compares the
resource-aware policy, FIFO, priority, and Nemotron on one predeclared seed and
one bounded scenario (at most ten simulation steps). The API refuses live
`/run` and benchmark requests until `/model/verify` has confirmed the exact
authenticated catalogue entry and one real, non-empty Nemotron proposal that
passes deterministic simulator validation. The CLI's explicit `--live-model`
path performs the same catalogue and single-request preflight before starting
its bounded experiment. The preflight is separate from benchmark samples and
its status/latency/usage are recorded separately.

Each policy run uses the same materialized scenario and exogenous node-failure
trace; records retain scenario and failure-trace SHA-256 hashes for pairing.
Provider errors, malformed/invalid proposals, deterministic fallbacks, and
simulator errors remain visible; they are not removed from the main result
records. A fallback policy step remains a Nemotron-policy outcome and is
counted in `ai_fallbacks`. Provider failures are distinguished from operational
workload failures.

`ai_attempts` is eligible Nemotron scheduling decisions; `ai_request_attempts`
is SDK request calls started; `ai_retries` is the additional call count;
`ai_invocations` is the count of completion response objects received;
`ai_valid_responses` is schema-valid model output; `ai_failures` is a request
that did not produce schema-valid output; `ai_invalid_proposals` includes
schema- or simulator-invalid proposals; `ai_fallbacks` counts deterministic
fallback decisions. Timeout attempts may have executed remotely without a
response, so these client-side counters are not a provider billing ledger.
Provider latency includes retries and is separate from simulated queue wait,
turnaround, and execution time. Prompt/completion usage is the provider's
reported value only; when absent, its run metric is `null`, and the summary's
`n` is the count of runs with returned usage. Other summary metric `n` values
count successful fixed-horizon simulator runs with a defined metric value;
workload metrics retain their explicit per-metric denominators in each run's
raw metrics. No scalar overall score combines trade-offs.

Live inference is nondeterministic and network-dependent. The initial one-seed
comparison is exploratory only; it cannot establish superiority or support
statistical claims. A provider-backed comparison was not run for this checkout
because authorized credentials and a configured model ID were unavailable.
No live sample, request count, token usage, or model-performance result is
claimed here.

Each policy receives the same seed-materialized workloads, node topology,
power budget, scenario hash, and complete exogenous node-failure trace. The
scenario hash covers the scenario version, horizon, topology, workload
parameters and arrivals, seed, and constraints. Each record also stores the
simulator/policy versions, a policy identity/version hash, actual failure
trace and trace hash, event trace, scheduling diagnostics, counters, final
node/workload state, and metrics. Increment the relevant version when changing
simulator or policy semantics. `created_at` fields in JSON are intentionally
nondeterministic; substantive run data, CSV rows, and Markdown reports are
deterministic for identical inputs.

The suite is synthetic. It does not use cluster telemetry, facility power
measurements, cloud prices, or hardware execution. Cost uses the configured
synthetic energy price and is not a cloud bill.

## Diagnosis of the previously checked-in sample

The documented baseline command was run against the PR #3 checkout before
editing PR #4. Its 200 runs regenerated `runs.csv` and `report.md` byte for
byte against the committed copies. The substantive JSON run records also
matched after excluding the intentional `created_at` fields.

The old report counted 64 runs as `completed`, 136 as `incomplete`, and none
as `failed`. This was not evidence that 136 simulations crashed. The episode
runner called any run with a pending or running workload at the cutoff
`incomplete`; it did not distinguish a normal, successfully reached fixed
horizon from a simulation error or a workload outcome. The same status also
excluded all of those horizon-limited runs from paired comparisons.

Three scenario definitions intentionally contain structurally impossible
jobs. In the old simulator these jobs stayed pending forever:

* Heterogeneous GPU requirements: four 4-GPU, 64-GB L40S requests per seed do
  not fit the configured 4-GPU L40S node's 48-GB memory.
* GPU memory pressure: four 3-GPU, 88-GB requests per seed cannot fit either
  the 2-GPU/96-GB A100 node or the 6-GPU/24-GB L40S node.
* Infeasible workloads: three 12-GPU/512-GB requests per seed exceed every
  node's GPU-count and memory envelope.

Across four policies and five seeds, those are 220 structurally impossible
workloads. Their presence alone marked all 60 runs in those three scenarios
as `incomplete`. The remaining 76 old incomplete runs came from feasible work
still waiting at the fixed cutoff: 20 tight-power, 16 node-failure, 20
short/long-contention, and 20 combined-stress policy runs. These were
horizon-limited outcomes, not simulator exceptions. Separately, the old
starvation metric counted feasible pending jobs older than 30 minutes without
checking whether active reservations, facility power, or node recovery
explained the wait; short/long and combined-stress contention was therefore
misreported as starvation.

| Scenario | Old incomplete runs / 20 | Evidence-based diagnosis |
|---|---:|---|
| Balanced baseline | 0 | No unresolved jobs; ordinary fixed-horizon run. |
| Burst arrivals | 0 | Jobs completed; deadline misses remained policy outcomes, not run failures. |
| Mixed priorities and tight deadlines | 0 | Jobs completed; FIFO missed deadlines that other policies attained. |
| Heterogeneous GPU requirements | 20 | Four permanently memory-infeasible L40S requests per seed and policy remained pending. |
| GPU memory pressure | 20 | Four permanently infeasible 3-GPU/88-GB requests plus one feasible job still contending at the horizon per seed and policy. |
| Tight facility power budget | 20 | Five feasible queue entries per run remained unresolved at the fixed cutoff; the old artifact did not record the scheduler's skip reason. |
| Node failure and recovery | 16 | Retried failures plus feasible work pending through outages/recovery and contention; one seed per policy drained before the old early-stop condition. |
| Short jobs versus long-running work | 20 | Feasible jobs remained pending behind long GPU reservations at the 90-step cutoff; the old starvation counter had no reservation-aware exclusion. |
| Infeasible workloads | 20 | Three 12-GPU requests per seed exceeded the configured maximum of four GPUs per node and remained pending. |
| Combined operational stress | 20 | A mixture of max-retry failures, node-recovery delays, power constraints, and resource contention remained unresolved. |

The primary horizons have not been increased to make these outcomes disappear.
Each scenario now records a horizon rationale in `configs/scenarios.json`.
`short_long_contention` intentionally schedules three simultaneous 60-minute,
four-GPU jobs onto two fitting nodes; even before later arrivals, its serialized
service lower bound exceeds the 90-minute primary window.

## Run status and workload lifecycle

Run status describes simulator execution, not queue completion:

* `completed` means the simulation executed the entire declared horizon
  without an exception. It may contain failed, infeasible, or horizon-
  unresolved workloads.
* `failed` means a simulation/policy exception interrupted execution. The
  record retains the exception type and any partial state, but failed runs
  are excluded from successful-run aggregates and paired samples.
* The legacy `incomplete` status is retained only when reading old records; a
  normally reached horizon is no longer labeled incomplete.

Every policy executes every step of the fixed horizon, even if the queue
drains early. This keeps elapsed time, energy sampling, and the exogenous
failure trace comparable across policies. A separately recorded
`workloads_terminal_at_step` indicates when all workloads first became
terminal, if they did. Infeasible requests become terminal `failed` workloads
with a `permanent_infeasibility:<reason>` field once submitted. The simulator
does not relax GPU, memory, model, node-power, or facility-power constraints
to improve completion numbers.

At each scheduling tick, the simulator records per-workload skip reasons and
per-node details. Reasons distinguish GPU-model mismatch, GPU-count or memory
insufficiency, node unavailability/recovery, active GPU/memory contention,
same-decision reservations, node power, and facility power. The final workload
state also carries its last reason and skip counts. Event traces preserve
arrival, start, completion, failure, recovery, requeue, preemption, and
cancellation transitions.

Deadline misses and scheduling blockers are reported on separate axes. The
primary unresolved-outcome classification uses this precedence: permanent
infeasibility; terminal completed/failed/cancelled status; arrival after the
horizon; deadline miss; node-failure recovery; temporary capacity contention;
power-constrained waiting; explicit policy deferral; starvation/scheduler
defect; then unexplained horizon incomplete. A pending job continues to be
eligible after its deadline. For an unresolved deadline-missed job, the
separate blocker counts and event/decision traces preserve whether power,
resource reservations, or recovery caused the wait. A workload is starved
only when it is structurally feasible, remains pending for at least 30
minutes, and its latest scheduling result is an unexplained
`scheduler_deferral`; resource- or policy-explained waits are not starvation.

## Metric definitions

The shared implementation is `server/metrics.py`; the API and benchmarks use
the same calculations. A missing denominator/sample is `null`/`n/a`, not zero.

| Metric | Definition, unit, and denominator |
|---|---|
| Workload status counts | Counts of pending, running, completed, failed, and cancelled across every materialized workload; their sum equals `total_workloads`. Arrived/submitted and not-yet-arrived counts are also separate. |
| Full-set completion rate | Completed workloads / all materialized scenario workloads. This denominator retains structurally infeasible and not-yet-arrived work. |
| Submitted completion rate | Completed workloads / workloads that arrived by the measurement point. Reported separately; it never replaces the full-set rate. |
| Feasible completion rate | Completed workloads / all statically placeable scenario workloads. Feasibility means some configured node can satisfy model, GPU count, memory, node power, and idle facility power. |
| Infeasible workloads | Permanent-infeasibility terminal count, exact workload IDs, and reason counts. Structural feasibility over the full materialized set is also reported so a not-yet-arrived impossible job is not hidden. |
| Horizon incomplete | Pending/running/not-yet-arrived workloads at the fixed cutoff, with both a mutually exclusive primary outcome classification and a separate last-blocker classification. |
| Deadline misses | Late completions plus work unresolved at/after its deadline. `deadline_miss_rate` denominator is the count of deadlines elapsed by the horizon or completed late. |
| Deadline attainment | On-time completed jobs / submitted workloads with deadlines. Post-deadline jobs remain eligible to complete, but cannot attain a missed deadline. |
| SLA attainment | On-time completion for jobs with deadlines (or completion for jobs without deadlines) / submitted workloads. |
| Throughput | Completed submitted jobs / elapsed simulated hours. All policies use the same fixed elapsed horizon. |
| Queue wait / turnaround | `started_at - submission_time` and `completed_at - submission_time`, respectively, in minutes; completed workloads with timestamps only. |
| Starvation | Feasible, still-pending workload with at least 30 minutes elapsed and no resource, power, recovery, or explicit policy explanation. |
| Failures and recovery | Node failures, recoveries, workload operational failures, requeues, and preemptions are counted separately. Max-retry failures remain in the workload denominator. |
| Resource/power rejections | Invalid assignment rejection counters; scheduler skips are recorded separately and are not counted as rejected actions. Power-limit rejections are distinct from actual power-budget violations. |
| GPU/memory utilization | Allocated capacity / total configured capacity. Current is a point-in-time ratio; average is the arithmetic mean of tick samples. |
| Power and energy | Available-node idle power plus allocated-GPU coefficients, in synthetic kW; energy is the sum of tick power / 60, in synthetic kWh. Completion ticks and the rest of the fixed horizon are included. |
| Estimated energy cost | Synthetic kWh × configured illustrative energy rate. It is not a provider invoice or a cloud bill. |
| Model operations | Attempts, actual invocations, failures, fallback count, observed latency, and returned token usage. No synthetic-run model cost is invented. |

Queue-wait and turnaround percentiles use linear interpolation between sorted
observations. Bootstrap intervals are deterministic descriptive percentile
intervals over paired independent scenario-seed samples. They are omitted
below five valid pairs and must not be interpreted as statistical proof.

## Pairing, aggregation, and interpretation

Pairing keys are scenario hash and seed. A comparison includes only pairs
where both executions reached the fixed horizon and both have identical
exogenous failure-trace hashes. Each metric also reports its own valid `n`.
Failed simulator executions and trace-mismatched pairs are counted and
excluded, not relabeled successful. Aggregates report the successful-run
sample count and explicit pooled workload totals; partial error-run state
remains available in JSON/CSV. Scenario results are shown separately and are
not collapsed into a cross-scenario policy ranking.

The offline `nemotron` policy is deterministic resource-aware fallback and
does not call a model. Its benchmark rows are explicitly marked
`deterministic_fallback`. They are not evidence of live NVIDIA/Nebius inference
or AI superiority. Live model measurements require a separately verified
request and a fair comparison.

## Interactive decision trace

The `/run` API response records `placement_diagnostics` for each decision.
Deterministic scheduler records are produced during the same candidate
evaluation that chooses a node. They show eligible node alternatives,
post-placement GPU fill, free resources before placement, estimated
incremental power, projected node/facility power, and the selected candidate.
Candidates rejected by placement constraints are not ranked as feasible
alternatives; their reasons remain in `scheduling_diagnostics`. Queue rank,
priority, deadline, policy ordering, and the deterministic node-selection
rule provide additional context.

For a live Nemotron proposal, the trace reports only the proposed node and
whether the simulator's deterministic resource/power validator accepted it.
It explicitly does not assert that the deterministic scheduler evaluated or
ranked the alternatives. The model's free-text rationale remains a proposal,
not proof of causal reasoning. The API retains the last 20 decision steps
per recent simulation run in process-local history; this is separate from
the fixed-horizon benchmark artifacts and does not affect metrics or policy
actions.

## Current sample outcome

The current five-seed sample contains 200 successful fixed-horizon simulation
executions and no failed/incomplete executions. That does **not** mean all
2,720 workload instances completed. Across the successful policy runs there
are 2,262 completed, 38 operationally failed, 0 cancelled, 220 permanently
infeasible, and 200 horizon-unresolved workload instances. These status
categories are mutually exclusive in the final workload snapshot. The
checked-in per-scenario report contains counts and denominators for every
policy:

* 220 permanently infeasible workload instances were terminally classified
  across the four policies instead of remaining pending.
* 200 workloads remained unresolved at their primary horizons. All are
  explicitly classified as deadline misses or horizon-incomplete, with their
  last actionable blocker reported separately. The outstanding cases are
  concentrated in GPU-memory pressure (20 across policies), tight facility
  power (20), node failure/recovery (18), short/long contention (64), and
  combined stress (78); other scenarios have none. The per-policy report
  distinguishes running work at the horizon, node recovery, power waiting,
  temporary capacity contention, and same-decision reservations.
* All four policies have zero starvation classifications under the explicit
  30-minute unexplained-deferral rule.
* Completed/deadline outcomes differ by scenario. For example, the burst
  scenario has 80/90 on-time completions under FIFO and 81/90 under the other
  policies; mixed-priority FIFO has 68/70 on-time while the other policies
  attain 70/70. These are small-sample synthetic observations, not evidence
  of live-model benefit; Nemotron rows are offline fallback.

### Separate 2x-horizon diagnostic continuation

A separate diagnostic used the same five seeds, materialized workloads,
topologies, and policies, with every scenario horizon uniformly doubled.
These outcomes are diagnostic only and are not included in the primary sample,
comparisons, or artifacts. In that continuation, the 20 GPU-memory-pressure,
20 tight-power, and 64 short/long unresolved primary workload instances
drained by the doubled horizon. Node-failure/recovery also drained its 18
primary unresolved instances, while additional time exposed retry-exhaustion
failures. Combined stress remained unresolved: 1 FIFO workload and 6 per
non-FIFO policy across the five seeds, with recorded blockers including node
recovery, power waiting, running work, reservations, and temporary capacity
contention. This is evidence that some primary outcomes are horizon-limited,
not proof that all stress cases will drain or that any policy is operationally
safe.

The `results.json` artifact includes per-run workload states, event traces,
hashes, and detailed diagnostics. `runs.csv` contains one row per run and
metrics; `report.md` keeps scenario-level summaries and paired sample sizes
separate. The JSON timestamps are intentionally excluded from byte comparisons;
the committed CSV and Markdown outputs are verified byte-for-byte across two
identical generations, and substantive JSON data also matched after excluding
only those timestamps.
