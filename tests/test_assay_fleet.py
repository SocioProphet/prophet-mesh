"""Fleet rollup builder, the persistent store, and the /fleet endpoints."""

from __future__ import annotations

import importlib.util

import pytest

from prophet_mesh.assay import validate_assay_rollup
from prophet_mesh.assay_fleet import build_fleet_snapshot, record_node_assay
from prophet_mesh.assay_store import AssayStore

_HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None


@pytest.fixture()
def store(tmp_path):
    return AssayStore(tmp_path / "assays.jsonl")


def _ok_assay(cal_ref: str) -> dict:
    return {
        "id": "urn:srcos:reasoning-assay:test", "type": "ReasoningAssay",
        "runRef": "urn:srcos:reasoning-run:test", "method": "computed", "binding": "inline",
        "verifier": {"judgment": "supported", "calibrationRef": cal_ref},
        "authority": {"integrityVerified": True},
    }


def test_empty_store_bootstraps_and_computes_a_sound_rollup(store):
    assert store.count() == 0
    snap = build_fleet_snapshot(store=store)
    assert store.count() == 12  # bootstrapped
    rollup = snap["rollup"]
    assert rollup["distribution"] == {"ok": 4, "sad": 6, "bad": 2}
    assert sum(rollup["distribution"].values()) == rollup["totalAssays"] == 12
    assert validate_assay_rollup(rollup).valid is True


def test_rollup_reflects_real_ingested_verdicts(store):
    build_fleet_snapshot(store=store)  # bootstrap 12
    # a real node reports an ok verdict behind a calibrated verifier
    res = record_node_assay("node-99", _ok_assay("urn:srcos:assay-standard:narration-fidelity:cfr-eval-001"), store=store)
    assert res["projectedState"] == "ok"
    snap = build_fleet_snapshot(store=store)
    assert snap["rollup"]["totalAssays"] == 13      # the new node is counted
    assert snap["rollup"]["distribution"]["ok"] == 5  # ok went 4 → 5
    assert validate_assay_rollup(snap["rollup"]).valid is True


def test_latest_verdict_per_node_supersedes(store):
    NF = "urn:srcos:assay-standard:narration-fidelity:cfr-eval-001"
    record_node_assay("node-x", _ok_assay(NF), store=store)
    # same node reports again, this time refuted; supersedes the ok (last-writer-wins)
    refuted = _ok_assay(NF)
    refuted["verifier"]["judgment"] = "refuted"
    record_node_assay("node-x", refuted, store=store)
    assert store.count() == 1  # still one node
    assert store.current()["node-x"]["verifier"]["judgment"] == "refuted"


def test_ingest_rejects_an_invalid_assay(store):
    bad = _ok_assay("urn:srcos:assay-standard:narration-fidelity:cfr-eval-001")
    del bad["verifier"]["judgment"]  # missing required axis
    with pytest.raises(ValueError):
        record_node_assay("node-bad", bad, store=store)


def test_snapshot_surfaces_drift_and_standards(store):
    snap = build_fleet_snapshot(store=store)
    rollup = snap["rollup"]
    assert rollup["driftDetected"] is True
    assert rollup["unassayedReasons"] == {"post-hoc-binding": 3, "uncalibrated-verifier": 3}
    by_id = {s["verifierId"]: s for s in snap["standards"]}
    assert by_id["narration-fidelity"]["real"] is True
    assert by_id["deployed-nli"]["calibrated"] is False


@pytest.mark.skipif(not _HAS_FASTAPI, reason="fastapi (serve extra) not installed")
def test_endpoints_ingest_then_serve(tmp_path, monkeypatch):
    monkeypatch.setenv("PROPHET_MESH_ASSAY_STORE", str(tmp_path / "assays.jsonl"))
    from fastapi.testclient import TestClient

    from prophet_mesh.api import app

    client = TestClient(app)
    # ingest a verdict
    post = client.post("/fleet/assay", json={
        "nodeRef": "node-42",
        "assay": _ok_assay("urn:srcos:assay-standard:nl-lexical-baseline:v1"),
    })
    assert post.status_code == 200
    assert post.json()["projectedState"] == "ok"
    # it shows up in the rollup
    body = client.get("/fleet/rollup").json()
    assert set(body) == {"rollup", "rollout", "standards"}
    assert validate_assay_rollup(body["rollup"]).valid is True
    assert body["rollup"]["totalAssays"] == 13  # 12 bootstrap + node-42
