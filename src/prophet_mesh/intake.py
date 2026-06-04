"""Premium customer intake validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_TOP_LEVEL_FIELDS = frozenset(
    {
        "customer",
        "agent_surface",
        "workflows",
        "authority",
        "memory",
        "connectors",
        "policy",
        "deployment",
        "evaluation",
    }
)

REQUIRED_AUTHORITY_FIELDS = frozenset(
    {
        "human_approval_required",
        "recommend_only",
        "execute_after_approval",
        "never_delegated",
    }
)

REQUIRED_TRUST_KERNEL_FIELDS = frozenset(
    {
        "identity_required",
        "evidence_required",
        "attestation_required",
        "revocation_required",
        "audit_required",
        "lifecycle_semantics_required",
    }
)


@dataclass(frozen=True)
class IntakeValidationResult:
    """Validation result for a premium customer intake artifact."""

    valid: bool
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": self.errors}


def load_intake(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("customer intake artifact must be a JSON object")
    return data


def _require_non_empty_list(data: dict[str, Any], key: str, errors: list[str]) -> None:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        errors.append(f"{key} must be a non-empty list")


def validate_intake(data: dict[str, Any]) -> IntakeValidationResult:
    """Validate a premium customer intake artifact.

    This intentionally avoids external JSON-schema dependencies so the contract can run anywhere the
    reference CLI runs. The JSON Schema in `specs/` is the published interoperability artifact; this
    validator is the operational guardrail for CI and demos.
    """

    errors: list[str] = []
    missing = REQUIRED_TOP_LEVEL_FIELDS - set(data)
    if missing:
        errors.append("missing required sections: " + ", ".join(sorted(missing)))

    customer = data.get("customer", {})
    if not isinstance(customer, dict):
        errors.append("customer must be an object")
    elif not customer.get("organization"):
        errors.append("customer.organization is required")

    agent_surface = data.get("agent_surface", {})
    if not isinstance(agent_surface, dict):
        errors.append("agent_surface must be an object")
    elif not agent_surface.get("requested_agent_name"):
        errors.append("agent_surface.requested_agent_name is required")

    workflows = data.get("workflows", {})
    if not isinstance(workflows, dict):
        errors.append("workflows must be an object")
    else:
        _require_non_empty_list(workflows, "target", errors)
        _require_non_empty_list(workflows, "excluded", errors)

    authority = data.get("authority", {})
    if not isinstance(authority, dict):
        errors.append("authority must be an object")
    else:
        missing_authority = REQUIRED_AUTHORITY_FIELDS - set(authority)
        if missing_authority:
            errors.append("missing authority fields: " + ", ".join(sorted(missing_authority)))
        for key in sorted(REQUIRED_AUTHORITY_FIELDS & set(authority)):
            if not isinstance(authority[key], list):
                errors.append(f"authority.{key} must be a list")

    memory = data.get("memory", {})
    if not isinstance(memory, dict):
        errors.append("memory must be an object")
    else:
        _require_non_empty_list(memory, "approved_sources", errors)
        if "customer_data_to_canonical_michael_state" not in memory:
            errors.append("memory.customer_data_to_canonical_michael_state is required")

    connectors = data.get("connectors", [])
    if not isinstance(connectors, list) or not connectors:
        errors.append("connectors must be a non-empty list")
    else:
        for index, connector in enumerate(connectors):
            if not isinstance(connector, dict):
                errors.append(f"connectors[{index}] must be an object")
                continue
            for key in ("name", "owner", "scope", "policy_gate", "revocation_path"):
                if not connector.get(key):
                    errors.append(f"connectors[{index}].{key} is required")

    policy = data.get("policy", {})
    if not isinstance(policy, dict):
        errors.append("policy must be an object")
    else:
        missing_kernel = REQUIRED_TRUST_KERNEL_FIELDS - set(policy)
        if missing_kernel:
            errors.append("missing policy trust-kernel fields: " + ", ".join(sorted(missing_kernel)))
        for key in sorted(REQUIRED_TRUST_KERNEL_FIELDS & set(policy)):
            if policy[key] is not True:
                errors.append(f"policy.{key} must be true")

    deployment = data.get("deployment", {})
    if not isinstance(deployment, dict):
        errors.append("deployment must be an object")
    else:
        if not deployment.get("topology"):
            errors.append("deployment.topology is required")
        if not deployment.get("identity_provider"):
            errors.append("deployment.identity_provider is required")

    evaluation = data.get("evaluation", {})
    if not isinstance(evaluation, dict):
        errors.append("evaluation must be an object")
    else:
        _require_non_empty_list(evaluation, "benchmark_tasks", errors)
        _require_non_empty_list(evaluation, "acceptance_criteria", errors)

    return IntakeValidationResult(valid=not errors, errors=errors)


def validate_intake_file(path: str | Path) -> IntakeValidationResult:
    return validate_intake(load_intake(path))
