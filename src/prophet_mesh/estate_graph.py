"""Estate Knowledge Graph — the graph the agentic operating system is built over.

Reuses the PKG Node/Edge primitives (pkg.py), the PKG→HellGraph writer
(pkg_hellgraph.to_hellgraph), and the fail-closed merge-gate (pkg_gate) — but
anchored on the Estate rather than Self. Registers the agentic-OS objects
(Opportunity / AgentPod / Repository / SharedLibrary / Cluster) and their typed
edges so the cockpit's estate graph and its ``hg:`` refs resolve against the real
HellGraph substrate. Not a new store — a schema over HellGraph, sibling to the
personal knowledge graph.

The vocabulary lives in specs/estate-knowledge-graph.yaml. Estate nodes are
declared imports (method="declared") — they enter HellGraph as confirmed atoms,
not speculative candidates.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from prophet_mesh.pkg import PKG, Edge, Node, Provenance, valid_node_types, valid_relations

ESTATE_SPEC_PATH = Path("specs/estate-knowledge-graph.yaml")


def load_estate_spec(path: str | Path = ESTATE_SPEC_PATH) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text())


def _prov(source: str = "agentic-os") -> Provenance:
    return Provenance(source=source, method="declared")


def _slug(s: str) -> str:
    return s.strip().lower().replace(" ", "-").replace("/", "-")


# ── Seed ──────────────────────────────────────────────────────────────────────
def seed_estate(estate_id: str = "estate:root", label: str = "Estate") -> PKG:
    """A fresh estate graph: the single Estate anchor."""
    g = PKG(self_id=estate_id)
    g.add_node(Node(
        id=estate_id, type="Estate", label=label,
        provenance=_prov("onboarding"), assertion_class="Structural",
    ))
    return g


# ── Registration (agentic-OS objects → typed estate nodes + edges) ────────────
def register_cluster(g: PKG, cluster: str) -> str:
    nid = f"cluster:{_slug(cluster)}"
    if nid not in g.nodes:
        g.add_node(Node(id=nid, type="Cluster", label=cluster, provenance=_prov(), assertion_class="Structural"))
    return nid


def register_repo(g: PKG, repo: str) -> str:
    nid = f"repo:{repo}"
    if nid not in g.nodes:
        g.add_node(Node(id=nid, type="Repository", label=repo, provenance=_prov(), assertion_class="Structural"))
    return nid


def register_library(g: PKG, lib_id: str, label: str) -> str:
    nid = f"library:{lib_id}"
    if nid not in g.nodes:
        g.add_node(Node(id=nid, type="SharedLibrary", label=label, provenance=_prov()))
    return nid


def register_pod(g: PKG, pod_id: str, label: str) -> str:
    """A staffing pod — an Executable agent node (the choir role, capture-side)."""
    nid = f"agent-pod:{pod_id}"
    if nid not in g.nodes:
        g.add_node(Node(id=nid, type="AgentPod", label=label, provenance=_prov(), assertion_class="Executable"))
    return nid


def register_opportunity(g: PKG, opp_id: str, label: str, cluster: str | None = None) -> str:
    """An objective the estate pursues; anchored under the Estate."""
    nid = f"opportunity:{opp_id}"
    g.add_node(Node(id=nid, type="Opportunity", label=label, provenance=_prov()))
    g.add_edge(Edge(src=g.self_id, dst=nid, rel="pursues", provenance=_prov(), assertion_class="Structural"))
    if cluster:
        cid = register_cluster(g, cluster)
        g.add_edge(Edge(src=nid, dst=cid, rel="inCluster", provenance=_prov(), assertion_class="Structural"))
    return nid


def assign_pod(g: PKG, pod_nid: str, opp_nid: str) -> None:
    g.add_edge(Edge(src=pod_nid, dst=opp_nid, rel="assignedTo", provenance=_prov()))


def reuse_repo(g: PKG, opp_nid: str, repo_nid: str) -> None:
    g.add_edge(Edge(src=opp_nid, dst=repo_nid, rel="reuses", provenance=_prov()))


def anchor_pod(g: PKG, pod_nid: str, repo_nid: str) -> None:
    g.add_edge(Edge(src=pod_nid, dst=repo_nid, rel="anchoredTo", provenance=_prov()))


def inherit_library(g: PKG, opp_nid: str, lib_nid: str) -> None:
    g.add_edge(Edge(src=opp_nid, dst=lib_nid, rel="inherits", provenance=_prov()))


# ── Validation (mirrors pkg.validate but anchors on Estate) ───────────────────
def validate_estate(g: PKG, spec: dict | None = None) -> list[str]:
    spec = spec or load_estate_spec()
    ntypes, rels = valid_node_types(spec), valid_relations(spec)
    errs: list[str] = []

    anchors = [n for n in g.nodes.values() if n.type == "Estate"]
    if len(anchors) != 1:
        errs.append(f"invariant estate_is_the_single_anchor: found {len(anchors)} Estate nodes")

    for n in g.nodes.values():
        if n.type not in ntypes:
            errs.append(f"node {n.id}: unknown type {n.type!r}")
        if not n.provenance.source:
            errs.append(f"node {n.id}: missing provenance.source")
        if n.type == "AgentPod" and n.assertion_class != "Executable":
            errs.append(f"node {n.id}: invariant pods_are_executable violated ({n.assertion_class})")

    for e in g.edges:
        if e.rel not in rels:
            errs.append(f"edge {e.src}->{e.dst}: unknown relation {e.rel!r}")
        if e.src not in g.nodes or e.dst not in g.nodes:
            errs.append(f"edge {e.src}->{e.dst} ({e.rel}): dangling endpoint")
        if not e.provenance.source:
            errs.append(f"edge {e.src}->{e.dst}: missing provenance.source")
    return errs
