"""The Assay — epistemic verdicts as the prophet-mesh verdict substrate.

Conforms by shape to sourceos-spec v2 ``ReasoningAssay`` / ``AssayStandard`` /
``AssayRollup`` (no import — hand-authored dicts + validators, the house pattern
of ``evaluation.py``). A verdict on a claim is a tuple of orthogonal axes; the
ok/sad/bad readout is a *projection* of that tuple, never a stored scalar.

Two deployment modes, split on the existing ``locus`` axis (see ``pkg_gate``):

  * SINGLE-USER LOCAL — ``local`` / ``trusted_private``. Verdicts stay on device.
    The fleet rollup is not built here: ``build_rollup`` refuses cohort/fleet
    scope in local mode, so "no fleet dashboards for a single user" is a
    structural property, not a permission toggle.
  * CLOUD MESH — ``attested_fog`` / ``burst_cloud``. ``AssayStandard`` becomes the
    resolver ``pkg_gate.gate()`` consults: a gated-locus op is admitted to the
    canonical view only if its attestation resolves to an assay that projects ``ok``.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Mirror pkg_gate's split so the two agree by construction.
LOCAL_LOCI = ("local", "trusted_private")
FLEET_LOCI = ("attested_fog", "burst_cloud")

DEFAULT_CALIBRATION_THRESHOLD = 0.6
METRIC_TOLERANCE = 0.02

ATTESTABLE_METHODS = ("computed", "retrieved")


def deployment_mode(locus: str) -> str:
    """'local' for on-device self-trusting loci, 'fleet' for gated cloud loci."""
    if locus in LOCAL_LOCI:
        return "local"
    if locus in FLEET_LOCI:
        return "fleet"
    raise ValueError(f"unknown locus {locus!r}")


# --------------------------------------------------------------------------- #
# projection — the ok/sad/bad readout, recomputed from the axes
# --------------------------------------------------------------------------- #

def derived_f1(matrix: dict[str, int]) -> float:
    """F1 from raw confusion-matrix counts — the matrix is authoritative."""
    tp, fp, fn = matrix["truePositive"], matrix["falsePositive"], matrix["falseNegative"]
    denom = 2 * tp + fp + fn
    return (2 * tp / denom) if denom else 0.0


def is_calibrated(standard: dict[str, Any] | None) -> bool:
    """A verifier cannot declare itself trustworthy: calibration is derived from
    the confusion matrix against the standard's threshold, not read off a flag."""
    if not standard:
        return False
    threshold = standard.get("calibrationThreshold", DEFAULT_CALIBRATION_THRESHOLD)
    return derived_f1(standard["confusionMatrix"]) >= threshold


def project(assay: dict[str, Any], standards: dict[str, dict[str, Any]]) -> str:
    """Recompute ok/sad/bad from the stored axes.

    bad  — authority broken, OR refuted by a *calibrated* verifier.
    ok   — supported + inline + attestable method + calibrated verifier.
    sad  — everything else (unresolved but not decisively refuted).
    """
    if assay.get("authority", {}).get("integrityVerified") is False:
        return "bad"

    verifier = assay["verifier"]
    calibrated = is_calibrated(standards.get(verifier["calibrationRef"]))
    judgment = verifier["judgment"]

    if judgment == "refuted":
        return "bad" if calibrated else "sad"

    inline = assay["binding"] == "inline"
    attestable = assay["method"] in ATTESTABLE_METHODS
    if judgment == "supported" and inline and attestable and calibrated:
        return "ok"
    return "sad"


# --------------------------------------------------------------------------- #
# validators — house style: (valid, errors)
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class AssayValidationResult:
    valid: bool
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": self.errors}


def _req(container: dict, key: str, path: str, errors: list[str]) -> None:
    if key not in container:
        errors.append(f"{path}.{key} is required")


def validate_assay_standard(data: dict[str, Any]) -> AssayValidationResult:
    errors: list[str] = []
    for key in ("id", "type", "verifierId", "version", "confusionMatrix", "sampleSize"):
        _req(data, key, "AssayStandard", errors)
    matrix = data.get("confusionMatrix")
    if isinstance(matrix, dict) and {"truePositive", "falsePositive", "trueNegative", "falseNegative"} <= set(matrix):
        f1 = derived_f1(matrix)
        metrics = data.get("metrics", {})
        if "f1" in metrics and abs(metrics["f1"] - f1) > METRIC_TOLERANCE:
            errors.append(f"metrics.f1={metrics['f1']} contradicts confusionMatrix ({f1:.3f})")
        if "calibrated" in data:
            threshold = data.get("calibrationThreshold", DEFAULT_CALIBRATION_THRESHOLD)
            expected = f1 >= threshold
            if data["calibrated"] != expected:
                errors.append(
                    f"calibrated={data['calibrated']} but derivedF1={f1:.3f} vs "
                    f"threshold={threshold} implies {expected} — trust is measured, not asserted"
                )
    else:
        errors.append("AssayStandard.confusionMatrix must carry all four counts")
    return AssayValidationResult(not errors, errors)


