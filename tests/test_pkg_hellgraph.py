"""Tests for the PKG → HellGraph writer (canonical wire-shape conformance)."""
from __future__ import annotations

from prophet_mesh.pkg import ExternalLink, ingest_contact, link_external, seed_graph
from prophet_mesh.pkg_hellgraph import edge_payload, node_payload, to_hellgraph

REQUIRED_EDGE_EPISTEMIC = {"epistemicClass", "confidence", "promotionState", "createdAt"}
EPISTEMIC_CLASSES = {
    "extracted_relation", "inferred_relation", "confirmed_relation",
    "graph_extraction", "semantic",
}
PROMOTION_STATES = {"candidate", "confirmed", "contested", "superseded", "vetoed"}


def test_node_payload_has_graphnode_shape():
    g = seed_graph()
    p = node_payload(g.nodes["self"])
    assert set(p.keys()) == {"id", "labels", "properties", "createdAt"}
    assert p["id"] == "self"
    assert p["labels"][0] == "Self" and "Structural" in p["labels"]
    assert p["properties"]["provenance.source"] == "onboarding"
    assert p["createdAt"]  # never empty


def test_edge_payload_carries_mandatory_epistemic_fields():
    g = seed_graph()
    ingest_contact(g, "Mom", relationship="mother")
    e = g.edges[0]
    p = edge_payload(e)
    assert set(p.keys()) == {"label", "from", "to", "properties"}
    assert REQUIRED_EDGE_EPISTEMIC <= set(p["properties"])
    assert p["properties"]["epistemicClass"] in EPISTEMIC_CLASSES
    assert p["properties"]["promotionState"] in PROMOTION_STATES


def test_ingested_workspace_edge_is_confirmed_import():
    g = seed_graph()
    ingest_contact(g, "Jamie", relationship="friend")
    props = edge_payload(g.edges[0])["properties"]
    # method="ingested", I-NON → a confirmed import, not a speculative candidate
    assert props["epistemicClass"] == "confirmed_relation"
    assert props["promotionState"] == "confirmed"


def test_external_link_is_reference_only_in_props():
    g = seed_graph()
    p = ingest_contact(g, "Jamie", relationship="friend")
    link_external(g, p, ExternalLink("social_network", "sn:jamie", 0.9, "platform"))
    props = node_payload(g.nodes[p])["properties"]
    assert props["sameAs.0.kg"] == "social_network"
    assert props["sameAs.0.direction"] == "reference_only"


def test_full_bundle_nodes_before_edges_and_endpoints_exist():
    g = seed_graph()
    jamie = ingest_contact(g, "Jamie", relationship="friend")
    bundle = to_hellgraph(g)
    node_ids = {n["id"] for n in bundle["nodes"]}
    assert "self" in node_ids and jamie in node_ids
    # every edge endpoint is present as a node in the same bundle
    for e in bundle["edges"]:
        assert e["from"] in node_ids and e["to"] in node_ids
