"""End-to-end execution trace validation for Prophet Mesh."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = frozenset(
    {
        "trace_id",
        "request_id",
        "conductor_id",
        "principal",
        "task",
        "router_decision_ref",
        "choir_plan_ref",
        "conductor_response_ref",
        "lifecycle",
        "status",
        "evidence_refs",
        "audit_refs",
        "approval_state",
        "controls",
    }
)

REQUIRED_CONTROLS = frozenset(
    {"identity", "policy", "evidence", "attestation", "revocation", "audit", "tenant_isolation"}
)

ALLOWED_STATUS = frozenset({"draft", "awaiting_approval", "approved", "completed", "refused", "escalated"})
ALLOWED_LIFECYCLE = frozenset({"Draft", "Bound", "Built", "Attested", "Deployed", "Serving", "Degraded", "Retired"})


@dataclass(frozen=True)
class ExecutionTraceValidationResult:
    """Validation result for an end-to-end execution trace."""

    valid: bool
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": self.errors}


def load_execution_trace(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("execution trace must be a JSON object")
    return data


def validate_execution_trace(data: dict[str, Any]) -> ExecutionTraceValidationResult:
    errors: list[str] = []

    missing = REQUIRED_FIELDS - set(data)
    if missing:
        errors.append("missing fields: " + ", ".join(sorted(missing)))

    for key in sorted(REQUIRED_FIELDS - {"evidence_refs", "audit_refs", "approval_state", "controls"}):
        if key in data and (not isinstance(data[key], str) or not data[key]):
            errors.append(f"{key} must be a non-empty string")

    if data.get("status") not in ALLOWED_STATUS:
        errors.append("status must be draft, awaiting_approval, approved, completed, refused, or escalated")
    if data.get("lifecycle") not in ALLOWED_LIFECYCLE:
        errors.append("lifecycle is not a recognized Prophet Mesh lifecycle state")

    for key in ("evidence_refs", "audit_refs"):
        value = data.get(key, [])
        if not isinstance(value, list) or not value:
            errors.append(f"{key} must be a non-empty list")

    approval_state = data.get("approval_state", {})
    if not isinstance(approval_state, dict):
        errors.append("approval_state must be an object")
        approval_state = {}
    if "required" not in approval_state or not isinstance(approval_state.get("required"), bool):
        errors.append("approval_state.required must be boolean")
    pending = approval_state.get("pending", [])
    if not isinstance(pending, list):
        errors.append("approval_state.pending must be a list")
        pending = []

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

    if data.get("task") == "email_reply":
        if data.get("status") == "completed" and approval_state.get("required") is False:
            errors.append("email_reply traces must not complete without an approval requirement")
        if data.get("status") == "awaiting_approval" and not pending:
            errors.append("awaiting_approval traces must include pending approvals")

    return ExecutionTraceValidationResult(valid=not errors, errors=errors)


def validate_execution_trace_file(path: str | Path) -> ExecutionTraceValidationResult:
    return validate_execution_trace(load_execution_trace(path))
