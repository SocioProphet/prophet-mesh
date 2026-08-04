"""Governed-acquisition intake: LandedRecord validation, the evidence store, and the endpoint."""

from __future__ import annotations

import importlib.util

import pytest

from prophet_mesh.acquisition_intake import (
    EvidenceStore,
    ingest_record,
    validate_landed_record,
)

_HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None


@pytest.fixture()
def store(tmp_path):
    return EvidenceStore(tmp_path / "evidence.jsonl")


def _landed_record(**overrides) -> dict:
    record = {
        "provenance": {
            "sourceId": "src-acme-news",
            "url": "https://example.com/article",
            "fetchedAt": "2026-08-04T12:00:00Z",
            "httpStatus": 200,
            "contentHash": "sha256:" + "a" * 64,
            "tier": "T1",
            "renderMode": "http",
            "egress": {"class": "datacenter", "geo": "US"},
            "posture": "enforced",
            "policy": {
                "robots": "allowed",
                "tos": "public",
                "pii": False,
                "legalBasis": "public-data",
            },
            "override": None,
            "accountClass": "sovereign",
            "warnings": [],
        },
        "body": "the fetched content",
        "enrichment": {"enricher": "synapseiq", "enrichedAt": "2026-08-04T12:00:01Z", "language": "en"},
    }
    for key, value in overrides.items():
        record[key] = value
    return record


# ── unit: validate_landed_record ──────────────────────────────────────────────
def test_validate_accepts_a_well_formed_record():
    result = validate_landed_record(_landed_record())
    assert result.valid is True
    assert result.errors == []


def test_validate_rejects_missing_provenance_fields():
    record = _landed_record()
    del record["provenance"]["contentHash"]
    del record["provenance"]["tier"]
    result = validate_landed_record(record)
    assert result.valid is False
    assert any("missing required provenance fields" in e for e in result.errors)
    assert any("contentHash" in e and "tier" in e for e in result.errors)


def test_validate_rejects_auth_gated_tos():
    record = _landed_record()
    record["provenance"]["policy"]["tos"] = "auth-gated"
    result = validate_landed_record(record)
    assert result.valid is False
    assert any("auth-gated" in e for e in result.errors)


def test_validate_rejects_bad_enums_and_hash():
    record = _landed_record()
    record["provenance"]["tier"] = "T9"
    record["provenance"]["renderMode"] = "carrier-pigeon"
    record["provenance"]["contentHash"] = "md5:deadbeef"
    result = validate_landed_record(record)
    assert result.valid is False
    assert any("tier" in e for e in result.errors)
    assert any("renderMode" in e for e in result.errors)
    assert any("sha256" in e for e in result.errors)


# ── ingest_record + store ─────────────────────────────────────────────────────
def test_ingest_lands_evidence_and_is_retrievable(store):
    record = _landed_record()
    receipt = ingest_record(record, store=store)
    assert receipt["accepted"] is True
    assert receipt["evidenceRef"] == record["provenance"]["contentHash"]
    assert receipt["sourceId"] == "src-acme-news"
    assert receipt["url"] == "https://example.com/article"
    # the landed evidence is retrievable by its ref, with body + enrichment intact
    landed = store.get(receipt["evidenceRef"])
    assert landed is not None
    assert landed["body"] == "the fetched content"
    assert landed["enrichment"]["enricher"] == "synapseiq"
    assert store.count() == 1


def test_ingest_is_idempotent_by_content_hash(store):
    record = _landed_record()
    ingest_record(record, store=store)
    ingest_record(record, store=store)  # same contentHash → same evidence ref
    assert store.count() == 1


def test_ingest_raises_on_invalid_record(store):
    record = _landed_record()
    record["provenance"]["policy"]["tos"] = "auth-gated"
    with pytest.raises(ValueError):
        ingest_record(record, store=store)
    assert store.count() == 0  # nothing ungoverned was written


# ── endpoint: POST /v1/acquire/ingest ─────────────────────────────────────────
@pytest.mark.skipif(not _HAS_FASTAPI, reason="fastapi (serve extra) not installed")
def test_endpoint_ingests_then_evidence_is_landed(tmp_path, monkeypatch):
    monkeypatch.setenv("PROPHET_MESH_EVIDENCE_STORE", str(tmp_path / "evidence.jsonl"))
    from fastapi.testclient import TestClient

    from prophet_mesh.api import app

    client = TestClient(app)
    record = _landed_record()
    resp = client.post("/v1/acquire/ingest", json=record)
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] is True
    assert body["evidenceRef"] == record["provenance"]["contentHash"]

    # the evidence actually landed in the store the endpoint wrote to
    landed = EvidenceStore(tmp_path / "evidence.jsonl").get(body["evidenceRef"])
    assert landed is not None
    assert landed["provenance"]["sourceId"] == "src-acme-news"


@pytest.mark.skipif(not _HAS_FASTAPI, reason="fastapi (serve extra) not installed")
def test_endpoint_rejects_malformed_json(tmp_path, monkeypatch):
    monkeypatch.setenv("PROPHET_MESH_EVIDENCE_STORE", str(tmp_path / "evidence.jsonl"))
    from fastapi.testclient import TestClient

    from prophet_mesh.api import app

    client = TestClient(app)
    resp = client.post(
        "/v1/acquire/ingest", content=b"{not json", headers={"content-type": "application/json"}
    )
    assert resp.status_code == 400


@pytest.mark.skipif(not _HAS_FASTAPI, reason="fastapi (serve extra) not installed")
def test_endpoint_rejects_auth_gated_record(tmp_path, monkeypatch):
    monkeypatch.setenv("PROPHET_MESH_EVIDENCE_STORE", str(tmp_path / "evidence.jsonl"))
    from fastapi.testclient import TestClient

    from prophet_mesh.api import app

    client = TestClient(app)
    record = _landed_record()
    record["provenance"]["policy"]["tos"] = "auth-gated"
    resp = client.post("/v1/acquire/ingest", json=record)
    assert resp.status_code == 400
    assert "auth-gated" in resp.json()["detail"]
    # rejected → nothing landed
    assert EvidenceStore(tmp_path / "evidence.jsonl").count() == 0
