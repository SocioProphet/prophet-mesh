"""Choir execution plan validation for Prophet Mesh."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = frozenset(
    {
        "plan_id",
        "request_id",
        "conductor_id",
        "principal",
        "task",
        "domain",
        "policy_decision",
        "router_decision_ref",
        "summary",
        "steps",
        "approval_boundary",
        "evidence_refs",
        "audit_refs",
        "controls",
    }
)

REQUIRED_STEP_FIELDS = frozenset(
    {"step_id", "agent", "action", "requires_approval", "evidence_required", "audit_required"}
)

REQUIRED_CONTROLS = frozenset(
    {"identity", "policy", "evidence", "attestation", "revocation", "audit", "tenant_isolation"}
)

ALLOWED_POLICY_DECISIONS = frozenset({"allow", "deny", "requires_approval"})


@dataclass(frozen=True)
class ChoirPlanValidationResult:
    """Validation result for a choir execution plan."""

    valid: bool
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": self.errors}


def load_choir_plan(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("choir execution plan must be a JSON object")
    return data


def validate_choir_plan(data: dict[str, Any]) -> ChoirPlanValidationResult:
    errors: list[str] = []

    missing = REQUIRED_FIELDS - set(data)
    if missing:
        errors.append("missing fields: " + ", ".join(sorted(missing)))

    for key in sorted(REQUIRED_FIELDS - {"steps", "evidence_refs", "audit_refs", "controls"}):
        if key in data and (not isinstance(data[key], str) or not data[key]):
            errors.append(f"{key} must be a non-empty string")

    if data.get("policy_decision") not in ALLOWED_POLICY_DECISIONS:
        errors.append("policy_decision must be allow, deny, or requires_approval")

    steps = data.get("steps", [])
    if not isinstance(steps, list) or not steps:
        errors.append("steps must be a non-empty list")
        steps = []
    approval_steps = 0
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            errors.append(f"steps[{index}] must be an object")
            continue
        missing_step = REQUIRED_STEP_FIELDS - set(step)
        if missing_step:
            errors.append(f"steps[{index}] missing fields: " + ", ".join(sorted(missing_step)))
        for key in ("step_id", "agent", "action"):
            if key in step and (not isinstance(step[key], str) or not step[key]):
                errors.append(f"steps[{index}].{key} must be a non-empty string")
        for key in ("requires_approval", "evidence_required", "audit_required"):
            if key in step and not isinstance(step[key], bool):
                errors.append(f"steps[{index}].{key} must be boolean")
        if step.get("evidence_required") is not True:
            errors.append(f"steps[{index}].evidence_required must be true")
        if step.get("audit_required") is not True:
            errors.append(f"steps[{index}].audit_required must be true")
        if step.get("requires_approval") is True:
            approval_steps += 1

    for key in ("evidence_refs", "audit_refs"):
        refs = data.get(key, [])
        if not isinstance(refs, list) or not refs:
            errors.append(f"{key} must be a non-empty list")

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

    if data.get("policy_decision") == "requires_approval" and approval_steps == 0:
        errors.append("requires_approval plans must include at least one approval step")
    if data.get("task") == "email_reply" and data.get("policy_decision") == "allow":
        errors.append("email_reply plans must not be direct allow")
    if str(data.get("approval_boundary", "")).lower() in {"", "none", "n/a"}:
        errors.append("approval_boundary must be explicit")

    return ChoirPlanValidationResult(valid=not errors, errors=errors)


def validate_choir_plan_file(path: str | Path) -> ChoirPlanValidationResult:
    return validate_choir_plan(load_choir_plan(path))
