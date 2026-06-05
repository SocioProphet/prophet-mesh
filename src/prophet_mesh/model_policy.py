"""Model task/domain policy validation for Prophet Mesh."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REQUIRED_INVARIANTS = frozenset(
    {
        "conductor_routes_every_task",
        "task_policy_is_explicit",
        "domain_policy_is_explicit",
        "hosted_models_are_optional_routes",
        "open_models_are_first_class_routes",
        "private_tasks_prefer_private_routes",
        "customer_routes_are_tenant_isolated",
        "image_and_media_routes_are_separate_from_text_routes",
        "office_routes_preserve_document_intent",
        "communications_routes_preserve_relationship_context",
        "research_routes_require_evidence",
        "coding_routes_require_tests_or_review",
    }
)

REQUIRED_MODEL_FAMILIES = frozenset(
    {
        "hosted_frontier",
        "hosted_balanced",
        "hosted_fast",
        "open_private",
        "code_specialist",
        "reasoning_specialist",
        "image_specialist",
        "media_specialist",
        "document_specialist",
    }
)

REQUIRED_TASKS = frozenset(
    {
        "chat",
        "text_message_reply",
        "email_reply",
        "office_document_creation",
        "office_document_editing",
        "research",
        "coding",
        "code_review",
        "image_generation",
        "image_editing",
        "video_generation",
        "analytics",
        "operations_plan",
        "legal_compliance_draft",
        "scientific_reasoning",
    }
)

REQUIRED_TASK_FIELDS = frozenset(
    {"task", "domain", "primary_family", "private_family", "required_controls", "specialist_agents"}
)


@dataclass(frozen=True)
class ModelTaskPolicyValidationResult:
    valid: bool
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": self.errors}


def load_model_task_policy(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("model task policy must be a YAML object")
    return data


def _missing(label: str, required: frozenset[str], present: set[str], errors: list[str]) -> None:
    missing = required - present
    if missing:
        errors.append(f"missing {label}: " + ", ".join(sorted(missing)))


def validate_model_task_policy(data: dict[str, Any]) -> ModelTaskPolicyValidationResult:
    errors: list[str] = []

    if data.get("name") != "prophet-mesh-model-task-policy":
        errors.append("name must be prophet-mesh-model-task-policy")
    if data.get("product") != "Prophet Mesh":
        errors.append("product must be Prophet Mesh")

    invariants = data.get("invariants", [])
    if not isinstance(invariants, list):
        errors.append("invariants must be a list")
        invariants = []
    _missing("invariants", REQUIRED_INVARIANTS, {v for v in invariants if isinstance(v, str)}, errors)

    model_families = data.get("model_families", {})
    if not isinstance(model_families, dict):
        errors.append("model_families must be an object")
        model_families = {}
    _missing("model families", REQUIRED_MODEL_FAMILIES, set(model_families), errors)

    for family_name, family in model_families.items():
        if not isinstance(family, dict):
            errors.append(f"model_families.{family_name} must be an object")
            continue
        preferred = family.get("preferred", [])
        if not isinstance(preferred, list) or not preferred:
            errors.append(f"model_families.{family_name}.preferred must be a non-empty list")
        if not family.get("role"):
            errors.append(f"model_families.{family_name}.role is required")

    routes = data.get("task_routes", [])
    if not isinstance(routes, list) or not routes:
        errors.append("task_routes must be a non-empty list")
        routes = []

    seen_tasks: set[str] = set()
    known_families = set(model_families)
    for index, route in enumerate(routes):
        if not isinstance(route, dict):
            errors.append(f"task_routes[{index}] must be an object")
            continue
        missing_fields = REQUIRED_TASK_FIELDS - set(route)
        if missing_fields:
            errors.append(
                f"task_routes[{index}] missing fields: " + ", ".join(sorted(missing_fields))
            )
        task = route.get("task")
        if isinstance(task, str):
            seen_tasks.add(task)
        for key in ("primary_family", "private_family"):
            value = route.get(key)
            if value and value not in known_families:
                errors.append(f"task_routes[{index}].{key} references unknown family {value!r}")
        for key in ("required_controls", "specialist_agents"):
            value = route.get(key)
            if not isinstance(value, list) or not value:
                errors.append(f"task_routes[{index}].{key} must be a non-empty list")

    _missing("tasks", REQUIRED_TASKS, seen_tasks, errors)
    return ModelTaskPolicyValidationResult(valid=not errors, errors=errors)


def validate_model_task_policy_file(path: str | Path) -> ModelTaskPolicyValidationResult:
    return validate_model_task_policy(load_model_task_policy(path))
