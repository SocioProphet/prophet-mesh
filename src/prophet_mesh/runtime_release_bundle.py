"""Runtime release bundle validation for Prophet Mesh private preview."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import json
import yaml

DEFAULT_CONTRACT_PATH = Path("specs/runtime-release-bundle.yaml")


@dataclass(frozen=True)
class RuntimeReleaseBundleValidationResult:
    valid: bool
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": self.errors}


def load_runtime_release_contract(path: str | Path = DEFAULT_CONTRACT_PATH) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("runtime release bundle contract must be a YAML object")
    return data


def load_runtime_release_bundle(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("runtime release bundle must be a JSON object")
    return data


def _has_non_empty_list(data: dict[str, Any], key: str) -> bool:
    return isinstance(data.get(key), list) and bool(data[key])


def _controls_valid(data: dict[str, Any], required_controls: list[str]) -> list[str]:
    errors: list[str] = []
    controls = data.get("controls", {})
    if not isinstance(controls, dict):
        return ["controls must be an object"]
    for control in required_controls:
        if controls.get(control) is not True:
            errors.append(f"controls.{control} must be true")
    return errors


def validate_runtime_release_bundle(
    bundle: dict[str, Any], contract: dict[str, Any] | None = None
) -> RuntimeReleaseBundleValidationResult:
    release_contract = contract or load_runtime_release_contract()
    errors: list[str] = []

    if bundle.get("kind") not in set(release_contract.get("allowed_artifact_kinds", [])):
        errors.append("kind must be a permitted runtime release artifact kind")
    if bundle.get("release_channel") not in set(release_contract.get("release_channels", [])):
        errors.append("release_channel must be permitted by contract")
    for key in ("bundle_id", "schema_version", "source_request"):
        if not isinstance(bundle.get(key), str) or not bundle[key]:
            errors.append(f"{key} must be a non-empty string")

    runtime = bundle.get("runtime_result")
    if not isinstance(runtime, dict):
        errors.append("runtime_result must be an object")
        return RuntimeReleaseBundleValidationResult(valid=False, errors=errors)

    for section in release_contract.get("required_runtime_sections", []):
        if section not in runtime:
            errors.append(f"runtime_result.{section} is required")

    validation = runtime.get("validation", {})
    if not isinstance(validation, dict) or validation.get("valid") is not True:
        errors.append("runtime_result.validation.valid must be true")

    trace = runtime.get("execution_trace", {})
    if not isinstance(trace, dict):
        errors.append("runtime_result.execution_trace must be an object")
    else:
        for field in release_contract.get("required_trace_fields", []):
            if field not in trace:
                errors.append(f"execution_trace.{field} is required")
        if not isinstance(trace.get("memory_scope"), str) or not trace.get("memory_scope"):
            errors.append("execution_trace.memory_scope must be explicit")
        if trace.get("task") == "email_reply" and trace.get("status") != "awaiting_approval":
            errors.append("email_reply release traces must remain awaiting_approval")
        approval = trace.get("approval_state", {})
        if not isinstance(approval, dict) or approval.get("required") is not True:
            errors.append("execution_trace.approval_state.required must be true")
        if not _has_non_empty_list(trace, "evidence_refs"):
            errors.append("execution_trace.evidence_refs must be non-empty")
        if not _has_non_empty_list(trace, "audit_refs"):
            errors.append("execution_trace.audit_refs must be non-empty")
        errors.extend(f"execution_trace.{error}" for error in _controls_valid(trace, release_contract.get("required_controls", [])))

    plan = runtime.get("choir_plan", {})
    if isinstance(plan, dict):
        boundary = str(plan.get("approval_boundary", "")).lower()
        if "human approval" not in boundary:
            errors.append("choir_plan.approval_boundary must preserve human approval")
        if not _has_non_empty_list(plan, "evidence_refs"):
            errors.append("choir_plan.evidence_refs must be non-empty")
        if not _has_non_empty_list(plan, "audit_refs"):
            errors.append("choir_plan.audit_refs must be non-empty")
        errors.extend(f"choir_plan.{error}" for error in _controls_valid(plan, release_contract.get("required_controls", [])))
    else:
        errors.append("runtime_result.choir_plan must be an object")

    response = runtime.get("conductor_response", {})
    if isinstance(response, dict):
        if response.get("task") == "email_reply" and response.get("status") != "awaiting_approval":
            errors.append("conductor_response for email_reply must remain awaiting_approval")
        if not _has_non_empty_list(response, "pending_approvals"):
            errors.append("conductor_response.pending_approvals must be non-empty")
        if not _has_non_empty_list(response, "evidence_refs"):
            errors.append("conductor_response.evidence_refs must be non-empty")
        if not _has_non_empty_list(response, "audit_refs"):
            errors.append("conductor_response.audit_refs must be non-empty")
        errors.extend(
            f"conductor_response.{error}" for error in _controls_valid(response, release_contract.get("required_controls", []))
        )
    else:
        errors.append("runtime_result.conductor_response must be an object")

    notes = bundle.get("promotion_notes", [])
    if not isinstance(notes, list) or not notes:
        errors.append("promotion_notes must be a non-empty list")

    return RuntimeReleaseBundleValidationResult(valid=not errors, errors=errors)


def validate_runtime_release_bundle_file(
    path: str | Path, contract_path: str | Path = DEFAULT_CONTRACT_PATH
) -> RuntimeReleaseBundleValidationResult:
    return validate_runtime_release_bundle(
        load_runtime_release_bundle(path),
        load_runtime_release_contract(contract_path),
    )
