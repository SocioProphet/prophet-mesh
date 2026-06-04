from pathlib import Path

from prophet_mesh.intake import validate_intake_file


def test_accepted_customer_intake_is_valid():
    result = validate_intake_file(Path("examples/customer-intake.accepted.json"))
    assert result.valid, result.errors


def test_rejected_customer_intake_is_invalid():
    result = validate_intake_file(Path("examples/customer-intake.rejected.json"))
    assert not result.valid
    assert any("policy.evidence_required must be true" in error for error in result.errors)
    assert any("connectors[0].owner is required" in error for error in result.errors)
    assert any("approved_sources must be a non-empty list" in error for error in result.errors)
