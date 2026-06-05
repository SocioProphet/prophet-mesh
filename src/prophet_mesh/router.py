"""Model-router interface validation for Prophet Mesh."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REQUIRED_INVARIANTS = frozenset(
    {
        "single_interface",
        "conductor_mediated",
        "model_family_open",
        "route_decisions_explainable",
        "memory_context_scoped",
        "policy_checked_before_execution",
        "evidence_emitted_for_material_routes",
        "customer_routes_tenant_isolated",
        "fallback_paths_declared",
        "no_direct_tool_bypass",
    }
)

REQUIRED_ROUTE_INPUTS = frozenset(
    {
        "request_id",
        "conductor_id",
        "principal",
        "intent",
        "memory_scope",
        "policy_context",
        "candidate_routes",
    }
)

REQUIRED_ROUTE_OUTPUTS = frozenset(
    {
        "request_id",
        "selected_route",
        "route_type",
        "rationale",
        "policy_decision",
        "evidence_event",
        "fallback_route",
        "audit_ref",
    }
)

REQUIRED_ROUTE_TYPES = frozenset(
    {
        "local_model",
        "open_model",
        "fine_tuned_model",
        "domain_model",
        "customer_model",
        "specialist_agent",
        "tool",
        "workflow",
    }
)

REQUIRED_ROUTE_FAMILIES = frozenset(
    {
        "local_models",
        "open_models",
        "fine_tuned_models",
        "domain_models",
        "customer_models",
        "specialist_agents",
        "tools",
        "workflows",
    }
)

REQUIRED_CONTROLS = frozenset(
    {
        "identity",
        "policy",
        "evidence",
        "attestation",
        "revocation",
        "audit",
        "tenant_isolation",
        "fallback",
        "route_explanation",
    }
)

REQUIRED_INTEGRATION_REPOS = frozenset(
    {
        "SocioProphet/model-router",
        "SocioProphet/functional-model-surfaces",
        "SocioProphet/agent-registry",
        "SocioProphet/agentplane",
        "SocioProphet/memory-mesh",
        "SocioProphet/guardrail-fabric",
        "SocioProphet/model-governance-ledger",
    }
)


@dataclass(frozen=True)
class RouterValidationResult:
    """Validation result for a router-interface contract."""

    valid: bool
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": self.errors}


def load_router_interface(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("model-router interface must be a YAML object")
    return data


def _as_list(value: Any, path: str, errors: list[str]) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{path} must be a list")
        return []
    return value


def _missing(label: str, required: frozenset[str], values: list[Any], errors: list[str]) -> None:
    present = {value for value in values if isinstance(value, str)}
    missing = required - present
    if missing:
        errors.append(f"missing {label}: " + ", ".join(sorted(missing)))


def validate_router_interface(data: dict[str, Any]) -> RouterValidationResult:
    """Validate the single model-router interface contract."""

    errors: list[str] = []

    if data.get("name") != "prophet-mesh-model-router-interface":
        errors.append("name must be prophet-mesh-model-router-interface")
    if data.get("product") != "Prophet Mesh":
        errors.append("product must be Prophet Mesh")
    if data.get("canonical_repo") != "SocioProphet/model-router":
        errors.append("canonical_repo must be SocioProphet/model-router")
    if data.get("primary_consumer") != "Michael Agent":
        errors.append("primary_consumer must be Michael Agent")

    _missing("invariants", REQUIRED_INVARIANTS, _as_list(data.get("invariants", []), "invariants", errors), errors)

    route_inputs = data.get("route_inputs", {})
    if not isinstance(route_inputs, dict):
        errors.append("route_inputs must be an object")
        route_inputs = {}
    _missing(
        "route input fields",
        REQUIRED_ROUTE_INPUTS,
        _as_list(route_inputs.get("required", []), "route_inputs.required", errors),
        errors,
    )

    route_outputs = data.get("route_outputs", {})
    if not isinstance(route_outputs, dict):
        errors.append("route_outputs must be an object")
        route_outputs = {}
    _missing(
        "route output fields",
        REQUIRED_ROUTE_OUTPUTS,
        _as_list(route_outputs.get("required", []), "route_outputs.required", errors),
        errors,
    )
    _missing(
        "route types",
        REQUIRED_ROUTE_TYPES,
        _as_list(route_outputs.get("route_types", []), "route_outputs.route_types", errors),
        errors,
    )
    _missing(
        "policy decisions",
        frozenset({"allow", "deny", "requires_approval"}),
        _as_list(route_outputs.get("policy_decisions", []), "route_outputs.policy_decisions", errors),
        errors,
    )

    route_families = data.get("route_families", [])
    if not isinstance(route_families, list) or not route_families:
        errors.append("route_families must be a non-empty list")
        route_families = []
    family_ids: set[str] = set()
    for index, family in enumerate(route_families):
        if not isinstance(family, dict):
            errors.append(f"route_families[{index}] must be an object")
            continue
        for key in ("id", "route_type", "purpose"):
            if not family.get(key):
                errors.append(f"route_families[{index}].{key} is required")
        if isinstance(family.get("id"), str):
            family_ids.add(family["id"])
        if family.get("route_type") and family.get("route_type") not in REQUIRED_ROUTE_TYPES:
            errors.append(f"route_families[{index}].route_type is not a known route type")
    missing_families = REQUIRED_ROUTE_FAMILIES - family_ids
    if missing_families:
        errors.append("missing route families: " + ", ".join(sorted(missing_families)))

    _missing(
        "required controls",
        REQUIRED_CONTROLS,
        _as_list(data.get("required_controls", []), "required_controls", errors),
        errors,
    )

    integration_repos = data.get("integration_repos", [])
    if not isinstance(integration_repos, list) or not integration_repos:
        errors.append("integration_repos must be a non-empty list")
        integration_repos = []
    repo_names: set[str] = set()
    for index, repo in enumerate(integration_repos):
        if not isinstance(repo, dict):
            errors.append(f"integration_repos[{index}] must be an object")
            continue
        for key in ("name", "responsibility"):
            if not repo.get(key):
                errors.append(f"integration_repos[{index}].{key} is required")
        if isinstance(repo.get("name"), str):
            repo_names.add(repo["name"])
    missing_repos = REQUIRED_INTEGRATION_REPOS - repo_names
    if missing_repos:
        errors.append("missing integration repos: " + ", ".join(sorted(missing_repos)))

    return RouterValidationResult(valid=not errors, errors=errors)


def validate_router_interface_file(path: str | Path) -> RouterValidationResult:
    return validate_router_interface(load_router_interface(path))
