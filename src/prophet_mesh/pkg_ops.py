"""CRDT over the Personal Knowledge Graph — Slices 1–3.

Dual-writes every PKG mutation as a sourceos-spec v2 ``EventEnvelope`` op onto an
append-only, hash-linked log (the Figure-18 "railroad track"), then **reconstructs
and converges** graph state from those logs across replicas.

  * Slice 1 — emit: an EventEnvelope-conformant op per add/retract, content-hash DAG.
  * Slice 2 — reconstruct: deterministic ``materialize`` folds a log back to a PKG,
    with add-wins OR-Set semantics + observed-remove retracts.
  * Slice 3 — converge: ``merge`` unions two replicas' logs; ``materialize`` over the
    union is commutative / associative / idempotent → strong eventual consistency
    with zero coordination. This is what closes local-first ideals 2 (multi-device)
    and 4 (collaboration) without touching 5/6/7.

Causal + trust metadata (parents, lamport, locus, attestationRef, OR-Set tags/removes)
rides in the open ``payload`` — EventEnvelope keeps ``additionalProperties: false`` at
the top level, so no schema change. The locus/attestation *merge gate* (which converged
sub-graph is authoritative) is Slice 4; here every op still converges.

Conforms to: EventEnvelope.json; reuses the SyncCycleReceipt.locus vocabulary.
Accretive: does not modify pkg.py.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Iterable

from .pkg import PKG, Node, Edge, Provenance, ExternalLink

SPEC_VERSION = "2.0.0"

# SyncCycleReceipt.locus vocabulary — the "distance-to-execution" axis.
LOCI = ("local", "trusted_private", "attested_fog", "burst_cloud")

EdgeKey = tuple[str, str, str]  # (src, rel, dst)


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

    Single-replica ``parents`` is the linear chain head; after a ``merge`` the DAG
    is multi-head (``verify_chain`` is therefore a per-replica, pre-merge check)."""

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
        removes: Iterable[str] | None = None,
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
        if removes is not None:
            crdt["removes"] = list(removes)       # OR-Set observed-remove tags
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


def _node_from(nd: dict) -> Node:
    nd = dict(nd)
    nd["provenance"] = Provenance(**nd["provenance"])
    nd["external"] = tuple(ExternalLink(**x) for x in nd.get("external", ()))
    return Node(**nd)


def _edge_from(ed: dict) -> Edge:
    ed = dict(ed)
    ed["provenance"] = Provenance(**ed["provenance"])
    return Edge(**ed)


class EmittingPKG:
    """Composes a PKG with an OpLog: every mutation is applied AND emitted.

    Non-invasive wrapper — the underlying PKG is untouched, so all existing
    ingestion (ingest_contact, workspace adapters, hellgraph writer) can be driven
    through this to start producing ops with zero changes to pkg.py. Tracks the
    live add-tags per element so retracts are *observed-removes* (add-wins)."""

    def __init__(self, graph: PKG, *, replica_id: str, locus: str = "local") -> None:
        self.g = graph
        self.log = OpLog(replica_id=replica_id, subject_id=f"urn:srcos:replica:{replica_id}", locus=locus)
        self._node_tags: dict[str, set[str]] = {}
        self._edge_tags: dict[EdgeKey, set[str]] = {}

    @classmethod
    def seeded(cls, self_id: str = "self", *, replica_id: str, locus: str = "local") -> "EmittingPKG":
        """Fresh graph whose Self anchor is emitted as the genesis op, so the op-log
        is a *complete* source of truth (a fresh replica can materialize it and
        recover the anchor). external_kgs registration as an op is a later slice."""
        epkg = cls(PKG(self_id=self_id), replica_id=replica_id, locus=locus)
        epkg.add_node(Node(
            id=self_id, type="Self", label="Self",
            provenance=Provenance(source="onboarding", method="declared"),
            assertion_class="Structural",
        ))
        return epkg

    # ── local mutations (apply + emit) ──────────────────────────────────────
    def add_node(self, n: Node, *, attestation_ref: str | None = None) -> dict:
        self.g.add_node(n)
        env = self.log.append("GraphNodeAsserted", _node_urn(n.id), {"node": asdict(n)}, attestation_ref=attestation_ref)
        self._node_tags.setdefault(n.id, set()).add(env["payload"]["crdt"]["tag"])
        return env

    def add_edge(self, e: Edge, *, attestation_ref: str | None = None) -> dict:
        self.g.add_edge(e)
        env = self.log.append("GraphEdgeAsserted", _edge_urn(e), {"edge": asdict(e)}, attestation_ref=attestation_ref)
        self._edge_tags.setdefault((e.src, e.rel, e.dst), set()).add(env["payload"]["crdt"]["tag"])
        return env

    def retract_node(self, node_id: str, *, attestation_ref: str | None = None) -> dict:
        """Observed-remove: retract exactly the add-tags this replica has seen, so a
        concurrent re-add elsewhere (a tag we didn't observe) survives — add-wins."""
        observed = sorted(self._node_tags.get(node_id, set()))
        env = self.log.append("GraphNodeRetracted", _node_urn(node_id), {"nodeId": node_id},
                              attestation_ref=attestation_ref, removes=observed)
        self.g.nodes.pop(node_id, None)
        self._node_tags.pop(node_id, None)
        return env

    def retract_edge(self, key: EdgeKey, *, attestation_ref: str | None = None) -> dict:
        observed = sorted(self._edge_tags.get(key, set()))
        env = self.log.append("GraphEdgeRetracted", f"urn:srcos:pkg-edge:{key[0]}|{key[1]}|{key[2]}",
                              {"edgeKey": list(key)}, attestation_ref=attestation_ref, removes=observed)
        self.g.edges = [e for e in self.g.edges if (e.src, e.rel, e.dst) != key]
        self._edge_tags.pop(key, None)
        return env

    # ── remote op ingestion (apply without re-emitting) ─────────────────────
    def apply_remote(self, env: dict) -> None:
        """Ingest another replica's op into local view + tag trackers, WITHOUT
        appending it to our own log. Lets this replica observe a remote add so a
        later local retract removes the right tag."""
        p, crdt = env["payload"], env["payload"]["crdt"]
        op = p["op"]
        if op == "GraphNodeAsserted":
            self.g.add_node(_node_from(p["node"]))
            self._node_tags.setdefault(p["node"]["id"], set()).add(crdt["tag"])
        elif op == "GraphEdgeAsserted":
            ed = p["edge"]
            key = (ed["src"], ed["rel"], ed["dst"])
            self.g.add_edge(_edge_from(ed))
            self._edge_tags.setdefault(key, set()).add(crdt["tag"])
        elif op == "GraphNodeRetracted":
            nid, rem = p["nodeId"], set(crdt.get("removes", []))
            self._node_tags[nid] = self._node_tags.get(nid, set()) - rem
            if not self._node_tags.get(nid):
                self.g.nodes.pop(nid, None)
                self._node_tags.pop(nid, None)
        elif op == "GraphEdgeRetracted":
            key = tuple(p["edgeKey"])
            rem = set(crdt.get("removes", []))
            self._edge_tags[key] = self._edge_tags.get(key, set()) - rem
            if not self._edge_tags.get(key):
                self.g.edges = [e for e in self.g.edges if (e.src, e.rel, e.dst) != key]
                self._edge_tags.pop(key, None)


