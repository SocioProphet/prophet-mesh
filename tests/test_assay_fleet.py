"""Fleet rollup builder + the /fleet/rollup endpoint."""

from __future__ import annotations

import importlib.util

import pytest

from prophet_mesh.assay import validate_assay_rollup
from prophet_mesh.assay_fleet import build_fleet_snapshot

_HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None


def test_snapshot_distribution_is_computed_and_sound():
    snap = build_fleet_snapshot()
    rollup = snap["rollup"]
    # distribution is computed by projecting the 12 seeded assays
    assert rollup["distribution"] == {"ok": 4, "sad": 6, "bad": 2}
    assert sum(rollup["distribution"].values()) == rollup["totalAssays"] == 12
    assert validate_assay_rollup(rollup).valid is True


def test_snapshot_surfaces_drift_and_reasons():
    rollup = build_fleet_snapshot()["rollup"]
    assert rollup["driftDetected"] is True  # 3 versions, one uncalibrated
    assert rollup["unassayedReasons"] == {"post-hoc-binding": 3, "uncalibrated-verifier": 3}
    assert rollup["byMethod"] == {"computed": 6, "retrieved": 3, "generated": 3}


def test_snapshot_standards_include_the_real_calibrations():
    standards = build_fleet_snapshot()["standards"]
    by_id = {s["verifierId"]: s for s in standards}
    assert by_id["narration-fidelity"]["real"] is True
    assert by_id["narration-fidelity"]["calibrated"] is True
    assert by_id["nl-lexical-baseline"]["real"] is True
    assert by_id["deployed-nli"]["calibrated"] is False


def test_rollout_is_gated_on_an_observed_rollup():
    snap = build_fleet_snapshot()
    rollout = snap["rollout"]
    assert rollout["guard"]["observedRollupRef"] == snap["rollup"]["id"]
    assert rollout["guard"]["decision"] == "continue"


@pytest.mark.skipif(not _HAS_FASTAPI, reason="fastapi (serve extra) not installed")
def test_endpoint_serves_the_snapshot():
    from fastapi.testclient import TestClient

    from prophet_mesh.api import app

    resp = TestClient(app).get("/fleet/rollup")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"rollup", "rollout", "standards"}
    assert body["rollup"]["scope"]["mode"] == "fleet"
    assert validate_assay_rollup(body["rollup"]).valid is True
