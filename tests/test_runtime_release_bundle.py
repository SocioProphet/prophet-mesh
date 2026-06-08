from pathlib import Path

from prophet_mesh.runtime_release_bundle import validate_runtime_release_bundle_file


def test_runtime_release_bundle_accepted_validates():
    result = validate_runtime_release_bundle_file(Path("examples/runtime-release-bundle.accepted.json"))
    assert result.valid, result.errors


def test_runtime_release_bundle_rejected_fails():
    result = validate_runtime_release_bundle_file(Path("examples/runtime-release-bundle.rejected.json"))
    assert not result.valid
    joined = " ".join(result.errors)
    assert "validation.valid" in joined
    assert "awaiting_approval" in joined
    assert "memory_scope" in joined
