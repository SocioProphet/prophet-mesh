"""Conductor response envelope validation for Prophet Mesh."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = frozenset(
    {
        "response_id",
        "plan_id",
        "request_id",
        "conductor_id",
        "principal",
        "task",
        "status",
        "summary",
        "message",
        "evidence_refs",
        "audit_refs",
        "pending_approvals",
        "next_actions",
        "escalation",
        "controls",
    }
)

REQUIRED_CONTROLS = frozenset(
    {"identity", "policy", "evidence", "attestation", "revocation", "audit", "tenant_isolation"}
)

ALLOWED_STATUS = frozenset({"draft", "awaiting_approval", "approved", "completed", "refused", "escalated"})


@dataclass(frozen=True)
class ConductorResponseValidationResult:
    """Validation result for a conductor response envelope."""

    valid: bool
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": self.errors}


def load_conductor_response(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("conductor response must be a JSON object")
    return data


def validate_conductor_response(data: dict[str, Any]) -> ConductorResponseValidationResult:
    errors: list[str] = []

    missing = REQUIRED_FIELDS - set(data)
    if missing:
        errors.append("missing fields: " + ", ".join(sorted(missing)))

    for key in sorted(REQUIRED_FIELDS - {"evidence_refs", "audit_refs", "pending_approvals", "next_actions", "escalation", "controls"}):
        if key in data and (not isinstance(data[key], str) or not data[key]):
            errors.append(f"{key} must be a non-empty string")

    status = data.get("status")
    if status not in ALLOWED_STATUS:
        errors.append("status must be draft, awaiting_approval, approved, completed, refused, or escalated")

    for key in ("evidence_refs", "audit_refs", "next_actions"):
        value = data.get(key, [])
        if not isinstance(value, list) or not value:
            errors.append(f"{key} must be a non-empty list")

    pending = data.get("pending_approvals", [])
    if not isinstance(pending, list):
        errors.append("pending_approvals must be a list")
        pending = []

    escalation = data.get("escalation", {})
    if not isinstance(escalation, dict):
        errors.append("escalation must be an object")
        escalation = {}
    if "required" not in escalation or not isinstance(escalation.get("required"), bool):
        errors.append("escalation.required must be boolean")
    if not isinstance(escalation.get("reason"), str) or not escalation.get("reason"):
        errors.append("escalation.reason must be a non-empty string")

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

    if data.get("task") == "email_reply" and data.get("status") in {"approved", "completed", "sent"}:
        if not pending and not data.get("audit_refs"):
            errors.append("email_reply completion requires approval and audit trace")

    if data.get("task") == "email_reply" and data.get("status") == "sent":
        errors.append("status sent is not allowed; use awaiting_approval, approved, completed, refused, or escalated")

    if data.get("status") == "awaiting_approval" and not pending:
        errors.append("awaiting_approval responses must include pending approvals")

    return ConductorResponseValidationResult(valid=not errors, errors=errors)


def validate_conductor_response_file(path: str | Path) -> ConductorResponseValidationResult:
    return validate_conductor_response(load_conductor_response(path))
