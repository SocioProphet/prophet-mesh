"""Assay verdict substrate — projection, measured-trust validators, gate wiring, fleet rollup."""

from __future__ import annotations

import pytest

from prophet_mesh.assay import (
    LocalModeError,
    assay_resolver,
    build_rollup,
    deployment_mode,
    is_calibrated,
    project,
    validate_assay_rollup,
    validate_assay_standard,
    validate_reasoning_assay,
)
from prophet_mesh.pkg import Node, Provenance
from prophet_mesh.pkg_gate import gate
from prophet_mesh.pkg_ops import EmittingPKG

# --- fixtures ---------------------------------------------------------------

CAL = "urn:srcos:assay-standard:nf:0.2.0"
UNCAL = "urn:srcos:assay-standard:nli:0.1.0"

STANDARDS = {
    CAL: {
        "id": CAL, "type": "AssayStandard", "verifierId": "nf", "version": "0.2.0",
        "confusionMatrix": {"truePositive": 41, "falsePositive": 12, "trueNegative": 38, "falseNegative": 9},
        "calibrationThreshold": 0.6, "calibrated": True, "sampleSize": 100,
    },
    UNCAL: {
        "id": UNCAL, "type": "AssayStandard", "verifierId": "nli", "version": "0.1.0",
        "confusionMatrix": {"truePositive": 12, "falsePositive": 30, "trueNegative": 20, "falseNegative": 38},
        "calibrationThreshold": 0.6, "calibrated": False, "sampleSize": 100,
    },
}


def _assay(method="computed", binding="inline", judgment="supported", cal_ref=CAL, integrity=True, **extra):
    a = {
        "id": "urn:srcos:reasoning-assay:x", "type": "ReasoningAssay",
        "runRef": "urn:srcos:reasoning-run:r", "method": method, "binding": binding,
        "verifier": {"verifierId": "v", "judgment": judgment, "calibrationRef": cal_ref},
        "authority": {"actorRef": "urn:srcos:agent:a", "channel": "tool", "integrityVerified": integrity},
        "assayedAt": "2026-07-05T00:00:00Z",
    }
    a.update(extra)
    return a


# --- projection -------------------------------------------------------------

def test_deployment_mode_splits_on_locus():
    assert deployment_mode("trusted_private") == "local"
    assert deployment_mode("burst_cloud") == "fleet"
    with pytest.raises(ValueError):
        deployment_mode("mars")


def test_projection_ok():
    assert project(_assay(), STANDARDS) == "ok"


def test_projection_sad_when_generated_or_uncalibrated():
    assert project(_assay(method="generated", binding="post-hoc"), STANDARDS) == "sad"
    assert project(_assay(cal_ref=UNCAL), STANDARDS) == "sad"


def test_projection_refuted_needs_calibration_to_reach_bad():
    assert project(_assay(judgment="refuted", cal_ref=CAL), STANDARDS) == "bad"
    # an uncalibrated verifier cannot force bad
    assert project(_assay(judgment="refuted", cal_ref=UNCAL), STANDARDS) == "sad"


def test_projection_authority_broken_is_bad():
    assert project(_assay(integrity=False), STANDARDS) == "bad"


# --- measured trust, not asserted -------------------------------------------

def test_calibration_is_derived_not_asserted():
    assert is_calibrated(STANDARDS[CAL]) is True
    assert is_calibrated(STANDARDS[UNCAL]) is False
    # a standard that LIES about being calibrated is rejected
    liar = dict(STANDARDS[UNCAL], calibrated=True)
    assert validate_assay_standard(liar).valid is False


def test_standard_metrics_must_match_matrix():
    bogus = dict(STANDARDS[CAL], metrics={"f1": 0.99})
    assert validate_assay_standard(bogus).valid is False


def test_reasoning_assay_requires_judgment():
    a = _assay()
    del a["verifier"]["judgment"]
    assert validate_reasoning_assay(a).valid is False


