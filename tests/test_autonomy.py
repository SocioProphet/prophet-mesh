"""Tests for the AI-driven-development autonomy ladder + gate engine."""

from __future__ import annotations

from pathlib import Path

import json

from prophet_mesh.autonomy import (
    AutonomyLadder,
    canonical_ladder_file,
    validate_ai_driven_development_file,
)

SPEC = Path("specs/ai-driven-development.yaml")
CANONICAL = Path("specs/ai-driven-development.ladder.json")


def test_spec_is_valid() -> None:
    result = validate_ai_driven_development_file(SPEC)
    assert result.valid, result.errors


def test_l0_is_always_grantable_without_evidence() -> None:
    ladder = AutonomyLadder.from_file(SPEC)
    decision = ladder.evaluate(role="anyone", requested_level="L0", available_evidence=set())
    assert decision.granted_level == "L0"
    assert decision.demoted is False


def test_full_evidence_grants_requested_level() -> None:
    ladder = AutonomyLadder.from_file(SPEC)
    decision = ladder.evaluate(
        role="conductor",
        requested_level="L4",
        available_evidence={"conductor_response_envelope"},
    )
    assert decision.granted_level == "L4"
    assert decision.demoted is False


def test_missing_evidence_demotes_fail_closed() -> None:
    ladder = AutonomyLadder.from_file(SPEC)
    decision = ladder.evaluate(
        role="coding",
        requested_level="L2",
        available_evidence=set(),  # no test/review receipt
    )
    # L2 needs a test/review receipt; without it we must not grant L2.
    assert decision.granted_level != "L2"
    assert decision.demoted is True
    assert "demote" in decision.reason


def test_role_ceiling_caps_authorization() -> None:
    ladder = AutonomyLadder.from_file(SPEC)
    # 'writing' is in the full L4 choir but never declared at L5; it cannot
    # reach standing autonomous operation.
    decision = ladder.evaluate(
        role="writing",
        requested_level="L5",
        available_evidence={"continuous_attestation_with_revocation"},
    )
    assert decision.role_ceiling == "L4"
    assert decision.granted_level != "L5"
    assert "not authorized" in decision.reason


def test_unknown_role_floors_at_l0() -> None:
    ladder = AutonomyLadder.from_file(SPEC)
    decision = ladder.evaluate(role="memory-steward", requested_level="L3")
    assert decision.role_ceiling == "L0"
    assert decision.granted_level == "L0"


def test_canonical_export_is_committed_and_current() -> None:
    # The committed canonical ladder must match what the spec exports, so
    # downstream repos (tritfabric, prophet-platform, Noetica) never drift from
    # a stale source. Regenerate with: prophet-mesh export-autonomy-ladder --out
    assert CANONICAL.exists(), "run: prophet-mesh export-autonomy-ladder --out"
    on_disk = json.loads(CANONICAL.read_text(encoding="utf-8"))
    fresh = canonical_ladder_file(SPEC)
    assert on_disk == fresh, "canonical ladder is stale; regenerate it"


def test_l1_admits_with_disclosure_trail() -> None:
    ladder = AutonomyLadder.from_file(SPEC)
    decision = ladder.evaluate(
        role="writing", requested_level="L1", available_evidence={"trail_log"}
    )
    assert decision.granted_level == "L1"
    assert decision.demoted is False
