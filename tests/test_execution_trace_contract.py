from pathlib import Path

from prophet_mesh.execution_trace import validate_execution_trace_file


def test_accepted_execution_trace_validates():
    result = validate_execution_trace_file(Path("examples/execution-trace.accepted.json"))
    assert result.valid, result.errors


def test_rejected_execution_trace_is_invalid():
    result = validate_execution_trace_file(Path("examples/execution-trace.rejected.json"))
    assert not result.valid
    assert any("controls.policy must be true" in error for error in result.errors)
    assert any("email_reply traces must not complete without an approval requirement" in error for error in result.errors)
