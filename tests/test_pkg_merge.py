"""CRDT Slice 2/3 — reconstruct + converge.

Proves the OR-Set merge is commutative / associative / idempotent, that offline
replicas converge, and that concurrent add-vs-retract resolves add-wins.
"""
from __future__ import annotations

import random

from prophet_mesh.pkg import PKG, Node, Edge, Provenance
from prophet_mesh.pkg_ops import EmittingPKG, materialize, merge


def _prov(src="workspace:contacts"):
    return Provenance(source=src, method="ingested")


def _node(nid, label):
    return Node(id=nid, type="Person", label=label, provenance=_prov())


def _edge(src, rel, dst):
    return Edge(src=src, dst=dst, rel=rel, provenance=_prov())


def _state(g: PKG):
    """Comparable convergence fingerprint: node ids+labels and edge triples."""
    nodes = frozenset((n.id, n.label) for n in g.nodes.values())
    edges = frozenset((e.src, e.rel, e.dst) for e in g.edges)
    return nodes, edges


def _replica_a():
    a = EmittingPKG.seeded("self", replica_id="device-a", locus="trusted_private")
    a.add_node(_node("person:ada", "Ada"))
    a.add_edge(_edge("self", "knows", "person:ada"))
    return a


def _replica_b():
    b = EmittingPKG.seeded("self", replica_id="device-b", locus="trusted_private")
    b.add_node(_node("person:bob", "Bob"))
    b.add_edge(_edge("self", "knows", "person:bob"))
    return b


# ── Slice 2: reconstruct ────────────────────────────────────────────────────
def test_materialize_matches_live_graph():
    a = _replica_a()
    assert _state(materialize(a.log.ops)) == _state(a.g)


def test_retract_removes_element_but_keeps_the_rest():
    a = _replica_a()
    a.retract_node("person:ada")
    g = materialize(a.log.ops)
    ids = {n.id for n in g.nodes.values()}
    assert "person:ada" not in ids and "self" in ids


# ── Slice 3: converge ───────────────────────────────────────────────────────
def test_merge_is_commutative():
    a, b = _replica_a(), _replica_b()
    assert _state(materialize(merge(a.log, b.log))) == _state(materialize(merge(b.log, a.log)))


def test_merge_is_idempotent():
    a = _replica_a()
    once = merge(a.log)
    twice = merge(a.log, a.log)
    assert {e["eventId"] for e in once} == {e["eventId"] for e in twice}
    assert _state(materialize(twice)) == _state(materialize(a.log.ops))


def test_merge_is_associative():
    a, b = _replica_a(), _replica_b()
    c = EmittingPKG.seeded("self", replica_id="device-c", locus="local")
    c.add_node(_node("person:cyd", "Cyd"))
    left = merge(merge(a.log, b.log), c.log)
    right = merge(a.log, merge(b.log, c.log))
    assert _state(materialize(left)) == _state(materialize(right))


def test_two_offline_replicas_converge():
    a, b = _replica_a(), _replica_b()  # each edited offline, never saw the other
    converged = materialize(merge(a.log, b.log))
    nodes, edges = _state(converged)
    ids = {nid for nid, _ in nodes}
    assert ids == {"self", "person:ada", "person:bob"}
    assert ("self", "knows", "person:ada") in edges
    assert ("self", "knows", "person:bob") in edges


def test_order_independent_under_random_shuffle():
    a, b = _replica_a(), _replica_b()
    union = merge(a.log, b.log)
    baseline = _state(materialize(union))
    rng = random.Random(1729)
    for _ in range(20):
        shuffled = union[:]
        rng.shuffle(shuffled)
        assert _state(materialize(shuffled)) == baseline


def test_add_wins_over_concurrent_retract():
    # A adds Ada; B observes that add, then retracts it. Concurrently A re-adds Ada
    # (a NEW tag B never saw) with an updated label. Merge → Ada present, updated.
    a = EmittingPKG.seeded("self", replica_id="device-a", locus="local")
    add1 = a.add_node(_node("person:ada", "Ada"))

    b = EmittingPKG.seeded("self", replica_id="device-b", locus="local")
    b.apply_remote(add1)                 # B observed Ada@tag1
    b.retract_node("person:ada")         # removes only tag1

    a.add_node(_node("person:ada", "Ada (updated)"))  # concurrent re-add, tag2

    converged = materialize(merge(a.log, b.log))
    ada = [n for n in converged.nodes.values() if n.id == "person:ada"]
    assert len(ada) == 1                 # add-wins: survives the concurrent retract
    assert ada[0].label == "Ada (updated)"


def test_retract_wins_when_all_observed_tags_removed():
    # If the retract observed every add-tag, the element is genuinely gone.
    a = EmittingPKG.seeded("self", replica_id="device-a", locus="local")
    a.add_node(_node("person:ada", "Ada"))
    a.retract_node("person:ada")         # observed the only tag
    ids = {n.id for n in materialize(a.log.ops).nodes.values()}
    assert "person:ada" not in ids
