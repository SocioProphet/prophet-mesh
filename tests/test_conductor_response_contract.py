from pathlib import Path

from prophet_mesh.conductor_response import validate_conductor_response_file


def test_accepted_conductor_response_validates():
    result = validate_conductor_response_file(Path("examples/conductor-response.accepted.json"))
    assert result.valid, result.errors


def test_rejected_conductor_response_is_invalid():
    result = validate_conductor_response_file(Path("examples/conductor-response.rejected.json"))
    assert not result.valid
    assert any("status must be draft" in error for error in result.errors)
    assert any("controls.policy must be true" in error for error in result.errors)
