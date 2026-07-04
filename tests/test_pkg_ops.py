"""CRDT Slice 1 tests — op-emitter conformance, hash chain, and fold round-trip."""
from __future__ import annotations

import re

from prophet_mesh.pkg import PKG, Node, Edge, Provenance
from prophet_mesh.pkg_ops import EmittingPKG, fold, verify_chain, LOCI, SPEC_VERSION

_EVENT_ID = re.compile(r"^urn:srcos:event:")
_REQUIRED = {"eventId", "eventType", "specVersion", "occurredAt", "actor", "objectId", "payload"}


def _build() -> EmittingPKG:
    # seeded() emits the Self anchor as the genesis op → the log is complete.
    epkg = EmittingPKG.seeded("self", replica_id="device-a", locus="trusted_private")
    epkg.add_node(Node(
        id="person:ada", type="Person", label="Ada",
        provenance=Provenance(source="workspace:contacts", method="ingested"),
    ))
    epkg.add_edge(Edge(
        src="self", dst="person:ada", rel="knows",
        provenance=Provenance(source="workspace:contacts", method="ingested"),
    ))
    return epkg


def test_every_mutation_emits_a_conformant_envelope():
    epkg = _build()
    assert len(epkg.log.ops) == 3  # genesis Self + Person node + edge
    for env in epkg.log.ops:
        # EventEnvelope required fields (additionalProperties:false — only allowed keys)
        assert _REQUIRED <= set(env.keys())
        assert set(env.keys()) <= _REQUIRED | {"integrity"}
        assert _EVENT_ID.match(env["eventId"])
        assert env["specVersion"] == SPEC_VERSION
        assert env["actor"]["subjectId"].startswith("urn:srcos:replica:")
        assert env["eventType"] in ("GraphNodeAsserted", "GraphEdgeAsserted")


def test_crdt_metadata_records_locus_and_causal_order():
    epkg = _build()
    self_op, node_op, edge_op = epkg.log.ops
    for env in (self_op, node_op, edge_op):
        crdt = env["payload"]["crdt"]
        assert crdt["locus"] in LOCI and crdt["locus"] == "trusted_private"
        assert crdt["tag"] == env["eventId"]          # OR-Set add-tag identity
        assert crdt["trustLevel"] == "trusted-workspace-source"
    # lamport increases; edge causally follows the node (parents = node's hash)
    assert self_op["payload"]["crdt"]["lamport"] == 1
    assert node_op["payload"]["crdt"]["lamport"] == 2
    assert edge_op["payload"]["crdt"]["lamport"] == 3
    assert edge_op["payload"]["crdt"]["parents"] == [node_op["integrity"]["eventHash"]]


def test_hash_chain_verifies():
    epkg = _build()
    assert verify_chain(epkg.log.ops) is True


def test_tamper_breaks_the_chain():
    epkg = _build()
    epkg.log.ops[0]["payload"]["node"]["label"] = "Mallory"  # mutate content, not hash
    assert verify_chain(epkg.log.ops) is False


def test_fold_reconstructs_graph_state_from_log_alone():
    epkg = _build()
    rebuilt: PKG = fold(epkg.log.ops)
    # nodes + edges recovered from the op-log match the live graph
    assert set(rebuilt.nodes) == set(epkg.g.nodes)
    assert rebuilt.nodes["person:ada"].label == "Ada"
    live_edges = {(e.src, e.rel, e.dst) for e in epkg.g.edges}
    fold_edges = {(e.src, e.rel, e.dst) for e in rebuilt.edges}
    assert live_edges == fold_edges
