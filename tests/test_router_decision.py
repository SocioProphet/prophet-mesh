from pathlib import Path

from prophet_mesh.router_decision import validate_router_decision_file


def test_accepted_router_decision_validates():
    result = validate_router_decision_file(Path("examples/router-decision.accepted.json"))
    assert result.valid, result.errors


def test_rejected_router_decision_is_invalid():
    result = validate_router_decision_file(Path("examples/router-decision.rejected.json"))
    assert not result.valid
    assert any("email_reply must not be direct allow" in error for error in result.errors)
    assert any("memory_scope must not be unscoped" in error for error in result.errors)
    assert any("controls.policy must be true" in error for error in result.errors)
