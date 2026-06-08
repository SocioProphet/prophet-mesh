"""First deterministic Prophet Mesh runtime loop.

This runtime is intentionally non-networked and deterministic. It proves the product path:
router request -> router decision -> choir execution plan -> conductor response -> execution trace.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from prophet_mesh.agent_registry import AgentRegistry, load_agent_registry, validate_agent_registry
from prophet_mesh.choir_plan import validate_choir_plan
from prophet_mesh.conductor_response import validate_conductor_response
from prophet_mesh.execution_trace import validate_execution_trace
from prophet_mesh.memory_scope import validate_request_memory_scope
from prophet_mesh.model_policy import load_model_task_policy
from prophet_mesh.router_dry_run import dry_run_router_decision, load_router_request


@dataclass(frozen=True)
class RuntimeValidation:
    """Validation summary for a generated runtime chain."""

    valid: bool
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": self.errors}


@dataclass(frozen=True)
class RuntimeResult:
    """Generated runtime artifacts for one Prophet Mesh request."""

    router_decision: dict[str, Any]
    choir_plan: dict[str, Any]
    conductor_response: dict[str, Any]
    execution_trace: dict[str, Any]
    validation: RuntimeValidation

    def to_dict(self) -> dict[str, Any]:
        return {
            "router_decision": self.router_decision,
            "choir_plan": self.choir_plan,
            "conductor_response": self.conductor_response,
            "execution_trace": self.execution_trace,
            "validation": self.validation.to_dict(),
        }


def _controls() -> dict[str, bool]:
    return {
        "identity": True,
        "policy": True,
        "evidence": True,
        "attestation": True,
        "revocation": True,
        "audit": True,
        "tenant_isolation": True,
    }


def _choir_plan_from_decision(decision: dict[str, Any]) -> dict[str, Any]:
    request_id = str(decision["request_id"])
    task = str(decision["task"])
    agents = [agent for agent in decision.get("specialist_agents", []) if isinstance(agent, str)]
    if not agents:
        agents = ["governance-sentinel"]

    steps = [
        {
            "step_id": f"step-{index:03d}-{agent}",
            "agent": agent,
            "action": f"perform {task} responsibility for {agent}",
            "requires_approval": agent == "governance-sentinel"
            and decision.get("policy_decision") == "requires_approval",
            "evidence_required": True,
            "audit_required": True,
        }
        for index, agent in enumerate(agents, start=1)
    ]

    return {
        "plan_id": f"choir-plan:{request_id}",
        "request_id": request_id,
        "conductor_id": str(decision["conductor_id"]),
        "principal": str(decision["principal"]),
        "task": task,
        "domain": str(decision["domain"]),
        "policy_decision": str(decision["policy_decision"]),
        "router_decision_ref": f"router-decision:{request_id}",
        "summary": f"Execute {task} through the selected Agent Choir route.",
        "steps": steps,
        "approval_boundary": "human approval required before external action"
        if decision.get("policy_decision") == "requires_approval"
        else "no external action without policy confirmation",
        "evidence_refs": [str(decision["evidence_event"])],
        "audit_refs": [str(decision["audit_ref"])],
        "controls": _controls(),
    }


def _response_from_plan(plan: dict[str, Any]) -> dict[str, Any]:
    awaiting = plan.get("policy_decision") == "requires_approval"
    request_id = str(plan["request_id"])
    return {
        "response_id": f"conductor-response:{request_id}",
        "plan_id": str(plan["plan_id"]),
        "request_id": request_id,
        "conductor_id": str(plan["conductor_id"]),
        "principal": str(plan["principal"]),
        "task": str(plan["task"]),
        "status": "awaiting_approval" if awaiting else "completed",
        "summary": f"Prepared governed response for {plan['task']}.",
        "message": "I prepared the requested work through the Agent Choir and preserved evidence, audit, and approval boundaries.",
        "evidence_refs": list(plan["evidence_refs"]),
        "audit_refs": list(plan["audit_refs"]),
        "pending_approvals": ["approve_external_action"] if awaiting else [],
        "next_actions": ["review_output", "approve_or_request_revision"] if awaiting else ["review_output"],
        "escalation": {"required": False, "reason": "runtime policy path completed"},
        "controls": _controls(),
    }


def _trace_from_chain(
    decision: dict[str, Any], plan: dict[str, Any], response: dict[str, Any]
) -> dict[str, Any]:
    request_id = str(decision["request_id"])
    pending = list(response.get("pending_approvals", []))
    return {
        "trace_id": f"execution-trace:{request_id}",
        "request_id": request_id,
        "conductor_id": str(decision["conductor_id"]),
        "principal": str(decision["principal"]),
        "task": str(decision["task"]),
        "memory_scope": str(decision.get("memory_scope", "")),
        "router_decision_ref": f"router-decision:{request_id}",
        "choir_plan_ref": str(plan["plan_id"]),
        "conductor_response_ref": str(response["response_id"]),
        "lifecycle": "Serving",
        "status": str(response["status"]),
        "evidence_refs": list(response["evidence_refs"]),
        "audit_refs": list(response["audit_refs"]),
        "approval_state": {"required": bool(pending), "pending": pending},
        "controls": _controls(),
    }


def _validate_registered_agents(
    decision: dict[str, Any], plan: dict[str, Any], registry: AgentRegistry
) -> list[str]:
    errors: list[str] = []
    conductor_id = str(decision.get("conductor_id", ""))
    try:
        conductor = registry.require_active(conductor_id)
        if conductor.kind != "conductor":
            errors.append(f"conductor {conductor_id!r} must be kind conductor")
    except (KeyError, ValueError) as exc:
        errors.append(str(exc))

    selected_agents = [str(step.get("agent", "")) for step in plan.get("steps", []) if isinstance(step, dict)]
    errors.extend(registry.validate_selected_agents(selected_agents))
    for agent_id in selected_agents:
        manifest = registry.get(agent_id)
        if manifest is not None and manifest.kind != "specialist":
            errors.append(f"agent {agent_id!r} must be kind specialist")
    return errors


def run_runtime(
    request: dict[str, Any], policy: dict[str, Any], registry: AgentRegistry | None = None
) -> RuntimeResult:
    """Generate and validate the first deterministic Prophet Mesh runtime chain."""

    agent_registry = registry or load_agent_registry()
    router_result = dry_run_router_decision(request, policy)
    decision = router_result.decision
    plan = _choir_plan_from_decision(decision)
    response = _response_from_plan(plan)
    trace = _trace_from_chain(decision, plan, response)

    errors: list[str] = []
    memory_validation = validate_request_memory_scope(request)
    if not memory_validation.valid:
        errors.extend(f"memory_scope: {error}" for error in memory_validation.errors)

    registry_validation = validate_agent_registry()
    if not registry_validation.valid:
        errors.extend(f"agent_registry: {error}" for error in registry_validation.errors)
    errors.extend(f"agent_registry: {error}" for error in _validate_registered_agents(decision, plan, agent_registry))

    if not router_result.validation.valid:
        errors.extend(f"router_decision: {error}" for error in router_result.validation.errors)

    plan_validation = validate_choir_plan(plan)
    if not plan_validation.valid:
        errors.extend(f"choir_plan: {error}" for error in plan_validation.errors)

    response_validation = validate_conductor_response(response)
    if not response_validation.valid:
        errors.extend(f"conductor_response: {error}" for error in response_validation.errors)

    trace_validation = validate_execution_trace(trace)
    if not trace_validation.valid:
        errors.extend(f"execution_trace: {error}" for error in trace_validation.errors)

    return RuntimeResult(
        router_decision=decision,
        choir_plan=plan,
        conductor_response=response,
        execution_trace=trace,
        validation=RuntimeValidation(valid=not errors, errors=errors),
    )


def run_runtime_file(request_path: str | Path, policy_path: str | Path) -> RuntimeResult:
    return run_runtime(load_router_request(request_path), load_model_task_policy(policy_path))
