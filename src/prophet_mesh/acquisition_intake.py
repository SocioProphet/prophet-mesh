"""Governed-acquisition intake — land acquired documents into the mesh as EVIDENCE.

The SocioProphet governed acquisition worker's HttpSink POSTs a "LandedRecord"
(provenance + body + optional enrichment) to POST /v1/acquire/ingest. Evidence is
first-class in the trust kernel (``contracts.REQUIRED_STATE_CHANNELS`` includes
``"evidence_packet"``), so an accepted record lands as an evidence packet: a
validated, content-addressed artifact keyed by ``provenance.contentHash``.

Persistence mirrors ``assay_store``: an append-only JSONL log folded on read. Where
the assay store is latest-per-node (LWW-by-nodeRef), the evidence store is
content-addressed — the same content hash is the same evidence, so re-landing is
idempotent and the fold converges on the record for each ref. The store is not a
raw drop: ``ingest_record`` validates provenance BEFORE anything is written, so the
governance contract (robots/tos posture, required provenance axes) is enforced at
the door rather than asserted after the fact.

Path from PROPHET_MESH_EVIDENCE_STORE (default <repo>/artifacts/runtime/evidence.jsonl,
which is gitignored — runtime state, not source).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
_DEFAULT_PATH = _REPO / "artifacts" / "runtime" / "evidence.jsonl"

# The provenance axes the worker always stamps and the mesh requires before a record
# can land as evidence. Absence of any of these means the record is ungoverned.
REQUIRED_PROVENANCE_FIELDS = frozenset(
    {
        "sourceId",
        "url",
        "fetchedAt",
        "httpStatus",
        "contentHash",
        "tier",
        "renderMode",
        "egress",
        "posture",
        "policy",
        "accountClass",
    }
)

TIERS = frozenset({"T0", "T1", "T2", "T3", "T4"})
RENDER_MODES = frozenset({"http", "playwright", "unblocker", "api"})
POSTURES = frozenset({"advisory", "enforced"})
ACCOUNT_CLASSES = frozenset({"sovereign", "research", "own-estate", "commercial"})
EGRESS_CLASSES = frozenset({"direct", "datacenter", "residential", "mobile"})
ROBOTS_VALUES = frozenset({"allowed", "disallowed", "unknown"})
TOS_VALUES = frozenset({"public", "restricted", "auth-gated"})
# ToS the mesh will not land: auth-gated content is behind a login the acquisition
# was not authorized to cross, so it can never be admitted as public evidence.
BLOCKED_TOS = frozenset({"auth-gated"})


@dataclass(frozen=True)
class IngestResult:
    """Validation result for a governed-acquisition LandedRecord."""

    valid: bool
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": self.errors}


def validate_landed_record(record: dict[str, Any]) -> IngestResult:
    """Validate a LandedRecord against the governed-acquisition contract.

    Checks the required provenance axes, the closed enum sets the worker stamps, and
    the policy gate (auth-gated ToS is rejected). No external JSON-schema dependency —
    the validator is the operational guardrail for the ingest endpoint, mirroring
    ``intake.validate_intake`` and ``assay.validate_reasoning_assay``.
    """
    errors: list[str] = []

    if not isinstance(record, dict):
        return IngestResult(False, ["LandedRecord must be a JSON object"])

    provenance = record.get("provenance")
    if not isinstance(provenance, dict):
        return IngestResult(False, ["LandedRecord.provenance must be an object"])

    # body is a required key (the fetched content) but may be null (e.g. a HEAD/blocked fetch).
    if "body" not in record:
        errors.append("LandedRecord.body is required (may be null)")

    missing = REQUIRED_PROVENANCE_FIELDS - set(provenance)
    if missing:
        errors.append("missing required provenance fields: " + ", ".join(sorted(missing)))

    content_hash = provenance.get("contentHash")
    if isinstance(content_hash, str) and content_hash and not content_hash.startswith("sha256:"):
        errors.append("provenance.contentHash must be a 'sha256:<hex>' digest")
    elif "contentHash" in provenance and not isinstance(content_hash, str):
        errors.append("provenance.contentHash must be a string")

    if not isinstance(provenance.get("httpStatus", 0), int) or isinstance(
        provenance.get("httpStatus"), bool
    ):
        errors.append("provenance.httpStatus must be an integer")

    if "tier" in provenance and provenance["tier"] not in TIERS:
        errors.append("provenance.tier must be one of " + ", ".join(sorted(TIERS)))
    if "renderMode" in provenance and provenance["renderMode"] not in RENDER_MODES:
        errors.append("provenance.renderMode must be one of " + ", ".join(sorted(RENDER_MODES)))
    if "posture" in provenance and provenance["posture"] not in POSTURES:
        errors.append("provenance.posture must be one of " + ", ".join(sorted(POSTURES)))
    if "accountClass" in provenance and provenance["accountClass"] not in ACCOUNT_CLASSES:
        errors.append(
            "provenance.accountClass must be one of " + ", ".join(sorted(ACCOUNT_CLASSES))
        )

    egress = provenance.get("egress")
    if "egress" in provenance:
        if not isinstance(egress, dict):
            errors.append("provenance.egress must be an object")
        elif egress.get("class") not in EGRESS_CLASSES:
            errors.append("provenance.egress.class must be one of " + ", ".join(sorted(EGRESS_CLASSES)))

    policy = provenance.get("policy")
    if "policy" in provenance:
        if not isinstance(policy, dict):
            errors.append("provenance.policy must be an object")
        else:
            tos = policy.get("tos")
            if tos is not None and tos not in TOS_VALUES:
                errors.append("provenance.policy.tos must be one of " + ", ".join(sorted(TOS_VALUES)))
            elif tos in BLOCKED_TOS:
                errors.append(
                    f"provenance.policy.tos={tos!r} is not admissible as public evidence"
                )
            robots = policy.get("robots")
            if robots is not None and robots not in ROBOTS_VALUES:
                errors.append(
                    "provenance.policy.robots must be one of " + ", ".join(sorted(ROBOTS_VALUES))
                )

    return IngestResult(not errors, errors)


class EvidenceStore:
    """Append-only JSONL log of landed evidence packets, content-addressed by contentHash.

    Content addressing means the same bytes carry the same ref, so the fold-on-read
    converges to one record per ref (re-landing is idempotent), matching the
    append-only, converge-on-read discipline of ``assay_store``/``pkg_ops``.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def record(self, evidence_ref: str, landed_record: dict[str, Any]) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "evidenceRef": evidence_ref,
            "landedAt": datetime.now(UTC).isoformat(),
            "record": landed_record,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
        return entry

    def _entries(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        out: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def current(self) -> dict[str, dict[str, Any]]:
        """Current landed record per evidenceRef — last append wins (append order == file order)."""
        latest: dict[str, dict[str, Any]] = {}
        for entry in self._entries():
            latest[entry["evidenceRef"]] = entry["record"]
        return latest

    def get(self, evidence_ref: str) -> dict[str, Any] | None:
        return self.current().get(evidence_ref)

    def has(self, evidence_ref: str) -> bool:
        return evidence_ref in self.current()

    def count(self) -> int:
        return len(self.current())


def default_evidence_store() -> EvidenceStore:
    return EvidenceStore(os.environ.get("PROPHET_MESH_EVIDENCE_STORE", str(_DEFAULT_PATH)))


def ingest_record(record: dict[str, Any], store: EvidenceStore | None = None) -> dict[str, Any]:
    """Validate a LandedRecord and land it as an evidence packet (the POST /v1/acquire/ingest path).

    Validates provenance FIRST; on failure raises ``ValueError`` (joined errors) so the
    endpoint can map it to HTTP 400 — nothing ungoverned is ever written. On success the
    record is persisted content-addressed by ``provenance.contentHash`` and an acceptance
    receipt is returned carrying the ``evidenceRef`` a caller uses to retrieve it.
    """
    result = validate_landed_record(record)
    if not result.valid:
        raise ValueError("; ".join(result.errors))
    store = store or default_evidence_store()
    provenance = record["provenance"]
    evidence_ref = provenance["contentHash"]
    store.record(evidence_ref, record)
    return {
        "accepted": True,
        "evidenceRef": evidence_ref,
        "sourceId": provenance["sourceId"],
        "url": provenance["url"],
    }