def test_agreement_votes_cannot_exceed_arms():
    a = _assay(agreement={"arms": 1, "effectiveVotes": 99})
    assert validate_reasoning_assay(a).valid is False
    ok = _assay(agreement={"arms": 3, "effectiveVotes": 2.4})
    assert validate_reasoning_assay(ok).valid is True


# --- gate integration: AssayStandard-backed admission for cloud loci --------

def test_assay_resolver_admits_ok_quarantines_sad_through_gate():
    ok_ref, sad_ref = "att:ok", "att:sad"
    resolver = assay_resolver({ok_ref: _assay(), sad_ref: _assay(cal_ref=UNCAL)}, STANDARDS)

    epkg = EmittingPKG.seeded("self", replica_id="cloud-1", locus="burst_cloud")
    prov = Provenance(source="test", method="declared")
    epkg.add_node(Node(id="good", type="Fact", label="admitted", provenance=prov, assertion_class="Structural"),
                  attestation_ref=ok_ref)
    epkg.add_node(Node(id="weak", type="Fact", label="quarantined", provenance=prov, assertion_class="Structural"),
                  attestation_ref=sad_ref)

    result = gate(epkg.log, resolve=resolver, run_locus="burst_cloud")

    admitted_refs = {e["payload"]["crdt"]["attestationRef"] for e in result.canonical_ops}
    quarantined_refs = {e["payload"]["crdt"]["attestationRef"] for e in result.quarantine_ops}
    assert ok_ref in admitted_refs
    assert sad_ref in quarantined_refs
    # the unattested genesis Self op is fail-closed out of the canonical view too
    assert None in quarantined_refs


def test_local_locus_needs_no_assay():
    # a trusted-private op is admitted with the default fail-closed resolver, no attestation
    epkg = EmittingPKG.seeded("self", replica_id="device-a", locus="trusted_private")
    result = gate(epkg.log, run_locus="trusted_private")
    assert result.admitted >= 1
    assert result.quarantined == 0


# --- fleet rollup: cloud-mesh only, structurally absent locally -------------

def test_local_mode_forbids_fleet_rollup():
    window = {"from": "2026-07-05T00:00:00Z", "to": "2026-07-05T01:00:00Z"}
    with pytest.raises(LocalModeError):
        build_rollup([_assay()], STANDARDS, scope_mode="fleet", node_count=1,
                     window=window, rollup_id="urn:srcos:assay-rollup:x", captured_at="2026-07-05T01:00:01Z")


def test_node_self_view_allowed_without_fleet_fields():
    window = {"from": "2026-07-05T00:00:00Z", "to": "2026-07-05T01:00:00Z"}
    r = build_rollup([_assay()], STANDARDS, scope_mode="node", node_count=1,
                     window=window, rollup_id="urn:srcos:assay-rollup:local", captured_at="2026-07-05T01:00:01Z")
    assert r["scope"]["mode"] == "node"
    assert "standardAdoption" not in r  # no fleet view on device
    assert validate_assay_rollup(r).valid is True


def test_fleet_rollup_builds_adoption_and_detects_drift():
    window = {"from": "2026-07-05T00:00:00Z", "to": "2026-07-05T01:00:00Z"}
    assays = [_assay(cal_ref=CAL), _assay(method="generated", binding="post-hoc", cal_ref=UNCAL,
                                          unassayedReason="uncalibrated-verifier")]
    r = build_rollup(assays, STANDARDS, scope_mode="fleet", node_count=2,
                     window=window, rollup_id="urn:srcos:assay-rollup:fleet", captured_at="2026-07-05T01:00:01Z")
    assert r["distribution"] == {"ok": 1, "sad": 1, "bad": 0}
    assert r["driftDetected"] is True  # a calibrated + an uncalibrated standard live at once
    assert r["unassayedReasons"] == {"uncalibrated-verifier": 1}
    assert validate_assay_rollup(r).valid is True
