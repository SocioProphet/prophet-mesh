from pathlib import Path

from prophet_mesh.runtime import run_runtime_file


def test_runtime_loop_generates_valid_chain():
    result = run_runtime_file(
        Path("examples/router-request.email.json"),
        Path("specs/model-task-policy.yaml"),
    )
    assert result.validation.valid, result.validation.errors
    assert result.router_decision["task"] == "email_reply"
    assert result.choir_plan["policy_decision"] == "requires_approval"
    assert result.conductor_response["status"] == "awaiting_approval"
    assert result.execution_trace["status"] == "awaiting_approval"
