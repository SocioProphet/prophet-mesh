from pathlib import Path

from prophet_mesh.runtime_release_bundle import validate_runtime_release_bundle, validate_runtime_release_bundle_file

VALID_ADAPTER_REF = {
    "repo": "SocioProphet/agentplane",
    "path": "contracts/prophet-mesh/prophet-mesh-agentplane-adapter.v0.1.json",
    "contract_version": "v0.1",
    "merge_commit": "faa767f42028ad0f2475c993700cdbef8490a38e",
    "content_sha256": "38a3edb62813521a62f257f3f952271255d25dc3a05a14d6b96f04a6ff9b4268",
    "mode": "dry_run_receipt_preview",
    "required": True,
}


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


def _load_accepted_bundle() -> dict:
    import json
    with open("examples/runtime-release-bundle.accepted.json") as f:
        return json.load(f)


def test_agentplane_adapter_ref_absent_fails():
    bundle = _load_accepted_bundle()
    del bundle["agentplane_adapter_ref"]
    result = validate_runtime_release_bundle(bundle)
    assert not result.valid
    assert any("agentplane_adapter_ref is required" in e for e in result.errors)


def test_agentplane_adapter_ref_wrong_repo_fails():
    bundle = _load_accepted_bundle()
    bundle["agentplane_adapter_ref"] = {**VALID_ADAPTER_REF, "repo": "SocioProphet/wrong-repo"}
    result = validate_runtime_release_bundle(bundle)
    assert not result.valid
    assert any("agentplane_adapter_ref.repo" in e for e in result.errors)


def test_agentplane_adapter_ref_wrong_mode_fails():
    bundle = _load_accepted_bundle()
    bundle["agentplane_adapter_ref"] = {**VALID_ADAPTER_REF, "mode": "live_execution"}
    result = validate_runtime_release_bundle(bundle)
    assert not result.valid
    assert any("agentplane_adapter_ref.mode" in e for e in result.errors)


def test_agentplane_adapter_ref_required_false_fails():
    bundle = _load_accepted_bundle()
    bundle["agentplane_adapter_ref"] = {**VALID_ADAPTER_REF, "required": False}
    result = validate_runtime_release_bundle(bundle)
    assert not result.valid
    assert any("agentplane_adapter_ref.required" in e for e in result.errors)


def test_agentplane_adapter_ref_malformed_sha_fails():
    bundle = _load_accepted_bundle()
    bundle["agentplane_adapter_ref"] = {**VALID_ADAPTER_REF, "content_sha256": "not-a-sha"}
    result = validate_runtime_release_bundle(bundle)
    assert not result.valid
    assert any("content_sha256" in e for e in result.errors)


def test_agentplane_adapter_ref_missing_path_fails():
    bundle = _load_accepted_bundle()
    ref = {k: v for k, v in VALID_ADAPTER_REF.items() if k != "path"}
    bundle["agentplane_adapter_ref"] = ref
    result = validate_runtime_release_bundle(bundle)
    assert not result.valid
    assert any("agentplane_adapter_ref.path" in e for e in result.errors)
