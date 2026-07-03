"""CRDT Slice 5 — live replicas + HellGraph ingester.

Proves two live replicas converge via anti-entropy, the ingester replays a PKG
through a HellGraphStore-shaped sink (idempotently), and end-to-end only the
gated-canonical graph reaches the store.
"""
from __future__ import annotations

from prophet_mesh.pkg import PKG, Node, Edge, Provenance
from prophet_mesh.pkg_replica import (
    Replica, sync, replay_to_hellgraph, persist_canonical, HellGraphSink,
)
from prophet_mesh.pkg_gate import passing, deny_all

PASS_REF = "urn:srcos:reasoning-receipt:pass-001"


def _prov(src="workspace:contacts"):
    return Provenance(source=src, method="ingested")


def _node(nid, label, src="workspace:contacts"):
    return Node(id=nid, type="Person", label=label, provenance=_prov(src))


def _edge(src, rel, dst):
    return Edge(src=src, dst=dst, rel=rel, provenance=_prov())


def _state(g: PKG):
    return (frozenset((n.id, n.label) for n in g.nodes.values()),
            frozenset((e.src, e.rel, e.dst) for e in g.edges))


class FakeHellGraphStore:
    """In-memory double of the TS HellGraphStore façade. Content-addressed:
    nodes keyed by id, edges by (from, label, to) — so replay is idempotent."""

    def __init__(self):
        self.nodes: dict[str, dict] = {}
        self.edges: dict[tuple, dict] = {}

    def addNode(self, id, labels, properties, createdAt=None):
        self.nodes[id] = {"labels": labels, "properties": properties, "createdAt": createdAt}

    def addEdge(self, label, frm, to, properties):
        self.edges[(frm, label, to)] = properties


# ── live convergence ─────────────────────────────────────────────────────────
def test_two_live_replicas_converge_via_sync():
    a = Replica("device-a", locus="trusted_private")
    b = Replica("device-b", locus="trusted_private")
    a.add_node(_node("person:ada", "Ada")); a.add_edge(_edge("self", "knows", "person:ada"))
    b.add_node(_node("person:bob", "Bob")); b.add_edge(_edge("self", "knows", "person:bob"))

    n_ab, n_ba = sync(a, b)
    assert n_ab > 0 and n_ba > 0
    assert a._seen == b._seen                       # anti-entropy complete
    assert _state(a.materialized()) == _state(b.materialized())
    ids = {n.id for n in a.materialized().nodes.values()}
    assert ids == {"self", "person:ada", "person:bob"}


def test_sync_is_idempotent_second_pass_transfers_nothing():
    a = Replica("device-a", locus="trusted_private")
    b = Replica("device-b", locus="trusted_private")
    a.add_node(_node("person:ada", "Ada"))
    sync(a, b)
    assert sync(a, b) == (0, 0)                      # nothing left to exchange


def test_local_edit_after_sync_propagates_back():
    a = Replica("device-a", locus="trusted_private")
    b = Replica("device-b", locus="trusted_private")
    sync(a, b)
    b.add_node(_node("person:cyd", "Cyd"))          # B edits after first sync
    sync(a, b)
    assert "person:cyd" in {n.id for n in a.materialized().nodes.values()}


# ── the ingester (gap #4) ────────────────────────────────────────────────────
def test_replay_persists_to_hellgraph_sink():
    a = Replica("device-a", locus="trusted_private")
    a.add_node(_node("person:ada", "Ada")); a.add_edge(_edge("self", "knows", "person:ada"))
    store = FakeHellGraphStore()
    assert isinstance(store, HellGraphSink)          # structural conformance
    counts = replay_to_hellgraph(a.materialized(), store)
    assert "person:ada" in store.nodes and "self" in store.nodes
    assert ("self", "knows", "person:ada") in store.edges
    assert counts["nodes"] == len(store.nodes)


def test_replay_is_idempotent():
    a = Replica("device-a", locus="trusted_private")
    a.add_node(_node("person:ada", "Ada")); a.add_edge(_edge("self", "knows", "person:ada"))
    store = FakeHellGraphStore()
    replay_to_hellgraph(a.materialized(), store)
    n1, e1 = len(store.nodes), len(store.edges)
    replay_to_hellgraph(a.materialized(), store)     # replay again
    assert (len(store.nodes), len(store.edges)) == (n1, e1)


# ── end-to-end: only the canonical graph is persisted ────────────────────────
def test_only_gated_canonical_graph_reaches_the_store():
    a = Replica("device-a", locus="trusted_private")
    a.add_node(_node("person:ada", "Ada"))

    cloud = Replica("cloud-1", locus="burst_cloud", seed=False)
    cloud.add_node(_node("claim:cpi", "CPI", src="cloud:analysis"), attestation_ref=PASS_REF)
    cloud.add_node(_node("claim:gdp", "GDP", src="cloud:analysis"))   # unattested

    sync(a, cloud)                                   # everything converges into both logs
    # both unattested + attested claims are present in the converged (pre-gate) view
    conv_ids = {n.id for n in a.materialized().nodes.values()}
    assert {"claim:cpi", "claim:gdp"} <= conv_ids

    store = FakeHellGraphStore()
    res, counts = persist_canonical(a, store, resolve=passing(PASS_REF))

    persisted = set(store.nodes)
    assert "person:ada" in persisted                 # trusted → persisted
    assert "claim:cpi" in persisted                  # attested → persisted
    assert "claim:gdp" not in persisted              # unattested → quarantined, NOT persisted
    assert res.quarantined >= 1
    assert res.receipt["type"] == "SyncCycleReceipt"
