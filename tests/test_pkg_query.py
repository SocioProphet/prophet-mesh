"""Tests for the PKG read/query side: resolve an identity + project a neighborhood view."""
from __future__ import annotations

from prophet_mesh.pkg import Edge, Provenance, ingest_contact, ingest_event, seed_graph
from prophet_mesh.pkg_query import neighborhood, node_view, resolve


def _graph():
    g = seed_graph("self")
    jonah = ingest_contact(g, "Jonah Mercer", relationship="colleague")   # person:jonah_mercer, self-knows->jonah
    ada = ingest_contact(g, "Ada Okonkwo", relationship="colleague")      # person:ada_okonkwo
    ingest_event(g, "Smelter Audit")                                       # event, self-participatedIn
    # a person->person edge so a person's neighborhood has more than just Self
    g.add_edge(Edge(src=jonah, dst=ada, rel="collaboratedWith",
                    provenance=Provenance(source="workspace:contacts", method="ingested")))
    return g, jonah, ada


def test_resolve_hits_and_misses():
    g, jonah, _ = _graph()
    assert resolve(g, "self").type == "Self"
    assert resolve(g, jonah).label == "Jonah Mercer"
    assert resolve(g, "person:nobody") is None


def test_node_view_carries_provenance_and_confidence():
    g, jonah, _ = _graph()
    v = node_view(resolve(g, jonah))
    assert v["id"] == jonah and v["type"] == "Person" and v["label"] == "Jonah Mercer"
    assert "provenance" in v and v["provenance"]["method"] == "ingested"
    assert 0.0 <= v["confidence"] <= 1.0


def test_neighborhood_of_self_includes_direct_relations():
    g, jonah, ada = _graph()
    nb = neighborhood(g, "self", depth=1)
    assert nb["found"] is True
    ids = {n["id"] for n in nb["nodes"]}
    assert "self" in ids and jonah in ids and ada in ids   # Self knows both
    # depth-1 from self does NOT pull the person↔person edge's far side beyond the frontier rule,
    # but both persons are direct neighbors of Self here.
    assert all(e["src"] in ids and e["dst"] in ids for e in nb["edges"])


def test_neighborhood_of_a_person_includes_self_and_peer():
    g, jonah, ada = _graph()
    nb = neighborhood(g, jonah, depth=1)
    assert nb["found"] is True
    ids = {n["id"] for n in nb["nodes"]}
    assert jonah in ids and "self" in ids and ada in ids   # Self→jonah edge + jonah→ada edge
    rels = {e["rel"] for e in nb["edges"]}
    assert "collaboratedWith" in rels


def test_absent_node_returns_found_false_not_error():
    g, _, _ = _graph()
    nb = neighborhood(g, "person:ghost", depth=2)
    assert nb["found"] is False and nb["nodes"] == [] and nb["edges"] == []


def test_depth_zero_is_just_the_center():
    g, jonah, _ = _graph()
    nb = neighborhood(g, jonah, depth=0)
    assert {n["id"] for n in nb["nodes"]} == {jonah} and nb["edges"] == []
