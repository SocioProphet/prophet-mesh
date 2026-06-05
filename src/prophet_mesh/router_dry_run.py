"""Deterministic router dry-run for Prophet Mesh."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from prophet_mesh.model_policy import load_model_task_policy
from prophet_mesh.router_decision import RouterDecisionValidationResult, validate_router_decision


@dataclass(frozen=True)
class RouterDryRunResult:
    """Dry-run result containing a generated router decision and validation errors."""

    decision: dict[str, Any]
    validation: RouterDecisionValidationResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "validation": self.validation.to_dict(),
        }


def load_router_request(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("router request must be a JSON object")
    return data


def _task_route(policy: dict[str, Any], task: str) -> dict[str, Any]:
    routes = policy.get("task_routes", [])
    if not isinstance(routes, list):
        return {}
    for route in routes:
        if isinstance(route, dict) and route.get("task") == task:
            return route
    return {}


def _preferred_model(policy: dict[str, Any], family_name: str) -> str:
    family = policy.get("model_families", {}).get(family_name, {})
    preferred = family.get("preferred", []) if isinstance(family, dict) else []
    if not isinstance(preferred, list) or not preferred:
        return "unresolved.route"
    first = preferred[0]
    return first if isinstance(first, str) else "unresolved.route"


def _fallback_model(policy: dict[str, Any], family_name: str) -> str:
    family = policy.get("model_families", {}).get(family_name, {})
    preferred = family.get("preferred", []) if isinstance(family, dict) else []
    if isinstance(preferred, list) and len(preferred) > 1 and isinstance(preferred[1], str):
        return preferred[1]
    if isinstance(preferred, list) and preferred and isinstance(preferred[0], str):
        return preferred[0]
    return "unresolved.fallback"


def dry_run_router_decision(request: dict[str, Any], policy: dict[str, Any]) -> RouterDryRunResult:
    """Generate a deterministic router decision without invoking any external model or tool."""

    task = str(request.get("task", ""))
    route = _task_route(policy, task)
    primary_family = str(route.get("primary_family", "hosted_balanced"))
    private_family = str(route.get("private_family", primary_family))
    privacy_mode = str(request.get("privacy_mode", "hosted_allowed"))
    selected_family = private_family if privacy_mode in {"private", "local", "self_hosted"} else primary_family
    selected_route = _preferred_model(policy, selected_family)
    fallback_route = _fallback_model(policy, selected_family)
    specialist_agents = route.get("specialist_agents", []) if isinstance(route, dict) else []
    if not isinstance(specialist_agents, list) or not specialist_agents:
        specialist_agents = ["governance-sentinel"]

    policy_decision = "requires_approval" if task in {"email_reply", "operations_plan"} else "allow"
    route_type = "specialist_agent" if selected_family.endswith("specialist") else "hosted_frontier"
    request_id = str(request.get("request_id", "req-router-dry-run"))

    decision = {
        "request_id": request_id,
        "conductor_id": str(request.get("conductor_id", "michael-agent")),
        "principal": str(request.get("principal", "principal:unknown")),
        "task": task,
        "domain": str(request.get("domain", route.get("domain", "unknown"))),
        "intent": str(request.get("intent", "route request through Prophet Mesh")),
        "memory_scope": str(request.get("memory_scope", "relationship_context:approved")),
        "selected_family": selected_family,
        "selected_route": selected_route,
        "route_type": route_type,
        "specialist_agents": specialist_agents,
        "policy_decision": policy_decision,
        "rationale": f"Task {task!r} routes through family {selected_family!r} under conductor policy.",
        "fallback_route": fallback_route,
        "evidence_event": f"evidence:event:{request_id}",
        "audit_ref": f"audit:{request_id}",
        "controls": {
            "identity": True,
            "policy": True,
            "evidence": True,
            "attestation": True,
            "revocation": True,
            "audit": True,
            "tenant_isolation": True,
        },
    }
    validation = validate_router_decision(decision)
    return RouterDryRunResult(decision=decision, validation=validation)


def dry_run_router_decision_file(request_path: str | Path, policy_path: str | Path) -> RouterDryRunResult:
    return dry_run_router_decision(load_router_request(request_path), load_model_task_policy(policy_path))
