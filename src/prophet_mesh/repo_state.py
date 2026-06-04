"""Repository-state contract for Prophet Mesh.

This module makes the product architecture repo-native. Prophet Mesh is not just a diagram:
it is a contract that maps the Michael Agent, model router, memory, orchestration,
runtime, policy, and customer derivation layers onto the existing SocioProphet repo
estate.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REQUIRED_LAYERS = frozenset(
    {
        "human_interface",
        "lifelong_agent",
        "model_router",
        "memory",
        "agent_orchestration",
        "open_mesh_model_family",
        "tools_and_environments",
        "trust_governance",
        "premium_derived_agents",
    }
)

REQUIRED_INVARIANTS = frozenset(
    {
        "single_router_interface",
        "michael_first_experience",
        "relationship_memory",
        "repo_native_orchestration",
        "open_model_family",
        "policy_bound_execution",
        "customer_derivation_without_trust_kernel_bypass",
    }
)

REQUIRED_TRUST_KERNEL = frozenset(
    {"identity", "policy", "evidence", "attestation", "revocation", "audit"}
)

REQUIRED_ANCHOR_REPOS = frozenset(
    {
        "SocioProphet/prophet-mesh",
        "SocioProphet/prophet-platform",
        "SocioProphet/model-router",
        "SocioProphet/agentplane",
        "SocioProphet/agent-registry",
        "SocioProphet/agent-inbox",
        "SocioProphet/memory-mesh",
        "SocioProphet/hellgraph",
    }
)


@dataclass(frozen=True)
class RepoStateValidationResult:
    """Validation result for a repo-state architecture artifact."""

    valid: bool
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": self.errors}


def load_repo_state(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("repo-state artifact must be a YAML object")
    return data


def _require_dict(data: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        errors.append(f"{key} must be an object")
        return {}
    return value


def _repo_names(data: dict[str, Any]) -> set[str]:
    repositories = data.get("repositories", [])
    names: set[str] = set()
    if isinstance(repositories, list):
        for repo in repositories:
            if isinstance(repo, dict) and isinstance(repo.get("name"), str):
                names.add(repo["name"])
    return names


def validate_repo_state(data: dict[str, Any]) -> RepoStateValidationResult:
    """Validate the repo-native Prophet Mesh architecture spec."""

    errors: list[str] = []

    if data.get("name") != "prophet-mesh-repo-state":
        errors.append("name must be prophet-mesh-repo-state")

    if data.get("product") != "Prophet Mesh":
        errors.append("product must be Prophet Mesh")

    if data.get("primary_agent") != "Michael Agent":
        errors.append("primary_agent must be Michael Agent")

    if data.get("primary_repo") != "SocioProphet/prophet-mesh":
        errors.append("primary_repo must be SocioProphet/prophet-mesh")

    layers = _require_dict(data, "layers", errors)
    missing_layers = REQUIRED_LAYERS - set(layers)
    if missing_layers:
        errors.append("missing layers: " + ", ".join(sorted(missing_layers)))

    invariants = data.get("invariants", [])
    if not isinstance(invariants, list):
        errors.append("invariants must be a list")
        invariants = []
    missing_invariants = REQUIRED_INVARIANTS - set(invariants)
    if missing_invariants:
        errors.append("missing invariants: " + ", ".join(sorted(missing_invariants)))

    trust_kernel = data.get("trust_kernel", [])
    if not isinstance(trust_kernel, list):
        errors.append("trust_kernel must be a list")
        trust_kernel = []
    missing_trust = REQUIRED_TRUST_KERNEL - set(trust_kernel)
    if missing_trust:
        errors.append("missing trust_kernel entries: " + ", ".join(sorted(missing_trust)))

    repositories = data.get("repositories", [])
    if not isinstance(repositories, list) or not repositories:
        errors.append("repositories must be a non-empty list")
    else:
        for index, repo in enumerate(repositories):
            if not isinstance(repo, dict):
                errors.append(f"repositories[{index}] must be an object")
                continue
            for key in ("name", "layer", "role", "status"):
                if not repo.get(key):
                    errors.append(f"repositories[{index}].{key} is required")
            if repo.get("layer") and repo.get("layer") not in REQUIRED_LAYERS:
                errors.append(f"repositories[{index}].layer is not a known Prophet Mesh layer")

    missing_repos = REQUIRED_ANCHOR_REPOS - _repo_names(data)
    if missing_repos:
        errors.append("missing anchor repositories: " + ", ".join(sorted(missing_repos)))

    router = layers.get("model_router", {})
    if isinstance(router, dict) and router.get("single_interface") is not True:
        errors.append("layers.model_router.single_interface must be true")

    lifelong_agent = layers.get("lifelong_agent", {})
    if isinstance(lifelong_agent, dict) and lifelong_agent.get("agent") != "Michael Agent":
        errors.append("layers.lifelong_agent.agent must be Michael Agent")

    memory = layers.get("memory", {})
    if isinstance(memory, dict) and memory.get("relationship_aware") is not True:
        errors.append("layers.memory.relationship_aware must be true")

    premium = layers.get("premium_derived_agents", {})
    if isinstance(premium, dict) and premium.get("trust_kernel_inherited") is not True:
        errors.append("layers.premium_derived_agents.trust_kernel_inherited must be true")

    return RepoStateValidationResult(valid=not errors, errors=errors)


def validate_repo_state_file(path: str | Path) -> RepoStateValidationResult:
    return validate_repo_state(load_repo_state(path))
