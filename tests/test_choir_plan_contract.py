from pathlib import Path

from prophet_mesh.choir_plan import validate_choir_plan_file


def test_accepted_choir_execution_plan_validates():
    result = validate_choir_plan_file(Path("examples/choir-execution-plan.accepted.json"))
    assert result.valid, result.errors


def test_rejected_choir_execution_plan_is_invalid():
    result = validate_choir_plan_file(Path("examples/choir-execution-plan.rejected.json"))
    assert not result.valid
    assert any("email_reply plans must not be direct allow" in error for error in result.errors)
    assert any("controls.policy must be true" in error for error in result.errors)
