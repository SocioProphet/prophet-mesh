"""pkg_query — read/resolve side of the PKG.

pkg.py builds a graph and pkg_hellgraph.py exports it; this resolves an identity to a
serializable node + neighborhood VIEW — the shape a backend adapter serves so a surface
(the cockpit) can deep-link an opaque `hg:` ref to real graph context without ever
touching HellGraph directly. Views carry provenance + confidence for provenance-as-UX.
"""
from __future__ import annotations

from collections import deque
from typing import Any, Optional

from .pkg import PKG, Node, Edge


def node_view(n: Node) -> dict[str, Any]:
    """Serializable projection of a node — identity + typed label + trust/provenance."""
    return {
        "id": n.id,
        "type": n.type,
        "label": n.label,
        "assertion_class": n.assertion_class,
        "confidence": n.confidence,
        "memory_scope": n.memory_scope,
        "provenance": {"source": n.provenance.source, "method": n.provenance.method,
                       "captured_at": n.provenance.captured_at},
        "external": [{"target_kg": x.target_kg, "target_id": x.target_id,
                      "confidence": x.confidence, "trust_class": x.trust_class} for x in n.external],
    }


def edge_view(e: Edge) -> dict[str, Any]:
    return {
        "src": e.src, "dst": e.dst, "rel": e.rel,
        "assertion_class": e.assertion_class, "confidence": e.confidence,
        "provenance": {"source": e.provenance.source, "method": e.provenance.method},
    }


def resolve(g: PKG, node_id: str) -> Optional[Node]:
    """Resolve an identity to its node, or None if absent."""
    return g.nodes.get(node_id)


def neighborhood(g: PKG, node_id: str, depth: int = 1) -> dict[str, Any]:
    """A node + its <=depth-hop neighborhood as views (undirected traversal over edges).

    `found` is False when the id is absent, so a caller can fall back rather than 500.
    """
    center = g.nodes.get(node_id)
    if center is None:
        return {"center": node_id, "found": False, "nodes": [], "edges": []}

    depth = max(0, int(depth))
    # Adjacency over undirected edges (a person's context includes edges INTO them).
    adj: dict[str, list[Edge]] = {}
    for e in g.edges:
        adj.setdefault(e.src, []).append(e)
        adj.setdefault(e.dst, []).append(e)

    seen_nodes: set[str] = {node_id}
    seen_edges: set[int] = set()
    edges_out: list[Edge] = []
    frontier: deque[tuple[str, int]] = deque([(node_id, 0)])
    while frontier:
        cur, d = frontier.popleft()
        if d >= depth:
            continue
        for e in adj.get(cur, ()):
            eid = id(e)
            if eid not in seen_edges and (e.src in g.nodes and e.dst in g.nodes):
                seen_edges.add(eid)
                edges_out.append(e)
            other = e.dst if e.src == cur else e.src
            if other not in seen_nodes and other in g.nodes:
                seen_nodes.add(other)
                frontier.append((other, d + 1))

    return {
        "center": node_id,
        "found": True,
        "self_id": g.self_id,
        "nodes": [node_view(g.nodes[nid]) for nid in seen_nodes],
        "edges": [edge_view(e) for e in edges_out],
    }
