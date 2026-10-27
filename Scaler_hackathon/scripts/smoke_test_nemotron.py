"""Opt-in, sanitized Nebius catalogue and Nemotron inference verification."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime

from server.datacenter_simulator import DatacenterSimulator
from server.nemotron import (
    configured_base_url,
    configured_inference_timeout_seconds,
    request_proposal,
    verify_catalogue_model,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Explicitly authorize a real Token Factory API request.",
    )
    parser.add_argument(
        "--catalogue",
        action="store_true",
        help="Only query the authenticated /models catalogue; do not run inference.",
    )
    args = parser.parse_args(argv)
    if not args.live:
        print("REFUSED: pass --live to authorize a real provider request.")
        return 2

    api_key = os.getenv("NEBIUS_API_KEY")
    model_id = os.getenv("GRIDMIND_MODEL")
    if not api_key or not model_id:
        print("BLOCKED: set NEBIUS_API_KEY and GRIDMIND_MODEL; no request was made.")
        return 2
    if (
        model_id != model_id.strip()
        or any(ord(char) < 32 for char in model_id)
        or len(model_id) > 200
        or api_key in model_id
        or not model_id.casefold().startswith("nvidia/")
        or "nemotron" not in model_id.casefold()
    ):
        print("BLOCKED: GRIDMIND_MODEL must be an exact NVIDIA Nemotron catalogue ID.")
        return 2

    try:
        timeout_seconds = configured_inference_timeout_seconds()
        configured_base_url()
    except ValueError:
        print("BLOCKED: provider configuration is invalid; no request was made.")
        return 2

    print(
        "provider=Nebius Token Factory host=api.tokenfactory.nebius.com "
        f"timeout_seconds={timeout_seconds:g}"
    )
    print(f"configured_model_id={model_id}")
    print(f"test_time_utc={datetime.now(UTC).isoformat()}")
    try:
        available = verify_catalogue_model(
            model_id, api_key, timeout=min(timeout_seconds, 10.0)
        )
    except RuntimeError:
        print("catalogue_status=failed (details sanitized)")
        return 1
    if not available:
        print("catalogue_status=model_not_listed")
        return 1
    print("catalogue_status=verified_exact_match")
    if args.catalogue:
        return 0

    sim = DatacenterSimulator(seed=17)
    proposal = request_proposal(sim.state())
    rejection_reasons = sim.validate_assignments(proposal.assignments)
    proposal_valid = bool(proposal.assignments) and not rejection_reasons
    live_success = proposal.used_model and proposal_valid
    evidence = {
        "provider_request_status": (
            "success" if proposal.response_received else "failed"
        ),
        "inference_status": (
            "live_success"
            if live_success
            else "invalid_model_proposal"
            if proposal.used_model or proposal.response_received
            else "live_failure"
        ),
        "model_id": proposal.model_id,
        "latency_ms": proposal.latency_ms,
        "request_attempts": proposal.request_attempts,
        "retry_count": max(0, proposal.request_attempts - 1),
        "prompt_tokens": proposal.prompt_tokens,
        "completion_tokens": proposal.completion_tokens,
        "error_code": proposal.error_code,
        "proposal_validated": proposal_valid,
        "validation_reasons": rejection_reasons,
        "test_time_utc": datetime.now(UTC).isoformat(),
        "note": "Proposal is not executed; only simulator code may apply it.",
    }
    print(json.dumps(evidence, indent=2))
    return 0 if live_success else 1


if __name__ == "__main__":
    sys.exit(main())
