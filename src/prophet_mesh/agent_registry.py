"""Agent manifest registry for Prophet Mesh."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REQUIRED_AGENT_FIELDS = frozenset(
    {"id", "kind", "label", "version", "status", "role", "capabilities", "required_controls"}
)

ALLOWED_KINDS = frozenset({"conductor", "specialist"})
ALLOWED_STATUS = frozenset({"active", "disabled", "retired"})
REQUIRED_BASE_CONTROLS = frozenset({"identity", "policy", "audit"})
REQUIRED_DEFAULT_AGENTS = frozenset(
    {
        "michael-agent",
        "memory-steward",
        "writing-agent",
        "governance-sentinel",
        "research-agent",
        "coding-agent",
        "analytics-agent",
        "operations-agent",
        "creative-agent",
    }
)


@dataclass(frozen=True)
class AgentManifest:
    """Registered conductor or specialist manifest."""

    id: str
    kind: str
    label: str
    version: str
    status: str
    role: str
    capabilities: tuple[str, ...]
    required_controls: tuple[str, ...]
    path: str

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: str | Path) -> "AgentManifest":
        return cls(
            id=str(data["id"]),
            kind=str(data["kind"]),
            label=str(data["label"]),
            version=str(data["version"]),
            status=str(data["status"]),
            role=str(data["role"]),
            capabilities=tuple(str(item) for item in data.get("capabilities", [])),
            required_controls=tuple(str(item) for item in data.get("required_controls", [])),
            path=str(path),
        )

    @property
    def active(self) -> bool:
        return self.status == "active"


@dataclass(frozen=True)
class AgentRegistryValidationResult:
    """Validation result for the registered Agent Choir manifest set."""

    valid: bool
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": self.errors}


@dataclass(frozen=True)
class AgentRegistry:
    """In-memory registry of agent manifests."""

    agents: dict[str, AgentManifest]

    def get(self, agent_id: str) -> AgentManifest | None:
        return self.agents.get(agent_id)

    def require_active(self, agent_id: str) -> AgentManifest:
        manifest = self.get(agent_id)
        if manifest is None:
            raise KeyError(f"agent {agent_id!r} is not registered")
        if not manifest.active:
            raise ValueError(f"agent {agent_id!r} is not active")
        return manifest

    def validate_selected_agents(self, agent_ids: list[str]) -> list[str]:
        errors: list[str] = []
        for agent_id in agent_ids:
            manifest = self.get(agent_id)
            if manifest is None:
                errors.append(f"agent {agent_id!r} is not registered")
            elif not manifest.active:
                errors.append(f"agent {agent_id!r} is not active")
        return errors


def load_agent_manifest(path: str | Path) -> tuple[AgentManifest | None, list[str]]:
    errors: list[str] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        return None, [f"{path}: manifest must be a YAML object"]

    missing = REQUIRED_AGENT_FIELDS - set(data)
    if missing:
        errors.append(f"{path}: missing fields: " + ", ".join(sorted(missing)))

    for key in sorted(REQUIRED_AGENT_FIELDS - {"capabilities", "required_controls"}):
        if key in data and (not isinstance(data[key], str) or not data[key]):
            errors.append(f"{path}: {key} must be a non-empty string")

    if data.get("kind") not in ALLOWED_KINDS:
        errors.append(f"{path}: kind must be conductor or specialist")
    if data.get("status") not in ALLOWED_STATUS:
        errors.append(f"{path}: status must be active, disabled, or retired")

    for key in ("capabilities", "required_controls"):
        value = data.get(key, [])
        if not isinstance(value, list) or not value:
            errors.append(f"{path}: {key} must be a non-empty list")

    controls = {str(item) for item in data.get("required_controls", []) if isinstance(item, str)}
    missing_controls = REQUIRED_BASE_CONTROLS - controls
    if missing_controls:
        errors.append(f"{path}: missing required controls: " + ", ".join(sorted(missing_controls)))

    if errors:
        return None, errors
    return AgentManifest.from_dict(data, path), []


def load_agent_registry(path: str | Path = "agents") -> AgentRegistry:
    agents: dict[str, AgentManifest] = {}
    for manifest_path in sorted(Path(path).glob("*.yaml")):
        manifest, errors = load_agent_manifest(manifest_path)
        if errors:
            continue
        assert manifest is not None
        agents[manifest.id] = manifest
    return AgentRegistry(agents=agents)


def validate_agent_registry(path: str | Path = "agents") -> AgentRegistryValidationResult:
    errors: list[str] = []
    agents: dict[str, AgentManifest] = {}

    manifest_paths = sorted(Path(path).glob("*.yaml"))
    if not manifest_paths:
        errors.append(f"{path}: no agent manifests found")

    for manifest_path in manifest_paths:
        manifest, manifest_errors = load_agent_manifest(manifest_path)
        errors.extend(manifest_errors)
        if manifest is None:
            continue
        if manifest.id in agents:
            errors.append(f"duplicate agent id: {manifest.id}")
        agents[manifest.id] = manifest

    missing_agents = REQUIRED_DEFAULT_AGENTS - set(agents)
    if missing_agents:
        errors.append("missing default agents: " + ", ".join(sorted(missing_agents)))

    for agent_id in sorted(REQUIRED_DEFAULT_AGENTS & set(agents)):
        if not agents[agent_id].active:
            errors.append(f"default agent {agent_id!r} must be active")

    return AgentRegistryValidationResult(valid=not errors, errors=errors)


def validate_agent_registry_path(path: str | Path) -> AgentRegistryValidationResult:
    return validate_agent_registry(path)
