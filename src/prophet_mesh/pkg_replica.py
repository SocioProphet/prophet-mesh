"""CRDT Slice 5 — live replicas + the HellGraph ingester.

Slices 1–4 are pure functions over op-logs. Slice 5 makes them *live*:

  * ``Replica`` — a device/agent that holds a PKG + op-log and syncs with peers by
    **anti-entropy** (exchange only the ops the other side is missing), converging
    two live participants without any central coordinator.
  * ``replay_to_hellgraph`` — the ingester the writer docstring promised but never
    had (gap #4): replays a materialized PKG through a ``HellGraphStore``-shaped
    sink (``addNode`` / ``addEdge``), so the op-log is no longer emit-only — it
    lands on the real substrate.

The two compose into the punchline: sync converges *everything* (longevity), the
Slice-4 gate keeps only the proven-correct sub-graph, and **only that canonical
graph is replayed to HellGraph.** Unattested cloud ops live in every replica's log
but never reach the authoritative store.

Accretive: reuses pkg_ops (merge/materialize/apply_remote), pkg_gate (gate), and
pkg_hellgraph (to_hellgraph). Nothing below is modified.
"""
from __future__ import annotations

from typing import Iterable, Protocol, runtime_checkable

from .pkg import PKG, Node, Edge
from .pkg_ops import EmittingPKG, EdgeKey, materialize
from .pkg_gate import gate, GateResult, Resolver, deny_all
from .pkg_hellgraph import to_hellgraph


class Replica:
    """A live CRDT participant. Local edits emit ops; ``sync`` reconciles with a
    peer via anti-entropy. The authoritative view is always ``gate(self.ops)``."""

    def __init__(self, replica_id: str, *, locus: str = "local", self_id: str = "self", seed: bool = True) -> None:
        self.replica_id = replica_id
        if seed:
            self.epkg = EmittingPKG.seeded(self_id, replica_id=replica_id, locus=locus)
        else:
            self.epkg = EmittingPKG(PKG(self_id=self_id), replica_id=replica_id, locus=locus)
        self._seen: set[str] = {e["eventId"] for e in self.epkg.log.ops}

    # ── local mutations (delegate + track) ──────────────────────────────────
    def _track(self, env: dict) -> dict:
        self._seen.add(env["eventId"])
        return env

    def add_node(self, n: Node, **kw) -> dict:
        return self._track(self.epkg.add_node(n, **kw))

    def add_edge(self, e: Edge, **kw) -> dict:
        return self._track(self.epkg.add_edge(e, **kw))

    def retract_node(self, node_id: str, **kw) -> dict:
        return self._track(self.epkg.retract_node(node_id, **kw))

    def retract_edge(self, key: EdgeKey, **kw) -> dict:
        return self._track(self.epkg.retract_edge(key, **kw))

    @property
    def ops(self) -> list[dict]:
        return self.epkg.log.ops

    # ── anti-entropy ─────────────────────────────────────────────────────────
    def delta_for(self, have: set[str]) -> list[dict]:
        """Ops this replica holds that the peer (``have`` = its seen-set) lacks."""
        return [e for e in self.ops if e["eventId"] not in have]

    def receive(self, ops: Iterable[dict]) -> int:
        """Ingest a peer's ops we haven't seen: apply to view + tag trackers and
        incorporate into our log (multi-head DAG). Returns the count newly applied."""
        new = [e for e in ops if e["eventId"] not in self._seen]
        max_lamport = self.epkg.log._lamport
        for env in new:
            self.epkg.apply_remote(env)
            self.epkg.log.ops.append(env)
            self._seen.add(env["eventId"])
            max_lamport = max(max_lamport, env["payload"]["crdt"]["lamport"])
        self.epkg.log._lamport = max_lamport  # Lamport advance so later local edits win
        return len(new)

    def materialized(self, self_id: str = "self") -> PKG:
        """Fully converged view (pre-gate)."""
        return materialize(self.ops, self_id=self_id)

    def gated(self, *, resolve: Resolver = deny_all, **kw) -> GateResult:
        """Authoritative view + quarantine + receipt (Slice-4 gate over our log)."""
        return gate(self.ops, resolve=resolve, self_id=self.epkg.g.self_id, **kw)


def sync(a: Replica, b: Replica) -> tuple[int, int]:
    """Bidirectional anti-entropy: after this, both replicas hold the same op-set
    and therefore ``materialize`` to the same state. Returns (a→b, b→a) counts."""
    to_b = a.delta_for(b._seen)
    to_a = b.delta_for(a._seen)
    n_ab = b.receive(to_b)
    n_ba = a.receive(to_a)
    return n_ab, n_ba


# ── the live HellGraph ingester (closes gap #4) ─────────────────────────────
@runtime_checkable
class HellGraphSink(Protocol):
    """The subset of the TS ``HellGraphStore`` façade an ingester needs. The real
    implementation is an HTTP client to ``@socioprophet/hellgraph``; tests use an
    in-memory double."""

    def addNode(self, id: str, labels: list[str], properties: dict, createdAt: str | None = None) -> None: ...
    def addEdge(self, label: str, frm: str, to: str, properties: dict) -> None: ...


def replay_to_hellgraph(g: PKG, sink: HellGraphSink) -> dict[str, int]:
    """Replay a materialized PKG through the façade sink (nodes before edges, so
    endpoints exist). Idempotent because HellGraph atoms are content-addressed."""
    bundle = to_hellgraph(g)
    for n in bundle["nodes"]:
        sink.addNode(n["id"], n["labels"], n["properties"], n.get("createdAt"))
    for e in bundle["edges"]:
        sink.addEdge(e["label"], e["from"], e["to"], e["properties"])
    return {"nodes": len(bundle["nodes"]), "edges": len(bundle["edges"])}


def persist_canonical(replica: Replica, sink: HellGraphSink, *, resolve: Resolver = deny_all, **gate_kw) -> tuple[GateResult, dict[str, int]]:
    """End-to-end: gate the replica's converged log, then replay ONLY the canonical
    (proven-correct) graph to HellGraph. The quarantine view is retained in the log
    but never persisted. Returns (gate result incl. receipt, replay counts)."""
    res = replica.gated(resolve=resolve, **gate_kw)
    counts = replay_to_hellgraph(res.canonical, sink)
    return res, counts
