"""Tests for the Personal Knowledge Graph seed + ingestion + validation."""
from __future__ import annotations

from prophet_mesh.pkg import (
    ExternalLink,
    ingest_contact,
    ingest_document,
    ingest_event,
    ingest_message,
    link_external,
    load_spec,
    seed_graph,
    validate,
)

SPEC = load_spec()


def test_seed_is_single_self_anchor_plus_external_kgs():
    g = seed_graph()
    assert len(g.nodes) == 1
    self_node = g.nodes["self"]
    assert self_node.type == "Self"
    assert self_node.assertion_class == "Structural"
    assert self_node.provenance.source == "onboarding"
    assert set(g.external_kgs) == set(SPEC["seed"]["registered_external_kgs"])
    assert validate(g, SPEC) == []


def test_ingest_contact_family_vs_social_relation():
    g = seed_graph()
    mom = ingest_contact(g, "Mom", relationship="mother")
    jamie = ingest_contact(g, "Jamie", relationship="friend")
    assert g.nodes[mom].type == "Person"
    rels = {(e.src, e.dst): e.rel for e in g.edges}
    assert rels[("self", mom)] == "relatedTo"   # family
    assert rels[("self", jamie)] == "knows"      # social
    # every ingested element carries provenance
    assert all(e.provenance.source.startswith("workspace:") for e in g.edges)
    assert validate(g, SPEC) == []


def test_full_workspace_ingest_validates():
    g = seed_graph()
    jamie = ingest_contact(g, "Jamie", relationship="friend")
    ingest_message(g, jamie)
    ingest_event(g, "Band practice")
    ingest_document(g, "Setlist")
    errs = validate(g, SPEC)
    assert errs == [], errs
    # spot-check the typed shape
    types = sorted({n.type for n in g.nodes.values()})
    assert types == ["Document", "Event", "Person", "Self"]


def test_external_link_is_reference_only_and_kg_checked():
    g = seed_graph()
    p = ingest_contact(g, "Jamie", relationship="friend")
    link_external(g, p, ExternalLink(target_kg="social_network", target_id="sn:jamie", confidence=0.9, trust_class="platform"))
    assert validate(g, SPEC) == []
    # an unknown external KG is rejected by the validator
    link_external(g, p, ExternalLink(target_kg="darkweb", target_id="x"))
    assert any("unknown KG" in e for e in validate(g, SPEC))


def test_validator_catches_missing_provenance_and_bad_vocab():
    from dataclasses import replace
    from prophet_mesh.pkg import Provenance
    g = seed_graph()
    # break provenance on a node
    g.nodes["self"] = replace(g.nodes["self"], provenance=Provenance(source="", method="declared"))
    assert any("missing provenance.source" in e for e in validate(g, SPEC))