def validate_reasoning_assay(data: dict[str, Any]) -> AssayValidationResult:
    errors: list[str] = []
    for key in ("id", "type", "runRef", "method", "binding", "verifier"):
        _req(data, key, "ReasoningAssay", errors)
    if data.get("method") not in ("computed", "retrieved", "generated"):
        errors.append("method must be computed, retrieved, or generated")
    if data.get("binding") not in ("inline", "post-hoc"):
        errors.append("binding must be inline or post-hoc")
    verifier = data.get("verifier", {})
    if isinstance(verifier, dict):
        _req(verifier, "calibrationRef", "verifier", errors)
        if verifier.get("judgment") not in ("supported", "refuted", "abstained"):
            errors.append("verifier.judgment must be supported, refuted, or abstained")
    else:
        errors.append("verifier must be an object")
    agreement = data.get("agreement")
    if isinstance(agreement, dict):
        arms, votes = agreement.get("arms"), agreement.get("effectiveVotes")
        if arms is not None and votes is not None and votes > arms:
            errors.append(f"agreement.effectiveVotes={votes} exceeds arms={arms}")
    return AssayValidationResult(not errors, errors)


def validate_assay_rollup(data: dict[str, Any]) -> AssayValidationResult:
    errors: list[str] = []
    for key in ("id", "type", "scope", "totalAssays", "distribution"):
        _req(data, key, "AssayRollup", errors)
    dist = data.get("distribution", {})
    if isinstance(dist, dict) and {"ok", "sad", "bad"} <= set(dist):
        if dist["ok"] + dist["sad"] + dist["bad"] != data.get("totalAssays"):
            errors.append("distribution counts must sum to totalAssays")
        reasons = data.get("unassayedReasons")
        if reasons and sum(reasons.values()) > dist["sad"]:
            errors.append("unassayedReasons sum exceeds distribution.sad")
    else:
        errors.append("distribution must carry ok/sad/bad")
    adoption = data.get("standardAdoption")
    scope = data.get("scope", {})
    if adoption:
        if sum(a["nodeCount"] for a in adoption) != scope.get("nodeCount"):
            errors.append("standardAdoption node counts must match scope.nodeCount")
        expected_drift = len({a["calibrationRef"] for a in adoption}) > 1 or any(
            not a["calibrated"] for a in adoption
        )
        if "driftDetected" in data and data["driftDetected"] != expected_drift:
            errors.append(f"driftDetected disagrees with adoption table (implies {expected_drift})")
    return AssayValidationResult(not errors, errors)


# --------------------------------------------------------------------------- #
# gate integration — AssayStandard-backed admission for cloud loci
# --------------------------------------------------------------------------- #

# A pkg_gate.Resolver: attestationRef -> is it a passing correctness receipt?
Resolver = Callable[[str], bool]


def assay_resolver(
    assays_by_ref: dict[str, dict[str, Any]],
    standards: dict[str, dict[str, Any]],
) -> Resolver:
    """Build the resolver ``pkg_gate.gate()`` consults for gated (cloud) loci.

    An op's ``attestationRef`` names a ReasoningAssay; the op is admitted to the
    canonical view only if that assay projects ``ok`` — i.e. an inline-bound,
    attestable claim judged 'supported' by a *calibrated* verifier. Fail-closed:
    an unknown ref, or any verdict short of ``ok``, is not admitted.
    """
    def resolve(ref: str) -> bool:
        assay = assays_by_ref.get(ref)
        return assay is not None and project(assay, standards) == "ok"

    return resolve


# --------------------------------------------------------------------------- #
# fleet rollup — cloud-mesh only; structurally absent in local mode
# --------------------------------------------------------------------------- #

class LocalModeError(RuntimeError):
    """Raised when fleet-tier aggregation is attempted on a single-user local deployment."""


def build_rollup(
    assays: list[dict[str, Any]],
    standards: dict[str, dict[str, Any]],
    *,
    scope_mode: str,
    node_count: int,
    window: dict[str, str],
    rollup_id: str,
    captured_at: str,
) -> dict[str, Any]:
    """Aggregate node verdicts into an AssayRollup.

    ``scope_mode`` 'node' is the on-device self-view (allowed anywhere). 'cohort'
    and 'fleet' are the cloud-mesh tier and are refused here for a single node —
    the fleet aggregation path simply does not exist on-device.
    """
    if scope_mode not in ("node", "cohort", "fleet"):
        raise ValueError(f"unknown scope_mode {scope_mode!r}")
    if scope_mode in ("cohort", "fleet") and node_count < 2:
        raise LocalModeError(
            "cohort/fleet rollups require a multi-node deployment; a single-user "
            "local node has no fleet to roll up"
        )

    dist = {"ok": 0, "sad": 0, "bad": 0}
    reasons: dict[str, int] = {}
    adoption: dict[str, dict[str, Any]] = {}
    for a in assays:
        state = project(a, standards)
        dist[state] += 1
        if state == "sad" and a.get("unassayedReason"):
            reasons[a["unassayedReason"]] = reasons.get(a["unassayedReason"], 0) + 1
        ref = a["verifier"]["calibrationRef"]
        entry = adoption.setdefault(
            ref, {"calibrationRef": ref, "nodeCount": 0, "calibrated": is_calibrated(standards.get(ref))}
        )
        entry["nodeCount"] += 1

    rollup: dict[str, Any] = {
        "id": rollup_id,
        "type": "AssayRollup",
        "specVersion": "2.0.0",
        "scope": {"mode": scope_mode, "nodeCount": node_count},
        "window": window,
        "totalAssays": len(assays),
        "distribution": dist,
        "capturedAt": captured_at,
    }
    if reasons:
        rollup["unassayedReasons"] = reasons
    if scope_mode in ("cohort", "fleet"):
        adoption_list = list(adoption.values())
        rollup["standardAdoption"] = adoption_list
        rollup["driftDetected"] = len(adoption_list) > 1 or any(
            not e["calibrated"] for e in adoption_list
        )
    return rollup


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)
