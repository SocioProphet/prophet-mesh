"""SolutionShortlist contract tests.

The invariant this file exists for: `autoRouteVerdict.decision == 'auto-route'` MUST be
justified — top-2 gap >= AUTO_ROUTE_GAP_THRESHOLD, top counterTestStatus == 'confirmed',
top accessDecision.grade == 'granted'. A shortlist that CLAIMS auto-route without those
preconditions is invalid, and this suite pins each precondition by observing rejection.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from prophet_mesh.solution_shortlist import (
    AUTO_ROUTE_GAP_THRESHOLD,
    validate,
)

EXAMPLE_PATH = Path(__file__).resolve().parents[1] / "examples" / "solution-shortlist.accepted.json"


@pytest.fixture()
def accepted_example() -> dict:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def test_shipped_example_validates(accepted_example: dict) -> None:
    r = validate(accepted_example)
    assert r.valid, f"shipped example must validate: {r.errors}"


def test_empty_shortlist_requires_emptyReason(accepted_example: dict) -> None:
    e = copy.deepcopy(accepted_example)
    e["shortlist"] = []
    e.pop("autoRouteVerdict", None)  # auto-route makes no sense on empty
    e.pop("emptyReason", None)
    r = validate(e)
    assert not r.valid
    assert any("emptyReason" in msg for msg in r.errors), r.errors


def test_empty_shortlist_emptyReason_must_be_substantive(accepted_example: dict) -> None:
    e = copy.deepcopy(accepted_example)
    e["shortlist"] = []
    e["emptyReason"] = "no"  # too short
    e.pop("autoRouteVerdict", None)
    r = validate(e)
    assert not r.valid
    assert any("substantive" in msg for msg in r.errors), r.errors


def test_empty_shortlist_with_substantive_reason_validates(accepted_example: dict) -> None:
    e = copy.deepcopy(accepted_example)
    e["shortlist"] = []
    e["emptyReason"] = "no participant in MeshActionRegistry claims implementsAbb: ABB.03"
    e.pop("autoRouteVerdict", None)
    r = validate(e)
    assert r.valid, r.errors


def test_auto_route_requires_gap_over_threshold(accepted_example: dict) -> None:
    """The precondition that makes 'auto-route' lawful — the top-2 score gap.

    Below the threshold, Michael MUST return the shortlist for user pick. A claim of
    auto-route with a small gap is a shape-only failure: caller reads the verdict, trusts
    it, and never sees the runner-up that was almost as good.
    """
    e = copy.deepcopy(accepted_example)
    # Push runner-up close to the top so the gap collapses
    e["shortlist"][1]["score"] = e["shortlist"][0]["score"] - 0.01
    r = validate(e)
    assert not r.valid
    assert any("top-2 score gap" in msg for msg in r.errors), r.errors


def test_auto_route_requires_confirmed_counter_test(accepted_example: dict) -> None:
    """Per Noetica#570's counter-test gate. A candidate without a confirmed counter-test
    appears in the shortlist but never auto-routes."""
    e = copy.deepcopy(accepted_example)
    e["shortlist"][0]["counterTestStatus"] = "available"  # not confirmed
    r = validate(e)
    assert not r.valid
    assert any("counterTestStatus" in msg for msg in r.errors), r.errors


def test_auto_route_requires_granted_access(accepted_example: dict) -> None:
    """A requires-consent or denied candidate can appear in the shortlist but cannot
    auto-route — the user has to see and act on the remediation."""
    e = copy.deepcopy(accepted_example)
    e["shortlist"][0]["accessDecision"] = {"grade": "requires-consent", "trustScore": 0.82}
    r = validate(e)
    assert not r.valid
    assert any("accessDecision.grade" in msg for msg in r.errors), r.errors


def test_auto_route_requires_at_least_two_candidates(accepted_example: dict) -> None:
    """A one-candidate shortlist can be presented but cannot be auto-routed — with only
    one option the 'gap' is undefined and 'auto' is the caller's default, not Michael's."""
    e = copy.deepcopy(accepted_example)
    e["shortlist"] = [e["shortlist"][0]]
    r = validate(e)
    assert not r.valid
    assert any("at least 2 candidates" in msg for msg in r.errors), r.errors


def test_matchReason_cannot_be_empty(accepted_example: dict) -> None:
    """A candidate with an unreadable reason is a candidate nobody should route to.
    Empty matchReason means either the ranker failed to record its work OR nothing actually
    matched — either way, the candidate has no business appearing."""
    e = copy.deepcopy(accepted_example)
    e["shortlist"][0]["matchReason"] = []
    r = validate(e)
    assert not r.valid


def test_score_out_of_bounds_rejected(accepted_example: dict) -> None:
    e = copy.deepcopy(accepted_example)
    e["shortlist"][0]["score"] = 1.5
    r = validate(e)
    assert not r.valid


def test_abbRequirement_pattern_enforced(accepted_example: dict) -> None:
    e = copy.deepcopy(accepted_example)
    e["abbRequirement"] = "ABB.3"  # one digit — must be two
    r = validate(e)
    assert not r.valid


def test_participantRef_must_be_owner_slash_repo(accepted_example: dict) -> None:
    e = copy.deepcopy(accepted_example)
    e["shortlist"][0]["participantRef"] = "just-a-repo"
    r = validate(e)
    assert not r.valid


def test_gap_threshold_is_exposed_as_constant() -> None:
    """AUTO_ROUTE_GAP_THRESHOLD is a MODULE constant, not a magic number, so a policy change
    is one edit and the test that pins it here is the change-notice."""
    assert 0 < AUTO_ROUTE_GAP_THRESHOLD < 1
    assert AUTO_ROUTE_GAP_THRESHOLD == 0.15  # if this changes, callers must be reviewed


def test_derived_from_digests_required(accepted_example: dict) -> None:
    """Provenance is not optional. A shortlist without derivedFrom digests cannot be checked
    for staleness — the caller has no way to know if the underlying MAR or ABB catalog moved
    after the shortlist was computed."""
    e = copy.deepcopy(accepted_example)
    e["derivedFrom"] = {}
    r = validate(e)
    assert not r.valid
