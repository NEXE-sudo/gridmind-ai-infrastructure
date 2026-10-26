import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowDownToLine,
  Check,
  ChevronRight,
  Cpu,
  Database,
  Gauge,
  Play,
  RefreshCw,
  RotateCcw,
  Server,
  ShieldCheck,
  Zap,
} from "lucide-react";
import {
  api,
  formatNumber,
  formatPercent,
  type BenchmarkResult,
  type DecisionRecord,
  type OperationalMetrics,
  type PolicyId,
  type RunRecord,
  type ScenarioId,
  type SimulationState,
} from "@/lib/gridmind";

const POLICIES: Array<{ id: PolicyId; label: string }> = [
  { id: "resource_aware", label: "Resource-aware" },
  { id: "priority", label: "Priority" },
  { id: "fifo", label: "FIFO" },
  { id: "nemotron", label: "Nemotron + safe fallback" },
];

const SCENARIOS = [
  { id: "balanced", label: "Balanced baseline" },
  { id: "burst_arrivals", label: "Burst arrivals" },
  { id: "mixed_priority_deadlines", label: "Mixed priorities / deadlines" },
  { id: "heterogeneous_gpu_types", label: "GPU types / capacity" },
  { id: "gpu_memory_pressure", label: "GPU memory pressure" },
  { id: "tight_power_budget", label: "Tight power budget" },
  { id: "node_failure_recovery", label: "Node failure / recovery" },
  { id: "short_long_contention", label: "Short / long job contention" },
  { id: "infeasible_workloads", label: "Infeasible requests" },
  { id: "combined_stress", label: "Combined stress" },
] satisfies Array<{ id: ScenarioId; label: string }>;

const statusClass: Record<string, string> = {
  pending: "status-queued",
  running: "status-running",
  completed: "status-completed",
  failed: "status-failed",
  cancelled: "status-muted",
};

function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
  tone = "default",
}: {
  label: string;
  value: string;
  detail: string;
  icon: typeof Activity;
  tone?: "default" | "warning" | "good";
}) {
  return (
    <article className={`metric-card metric-${tone}`}>
      <div className="metric-heading">
        <span>{label}</span>
        <Icon size={17} aria-hidden="true" />
      </div>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function ProgressBar({ value, tone = "blue" }: { value: number; tone?: string }) {
  return (
    <div className="meter" role="progressbar" aria-valuenow={Math.round(value * 100)} aria-valuemin={0} aria-valuemax={100}>
      <span className={`meter-fill meter-${tone}`} style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }} />
    </div>
  );
}

function getMetric(
  summary: BenchmarkResult["comparison"][string] | undefined,
  metric: string,
): number | null {
  return summary?.metrics[metric]?.mean ?? null;
}

function formatRate(value: number | null | undefined): string {
  return value == null ? "—" : formatPercent(value);
}

