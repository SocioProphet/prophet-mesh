"""Fleet rollup builder — the data behind GET /fleet/rollup.

Computes an AssayFleetSnapshot (rollup + rollout + standard summaries) by projecting
real ReasoningAssay records through project() and aggregating with build_rollup. The
ok/sad/bad distribution is therefore *computed*, not hardcoded: change the assays or
the standards and the rollup changes.

The per-node verdicts here are a seeded demo fleet (there is no live assay store yet);
swap `_demo_fleet()` for a real store to make the endpoint fully live. The standards are
the real committed calibrations (narration-fidelity, nl-lexical-baseline, deployed-nli).
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .assay import build_rollup, derived_f1, is_calibrated
from .assay_calibrate import interpret_kappa

REPO = Path(__file__).resolve().parents[2]
EXAMPLES = REPO / "examples"

NF = "urn:srcos:assay-standard:narration-fidelity:cfr-eval-001"
NL = "urn:srcos:assay-standard:nl-lexical-baseline:v1"
NLI = "urn:srcos:assay-standard:deployed-nli:0.1.0"

# Verifiers whose standard was measured from a real calibration run (vs a placeholder).
_REAL_VERIFIERS = {"urn:srcos:verifier:narration-fidelity", "urn:srcos:verifier:nl-lexical-baseline"}


def load_standards() -> dict[str, dict[str, Any]]:
    """Index every committed AssayStandard fixture by its URN."""
    standards: dict[str, dict[str, Any]] = {}
    for path in EXAMPLES.glob("*.json"):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(doc, dict) and doc.get("type") == "AssayStandard":
            standards[doc["id"]] = doc
    return standards


def _assay(method: str, binding: str, judgment: str, cal_ref: str, integrity: bool = True,
           reason: str | None = None) -> dict[str, Any]:
    a: dict[str, Any] = {
        "type": "ReasoningAssay",
        "method": method,
        "binding": binding,
        "verifier": {"judgment": judgment, "calibrationRef": cal_ref},
        "authority": {"integrityVerified": integrity},
    }
    if reason:
        a["unassayedReason"] = reason
    return a


def _demo_fleet() -> list[dict[str, Any]]:
    """One assay per node — a representative spread across the three standards."""
    return [
        # narration-fidelity (calibrated) — 5 nodes
        _assay("computed", "inline", "supported", NF),                                  # ok
        _assay("retrieved", "inline", "supported", NF),                                 # ok
        _assay("generated", "post-hoc", "supported", NF, reason="post-hoc-binding"),    # sad
        _assay("computed", "inline", "refuted", NF),                                    # bad (refuted+calibrated)
        _assay("computed", "inline", "supported", NF, integrity=False),                 # bad (authority)
        # nl-lexical-baseline (calibrated) — 4 nodes
        _assay("computed", "inline", "supported", NL),                                  # ok
        _assay("retrieved", "inline", "supported", NL),                                 # ok
        _assay("generated", "post-hoc", "supported", NL, reason="post-hoc-binding"),    # sad
        _assay("computed", "post-hoc", "supported", NL, reason="post-hoc-binding"),     # sad
        # deployed-nli (UNcalibrated) — 3 nodes, none can reach ok
        _assay("computed", "inline", "supported", NLI, reason="uncalibrated-verifier"), # sad
        _assay("retrieved", "inline", "supported", NLI, reason="uncalibrated-verifier"),# sad
        _assay("generated", "post-hoc", "supported", NLI, reason="uncalibrated-verifier"),  # sad
    ]


def _standard_summary(std: dict[str, Any]) -> dict[str, Any]:
    metrics = std.get("metrics", {})
    f1 = metrics.get("f1", round(derived_f1(std["confusionMatrix"]), 4))
    kappa = std.get("interRaterAgreement", {}).get("kappa", 0.0)
    label = std.get("interRaterAgreement", {}).get("interpretation", interpret_kappa(kappa))
    return {
        "id": std["id"],
        "verifierId": std["verifierId"].rsplit(":", 1)[-1],
        "version": std["version"],
        "f1": f1,
        "kappa": kappa,
        "kappaLabel": label,
        "calibrated": is_calibrated(std),
        "sampleSize": std["sampleSize"],
        "real": std["verifierId"] in _REAL_VERIFIERS,
    }


def build_fleet_snapshot(now: datetime | None = None) -> dict[str, Any]:
    """Assemble the AssayFleetSnapshot the dashboard consumes."""
    now = now or datetime.now(UTC)
    standards = load_standards()
    assays = _demo_fleet()

    window = {"from": (now - timedelta(hours=1)).isoformat(), "to": now.isoformat()}
    rollup = build_rollup(
        assays, standards,
        scope_mode="fleet", node_count=len(assays), window=window,
        rollup_id="urn:srcos:assay-rollup:fleet-live", captured_at=now.isoformat(),
    )
    # byMethod is not part of build_rollup's core; add the breakdown for the dashboard.
    by_method: dict[str, int] = {}
    for a in assays:
        by_method[a["method"]] = by_method.get(a["method"], 0) + 1
    rollup["byMethod"] = by_method

    rollout = {
        "id": "urn:srcos:assay-standard-rollout:narration-fidelity-next",
        "type": "AssayStandardRollout",
        "specVersion": "2.0.0",
        "standardRef": "urn:srcos:assay-standard:narration-fidelity:cfr-eval-002",
        "supersedes": NF,
        "strategy": "canary",
        "phase": "widening",
        "cohorts": [
            {"cohortId": "canary-a", "nodeCount": 2, "state": "promoted"},
            {"cohortId": "fleet-remainder", "nodeCount": 10, "state": "pending"},
        ],
        "guard": {"observedRollupRef": rollup["id"], "metric": "bad_rate_delta", "decision": "continue"},
        "rolloutPct": 16.7,
    }

    summaries = [_standard_summary(standards[ref]) for ref in (NF, NL, NLI) if ref in standards]
    return {"rollup": rollup, "rollout": rollout, "standards": summaries}
