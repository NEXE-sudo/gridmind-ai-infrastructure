export type PolicyId = "fifo" | "priority" | "resource_aware" | "nemotron";
export type ScenarioId =
  | "standard"
  | "workload_surge"
  | "node_failure"
  | "tight_deadlines"
  | "balanced"
  | "burst_arrivals"
  | "mixed_priority_deadlines"
  | "heterogeneous_gpu_types"
  | "gpu_memory_pressure"
  | "tight_power_budget"
  | "node_failure_recovery"
  | "short_long_contention"
  | "infeasible_workloads"
  | "combined_stress";
export type WorkloadStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

export interface NodeState {
  id: string;
  gpu_model: string;
  gpu_count: number;
  memory_gb: number;
  allocated_gpus: number;
  allocated_memory_gb: number;
  workloads: string[];
  available: boolean;
  recover_at_step: number | null;
  utilization: number;
  memory_utilization: number;
  estimated_power_kw: number;
  power_limit_kw: number;
}

export interface WorkloadState {
  id: string;
  name: string;
  gpu_count: number;
  memory_gb: number;
  duration: number;
  priority: number;
  workload_class: string;
  required_gpu_model: string | null;
  deadline: number | null;
  submission_time: number;
  submitted: boolean;
  status: WorkloadStatus;
  node_id: string | null;
  remaining: number;
  started_at: number | null;
  completed_at: number | null;
  failure_reason: string | null;
  failed_at: number | null;
  last_scheduling_reason: string | null;
  last_scheduling_step: number | null;
  scheduling_skip_counts: Record<string, number>;
}

export interface OperationalMetrics {
  total_workloads: number;
  submitted_workloads: number;
  not_yet_arrived_workloads: number;
  completed_workloads: number;
  failed_workloads: number;
  permanently_infeasible_workloads: number;
  cancelled_workloads: number;
  unfinished_workloads: number;
  unresolved_workloads: number;
  horizon_incomplete_workloads: number | null;
  completion_rate: number | null;
  completion_rate_scenario_denominator: number | null;
  feasible_scenario_completion_rate: number | null;
  queued_workloads: number;
  running_workloads: number;
  throughput_jobs_per_hour: number;
  deadline_misses: number;
  deadline_miss_denominator: number;
  deadline_miss_rate: number | null;
  deadline_attainment_rate: number | null;
  sla_attainment_rate: number | null;
  average_queue_wait_minutes: number | null;
  p95_queue_wait_minutes: number | null;
  average_turnaround_minutes: number | null;
  current_gpu_utilization: number;
  average_gpu_utilization: number;
  current_memory_utilization: number;
  estimated_power_kw: number;
  power_budget_kw: number;
  estimated_energy_kwh: number;
  estimated_energy_cost: number;
  rejected_actions: number;
  resource_rejections: number;
  node_power_rejections: number;
  facility_power_rejections: number;
  power_budget_violations: number;
  failed_nodes: number;
  recovered_nodes: number;
  workloads_requeued: number;
  workloads_preempted: number;
  starved_workloads: number;
  ai_attempts: number;
  ai_invocations: number;
  ai_request_attempts?: number;
  ai_retries?: number;
  ai_failures: number;
  ai_fallbacks: number;
  ai_valid_responses?: number;
  ai_invalid_proposals: number;
  ai_latency_ms_mean: number | null;
  ai_prompt_tokens?: number | null;
  ai_prompt_token_reports?: number;
  ai_completion_tokens?: number | null;
  ai_completion_token_reports?: number;
}

export interface SimulationState {
  step: number;
  seed: number;
  horizon_steps: number | null;
  scenario?: ScenarioId;
  power_budget_kw: number;
  queue_depth: number;
  nodes: NodeState[];
  workloads: WorkloadState[];
  metrics: OperationalMetrics;
}

export interface DecisionRecord {
  step: number;
  decision: string;
  explanation: string;
  proposal_status: string;
  inference_mode?: string;
  proposal_latency_ms?: number | null;
  proposal_request_attempts?: number;
  proposal_retry_count?: number;
  proposal_response_received?: boolean;
  proposal_prompt_tokens?: number | null;
  proposal_completion_tokens?: number | null;
  proposed_assignments: Record<string, string>;
  executed_assignments: Record<string, string>;
  proposal_validation_rejections: Array<{ workload_id: string; reason: string }>;
  scheduling_diagnostics: Array<{
    workload_id: string;
    reason: string;
    node_reasons: Record<string, string | null>;
  }>;
  rejected_actions: Array<{ workload_id: string; reason: string }>;
  fallback_used: boolean;
}

export interface RunRecord {
  run_id: string;
  kind: string;
  policy: string;
  seed: number;
  status: string;
  metrics: OperationalMetrics;
  created_at?: string;
  scenario_sha256?: string;
}

export interface BenchmarkRun {
  run_id: string;
  policy: PolicyId;
  seed: number;
  status: "completed" | "failed";
  steps_executed: number;
  metrics: OperationalMetrics;
}

export interface BenchmarkResult {
  created_at: string;
  seeds: number[];
  policies: PolicyId[];
  live_model_enabled: boolean;
  model_id: string | null;
  schema_version: number;
  runs: BenchmarkRun[];
  comparison: Record<string, {
    run_count: number;
    successful_run_count: number;
    failed_run_count: number;
    incomplete_run_count: number;
    run_status_counts: Record<string, number>;
    workload_totals: Record<string, number>;
    horizon_incomplete_reason_totals: Record<string, number>;
    metrics: Record<string, { mean: number | null; n: number }>;
  }>;
  paired_comparison_vs_resource_aware: Record<string, {
    paired_successful_seed_count: number;
    paired_successful_run_count: number;
    mean_policy_minus_resource_aware: Record<string, { mean_delta: number | null; n: number }>;
  }>;
}

const API_BASE = import.meta.env.VITE_API_URL ?? "";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      message = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      // Keep the HTTP status as the useful fallback for non-JSON server errors.
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`;
export const formatNumber = (value: number | null | undefined, digits = 2) =>
  value == null ? "—" : value.toLocaleString(undefined, { maximumFractionDigits: digits });
