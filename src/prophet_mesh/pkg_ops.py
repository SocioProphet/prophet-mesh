"""CRDT Slice 1 — op-emitter over the Personal Knowledge Graph.

Dual-writes every PKG mutation as a sourceos-spec v2 ``EventEnvelope`` op onto an
append-only, hash-linked log (the Figure-18 "railroad track"). This is Slice 1 of
the CRDT-over-evidence-fabric design: **emit only, no merge yet**. It gives us:

  * an EventEnvelope-conformant op for every add_node / add_edge,
  * a content-hash DAG (parents chain) so history is verifiable, and
  * a deterministic ``fold`` that rebuilds graph state from the log alone
    (the round-trip proof that the log is sufficient — the substrate Slice 3
    merge will union).

Causal + trust metadata rides in the open ``payload`` (EventEnvelope keeps
``additionalProperties: false`` at the top level, so we add nothing there).
The merge gate that consumes ``crdt.locus`` / ``crdt.attestationRef`` is Slice 4;
here we only record them.

Conforms to: EventEnvelope.json, and reuses the SyncCycleReceipt.locus vocabulary.
Accretive: does not modify pkg.py.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from .pkg import PKG, Node, Edge, Provenance

SPEC_VERSION = "2.0.0"

# SyncCycleReceipt.locus vocabulary — the "distance-to-execution" axis.
LOCI = ("local", "trusted_private", "attested_fog", "burst_cloud")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(obj: Any) -> str:
    """Stable JSON for content hashing (sorted keys, no whitespace drift)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _content_hash(event_type: str, object_id: str, payload: dict) -> str:
    """Merkle-DAG node hash. Covers semantics + causal parents, NOT wall-clock
    (occurredAt is display-only and never trusted for ordering)."""
    material = _canonical({"eventType": event_type, "objectId": object_id, "payload": payload})
    return "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


class OpLog:
    """Append-only EventEnvelope log with a single-replica hash chain.

    Slice 1 is single-replica, so ``parents`` is the linear chain head. Slice 3
    generalises ``parents`` to the concurrent (multi-head) case for OR-Set merge.
    """

    def __init__(self, replica_id: str, subject_id: str, locus: str = "local") -> None:
        if locus not in LOCI:
            raise ValueError(f"locus must be one of {LOCI}, got {locus!r}")
        self.replica_id = replica_id
        self.subject_id = subject_id
        self.locus = locus
        self.ops: list[dict] = []
        self._head: str | None = None
        self._lamport = 0

    def append(
        self,
        event_type: str,
        object_id: str,
        core: dict,
        *,
        attestation_ref: str | None = None,
        trust_level: str = "trusted-workspace-source",
    ) -> dict:
        self._lamport += 1
        event_id = f"urn:srcos:event:{uuid.uuid4()}"
        crdt = {
            "replicaId": self.replica_id,
            "lamport": self._lamport,
            "parents": [self._head] if self._head else [],
            "locus": self.locus,
            "attestationRef": attestation_ref,   # resolved by the Slice-4 merge gate
            "trustLevel": trust_level,
            "tag": event_id,                      # OR-Set unique add-tag
        }
        payload = {"op": event_type, **core, "crdt": crdt}
        event_hash = _content_hash(event_type, object_id, payload)
        envelope = {
            "eventId": event_id,
            "eventType": event_type,
            "specVersion": SPEC_VERSION,
            "occurredAt": _now(),
            "actor": {"subjectId": self.subject_id},
            "objectId": object_id,
            "payload": payload,
            "integrity": {"eventHash": event_hash, "signature": None},
        }
        self._head = event_hash
        self.ops.append(envelope)
        return envelope


def _node_urn(node_id: str) -> str:
    return f"urn:srcos:pkg-node:{node_id}"


def _edge_urn(e: Edge) -> str:
    return f"urn:srcos:pkg-edge:{e.src}|{e.rel}|{e.dst}"


class EmittingPKG:
    """Composes a PKG with an OpLog: every mutation is applied AND emitted.

    Non-invasive wrapper — the underlying PKG is untouched, so all existing
    ingestion (ingest_contact, workspace adapters, hellgraph writer) can be
    driven through this to start producing ops with zero changes to pkg.py.
    """

    def __init__(self, graph: PKG, *, replica_id: str, locus: str = "local") -> None:
        self.g = graph
        self.log = OpLog(replica_id=replica_id, subject_id=f"urn:srcos:replica:{replica_id}", locus=locus)

    @classmethod
    def seeded(cls, self_id: str = "self", *, replica_id: str, locus: str = "local") -> "EmittingPKG":
        """Fresh graph whose Self anchor is emitted as the genesis op, so the
        op-log is a *complete* source of truth (a fresh replica can fold it and
        recover the anchor). external_kgs registration as an op is a later slice.
        """
        epkg = cls(PKG(self_id=self_id), replica_id=replica_id, locus=locus)
        epkg.add_node(Node(
            id=self_id, type="Self", label="Self",
            provenance=Provenance(source="onboarding", method="declared"),
            assertion_class="Structural",
        ))
        return epkg

    def add_node(self, n: Node, *, attestation_ref: str | None = None) -> dict:
        self.g.add_node(n)
        return self.log.append(
            "GraphNodeAsserted", _node_urn(n.id), {"node": asdict(n)},
            attestation_ref=attestation_ref,
        )

    def add_edge(self, e: Edge, *, attestation_ref: str | None = None) -> dict:
        self.g.add_edge(e)
        return self.log.append(
            "GraphEdgeAsserted", _edge_urn(e), {"edge": asdict(e)},
            attestation_ref=attestation_ref,
        )


def fold(ops: list[dict], self_id: str = "self") -> PKG:
    """Deterministically rebuild graph state from the op-log alone.

    Slice-1 semantics: asserts only (add-wins, no retracts yet). Proves the log
    is a sufficient source of truth — the property Slice 3's merge relies on.
    """
    g = PKG(self_id=self_id)
    for env in ops:
        p = env["payload"]
        op = p["op"]
        if op == "GraphNodeAsserted":
            nd = dict(p["node"])
            nd["provenance"] = _Prov(**nd["provenance"])
            nd["external"] = tuple(_Ext(**x) for x in nd.get("external", ()))
            g.add_node(Node(**nd))
        elif op == "GraphEdgeAsserted":
            ed = dict(p["edge"])
            ed["provenance"] = _Prov(**ed["provenance"])
            g.add_edge(Edge(**ed))
    return g


# local re-imports kept at bottom to avoid confusing the module header
from .pkg import Provenance as _Prov, ExternalLink as _Ext  # noqa: E402


def verify_chain(ops: list[dict]) -> bool:
    """Every op's recorded eventHash matches its recomputed content hash, and
    parents point at the immediately preceding head (single-replica chain)."""
    prev: str | None = None
    for env in ops:
        p = env["payload"]
        recomputed = _content_hash(env["eventType"], env["objectId"], p)
        if recomputed != env["integrity"]["eventHash"]:
            return False
        if p["crdt"]["parents"] != ([prev] if prev else []):
            return False
        prev = env["integrity"]["eventHash"]
    return True
