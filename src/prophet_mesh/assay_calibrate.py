"""Calibration emitter — turn a verifier's labelled outputs into an AssayStandard.

This is what makes an AssayStandard *real* rather than a fixture. A verifier
(judge) that decides supported-vs-refuted is run over a labelled set; this module
computes the confusion matrix from its predictions against the gold labels, derives
F1 / precision / recall / Cohen's kappa, and emits a conformant AssayStandard whose
``calibrated`` flag is set by measurement, not assertion.

Feed it a labelled set:

    [ {"predicted": "supported", "gold": "supported"},
      {"predicted": "supported", "gold": "refuted"},   # a false positive
      ... ]

Booleans work too (True = supported). The positive class is 'supported': a
verdict projects 'ok' only behind a verifier calibrated to *support* claims well.
"""
from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .assay import DEFAULT_CALIBRATION_THRESHOLD, derived_f1, validate_assay_standard

POSITIVE = "supported"
NEGATIVE = "refuted"


def _label(value: Any) -> str:
    """Normalise a label to 'supported' / 'refuted'. Accepts bools and strings."""
    if isinstance(value, bool):
        return POSITIVE if value else NEGATIVE
    s = str(value).strip().lower()
    if s in ("supported", "support", "entailed", "true", "pass", "yes", "1"):
        return POSITIVE
    if s in ("refuted", "refute", "contradicted", "false", "fail", "no", "0"):
        return NEGATIVE
    raise ValueError(f"unrecognised label {value!r} (want supported/refuted)")


def confusion_from_labelled(items: Sequence[dict[str, Any]]) -> dict[str, int]:
    """Confusion matrix with 'supported' as the positive class."""
    if not items:
        raise ValueError("cannot calibrate on an empty labelled set")
    m = {"truePositive": 0, "falsePositive": 0, "trueNegative": 0, "falseNegative": 0}
    for it in items:
        pred, gold = _label(it["predicted"]), _label(it["gold"])
        if pred == POSITIVE and gold == POSITIVE:
            m["truePositive"] += 1
        elif pred == POSITIVE and gold == NEGATIVE:
            m["falsePositive"] += 1
        elif pred == NEGATIVE and gold == NEGATIVE:
            m["trueNegative"] += 1
        else:
            m["falseNegative"] += 1
    return m


def cohens_kappa(m: dict[str, int]) -> float:
    """Chance-corrected agreement between the verifier and the gold labels."""
    tp, fp, tn, fn = m["truePositive"], m["falsePositive"], m["trueNegative"], m["falseNegative"]
    n = tp + fp + tn + fn
    if n == 0:
        return 0.0
    po = (tp + tn) / n
    pe = ((tp + fp) * (tp + fn) + (fn + tn) * (fp + tn)) / (n * n)
    return 0.0 if pe == 1 else (po - pe) / (1 - pe)


def interpret_kappa(k: float) -> str:
    """Landis & Koch bands — the same vocabulary AssayStandard.interRaterAgreement uses."""
    if k < 0.0:
        return "poor"
    if k <= 0.20:
        return "slight"
    if k <= 0.40:
        return "fair"
    if k <= 0.60:
        return "moderate"
    if k <= 0.80:
        return "substantial"
    return "almost-perfect"


def _slug(verifier_id: str) -> str:
    return verifier_id.rsplit(":", 1)[-1]


def calibrate(
    verifier_id: str,
    version: str,
    labelled: Sequence[dict[str, Any]],
    *,
    threshold: float = DEFAULT_CALIBRATION_THRESHOLD,
    measured_at: str | None = None,
) -> dict[str, Any]:
    """Emit an AssayStandard from a verifier's labelled outputs. Every number is
    derived from the labelled set; ``calibrated`` is (F1 >= threshold), not asserted."""
    matrix = confusion_from_labelled(labelled)
    tp, fp, fn = matrix["truePositive"], matrix["falsePositive"], matrix["falseNegative"]
    f1 = derived_f1(matrix)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    kappa = cohens_kappa(matrix)

    standard: dict[str, Any] = {
        "id": f"urn:srcos:assay-standard:{_slug(verifier_id)}:{version}",
        "type": "AssayStandard",
        "specVersion": "2.0.0",
        "verifierId": verifier_id,
        "version": version,
        "confusionMatrix": matrix,
        "metrics": {"f1": round(f1, 4), "precision": round(precision, 4), "recall": round(recall, 4)},
        "interRaterAgreement": {"kappa": round(kappa, 4), "interpretation": interpret_kappa(kappa)},
        "sampleSize": len(labelled),
        "calibrationThreshold": threshold,
        "calibrated": f1 >= threshold,
        "measuredAt": measured_at or datetime.now(UTC).isoformat(),
    }

    result = validate_assay_standard(standard)
    if not result.valid:
        raise ValueError(f"emitted AssayStandard failed self-validation: {result.errors}")
    return standard


def calibrate_from_file(path: str | Path, verifier_id: str, version: str, **kw: Any) -> dict[str, Any]:
    """Calibrate from a JSON file that is either a list of labelled items or
    {"verifierId","version","items":[...]}."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(doc, dict):
        verifier_id = doc.get("verifierId", verifier_id)
        version = doc.get("version", version)
        items = doc["items"]
    else:
        items = doc
    return calibrate(verifier_id, version, items, **kw)


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if not argv:
        print("usage: python -m prophet_mesh.assay_calibrate <labelled.json> "
              "[verifier_id] [version]", file=sys.stderr)
        return 2
    path = argv[0]
    verifier_id = argv[1] if len(argv) > 1 else "urn:srcos:verifier:unnamed"
    version = argv[2] if len(argv) > 2 else "0.1.0"
    standard = calibrate_from_file(path, verifier_id, version)
    print(json.dumps(standard, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
