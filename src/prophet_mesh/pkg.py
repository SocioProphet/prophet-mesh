"""Personal Knowledge Graph — the default graph a person is built over.

Materializes the seed from specs/personal-knowledge-graph.yaml, ingests
prophet-workspace data (contacts / calendar / mail / drive) into typed nodes +
edges, and validates every element against the spec vocabulary + provenance
requirement (a SHACL-lite check). Brain-agnostic: this is the data model; the
mesh grounds on it, the Memory Steward owns it.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import yaml

SPEC_PATH = Path("specs/personal-knowledge-graph.yaml")


def load_spec(path: str | Path = SPEC_PATH) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text())


def valid_node_types(spec: dict) -> set[str]:
    return set(spec["node_types"].keys())


def valid_relations(spec: dict) -> set[str]:
    """Top-level edge types + all declared subtypes."""
    rels: set[str] = set()
    for name, body in spec["edge_types"].items():
        rels.add(name)
        for sub in (body or {}).get("subtypes", []) or []:
            rels.add(sub)
    return rels


@dataclass(frozen=True)
class Provenance:
    source: str                 # e.g. "onboarding", "workspace:contacts"
    method: str                 # declared | imported | inferred | ingested
    captured_at: str = ""       # ISO-8601, optional


@dataclass(frozen=True)
class ExternalLink:
    target_kg: str              # general_purpose | social_network | domain_specific | ecommerce_catalog
    target_id: str              # e.g. a Wikidata Q-id
    confidence: float = 0.0
    trust_class: str = "unverified"


@dataclass(frozen=True)
class Node:
    id: str
    type: str
    label: str
    provenance: Provenance
    assertion_class: str = "Assertion"   # Structural | Assertion | Executable
    provenance_tag: str = "P-RET"        # P-RET (pointer-bound) | P-GEN
    inference_type: str = "I-NON"        # I-NON | I-DED | I-IND | I-ABD
    memory_scope: str = "relationship_context:approved"
    confidence: float = 1.0
    external: tuple[ExternalLink, ...] = ()


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    rel: str
    provenance: Provenance
    assertion_class: str = "Assertion"
    provenance_tag: str = "P-RET"
    inference_type: str = "I-NON"
    memory_scope: str = "relationship_context:approved"
    confidence: float = 1.0


@dataclass
class PKG:
    self_id: str
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    external_kgs: list[str] = field(default_factory=list)

    def add_node(self, n: Node) -> None:
        self.nodes[n.id] = n

    def add_edge(self, e: Edge) -> None:
        self.edges.append(e)


# ── Seed ──────────────────────────────────────────────────────────────────────
def seed_graph(self_id: str = "self", spec: dict | None = None) -> PKG:
    """A brand-new person's graph: the Self anchor + registered external KGs."""
    spec = spec or load_spec()
    g = PKG(self_id=self_id, external_kgs=list(spec["seed"]["registered_external_kgs"]))
    g.add_node(Node(
        id=self_id, type="Self", label="Self",
        provenance=Provenance(source="onboarding", method="declared"),
        assertion_class="Structural",
    ))
    return g


# ── Ingestion: prophet-workspace → typed nodes + edges ────────────────────────
def _prov(app: str) -> Provenance:
    return Provenance(source=f"workspace:{app}", method="ingested")


def ingest_contact(g: PKG, name: str, relationship: str | None = None) -> str:
    """A contact → a Person node + an edge from Self (relatedTo family / knows social)."""
    nid = f"person:{name.strip().lower().replace(' ', '_')}"
    g.add_node(Node(id=nid, type="Person", label=name, provenance=_prov("contacts")))
    family = {"parentOf", "childOf", "siblingOf", "spouseOf", "mom", "dad", "mother", "father", "sister", "brother"}
    rel = "relatedTo" if (relationship or "").lower() in family else "knows"
    g.add_edge(Edge(src=g.self_id, dst=nid, rel=rel, provenance=_prov("contacts")))
    return nid


def ingest_event(g: PKG, title: str) -> str:
    nid = f"event:{title.strip().lower().replace(' ', '_')}"
    g.add_node(Node(id=nid, type="Event", label=title, provenance=_prov("calendar")))
    g.add_edge(Edge(src=g.self_id, dst=nid, rel="participatedIn", provenance=_prov("calendar")))
    return nid


def ingest_message(g: PKG, peer_node_id: str) -> None:
    """A message → a communicatedWith edge (the peer Person must already exist)."""
    g.add_edge(Edge(src=g.self_id, dst=peer_node_id, rel="communicatedWith", provenance=_prov("mail")))


def ingest_document(g: PKG, title: str) -> str:
    nid = f"doc:{title.strip().lower().replace(' ', '_')}"
    g.add_node(Node(id=nid, type="Document", label=title, provenance=_prov("drive")))
    g.add_edge(Edge(src=g.self_id, dst=nid, rel="authored", provenance=_prov("drive")))
    return nid


def link_external(g: PKG, node_id: str, link: ExternalLink) -> None:
    """Attach a reference-only external-KG link to a node (privacy: read, never leak)."""
    n = g.nodes[node_id]
    g.nodes[node_id] = replace(n, external=n.external + (link,))


# ── Validation (SHACL-lite): vocabulary + provenance + invariants ─────────────
def validate(g: PKG, spec: dict | None = None) -> list[str]:
    spec = spec or load_spec()
    ntypes, rels = valid_node_types(spec), valid_relations(spec)
    kgs = set(spec["external_kgs"].keys())
    errs: list[str] = []

    selves = [n for n in g.nodes.values() if n.type == "Self"]
    if len(selves) != 1:
        errs.append(f"invariant self_is_the_single_anchor: found {len(selves)} Self nodes")

    for n in g.nodes.values():
        if n.type not in ntypes:
            errs.append(f"node {n.id}: unknown type {n.type!r}")
        if not n.provenance.source:
            errs.append(f"node {n.id}: missing provenance.source")
        for x in n.external:
            if x.target_kg not in kgs:
                errs.append(f"node {n.id}: external link to unknown KG {x.target_kg!r}")

    for e in g.edges:
        if e.rel not in rels:
            errs.append(f"edge {e.src}->{e.dst}: unknown relation {e.rel!r}")
        if e.src not in g.nodes or e.dst not in g.nodes:
            errs.append(f"edge {e.src}->{e.dst} ({e.rel}): dangling endpoint")
        if not e.provenance.source:
            errs.append(f"edge {e.src}->{e.dst}: missing provenance.source")
    return errs
