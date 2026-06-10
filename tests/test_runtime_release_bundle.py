import copy
from pathlib import Path

from prophet_mesh.runtime_release_bundle import (
    validate_runtime_release_bundle,
    validate_runtime_release_bundle_file,
    load_runtime_release_contract,
    load_runtime_release_bundle,
)

CONTRACT = load_runtime_release_contract()
ACCEPTED = load_runtime_release_bundle(Path("examples/runtime-release-bundle.accepted.json"))


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


# ── Adapter ref rejection tests ───────────────────────────────────────────────

def _mutate(path: list[str], value) -> dict:
    """Return a deep copy of ACCEPTED with the given nested path set to value."""
    bundle = copy.deepcopy(ACCEPTED)
    target = bundle
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return bundle


def _drop(path: list[str]) -> dict:
    """Return a deep copy of ACCEPTED with the given nested key deleted."""
    bundle = copy.deepcopy(ACCEPTED)
    target = bundle
    for key in path[:-1]:
        target = target[key]
    del target[path[-1]]
    return bundle


def test_adapter_refs_absent_rejected():
    bundle = _drop(["adapter_refs"])
    result = validate_runtime_release_bundle(bundle, CONTRACT)
    assert not result.valid
    assert any("adapter_refs" in e and "absent" in e for e in result.errors)


def test_adapter_refs_agentplane_missing_rejected():
    bundle = _mutate(["adapter_refs"], {})
    result = validate_runtime_release_bundle(bundle, CONTRACT)
    assert not result.valid
    assert any("agentplane_adapter" in e and "missing" in e for e in result.errors)


def test_adapter_refs_required_false_rejected():
    bundle = _mutate(["adapter_refs", "agentplane_adapter", "required"], False)
    result = validate_runtime_release_bundle(bundle, CONTRACT)
    assert not result.valid
    assert any("required must be true" in e for e in result.errors)


def test_adapter_refs_wrong_mode_rejected():
    bundle = _mutate(["adapter_refs", "agentplane_adapter", "mode"], "live_execution")
    result = validate_runtime_release_bundle(bundle, CONTRACT)
    assert not result.valid
    assert any("mode" in e and "dry_run_receipt_preview" in e for e in result.errors)


def test_adapter_refs_wrong_repo_rejected():
    bundle = _mutate(["adapter_refs", "agentplane_adapter", "repo"], "other-org/agentplane")
    result = validate_runtime_release_bundle(bundle, CONTRACT)
    assert not result.valid
    assert any("repo" in e for e in result.errors)


def test_adapter_refs_wrong_path_rejected():
    bundle = _mutate(["adapter_refs", "agentplane_adapter", "path"], "contracts/wrong/path.json")
    result = validate_runtime_release_bundle(bundle, CONTRACT)
    assert not result.valid
    assert any("path" in e for e in result.errors)


def test_adapter_refs_missing_sha256_rejected():
    bundle = _drop(["adapter_refs", "agentplane_adapter", "content_sha256"])
    result = validate_runtime_release_bundle(bundle, CONTRACT)
    assert not result.valid
    assert any("content_sha256" in e for e in result.errors)


def test_adapter_refs_malformed_sha256_rejected():
    bundle = _mutate(["adapter_refs", "agentplane_adapter", "content_sha256"], "not-a-hash")
    result = validate_runtime_release_bundle(bundle, CONTRACT)
    assert not result.valid
    assert any("content_sha256" in e and "64-character" in e for e in result.errors)


def test_adapter_refs_missing_merge_commit_rejected():
    bundle = _drop(["adapter_refs", "agentplane_adapter", "merge_commit"])
    result = validate_runtime_release_bundle(bundle, CONTRACT)
    assert not result.valid
    assert any("merge_commit" in e for e in result.errors)


def test_rejected_fixture_includes_adapter_mode_and_required_errors():
    """Rejected fixture has mode=live_execution and required=false — both must surface."""
    result = validate_runtime_release_bundle_file(Path("examples/runtime-release-bundle.rejected.json"))
    assert not result.valid
    joined = " ".join(result.errors)
    assert "dry_run_receipt_preview" in joined
    assert "required must be true" in joined
