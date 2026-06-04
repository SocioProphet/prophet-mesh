"""Evaluation harness validation for Prophet Mesh."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_TOP_LEVEL_FIELDS = frozenset({"agent", "suite", "tasks", "summary", "trust_kernel"})
REQUIRED_TASK_FIELDS = frozenset({"id", "prompt", "expected_behavior", "result"})
REQUIRED_RESULT_FIELDS = frozenset(
    {
        "passed",
        "material_claims_cited",
        "evidence_packet_present",
        "policy_decision",
        "lifecycle_event_present",
        "contradiction_handled",
    }
)
REQUIRED_TRUST_KERNEL_FIELDS = frozenset(
    {
        "identity_preserved",
        "policy_preserved",
        "evidence_preserved",
        "attestation_preserved",
        "revocation_preserved",
        "audit_preserved",
    }
)
ALLOWED_POLICY_DECISIONS = frozenset({"allow", "deny", "requires_approval"})


@dataclass(frozen=True)
class EvaluationValidationResult:
    """Validation result for an evaluation report."""

    valid: bool
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": self.errors}


def load_evaluation_report(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("evaluation report must be a JSON object")
    return data


def _require_string(container: dict[str, Any], key: str, path: str, errors: list[str]) -> None:
    if not isinstance(container.get(key), str) or not container[key]:
        errors.append(f"{path}.{key} is required")


def _validate_agent(agent: Any, errors: list[str]) -> None:
    if not isinstance(agent, dict):
        errors.append("agent must be an object")
        return
    _require_string(agent, "name", "agent", errors)
    _require_string(agent, "edition", "agent", errors)
    if agent.get("archetype") not in {"michael", "michael-derived"}:
        errors.append("agent.archetype must be michael or michael-derived")


def _validate_suite(suite: Any, errors: list[str]) -> None:
    if not isinstance(suite, dict):
        errors.append("suite must be an object")
        return
    _require_string(suite, "name", "suite", errors)
    _require_string(suite, "version", "suite", errors)


def _validate_task(task: Any, index: int, errors: list[str]) -> bool:
    if not isinstance(task, dict):
        errors.append(f"tasks[{index}] must be an object")
        return False

    missing = REQUIRED_TASK_FIELDS - set(task)
    if missing:
        errors.append(f"tasks[{index}] missing fields: " + ", ".join(sorted(missing)))

    for key in ("id", "prompt", "expected_behavior"):
        _require_string(task, key, f"tasks[{index}]", errors)

    result = task.get("result", {})
    if not isinstance(result, dict):
        errors.append(f"tasks[{index}].result must be an object")
        return False

    missing_result = REQUIRED_RESULT_FIELDS - set(result)
    if missing_result:
        errors.append(
            f"tasks[{index}].result missing fields: " + ", ".join(sorted(missing_result))
        )

    for key in sorted(REQUIRED_RESULT_FIELDS - {"policy_decision"}):
        if key in result and not isinstance(result[key], bool):
            errors.append(f"tasks[{index}].result.{key} must be boolean")

    if result.get("policy_decision") not in ALLOWED_POLICY_DECISIONS:
        errors.append(
            f"tasks[{index}].result.policy_decision must be allow, deny, or requires_approval"
        )

    failed_controls = [
        key
        for key in sorted(REQUIRED_RESULT_FIELDS - {"policy_decision"})
        if result.get(key) is not True
    ]
    for key in failed_controls:
        errors.append(f"tasks[{index}].result.{key} must be true")

    return bool(result.get("passed") is True)


def _validate_summary(summary: Any, task_count: int, passed_count: int, errors: list[str]) -> None:
    if not isinstance(summary, dict):
        errors.append("summary must be an object")
        return
    if summary.get("total_tasks") != task_count:
        errors.append("summary.total_tasks must match the number of tasks")
    if summary.get("passed_tasks") != passed_count:
        errors.append("summary.passed_tasks must match passed task count")
    if summary.get("failed_tasks") != task_count - passed_count:
        errors.append("summary.failed_tasks must match failed task count")


def _validate_trust_kernel(trust_kernel: Any, errors: list[str]) -> None:
    if not isinstance(trust_kernel, dict):
        errors.append("trust_kernel must be an object")
        return
    missing = REQUIRED_TRUST_KERNEL_FIELDS - set(trust_kernel)
    if missing:
        errors.append("trust_kernel missing fields: " + ", ".join(sorted(missing)))
    for key in sorted(REQUIRED_TRUST_KERNEL_FIELDS & set(trust_kernel)):
        if trust_kernel[key] is not True:
            errors.append(f"trust_kernel.{key} must be true")


def validate_evaluation_report(data: dict[str, Any]) -> EvaluationValidationResult:
    """Validate a Prophet Mesh evaluation report."""

    errors: list[str] = []
    missing = REQUIRED_TOP_LEVEL_FIELDS - set(data)
    if missing:
        errors.append("missing required sections: " + ", ".join(sorted(missing)))

    _validate_agent(data.get("agent"), errors)
    _validate_suite(data.get("suite"), errors)
    _validate_trust_kernel(data.get("trust_kernel"), errors)

    tasks = data.get("tasks", [])
    passed_count = 0
    if not isinstance(tasks, list) or not tasks:
        errors.append("tasks must be a non-empty list")
        tasks = []
    else:
        for index, task in enumerate(tasks):
            if _validate_task(task, index, errors):
                passed_count += 1

    _validate_summary(data.get("summary"), len(tasks), passed_count, errors)
    return EvaluationValidationResult(valid=not errors, errors=errors)


def validate_evaluation_report_file(path: str | Path) -> EvaluationValidationResult:
    return validate_evaluation_report(load_evaluation_report(path))
