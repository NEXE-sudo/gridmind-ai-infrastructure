"""Deterministic baselines and optional Nebius-hosted Nemotron proposals."""
from __future__ import annotations

import json
import logging
import os

from .datacenter_simulator import DatacenterSimulator

logger = logging.getLogger(__name__)


def schedule(sim: DatacenterSimulator, policy: str = "resource_aware") -> dict[str,str]:
    pending = [w for w in sim.workloads if w.status == "pending"]
    if policy == "fifo":
        pass
    elif policy in {"priority","resource_aware"}:
        pending.sort(key=lambda w:(-w.priority,w.deadline if w.deadline is not None else 10**9,
                                   -(w.gpu_count*w.memory_gb) if policy=="resource_aware" else 0,w.id))
    else: raise ValueError(f"Unknown scheduler policy: {policy}")
    reserved = {n.id:[n.allocated_gpus,n.allocated_memory_gb] for n in sim.nodes}
    power = sum(n.power_kw for n in sim.nodes)
    out = {}
    for w in pending:
        options=[]
        for n in sim.nodes:
            g,m=reserved[n.id]
            if (
                n.available
                and g + w.gpu_count <= n.gpu_count
                and m + w.memory_gb <= n.memory_gb
                and n.idle_kw + n.per_gpu_kw * (g + w.gpu_count) <= n.power_limit_kw
            ):
                delta=n.per_gpu_kw*w.gpu_count
                if power+delta<=sim.power_budget_kw:
                    options.append(((g+w.gpu_count)/n.gpu_count,n.id,delta))
        if options:
            _,nid,delta=max(options,key=lambda x:(x[0],x[1]))
            n=next(x for x in sim.nodes if x.id==nid)
            reserved[nid][0]+=w.gpu_count; reserved[nid][1]+=w.memory_gb
            power+=delta; out[w.id]=nid
    return out

def nemotron_propose(state: dict) -> dict[str,str]:
    """Request a proposal; all placements are validated by the simulator."""
    key=os.getenv("NEBIUS_API_KEY")
    if not key:
        logger.info("Nebius credentials are not configured; deterministic fallback will be used")
        return {}

    try:
        from openai import OpenAI, OpenAIError
    except ImportError as exc:
        logger.warning(
            "OpenAI client is unavailable (%s); deterministic fallback will be used",
            type(exc).__name__,
        )
        return {}

    try:
        client=OpenAI(api_key=key,base_url=os.getenv("NEBIUS_BASE_URL","https://api.tokenfactory.nebius.com/v1/"),timeout=20,max_retries=1)
        data={"nodes":[{"id":n["id"],"free_gpus":n["gpu_count"]-n["allocated_gpus"],"free_memory_gb":n["memory_gb"]-n["allocated_memory_gb"],"available":n["available"]} for n in state["nodes"]],
              "pending":[{"id":w["id"],"gpu_count":w["gpu_count"],"memory_gb":w["memory_gb"],"priority":w["priority"],"deadline":w["deadline"]} for w in state["workloads"] if w["status"]=="pending"],
              "power_budget_kw":state["power_budget_kw"]}
        response=client.chat.completions.create(model=os.getenv("GRIDMIND_MODEL","nvidia/NVIDIA-Nemotron-Nano-9B-v2"),temperature=0,max_tokens=500,
            messages=[{"role":"system","content":"Return only JSON: {\"assignments\":{\"workload-id\":\"node-id\"}}. Do not invent IDs. Output is only a proposal."},
                      {"role":"user","content":json.dumps(data)}])
        content = response.choices[0].message.content
        if not isinstance(content, str):
            logger.warning("Nemotron returned an empty or non-text proposal; deterministic fallback will be used")
            return {}
        parsed = json.loads(content)
        if (
            not isinstance(parsed, dict)
            or set(parsed) != {"assignments"}
            or not isinstance(parsed["assignments"], dict)
            or any(not isinstance(k, str) or not isinstance(v, str) for k, v in parsed["assignments"].items())
        ):
            logger.warning("Nemotron returned a malformed proposal; deterministic fallback will be used")
            return {}
        return parsed["assignments"]
    except (
        OpenAIError,
        AttributeError,
        IndexError,
        TypeError,
        ValueError,
    ) as exc:
        logger.warning(
            "Nemotron proposal failed (%s); deterministic fallback will be used",
            type(exc).__name__,
        )
        return {}
