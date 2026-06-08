"""Memory-scope policy validation for Prophet Mesh runtime requests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REQUIRED_POLICY_FIELDS = frozenset({"schema_version", "kind", "allowed_scopes", "forbidden_scopes", "invariants"})
REQUIRED_SCOPE_FIELDS = frozenset({"scope", "class", "approval_state", "allowed_tasks", "required_controls"})
REQUIRED_CONTROLS = frozenset({"identity", "policy", "audit"})
EXPECTED_KIND = "prophet_mesh_memory_scope_policy"


@dataclass(frozen=True)
class MemoryScopeValidationResult:
    valid: bool
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": self.errors}


def load_memory_scope_policy(path: str | Path = "specs/memory-scope.yaml") -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("memory scope policy must be a YAML object")
    return data


def validate_memory_scope_policy(policy: dict[str, Any]) -> MemoryScopeValidationResult:
    errors: list[str] = []
    missing = REQUIRED_POLICY_FIELDS - set(policy)
    if missing:
        errors.append("missing fields: " + ", ".join(sorted(missing)))

    if policy.get("kind") != EXPECTED_KIND:
        errors.append(f"kind must be {EXPECTED_KIND}")

    allowed_scopes = policy.get("allowed_scopes", [])
    if not isinstance(allowed_scopes, list) or not allowed_scopes:
        errors.append("allowed_scopes must be a non-empty list")
    else:
        seen: set[str] = set()
        for index, entry in enumerate(allowed_scopes):
            if not isinstance(entry, dict):
                errors.append(f"allowed_scopes[{index}] must be an object")
                continue
            missing_scope_fields = REQUIRED_SCOPE_FIELDS - set(entry)
            if missing_scope_fields:
                errors.append(
                    f"allowed_scopes[{index}] missing fields: " + ", ".join(sorted(missing_scope_fields))
                )
            scope = entry.get("scope")
            if not isinstance(scope, str) or not scope:
                errors.append(f"allowed_scopes[{index}].scope must be a non-empty string")
            elif scope in seen:
                errors.append(f"duplicate allowed scope: {scope}")
            else:
                seen.add(scope)

            for key in ("class", "approval_state"):
                if key in entry and (not isinstance(entry[key], str) or not entry[key]):
                    errors.append(f"allowed_scopes[{index}].{key} must be a non-empty string")

            for key in ("allowed_tasks", "required_controls"):
                value = entry.get(key, [])
                if not isinstance(value, list) or not value:
                    errors.append(f"allowed_scopes[{index}].{key} must be a non-empty list")

            controls = {str(item) for item in entry.get("required_controls", []) if isinstance(item, str)}
            missing_controls = REQUIRED_CONTROLS - controls
            if missing_controls:
                errors.append(
                    f"allowed_scopes[{index}] missing required controls: "
                    + ", ".join(sorted(missing_controls))
                )

    forbidden = policy.get("forbidden_scopes", [])
    if not isinstance(forbidden, list) or not forbidden:
        errors.append("forbidden_scopes must be a non-empty list")
    elif "unscoped" not in {str(item) for item in forbidden}:
        errors.append("forbidden_scopes must include unscoped")

    invariants = policy.get("invariants", [])
    if not isinstance(invariants, list) or not invariants:
        errors.append("invariants must be a non-empty list")

    return MemoryScopeValidationResult(valid=not errors, errors=errors)


def validate_memory_scope_policy_file(path: str | Path) -> MemoryScopeValidationResult:
    return validate_memory_scope_policy(load_memory_scope_policy(path))


def validate_request_memory_scope(
    request: dict[str, Any], policy: dict[str, Any] | None = None
) -> MemoryScopeValidationResult:
    memory_policy = policy or load_memory_scope_policy()
    errors: list[str] = []

    policy_validation = validate_memory_scope_policy(memory_policy)
    if not policy_validation.valid:
        errors.extend(f"policy: {error}" for error in policy_validation.errors)
        return MemoryScopeValidationResult(valid=False, errors=errors)

    scope = request.get("memory_scope")
    task = request.get("task")
    if not isinstance(scope, str) or not scope:
        errors.append("memory_scope must be explicit")
        return MemoryScopeValidationResult(valid=False, errors=errors)
    if not isinstance(task, str) or not task:
        errors.append("task must be explicit for memory scope validation")
        return MemoryScopeValidationResult(valid=False, errors=errors)

    forbidden = {str(item) for item in memory_policy.get("forbidden_scopes", [])}
    if scope in forbidden:
        errors.append(f"memory_scope {scope!r} is forbidden")

    allowed = {
        str(entry.get("scope")): entry
        for entry in memory_policy.get("allowed_scopes", [])
        if isinstance(entry, dict) and isinstance(entry.get("scope"), str)
    }
    selected = allowed.get(scope)
    if selected is None:
        errors.append(f"memory_scope {scope!r} is not allowed")
    else:
        allowed_tasks = {str(item) for item in selected.get("allowed_tasks", [])}
        if task not in allowed_tasks:
            errors.append(f"memory_scope {scope!r} is not allowed for task {task!r}")
        if selected.get("approval_state") != "approved":
            errors.append(f"memory_scope {scope!r} must be approved")

    return MemoryScopeValidationResult(valid=not errors, errors=errors)
