"""Verify a configured Nemotron ID in Nebius' live catalogue and make one call."""
from __future__ import annotations

import argparse
import json
import os
import sys

from server.datacenter_simulator import DatacenterSimulator
from server.nemotron import request_proposal, verify_catalogue_model


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalogue",
        action="store_true",
        help="Only query the authenticated /models catalogue; do not run inference.",
    )
    args = parser.parse_args()
    api_key = os.getenv("NEBIUS_API_KEY")
    model_id = os.getenv("GRIDMIND_MODEL")
    if not api_key or not model_id:
        print("BLOCKED: set NEBIUS_API_KEY and GRIDMIND_MODEL; no request was made.")
        return 2
    try:
        available = verify_catalogue_model(model_id, api_key)
    except RuntimeError as exc:
        print(f"CATALOGUE_CHECK_FAILED: {exc}")
        return 1
    if not available:
        print(f"MODEL_NOT_LISTED: exact model ID is absent from /v1/models: {model_id}")
        return 1
    print(f"CATALOGUE_VERIFIED: {model_id}")
    if args.catalogue:
        return 0

    state = DatacenterSimulator(seed=17).state()
    proposal = request_proposal(state)
    print(
        json.dumps(
            {
                "inference_status": proposal.status,
                "model_id": proposal.model_id,
                "latency_ms": proposal.latency_ms,
                "prompt_tokens": proposal.prompt_tokens,
                "completion_tokens": proposal.completion_tokens,
                "error_code": proposal.error_code,
                "proposal_valid_json": proposal.status == "model",
                "note": "Proposal is not executed; only simulator code may validate and apply it.",
            },
            indent=2,
        )
    )
    if not proposal.used_model:
        print("INFERENCE_FAILED: inspect the status above; no successful model call is claimed.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
