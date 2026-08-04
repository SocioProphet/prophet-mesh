"""Baseline NL claim verifier + its real (non-synthetic) calibration."""

from __future__ import annotations

import json
from pathlib import Path

from prophet_mesh.assay import validate_assay_standard
from prophet_mesh.assay_calibrate import calibrate, confusion_from_labelled
from prophet_mesh.nl_verifier import predict_labelled, verify

REPO = Path(__file__).resolve().parents[1]
CORPUS = REPO / "examples" / "calibration" / "nl_claim_verification.jsonl"


def _load():
    return [json.loads(line) for line in CORPUS.read_text().splitlines() if line.strip()]


def test_verifier_handles_clean_and_negation():
    assert verify("The server returned a 200 status code.",
                  "The request completed and the server returned a 200 status code.") == "supported"
    # polarity mismatch reads as refuted
    assert verify("The server was reachable.",
                  "The server was not reachable during the outage.") == "refuted"


def test_baseline_is_honestly_imperfect():
    # paraphrase → missed (false negative); entity swap → fooled (false positive)
    assert verify("The incident was resolved quickly.",
                  "Engineers restored service in a short time.") == "refuted"      # FN
    assert verify("Node A promoted the standard.",
                  "Node B promoted the standard.") == "supported"                  # FP


def test_corpus_is_balanced_and_min_n():
    items = _load()
    assert len(items) >= 30
    supported = sum(1 for i in items if i["gold"] == "supported")
    refuted = sum(1 for i in items if i["gold"] == "refuted")
    assert supported == refuted  # balanced


def test_calibration_reproduces_committed_standard():
    items = _load()
    preds = predict_labelled(items)
    m = confusion_from_labelled(preds, positive="supported")
    assert m == {"truePositive": 12, "falsePositive": 6, "trueNegative": 10, "falseNegative": 4}

    std = calibrate("urn:srcos:verifier:nl-lexical-baseline", "v1", preds,
                    positive="supported", measured_at="2026-07-05T00:00:00Z")
    committed = json.loads((REPO / "examples" / "assay_standard.nl_baseline.json").read_text())
    assert std == committed  # the committed standard is exactly what the pipeline emits
    assert std["calibrated"] is True  # F1 0.706 clears the 0.6 bar — just
    assert validate_assay_standard(std).valid is True
