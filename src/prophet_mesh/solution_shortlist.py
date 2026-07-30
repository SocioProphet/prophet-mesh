"""SolutionShortlist validation for Prophet Mesh.

The response envelope Michael Agent returns when routing an intent to solutions. Rather than
silently auto-selecting the top-1 (the shape Zurich's Damian falls back to), Michael returns
a ranked shortlist with matchReason, counterTestStatus, and accessDecision per candidate.
Auto-route only fires when the top-2 score gap exceeds threshold AND top counterTestStatus
== 'confirmed' AND top accessDecision == 'granted'; otherwise the user picks.

Empties are signal: `shortlist: []` with an `emptyReason` is a valid response, not a bug.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "specs" / "solution-shortlist.schema.json"
AUTO_ROUTE_GAP_THRESHOLD = 0.15

_ABB_PATTERN = re.compile(r"^ABB\.[0-9]{2}$")
_SHA_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_REPO_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$")
_SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
_ISO8601_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$")


@dataclass
class ValidationResult:
    """Outcome of validating a candidate SolutionShortlist against the schema and invariants.

    `errors` is the list of specific findings — never `["invalid"]`. A validator that says
    only "invalid" has told the caller nothing. Empty list ⇒ valid; non-empty ⇒ each item is
    an actionable pointer to what to fix.
    """

    valid: bool
    errors: list[str]


def validate(instance: Any) -> ValidationResult:
    """Validate a SolutionShortlist instance.

    Uses jsonschema when available for the shape checks; when unavailable, runs a manual
    subset covering the properties that carry governance meaning (score bounds,
    counterTestStatus enum, accessDecision.grade enum, empty-shortlist requires
    emptyReason). Missing the optional dependency does not mean skipping the check — it
    means checking less, and saying so.

    Invariants enforced beyond the raw schema:
      - `shortlist == []` REQUIRES `emptyReason` (schema allows it; this makes it explicit)
      - `autoRouteVerdict.decision == 'auto-route'` REQUIRES the top-2 score gap to exceed
        AUTO_ROUTE_GAP_THRESHOLD, top `counterTestStatus == 'confirmed'`, and top
        `accessDecision.grade == 'granted'`. A verdict that claims 'auto-route' without
        satisfying these is invalid — the discipline sourceos-spec LawfulDispatchReceipt
        applies to verdicts, applied here to routing decisions.
    """

    errors: list[str] = []

    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        errors.extend(_manual_shape(instance))
    else:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        for err in sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda e: list(e.path)):
            path = ".".join(str(p) for p in err.path) or "<root>"
            errors.append(f"schema: {path}: {err.message[:200]}")

    # ── governance invariants beyond the schema ────────────────────────────────
    shortlist = instance.get("shortlist", []) if isinstance(instance, dict) else []
    if isinstance(shortlist, list) and len(shortlist) == 0:
        if not instance.get("emptyReason"):
            errors.append("empty shortlist requires emptyReason (a specific reason, not a generic one)")
        elif len(instance.get("emptyReason", "")) < 10:
            errors.append("emptyReason must be a substantive explanation (>= 10 chars)")

    verdict = instance.get("autoRouteVerdict") if isinstance(instance, dict) else None
    if isinstance(verdict, dict) and verdict.get("decision") == "auto-route":
        errors.extend(_check_auto_route_lawfulness(shortlist, verdict))

    return ValidationResult(valid=not errors, errors=errors)


def _manual_shape(instance: Any) -> list[str]:
    """Shape check without jsonschema. Covers the fields with governance meaning."""
    errors: list[str] = []
    if not isinstance(instance, dict):
        return ["instance is not an object"]
    for k in ("schemaVersion", "kind", "shortlist", "derivedAt", "derivedFrom"):
        if k not in instance:
            errors.append(f"missing required field: {k}")
    if instance.get("kind") != "SolutionShortlist":
        errors.append(f"kind must be 'SolutionShortlist', got {instance.get('kind')!r}")
    if not _SEMVER_PATTERN.match(str(instance.get("schemaVersion", ""))):
        errors.append("schemaVersion must be semver")
    if "abbRequirement" in instance and not _ABB_PATTERN.match(instance["abbRequirement"]):
        errors.append(f"abbRequirement must match ABB.NN, got {instance['abbRequirement']!r}")
    derived = instance.get("derivedFrom", {})
    if isinstance(derived, dict):
        for k in ("marDigest", "abbCatalogDigest"):
            if not _SHA_PATTERN.match(str(derived.get(k, ""))):
                errors.append(f"derivedFrom.{k} must be sha256:<64 hex>")
    if not _ISO8601_PATTERN.match(str(instance.get("derivedAt", ""))):
        errors.append("derivedAt must be RFC-3339 with Z or offset")
    for i, c in enumerate(instance.get("shortlist", []) or []):
        if not isinstance(c, dict):
            errors.append(f"shortlist[{i}]: not an object")
            continue
        for k in ("participantRef", "score", "matchReason", "counterTestStatus", "accessDecision"):
            if k not in c:
                errors.append(f"shortlist[{i}]: missing required field: {k}")
        if "participantRef" in c and not _REPO_PATTERN.match(c["participantRef"]):
            errors.append(f"shortlist[{i}].participantRef must be owner/repo, got {c['participantRef']!r}")
        if "score" in c and not (isinstance(c["score"], (int, float)) and 0 <= c["score"] <= 1):
            errors.append(f"shortlist[{i}].score must be a number in [0,1]")
        if c.get("counterTestStatus") not in {"confirmed", "available", "unavailable"}:
            errors.append(f"shortlist[{i}].counterTestStatus invalid: {c.get('counterTestStatus')!r}")
        access = c.get("accessDecision", {})
        if not isinstance(access, dict) or access.get("grade") not in {"granted", "requires-consent", "denied"}:
            errors.append(f"shortlist[{i}].accessDecision.grade invalid")
        reason = c.get("matchReason", [])
        if not isinstance(reason, list) or len(reason) == 0:
            errors.append(f"shortlist[{i}].matchReason must be non-empty (a candidate without a reason is a candidate nobody should route to)")
    return errors


def _check_auto_route_lawfulness(shortlist: list[dict], verdict: dict) -> list[str]:
    """A verdict of 'auto-route' must be lawful — the same discipline as verdict = law × evidence.

    An auto-route claim is a Michael-side assertion; making it valid only when the objective
    preconditions hold prevents the shape-only failure mode where a caller reads
    ``autoRouteVerdict.decision`` and trusts it without inspecting whether it's justified.
    """
    errors: list[str] = []
    idx = verdict.get("chosenIndex")
    if idx is None or not isinstance(idx, int) or idx < 0 or idx >= len(shortlist):
        errors.append("auto-route verdict must reference a valid chosenIndex within the shortlist")
        return errors
    if len(shortlist) < 2:
        errors.append("auto-route requires at least 2 candidates so the top-2 gap can be measured")
        return errors
    scores = sorted((c.get("score", 0) for c in shortlist), reverse=True)
    gap = scores[0] - scores[1]
    if gap < AUTO_ROUTE_GAP_THRESHOLD:
        errors.append(
            f"auto-route requires top-2 score gap >= {AUTO_ROUTE_GAP_THRESHOLD}, got {gap:.3f}. "
            "Below threshold the shortlist must be presented for user pick."
        )
    top = shortlist[idx]
    if top.get("counterTestStatus") != "confirmed":
        errors.append(
            f"auto-route requires top counterTestStatus == 'confirmed', "
            f"got {top.get('counterTestStatus')!r}. Per Noetica#570's counter-test gate."
        )
    access_grade = top.get("accessDecision", {}).get("grade")
    if access_grade != "granted":
        errors.append(
            f"auto-route requires top accessDecision.grade == 'granted', got {access_grade!r}. "
            "Requires-consent or denied candidates appear in the shortlist but do not auto-route."
        )
    return errors
