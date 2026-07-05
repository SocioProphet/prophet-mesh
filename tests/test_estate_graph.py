"""Tests for the estate knowledge graph — the agentic-OS graph over HellGraph.

Verifies estate nodes/edges validate against the estate vocabulary, that the
Estate anchor invariant holds, that pods are Executable, and that the estate
graph projects to HellGraph's canonical wire shape via the shared writer.
"""
from __future__ import annotations

from prophet_mesh.estate_graph import (
    anchor_pod,
    assign_pod,
    inherit_library,
    load_estate_spec,
    register_library,
    register_opportunity,
    register_pod,
    register_repo,
    reuse_repo,
    seed_estate,
    validate_estate,
)
from prophet_mesh.pkg_hellgraph import edge_payload, node_payload, to_hellgraph

SPEC = load_estate_spec()


def _sample():
    g = seed_estate()
    opp = register_opportunity(g, "health-devsecops", "Health Services DevSecOps", cluster="Health")
    pod = register_pod(g, "capture", "Capture Lead")
    repo = register_repo(g, "prophet-platform")
    lib = register_library(g, "release-gates", "Quality / release gates")
    assign_pod(g, pod, opp)
    reuse_repo(g, opp, repo)
    anchor_pod(g, pod, repo)
    inherit_library(g, opp, lib)
    return g, opp, pod, repo


def test_estate_graph_validates():
    g, *_ = _sample()
    assert validate_estate(g, SPEC) == []


def test_estate_is_the_single_anchor():
    g, *_ = _sample()
    anchors = [n for n in g.nodes.values() if n.type == "Estate"]
    assert len(anchors) == 1
    # A second Estate anchor breaks the invariant.
    from prophet_mesh.pkg import Node, Provenance
    g.add_node(Node(id="estate:other", type="Estate", label="Other",
                    provenance=Provenance(source="test", method="declared"), assertion_class="Structural"))
    assert any("estate_is_the_single_anchor" in e for e in validate_estate(g, SPEC))


def test_pod_is_executable():
    g, _opp, pod, _repo = _sample()
    assert g.nodes[pod].assertion_class == "Executable"


def test_unknown_relation_is_rejected():
    g, opp, pod, _repo = _sample()
    from prophet_mesh.pkg import Edge, Provenance
    g.add_edge(Edge(src=pod, dst=opp, rel="bogusRel", provenance=Provenance(source="test", method="declared")))
    assert any("unknown relation" in e for e in validate_estate(g, SPEC))


def test_projects_to_hellgraph_wire_shape():
    g, opp, pod, _repo = _sample()
    payload = to_hellgraph(g)
    assert set(payload.keys()) == {"nodes", "edges"}
    # The Opportunity node carries its type + assertion_class as labels.
    opp_node = next(node_payload(g.nodes[opp]) for _ in [0])
    assert opp_node["labels"][0] == "Opportunity" and "Assertion" in opp_node["labels"]
    # The pod is Executable.
    pod_node = node_payload(g.nodes[pod])
    assert "Executable" in pod_node["labels"]
    # Edges carry the mandatory epistemic fields and enter as confirmed imports.
    assigned = next(e for e in g.edges if e.rel == "assignedTo")
    props = edge_payload(assigned)["properties"]
    assert {"epistemicClass", "confidence", "promotionState", "createdAt"} <= set(props)
    assert props["epistemicClass"] == "confirmed_relation"
    assert props["promotionState"] == "confirmed"
