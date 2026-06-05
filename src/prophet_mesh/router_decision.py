"""Router decision validation for Prophet Mesh."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = frozenset(
    {
        "request_id",
        "conductor_id",
        "principal",
        "task",
        "domain",
        "intent",
        "memory_scope",
        "selected_family",
        "selected_route",
        "route_type",
        "specialist_agents",
        "policy_decision",
        "rationale",
        "fallback_route",
        "evidence_event",
        "audit_ref",
        "controls",
    }
)

REQUIRED_CONTROLS = frozenset(
    {"identity", "policy", "evidence", "attestation", "revocation", "audit", "tenant_isolation"}
)

ALLOWED_POLICY_DECISIONS = frozenset({"allow", "deny", "requires_approval"})


@dataclass(frozen=True)
class RouterDecisionValidationResult:
    valid: bool
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": self.errors}


def load_router_decision(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("router decision must be a JSON object")
    return data


def validate_router_decision(data: dict[str, Any]) -> RouterDecisionValidationResult:
    errors: list[str] = []

    missing = REQUIRED_FIELDS - set(data)
    if missing:
        errors.append("missing fields: " + ", ".join(sorted(missing)))

    for key in sorted(REQUIRED_FIELDS - {"specialist_agents", "controls"}):
        if key in data and (not isinstance(data[key], str) or not data[key]):
            errors.append(f"{key} must be a non-empty string")

    agents = data.get("specialist_agents", [])
    if not isinstance(agents, list) or not agents:
        errors.append("specialist_agents must be a non-empty list")

    if data.get("policy_decision") not in ALLOWED_POLICY_DECISIONS:
        errors.append("policy_decision must be allow, deny, or requires_approval")

    controls = data.get("controls", {})
    if not isinstance(controls, dict):
        errors.append("controls must be an object")
        controls = {}

    missing_controls = REQUIRED_CONTROLS - set(controls)
    if missing_controls:
        errors.append("missing controls: " + ", ".join(sorted(missing_controls)))

    for control in sorted(REQUIRED_CONTROLS & set(controls)):
        if controls[control] is not True:
            errors.append(f"controls.{control} must be true")

    if data.get("task") == "email_reply" and data.get("policy_decision") == "allow":
        errors.append("email_reply must not be direct allow; use requires_approval or deny")

    if data.get("memory_scope") and "unscoped" in str(data["memory_scope"]):
        errors.append("memory_scope must not be unscoped")

    return RouterDecisionValidationResult(valid=not errors, errors=errors)


def validate_router_decision_file(path: str | Path) -> RouterDecisionValidationResult:
    return validate_router_decision(load_router_decision(path))