export default function GridMindConsole() {
  const [state, setState] = useState<SimulationState | null>(null);
  const [ready, setReady] = useState<{
    model_configured: boolean;
    model_verification_status: string;
    state_scope: string;
  } | null>(null);
  const [history, setHistory] = useState<RunRecord[]>([]);
  const [benchmark, setBenchmark] = useState<BenchmarkResult | null>(null);
  const [decisionLog, setDecisionLog] = useState<DecisionRecord[]>([]);
  const [policy, setPolicy] = useState<PolicyId>("resource_aware");
  const [scenario, setScenario] = useState<ScenarioId>("balanced");
  const [seed, setSeed] = useState(42);
  const [steps, setSteps] = useState(10);
  const [benchmarkSeeds, setBenchmarkSeeds] = useState("1,2,3");
  const [useLiveModel, setUseLiveModel] = useState(false);
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const refresh = useCallback(async () => {
    const [nextState, nextReady, nextHistory] = await Promise.all([
      api<SimulationState>("/state"),
      api<typeof ready>("/ready"),
      api<{ runs: RunRecord[] }>("/history?limit=12"),
    ]);
    setState(nextState);
    setScenario(nextState.scenario ?? "balanced");
    setReady(nextReady);
    setHistory(nextHistory.runs);
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([
      api<SimulationState>("/state"),
      api<typeof ready>("/ready"),
      api<{ runs: RunRecord[] }>("/history?limit=12"),
    ])
      .then(([nextState, nextReady, nextHistory]) => {
        if (!active) return;
        setState(nextState);
        setScenario(nextState.scenario ?? "balanced");
        setReady(nextReady);
        setHistory(nextHistory.runs);
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : "Could not connect to GridMind API.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const runAction = async (action: () => Promise<unknown>, success: string) => {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const outcome = await action();
      await refresh();
      setNotice(typeof outcome === "string" ? outcome : success);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The operation failed.");
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  };

  const resetScenario = () =>
    runAction(
      async () => {
        await api<SimulationState>("/reset", {
          method: "POST",
          body: JSON.stringify({ seed, scenario }),
        });
        setDecisionLog([]);
      },
      `Scenario reset with seed ${seed}.`,
    );

  const verifyLiveModel = () =>
    runAction(
      async () => {
        const result = await api<{ status: string }>("/model/verify", {
          method: "POST",
          body: JSON.stringify({ confirm_live_request: true }),
        });
        if (result.status !== "live_success") setUseLiveModel(false);
        return result.status === "live_success"
          ? "Catalogue and one live Nemotron request verified; live scheduling is now enabled for this server process."
          : `Live verification did not succeed: ${result.status.replace(/_/g, " ")}.`;
      },
      "Live model verification finished.",
    );

  const execute = (count: number) =>
    runAction(
      async () => {
        if (useLiveModel && policy !== "nemotron") {
          throw new Error("Select Nemotron before enabling live inference.");
        }
        if (useLiveModel && count > 10) {
          throw new Error("Live inference is limited to ten steps per request.");
        }
        const result = await api<{
          history: DecisionRecord[];
          fallback_used: boolean;
          steps_executed: number;
        }>("/run", {
          method: "POST",
          body: JSON.stringify({
            policy,
            steps: count,
            use_live_model: useLiveModel,
          }),
        });
        setDecisionLog((previous) => [...result.history, ...previous].slice(0, 20));
        return result.fallback_used
          ? `Completed ${result.steps_executed} step(s); Nemotron used deterministic fallback.`
          : `Completed ${result.steps_executed} step(s) using ${policy}.`;
      },
      "Simulation updated.",
    );

  const runBenchmark = () => {
    const parsedSeeds = benchmarkSeeds
      .split(",")
      .map((value) => Number(value.trim()))
      .filter((value) => Number.isInteger(value));
    if (!parsedSeeds.length || parsedSeeds.length > 5) {
      setError("Enter one to five integer seeds, separated by commas.");
      return;
    }
    if (useLiveModel && parsedSeeds.length !== 1) {
      setError("Live comparisons are limited to one seed. Use offline mode for repeated trials.");
      return;
    }
    void runAction(
      async () => {
        const result = await api<BenchmarkResult>("/benchmarks/run", {
          method: "POST",
          body: JSON.stringify({
            seeds: parsedSeeds,
            policies: POLICIES.map((item) => item.id),
            scenario,
            use_live_model: useLiveModel,
          }),
        });
        setBenchmark(result);
      },
      "Paired benchmark finished; inspect run statuses and paired seeds below.",
    );
  };

  const downloadJson = () => {
    if (!benchmark) return;
    const blob = new Blob([JSON.stringify(benchmark, null, 2)], { type: "application/json" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "gridmind-experiment.json";
    link.click();
    URL.revokeObjectURL(link.href);
  };

  const metrics: OperationalMetrics | undefined = state?.metrics;
  const modelVerificationStatus =
    ready?.model_verification_status ??
    (ready?.model_configured ? "not_attempted" : "not_configured");
  const displayedDecisions = useMemo(() => decisionLog.slice(0, 5), [decisionLog]);

  return (
    <main className="gridmind-shell">
      <header className="topbar">
        <a className="brand" href="#overview" aria-label="GridMind operations home">
          <span className="brand-mark"><Cpu size={20} /></span>
          <span>GRIDMIND <small>OPERATIONS SIMULATOR</small></span>
        </a>
        <nav className="top-nav" aria-label="Main navigation">
          <a href="#overview">Overview</a>
          <a href="#workloads">Workloads</a>
          <a href="#experiments">Experiments</a>
        </nav>
        <div className="top-status">
          <span className="live-dot" />
          <span>SIMULATION</span>
          <span className="separator">/</span>
          <span className={modelVerificationStatus === "live_success" ? "model-ready" : "model-offline"}>
            {modelVerificationStatus.replace(/_/g, " ").toUpperCase()}
          </span>
          <button className="text-button" onClick={() => void verifyLiveModel()} disabled={busy || !ready?.model_configured}>
            Verify model · 1 live request
          </button>
        </div>
      </header>

      <div className="page-content">
        <section className="hero-row" id="overview">
          <div>
            <p className="eyebrow">DATA-CENTRE OPERATIONS · DISCRETE-TIME SIMULATOR</p>
            <h1>Infrastructure at a glance.</h1>
            <p className="subtitle">Schedule GPU workloads against capacity, deadlines and a facility power budget.</p>
          </div>
          <div className="session-chip" aria-label={`Simulation step ${state?.step ?? 0}, seed ${state?.seed ?? seed}`}>
            <span>STEP <b>{state?.step ?? "—"}</b></span>
            <i />
            <span>SEED <b>{state?.seed ?? seed}</b></span>
            <button className="icon-button" onClick={() => void runAction(refresh, "State refreshed.")} disabled={busy || loading} aria-label="Refresh simulation state">
              <RefreshCw size={16} />
            </button>
          </div>
        </section>

        {(error || notice) && (
          <div className={`banner ${error ? "banner-error" : "banner-success"}`} role={error ? "alert" : "status"}>
            {error ? <AlertTriangle size={17} /> : <Check size={17} />}
            <span>{error || notice}</span>
            {error && <button onClick={() => setError("")} aria-label="Dismiss error">Dismiss</button>}
          </div>
        )}

        {loading && !state ? (
          <div className="loading-state" role="status"><span className="spinner" /> Connecting to the local GridMind API…</div>
        ) : !state ? (
          <section className="offline-panel">
            <Server size={28} />
            <h2>GridMind API is unavailable</h2>
            <p>Start the backend from <code>Scaler_hackathon/</code> with the documented Uvicorn command, then retry.</p>
            <button className="button button-primary" onClick={() => void runAction(refresh, "Connected to GridMind.")} disabled={busy}>Retry connection</button>
          </section>
        ) : (
          <>
            <section className="metric-grid" aria-label="Current operational metrics">
              <MetricCard label="GPU CAPACITY" value={`${state.nodes.reduce((sum, node) => sum + node.allocated_gpus, 0)} / ${state.nodes.reduce((sum, node) => sum + node.gpu_count, 0)}`} detail={`${formatPercent(metrics?.current_gpu_utilization ?? 0)} current utilisation`} icon={Cpu} />
              <MetricCard label="QUEUE DEPTH" value={formatNumber(metrics?.queued_workloads ?? state.queue_depth, 0)} detail={`${formatNumber(metrics?.running_workloads, 0)} active workloads`} icon={Activity} />
              <MetricCard label="POWER DRAW" value={`${formatNumber(metrics?.estimated_power_kw)} kW`} detail={`of ${formatNumber(metrics?.power_budget_kw)} kW facility budget`} icon={Zap} tone={(metrics?.estimated_power_kw ?? 0) > (metrics?.power_budget_kw ?? 1) * 0.85 ? "warning" : "default"} />
              <MetricCard label="COMPLETED" value={formatNumber(metrics?.completed_workloads, 0)} detail={`${formatNumber(metrics?.permanently_infeasible_workloads, 0)} infeasible · ${formatNumber(metrics?.horizon_incomplete_workloads ?? metrics?.unfinished_workloads, 0)} unresolved`} icon={Check} tone="good" />
              <MetricCard label="DEADLINE MISSES" value={formatNumber(metrics?.deadline_misses, 0)} detail={`${formatRate(metrics?.deadline_miss_rate)} of ${formatNumber(metrics?.deadline_miss_denominator, 0)} due`} icon={AlertTriangle} tone={(metrics?.deadline_misses ?? 0) > 0 ? "warning" : "good"} />
              <MetricCard label="EST. ENERGY" value={`${formatNumber(metrics?.estimated_energy_kwh, 4)} kWh`} detail={`$${formatNumber(metrics?.estimated_energy_cost, 4)} at configured tariff`} icon={Gauge} />
              <MetricCard label="CONSTRAINT REJECTIONS" value={formatNumber(metrics?.rejected_actions, 0)} detail={`${formatNumber(metrics?.resource_rejections, 0)} constraint rejections · ${formatNumber((metrics?.node_power_rejections ?? 0) + (metrics?.facility_power_rejections ?? 0), 0)} are power-related`} icon={ShieldCheck} tone={(metrics?.rejected_actions ?? 0) > 0 ? "warning" : "default"} />
              <MetricCard label="INFRA EVENTS" value={formatNumber(metrics?.failed_nodes, 0)} detail={`${formatNumber(metrics?.workloads_requeued, 0)} workloads requeued`} icon={Server} tone={(metrics?.failed_nodes ?? 0) > 0 ? "warning" : "default"} />
              <MetricCard label="AI FALLBACKS" value={formatNumber(metrics?.ai_fallbacks, 0)} detail={`${formatNumber(metrics?.ai_request_attempts, 0)} request attempts · ${formatNumber(metrics?.ai_invocations, 0)} responses · ${formatNumber(metrics?.ai_valid_responses, 0)} schema-valid · ${formatNumber(metrics?.ai_retries, 0)} retries · ${formatNumber(metrics?.ai_failures, 0)} failures · ${formatNumber(metrics?.ai_invalid_proposals, 0)} invalid`} icon={ShieldCheck} />
              <MetricCard label="AI LATENCY" value={metrics?.ai_latency_ms_mean == null ? "—" : `${formatNumber(metrics.ai_latency_ms_mean, 1)} ms`} detail={`Mean end-to-end provider latency · reported tokens in/out ${formatNumber(metrics?.ai_prompt_tokens, 0)} / ${formatNumber(metrics?.ai_completion_tokens, 0)}`} icon={Activity} />
            </section>

            <section className="control-panel panel">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">SCHEDULER</p>
                  <h2>Choose a policy. Run the next decision.</h2>
                </div>
                <span className="single-session-label"><ShieldCheck size={14} /> SINGLE SESSION</span>
              </div>
              <div className="control-row">
                <label className="field">
                  <span>Policy</span>
                  <select value={policy} onChange={(event) => setPolicy(event.target.value as PolicyId)} disabled={busy}>
                    {POLICIES.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
                  </select>
                </label>
                <label className="field field-small">
                  <span>Scenario seed</span>
                  <input type="number" value={seed} onChange={(event) => setSeed(Number(event.target.value))} disabled={busy} />
                </label>
                <label className="field">
                  <span>Scenario</span>
                  <select value={scenario} onChange={(event) => setScenario(event.target.value as ScenarioId)} disabled={busy}>
                    {SCENARIOS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
                  </select>
                </label>
                <label className="field field-small">
                  <span>Run steps</span>
                  <input type="number" min={1} max={100} value={steps} onChange={(event) => setSteps(Math.max(1, Math.min(100, Number(event.target.value) || 1)))} disabled={busy} />
                </label>
                <label className={`model-toggle ${policy !== "nemotron" ? "toggle-disabled" : ""}`}>
                  <input type="checkbox" checked={useLiveModel} onChange={(event) => setUseLiveModel(event.target.checked)} disabled={busy || policy !== "nemotron" || ready?.model_verification_status !== "live_success"} />
                  <span className="toggle-track" />
                  <span>Request live model</span>
                </label>
                <div className="control-actions">
                  <button className="button button-quiet" onClick={() => void resetScenario()} disabled={busy}>
                    <RotateCcw size={15} /> Reset
                  </button>
                  <button className="button button-secondary" onClick={() => void execute(1)} disabled={busy}>
                    <ChevronRight size={16} /> Step
                  </button>
                  <button className="button button-primary" onClick={() => void execute(steps)} disabled={busy}>
                    {busy ? <span className="spinner spinner-small" /> : <Play size={15} />} Run
                  </button>
                </div>
              </div>
              <p className="fineprint">All actions are validated in deterministic simulator code. Estimated power and energy are synthetic, not hardware telemetry.</p>
            </section>

            <section className="main-grid">
              <article className="panel node-panel">
                <div className="section-heading">
                  <div><p className="eyebrow">COMPUTE POOL</p><h2>GPU nodes <span className="count-pill">{state.nodes.length}</span></h2></div>
                  <span className="subtle-label"><span className="live-dot" /> INVENTORY</span>
                </div>
                <div className="node-list">
                  {state.nodes.map((node) => (
                    <div className="node-card" key={node.id}>
                      <div className="node-top">
                        <span className="node-icon"><Server size={17} /></span>
                        <div className="node-name"><strong>{node.id}</strong><small>{node.gpu_model}</small></div>
                        <span className={`node-status ${node.available ? "node-online" : "node-offline"}`}>{node.available ? "HEALTHY" : "RECOVERING"}</span>
                      </div>
                      <div className="node-capacity"><span><Cpu size={14} /> GPU allocation</span><b>{node.allocated_gpus} / {node.gpu_count}</b></div>
                      <ProgressBar value={node.utilization} />
                      <div className="node-capacity"><span><Database size={14} /> Memory</span><b>{node.allocated_memory_gb} / {node.memory_gb} GB</b></div>
                      <ProgressBar value={node.memory_utilization} tone="violet" />
                      <div className="node-footer"><span><Zap size={13} /> {formatNumber(node.estimated_power_kw)} / {formatNumber(node.power_limit_kw)} kW</span><span>{node.workloads.length} workload{node.workloads.length === 1 ? "" : "s"}</span></div>
                    </div>
                  ))}
                </div>
              </article>

              <article className="panel decision-panel">
                <div className="section-heading">
                  <div><p className="eyebrow">DECISION TRACE</p><h2>Policy rationale</h2></div>
                  <span className={`trace-badge ${displayedDecisions[0]?.fallback_used ? "trace-fallback" : ""}`}>
                    {displayedDecisions[0]?.fallback_used ? "FALLBACK" : "DETERMINISTIC"}
                  </span>
                </div>
                {displayedDecisions.length ? (
                  <div className="decision-list">
                    {displayedDecisions.map((decision, index) => (
                      <div className="decision-item" key={`${decision.step}-${index}`}>
                        <div className="decision-meta">
                          <span>STEP {decision.step}</span>
                          <span>{(decision.inference_mode ?? decision.proposal_status).replace(/_/g, " ")}{decision.proposal_latency_ms == null ? "" : ` · ${formatNumber(decision.proposal_latency_ms, 1)} ms`}{decision.proposal_request_attempts ? ` · ${decision.proposal_request_attempts} provider attempt(s)` : ""}</span>
                        </div>
                        <p>{decision.explanation}</p>
                        <div className="decision-assignments">
                          <small>PROPOSED</small>
                          {Object.entries(decision.proposed_assignments).map(([job, node]) => <span key={job}>{job}<b>→</b>{node}</span>)}
                          {!Object.keys(decision.proposed_assignments).length && <span className="empty-inline">No proposal</span>}
                        </div>
                        <div className="decision-assignments">
                          <small>EXECUTED</small>
                          {Object.entries(decision.executed_assignments).map(([job, node]) => <span key={job}>{job}<b>→</b>{node}</span>)}
                          {!Object.keys(decision.executed_assignments).length && <span className="empty-inline">No placements this step</span>}
                        </div>
                        {decision.proposal_validation_rejections.length > 0 && (
                          <p className="rejection-note"><AlertTriangle size={13} /> Proposal rejected by simulator checks: {decision.proposal_validation_rejections.map((item) => `${item.workload_id} (${item.reason})`).join(", ")}</p>
                        )}
                        {decision.scheduling_diagnostics.length > 0 && (
                          <p className="rejection-note">Deferred: {decision.scheduling_diagnostics.map((item) => `${item.workload_id} (${item.reason})`).join(", ")}</p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-state"><ShieldCheck size={22} /><p>Decision explanations appear here after you run a policy.</p><small>Model rationales are proposals, not verified causal explanations.</small></div>
                )}
                <div className="decision-foot"><ShieldCheck size={14} /> Placement constraints are enforced by the simulator.</div>
              </article>
            </section>

            <section className="panel workload-panel" id="workloads">
              <div className="section-heading">
                <div><p className="eyebrow">JOB QUEUE</p><h2>Workload inventory <span className="count-pill">{state.workloads.length}</span></h2></div>
                <div className="workload-legend"><span><i className="legend-dot dot-running" /> Running</span><span><i className="legend-dot dot-queued" /> Queued</span><span><i className="legend-dot dot-done" /> Completed</span></div>
              </div>
              <div className="table-scroll">
                <table className="workload-table">
                  <thead><tr><th>Workload</th><th>Priority</th><th>Request</th><th>GPU type</th><th>Deadline</th><th>Progress</th><th>Node</th><th>Status</th></tr></thead>
                  <tbody>
                    {state.workloads.map((workload) => (
                      <tr key={workload.id}>
                        <td><strong>{workload.name}</strong><small>{workload.id} · arrives at t+{workload.submission_time}</small>{(workload.failure_reason || workload.last_scheduling_reason) && <small>Reason: {workload.failure_reason ?? workload.last_scheduling_reason}</small>}</td>
                        <td><span className={`priority priority-${workload.priority}`}>P{workload.priority}</span></td>
                        <td>{workload.gpu_count} GPU · {workload.memory_gb} GB</td>
                        <td>{workload.required_gpu_model ?? "Any compatible"}</td>
                        <td>{workload.deadline == null ? "—" : `t+${workload.deadline}`}</td>
                        <td>{workload.duration - workload.remaining} / {workload.duration} min</td>
                        <td>{workload.node_id ?? "—"}</td>
                        <td><span className={`status-chip ${statusClass[workload.status]}`}>{workload.submitted ? workload.status : "scheduled"}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="panel benchmark-panel" id="experiments">
              <div className="section-heading">
                <div><p className="eyebrow">PAIRED EXPERIMENTS</p><h2>Does model guidance help?</h2><p className="section-subtitle">Same scenario seed, workload set, and constraints for every policy.</p></div>
                <div className="benchmark-actions">
                  <label className="seed-input"><span>Seeds</span><input value={benchmarkSeeds} onChange={(event) => setBenchmarkSeeds(event.target.value)} aria-label="Benchmark seeds, comma separated" /></label>
                  <button className="button button-primary" onClick={runBenchmark} disabled={busy}><Activity size={15} /> Run comparison</button>
                </div>
              </div>
              {benchmark ? (
                <>
                  <div className="benchmark-meta">
                    <span>{benchmark.runs.length} run records · seeds {benchmark.seeds.join(", ")}</span>
                    <span>{benchmark.live_model_enabled ? `Live inference requested · ${benchmark.model_id ?? "model ID not set"}` : "Offline mode · Nemotron label means deterministic fallback"}</span>
                    <button className="text-button" onClick={downloadJson}><ArrowDownToLine size={14} /> Export JSON</button>
                    <a className="text-button" href="/exports/latest.csv"><ArrowDownToLine size={14} /> Export CSV</a>
                  </div>
                  <div className="table-scroll">
                    <table className="benchmark-table">
                      <thead><tr><th>Policy</th><th>Horizon executions / total</th><th>Throughput<br /><small>jobs/hour</small></th><th>All-workload completion</th><th>SLA attainment</th><th>Deadline misses</th><th>Queue wait<br /><small>mean min</small></th><th>Energy<br /><small>estimated kWh</small></th><th>Cost<br /><small>estimated</small></th><th>AI latency<br /><small>mean ms</small></th><th>Fallbacks</th><th>Rejections</th></tr></thead>
                      <tbody>
                        {benchmark.policies.map((id) => {
                          const summary = benchmark.comparison[id];
                          return (
                            <tr key={id}>
                              <td><span className="policy-name">{POLICIES.find((item) => item.id === id)?.label ?? id}</span></td>
                              <td>
                                {summary?.successful_run_count ?? 0} / {summary?.run_count ?? 0}
                                <small>{summary?.failed_run_count ?? 0} simulation errors</small>
                              </td>
                              <td>{formatNumber(getMetric(summary, "throughput_jobs_per_hour"))}</td>
                              <td>{formatRate(getMetric(summary, "completion_rate_scenario_denominator"))}<small>{summary?.workload_totals.completed_workloads ?? 0} / {summary?.workload_totals.total_workloads ?? 0} jobs · {summary?.workload_totals.permanently_infeasible_workloads ?? 0} infeasible</small></td>
                              <td><span className="benchmark-value">{formatRate(getMetric(summary, "sla_attainment_rate"))}</span></td>
                              <td>{formatRate(getMetric(summary, "deadline_miss_rate"))}</td>
                              <td>{formatNumber(getMetric(summary, "average_queue_wait_minutes"))}</td>
                              <td>{formatNumber(getMetric(summary, "estimated_energy_kwh"), 4)}</td>
                              <td>${formatNumber(getMetric(summary, "estimated_energy_cost"), 4)}</td>
                              <td>{formatNumber(getMetric(summary, "ai_latency_ms_mean"), 1)}</td>
                              <td>{formatNumber(getMetric(summary, "ai_fallbacks"), 0)}</td>
                              <td>{formatNumber(getMetric(summary, "rejected_actions"), 0)}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                  <div className="paired-comparison">
                    <h3>Mean difference vs resource-aware on matched horizon executions</h3>
                    <div className="paired-grid">
                      {Object.entries(benchmark.paired_comparison_vs_resource_aware).map(([id, comparison]) => (
                        <div className="paired-card" key={id}>
                          <span>{POLICIES.find((item) => item.id === id)?.label ?? id}</span>
                          <strong>{comparison.paired_successful_run_count} paired run{comparison.paired_successful_run_count === 1 ? "" : "s"}</strong>
                          <small>Throughput Δ {formatNumber(comparison.mean_policy_minus_resource_aware.throughput_jobs_per_hour.mean_delta)} jobs/h · deadline attainment Δ {formatRate(comparison.mean_policy_minus_resource_aware.deadline_attainment_rate.mean_delta)}</small>
                        </div>
                      ))}
                    </div>
                  </div>
                  <p className="fineprint">Completed means the simulator reached its fixed horizon, not that all jobs finished. Full-workload denominators retain infeasible and unresolved jobs; paired deltas include only matched scenario/seed runs with identical failure traces. Nemotron is deterministic fallback unless live inference is explicitly selected. Energy cost is an estimate, not a cloud bill.</p>
                </>
              ) : (
                <div className="empty-state benchmark-empty"><Activity size={23} /><p>Run the fixed-seed policy suite to populate this comparison.</p><small>No sample benchmark numbers are shown as current session output.</small></div>
              )}
            </section>

            <section className="panel history-panel">
              <div className="section-heading">
                <div><p className="eyebrow">SESSION AUDIT</p><h2>Recent experiment history</h2></div>
                <button className="text-button" onClick={() => void runAction(refresh, "History refreshed.")} disabled={busy}><RefreshCw size={14} /> Refresh</button>
              </div>
              {history.length ? (
                <div className="history-list">
                  {history.slice(0, 8).map((run) => (
                    <div className="history-row" key={run.run_id}>
                      <span className={`history-status ${run.status === "completed" ? "history-ok" : "history-error"}`} />
                      <div><strong>{run.policy}</strong><small>{run.kind} · seed {run.seed}{run.scenario_sha256 ? ` · ${run.scenario_sha256.slice(0, 8)}` : ""}</small></div>
                      <span>{formatNumber(run.metrics?.completed_workloads, 0)} complete</span>
                      <span>{formatRate(run.metrics?.sla_attainment_rate)} SLA</span>
                      <span className="history-state">{run.status}</span>
                      <ChevronRight size={15} />
                    </div>
                  ))}
                </div>
              ) : <div className="empty-inline">No runs have been recorded in this process yet.</div>}
            </section>

            <footer className="footer">
              <span>GRIDMIND <i>SIMULATION ONLY</i></span>
              <span>State: {ready?.state_scope ?? "single-process-single-session"} · Power estimates are not telemetry</span>
              <a href="https://github.com/NEXE-sudo/gridmind-ai-infrastructure" target="_blank" rel="noreferrer">Source repository ↗</a>
            </footer>
          </>
        )}
      </div>
    </main>
  );
}
