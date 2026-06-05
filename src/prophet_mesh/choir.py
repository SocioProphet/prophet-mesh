"""Agent Choir validation for Prophet Mesh.

The choir contract keeps Prophet Mesh from collapsing into a single-agent product.
Michael is the default conductor, but the commercial unit is the conductor plus
specialist choir, routed through the model router and constrained by the trust
kernel.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REQUIRED_INVARIANTS = frozenset(
    {
        "conductor_first_experience",
        "agent_choir_not_single_agent",
        "single_model_router_interface",
        "relationship_aware_memory",
        "customer_named_conductors",
        "open_mesh_model_family",
        "trust_kernel_inherited",
        "no_trust_kernel_bypass",
    }
)

REQUIRED_TRUST_KERNEL = frozenset(
    {"identity", "policy", "evidence", "attestation", "revocation", "audit"}
)

REQUIRED_CONDUCTOR_RESPONSIBILITIES = frozenset(
    {
        "chat_and_clarify",
        "maintain_relationship_context",
        "maintain_operator_preferences",
        "route_to_models_and_agents",
        "delegate_to_specialists",
        "synthesize_choir_outputs",
        "enforce_authority_boundaries",
        "preserve_trust_kernel",
    }
)

REQUIRED_CHOIR_ROLES = frozenset(
    {
        "memory-steward",
        "router-agent",
        "research-agent",
        "planning-agent",
        "writing-agent",
        "coding-agent",
        "analytics-agent",
        "operations-agent",
        "creative-agent",
        "governance-sentinel",
    }
)

REQUIRED_PREMIUM_CONTROLS = frozenset(
    {
        "conductor_name",
        "conductor_voice",
        "domain_memory",
        "specialist_agent_roster",
        "tool_allowlist",
        "model_allowlist",
        "workflow_catalog",
        "deployment_topology",
    }
)

REQUIRED_PREMIUM_REQUIRED_CONTROLS = frozenset(
    {
        "identity",
        "evidence",
        "policy",
        "attestation",
        "revocation",
        "audit",
        "tenant_isolation",
        "evaluation_report",
    }
)


@dataclass(frozen=True)
class ChoirValidationResult:
    """Validation result for an Agent Choir spec artifact."""

    valid: bool
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": self.errors}


def load_choir_spec(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("agent choir spec must be a YAML object")
    return data


def _as_list(data: dict[str, Any], key: str, errors: list[str]) -> list[Any]:
    value = data.get(key, [])
    if not isinstance(value, list):
        errors.append(f"{key} must be a list")
        return []
    return value


def _missing(label: str, required: frozenset[str], values: list[Any], errors: list[str]) -> None:
    present = {value for value in values if isinstance(value, str)}
    missing = required - present
    if missing:
        errors.append(f"missing {label}: " + ", ".join(sorted(missing)))


def validate_choir_spec(data: dict[str, Any]) -> ChoirValidationResult:
    """Validate the Prophet Mesh Agent Choir spec."""

    errors: list[str] = []

    if data.get("name") != "prophet-mesh-agent-choir":
        errors.append("name must be prophet-mesh-agent-choir")
    if data.get("product") != "Prophet Mesh":
        errors.append("product must be Prophet Mesh")
    if data.get("primary_repo") != "SocioProphet/prophet-mesh":
        errors.append("primary_repo must be SocioProphet/prophet-mesh")
    if data.get("primary_conductor") != "Michael Agent":
        errors.append("primary_conductor must be Michael Agent")

    _missing("invariants", REQUIRED_INVARIANTS, _as_list(data, "invariants", errors), errors)
    _missing("trust_kernel entries", REQUIRED_TRUST_KERNEL, _as_list(data, "trust_kernel", errors), errors)

    conductor = data.get("conductor", {})
    if not isinstance(conductor, dict):
        errors.append("conductor must be an object")
        conductor = {}
    if conductor.get("default") != "Michael Agent":
        errors.append("conductor.default must be Michael Agent")
    _missing(
        "conductor responsibilities",
        REQUIRED_CONDUCTOR_RESPONSIBILITIES,
        conductor.get("responsibilities", []) if isinstance(conductor.get("responsibilities", []), list) else [],
        errors,
    )
    _missing(
        "conductor non-configurable controls",
        REQUIRED_TRUST_KERNEL | {"lifecycle_semantics"},
        conductor.get("non_configurable_controls", [])
        if isinstance(conductor.get("non_configurable_controls", []), list)
        else [],
        errors,
    )

    choir_roles = data.get("choir_roles", [])
    if not isinstance(choir_roles, list) or not choir_roles:
        errors.append("choir_roles must be a non-empty list")
        choir_roles = []
    role_ids: set[str] = set()
    for index, role in enumerate(choir_roles):
        if not isinstance(role, dict):
            errors.append(f"choir_roles[{index}] must be an object")
            continue
        for key in ("id", "label", "layer", "canonical_repos", "purpose"):
            if not role.get(key):
                errors.append(f"choir_roles[{index}].{key} is required")
        if isinstance(role.get("id"), str):
            role_ids.add(role["id"])
        repos = role.get("canonical_repos", [])
        if not isinstance(repos, list) or not repos:
            errors.append(f"choir_roles[{index}].canonical_repos must be a non-empty list")
    missing_roles = REQUIRED_CHOIR_ROLES - role_ids
    if missing_roles:
        errors.append("missing choir roles: " + ", ".join(sorted(missing_roles)))

    router = data.get("router_interface", {})
    if not isinstance(router, dict):
        errors.append("router_interface must be an object")
        router = {}
    if router.get("canonical_repo") != "SocioProphet/model-router":
        errors.append("router_interface.canonical_repo must be SocioProphet/model-router")
    _missing(
        "router routes",
        frozenset({"local_models", "open_models", "fine_tuned_models", "domain_models", "customer_models", "specialist_agents", "tools", "workflows"}),
        router.get("routes", []) if isinstance(router.get("routes", []), list) else [],
        errors,
    )

    premium = data.get("premium_derived_agents", {})
    if not isinstance(premium, dict):
        errors.append("premium_derived_agents must be an object")
        premium = {}
    if premium.get("enabled") is not True:
        errors.append("premium_derived_agents.enabled must be true")
    _missing(
        "premium customer controls",
        REQUIRED_PREMIUM_CONTROLS,
        premium.get("customer_controls", []) if isinstance(premium.get("customer_controls", []), list) else [],
        errors,
    )
    _missing(
        "premium required controls",
        REQUIRED_PREMIUM_REQUIRED_CONTROLS,
        premium.get("required_controls", []) if isinstance(premium.get("required_controls", []), list) else [],
        errors,
    )

    return ChoirValidationResult(valid=not errors, errors=errors)


def validate_choir_spec_file(path: str | Path) -> ChoirValidationResult:
    return validate_choir_spec(load_choir_spec(path))
