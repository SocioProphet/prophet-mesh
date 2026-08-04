"""Calibration emitter — real confusion matrix from labelled verifier outputs → AssayStandard."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from prophet_mesh.assay import project, validate_assay_standard
from prophet_mesh.assay_calibrate import (
    calibrate,
    cohens_kappa,
    confusion_from_labelled,
    interpret_kappa,
)

REPO = Path(__file__).resolve().parents[1]


def _labelled(tp, fp, tn, fn):
    items = []
    items += [{"predicted": "supported", "gold": "supported"}] * tp
    items += [{"predicted": "supported", "gold": "refuted"}] * fp
    items += [{"predicted": "refuted", "gold": "refuted"}] * tn
    items += [{"predicted": "refuted", "gold": "supported"}] * fn
    return items


def test_confusion_matrix_counts():
    m = confusion_from_labelled(_labelled(8, 2, 7, 3))
    assert m == {"truePositive": 8, "falsePositive": 2, "trueNegative": 7, "falseNegative": 3}


def test_accepts_booleans():
    m = confusion_from_labelled([{"predicted": True, "gold": True}, {"predicted": False, "gold": True}])
    assert m == {"truePositive": 1, "falsePositive": 0, "trueNegative": 0, "falseNegative": 1}


def test_empty_set_rejected():
    with pytest.raises(ValueError):
        confusion_from_labelled([])


def test_cohens_kappa_and_bands():
    m = confusion_from_labelled(_labelled(8, 2, 7, 3))
    assert math.isclose(cohens_kappa(m), 0.5, abs_tol=1e-9)
    assert interpret_kappa(0.5) == "moderate"
    assert interpret_kappa(0.7) == "substantial"
    assert interpret_kappa(0.1) == "slight"
    assert interpret_kappa(-0.1) == "poor"


def test_calibrate_emits_valid_calibrated_standard():
    std = calibrate("urn:srcos:verifier:narration-fidelity", "1.0.0", _labelled(8, 2, 7, 3),
                    measured_at="2026-07-05T00:00:00Z")
    assert std["id"] == "urn:srcos:assay-standard:narration-fidelity:1.0.0"
    assert std["confusionMatrix"] == {"truePositive": 8, "falsePositive": 2, "trueNegative": 7, "falseNegative": 3}
    assert math.isclose(std["metrics"]["f1"], 0.7619, abs_tol=1e-3)
    assert std["calibrated"] is True                       # F1 0.76 >= 0.6
    assert std["interRaterAgreement"]["interpretation"] == "moderate"
    # the emitter's output must pass the same soundness gate the framework enforces
    assert validate_assay_standard(std).valid is True


def test_weak_verifier_is_not_calibrated():
    std = calibrate("urn:srcos:verifier:deployed-nli", "0.1.0", _labelled(2, 8, 2, 8),
                    measured_at="2026-07-05T00:00:00Z")
    assert std["metrics"]["f1"] < 0.6
    assert std["calibrated"] is False
    assert validate_assay_standard(std).valid is True       # honest: low F1, flag False, consistent


def test_refutation_detector_framing():
    # positive='refuted': a verifier whose job is catching lies. Abstentions (mapped
    # to the non-positive label) belong in the negative class, not counted as support.
    items = (
        [{"predicted": "refuted", "gold": "refuted"}] * 8      # caught lies (TP)
        + [{"predicted": "supported", "gold": "supported"}] * 34  # correctly not flagged (TN)
    )
    m = confusion_from_labelled(items, positive="refuted")
    assert m == {"truePositive": 8, "falsePositive": 0, "trueNegative": 34, "falseNegative": 0}
    std = calibrate("urn:srcos:verifier:narration-fidelity", "cfr-eval-001", items,
                    positive="refuted", measured_at="2026-07-05T00:00:00Z")
    assert std["metrics"]["f1"] == 1.0
    assert std["calibrated"] is True
    assert validate_assay_standard(std).valid is True


def test_committed_real_standard_is_sound_and_usable():
    # the standard derived from the real SP-TRACE-CFR verifier must stay valid and usable
    std = json.loads((REPO / "examples" / "assay_standard.narration_fidelity.json").read_text())
    assert validate_assay_standard(std).valid is True
    assert std["calibrated"] is True
    assay = {
        "method": "computed", "binding": "inline",
        "verifier": {"judgment": "supported", "calibrationRef": std["id"]},
        "authority": {"integrityVerified": True},
    }
    assert project(assay, {std["id"]: std}) == "ok"


def test_calibrated_standard_round_trips_into_projection():
    std = calibrate("urn:srcos:verifier:narration-fidelity", "1.0.0", _labelled(8, 2, 7, 3),
                    measured_at="2026-07-05T00:00:00Z")
    standards = {std["id"]: std}
    assay = {
        "method": "computed", "binding": "inline",
        "verifier": {"judgment": "supported", "calibrationRef": std["id"]},
        "authority": {"integrityVerified": True},
    }
    assert project(assay, standards) == "ok"     # a real, earned ok
    # the same claim behind the weak verifier cannot reach ok
    weak = calibrate("urn:srcos:verifier:deployed-nli", "0.1.0", _labelled(2, 8, 2, 8),
                     measured_at="2026-07-05T00:00:00Z")
    assay["verifier"]["calibrationRef"] = weak["id"]
    assert project(assay, {weak["id"]: weak}) == "sad"