# ── Slice 2/3: reconstruct + converge ──────────────────────────────────────
def _dedupe(ops: Iterable[dict]) -> list[dict]:
    """Idempotent op-set keyed by eventId (re-applying the same op is a no-op)."""
    seen: dict[str, dict] = {}
    for env in ops:
        seen[env["eventId"]] = env
    return list(seen.values())


def materialize(ops: Iterable[dict], self_id: str = "self") -> PKG:
    """Deterministically reconstruct graph state from an op-log (Slice 2).

    Add-wins OR-Set: an element is present iff it has ≥1 add-tag not covered by an
    observed-remove. Among surviving adds, value is last-writer-wins by
    (lamport, eventId) — a total, replica-independent tiebreak. Pure fold over the
    op *set*, so it is order-independent → the property Slice-3 merge relies on."""
    events = _dedupe(ops)
    node_adds: dict[str, list[tuple[int, str, dict, str]]] = {}
    edge_adds: dict[EdgeKey, list[tuple[int, str, dict, str]]] = {}
    removed: set[str] = set()

    for env in events:
        p, crdt = env["payload"], env["payload"]["crdt"]
        op = p["op"]
        if op == "GraphNodeAsserted":
            node_adds.setdefault(p["node"]["id"], []).append(
                (crdt["lamport"], env["eventId"], p["node"], crdt["tag"]))
        elif op == "GraphEdgeAsserted":
            e = p["edge"]
            key = (e["src"], e["rel"], e["dst"])
            edge_adds.setdefault(key, []).append(
                (crdt["lamport"], env["eventId"], e, crdt["tag"]))
        elif op in ("GraphNodeRetracted", "GraphEdgeRetracted"):
            removed.update(crdt.get("removes", []))

    g = PKG(self_id=self_id)
    for adds in node_adds.values():
        survivors = [a for a in adds if a[3] not in removed]
        if survivors:
            g.add_node(_node_from(max(survivors, key=lambda a: (a[0], a[1]))[2]))
    for adds in edge_adds.values():
        survivors = [a for a in adds if a[3] not in removed]
        if survivors:
            g.add_edge(_edge_from(max(survivors, key=lambda a: (a[0], a[1]))[2]))
    return g


def fold(ops: list[dict], self_id: str = "self") -> PKG:
    """Slice-1 alias — reconstruct from the log (now backed by ``materialize``)."""
    return materialize(ops, self_id=self_id)


def merge(*logs: "OpLog | list[dict]") -> list[dict]:
    """Union replicas' op-logs into one deduped, deterministically-ordered log (Slice 3).

    Commutative / associative / idempotent by construction (set union keyed by
    eventId). Ordering by (lamport, eventId) is only for a stable *serialized* form;
    ``materialize`` is order-independent, so convergence does not depend on it."""
    merged: list[dict] = []
    for log in logs:
        merged.extend(log.ops if isinstance(log, OpLog) else log)
    return sorted(_dedupe(merged), key=lambda e: (e["payload"]["crdt"]["lamport"], e["eventId"]))


def verify_chain(ops: list[dict]) -> bool:
    """Every op's recorded eventHash matches its recomputed content hash, and parents
    point at the immediately preceding head. Single-replica / pre-merge check — after
    a merge the DAG is multi-head and this no longer applies."""
    prev: str | None = None
    for env in ops:
        p = env["payload"]
        if _content_hash(env["eventType"], env["objectId"], p) != env["integrity"]["eventHash"]:
            return False
        if p["crdt"]["parents"] != ([prev] if prev else []):
            return False
        prev = env["integrity"]["eventHash"]
    return True
