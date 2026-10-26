import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import GridMindConsole from "./GridMindConsole";

const simulationState = (step: number) => ({
  step,
  seed: 42,
  power_budget_kw: 7.8,
  queue_depth: 1,
  nodes: [],
  workloads: [],
  metrics: {
    queued_workloads: 1,
    running_workloads: 0,
    completed_workloads: 0,
    failed_workloads: 0,
    unfinished_workloads: 1,
    deadline_misses: 0,
    deadline_miss_rate: 0,
    throughput_jobs_per_hour: 0,
    current_gpu_utilization: 0,
    current_memory_utilization: 0,
    estimated_power_kw: 0,
    power_budget_kw: 7.8,
    estimated_energy_kwh: 0,
    estimated_energy_cost: 0,
  },
});

function jsonResponse(payload: unknown) {
  return {
    ok: true,
    status: 200,
    statusText: "OK",
    json: async () => payload,
  };
}

const placementDecision = {
  step: 1,
  decision: "resource_aware",
  explanation: "Priority/deadline ordering with best-fit node packing under power limits.",
  proposal_status: "deterministic",
  proposed_assignments: {},
  executed_assignments: { "infer-001": "gpu-a" },
  proposal_validation_rejections: [],
  scheduling_diagnostics: [],
  placement_diagnostics: [{
    workload_id: "infer-001",
    node_id: "gpu-a",
    assignment_source: "deterministic_scheduler",
    policy: "resource_aware",
    queue_rank: 1,
    priority: 3,
    deadline_step: 12,
    selection_rule: "max_post_placement_gpu_fill_then_lexicographically_largest_node_id",
    candidate_nodes: [{
      node_id: "gpu-a",
      projected_gpu_fill: 0.5,
      free_gpus_before: 2,
      free_memory_gb_before: 32,
      power_delta_kw: 0.4,
      projected_node_power_kw: 0.5,
      projected_facility_power_kw: 1,
      selected: true,
    }],
  }],
  rejected_actions: [],
  fallback_used: false,
};

describe("GridMindConsole", () => {
  beforeEach(() => {
    let step = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const path = String(input);
        if (path === "/state") return jsonResponse(simulationState(step));
        if (path === "/ready") {
          return jsonResponse({ status: "ready", model_configured: false });
        }
        if (path.startsWith("/history")) return jsonResponse({ runs: [] });
        if (path === "/run") {
          step += 1;
          return jsonResponse({
            fallback_used: false,
            steps_executed: 1,
            history: [{
              step,
              decision: "resource_aware",
              explanation: "The deterministic policy selected an eligible placement.",
              proposal_status: "deterministic",
              proposed_assignments: {},
              executed_assignments: placementDecision.executed_assignments,
              proposal_validation_rejections: [],
              scheduling_diagnostics: [],
              placement_diagnostics: placementDecision.placement_diagnostics,
              rejected_actions: [],
              fallback_used: false,
            }],
          });
        }
        if (path === "/reset") return jsonResponse(simulationState(0));
        throw new Error(`Unexpected API request: ${path}`);
      }),
    );
  });

  it("loads state and steps the selected deterministic policy", async () => {
    render(<GridMindConsole />);
    expect(await screen.findByText("Infrastructure at a glance.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Step" }));

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Completed 1 step(s) using resource_aware.",
    );
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/run",
      expect.objectContaining({ method: "POST" }),
    );
    await waitFor(() => expect(screen.getByLabelText(/Simulation step 1/)).toBeInTheDocument());
    expect(await screen.findByText(/infer-001 → gpu-a/)).toBeInTheDocument();
    expect(screen.getByText(/GPU fill 50.0%/)).toBeInTheDocument();
  });

  it("restores the most recent decision trace from API history", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const path = String(input);
        if (path === "/state") return jsonResponse(simulationState(1));
        if (path === "/ready") {
          return jsonResponse({ status: "ready", model_configured: false });
        }
        if (path.startsWith("/history")) {
          return jsonResponse({
            runs: [{ kind: "simulation", decision_trace: [placementDecision] }],
          });
        }
        throw new Error(`Unexpected API request: ${path}`);
      }),
    );

    render(<GridMindConsole />);
    expect(await screen.findByText(/infer-001 → gpu-a/)).toBeInTheDocument();
    expect(screen.getByText(/max post placement gpu fill then lexicographically largest node id/i)).toBeInTheDocument();
  });

  it("submits selected scenario parameters on reset", async () => {
    render(<GridMindConsole />);
    await screen.findByText("Infrastructure at a glance.");
    fireEvent.change(screen.getByLabelText("Scenario"), {
      target: { value: "node_failure_recovery" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Reset/ }));

    await screen.findByText("Scenario reset with seed 42.");
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/reset",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ seed: 42, scenario: "node_failure_recovery" }),
      }),
    );
  });
});
