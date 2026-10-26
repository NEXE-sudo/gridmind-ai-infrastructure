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
              executed_assignments: {},
              proposal_validation_rejections: [],
              scheduling_diagnostics: [],
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

  it("enables live scheduling only after the confirmation-gated model check", async () => {
    let verified = false;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const path = String(input);
        if (path === "/state") return jsonResponse(simulationState(0));
        if (path === "/ready") {
          return jsonResponse({
            status: "ready",
            model_configured: true,
            model_verification_status: verified ? "live_success" : "not_attempted",
          });
        }
        if (path.startsWith("/history")) return jsonResponse({ runs: [] });
        if (path === "/model/verify") {
          verified = true;
          return jsonResponse({ status: "live_success" });
        }
        throw new Error(`Unexpected API request: ${path}`);
      }),
    );
    render(<GridMindConsole />);
    await screen.findByText("Infrastructure at a glance.");
    fireEvent.change(screen.getByLabelText("Policy"), {
      target: { value: "nemotron" },
    });

    const liveToggle = screen.getByRole("checkbox", { name: "Request live model" });
    expect(liveToggle).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Verify model · 1 live request" }));

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Catalogue and one live Nemotron request verified",
    );
    await waitFor(() => expect(liveToggle).toBeEnabled());
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/model/verify",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ confirm_live_request: true }),
      }),
    );
  });
});
