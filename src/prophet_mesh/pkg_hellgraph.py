"""PKG → HellGraph writer.

Projects a Personal Knowledge Graph (pkg.PKG) into HellGraph's canonical wire
shape so it persists on the real substrate. HellGraph's write path is the TS
``HellGraphStore`` façade (``@socioprophet/hellgraph``):

    g.addNode(id, labels[], properties)
    g.addEdge(label, from, to, properties)

with GraphNode = {id, labels[], properties, createdAt} and every edge carrying
the mandatory epistemic fields {epistemicClass, confidence, promotionState,
createdAt}. This module emits exactly those payloads (JSON-serializable dicts)
from the Python side; a thin TS ingester replays them through the façade. We do
NOT touch the Rust kernel — external writers go through the TS projection.

Idempotent by construction: HellGraph structural atoms are content-addressed, so
re-emitting the same PKG collapses to the same atoms.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from prophet_mesh.pkg import PKG, Edge, ExternalLink, Node

# ── Epistemic mapping: PKG inference/method → HellGraph EpistemicClass ─────────
# HellGraph EpistemicClass (ts/src/types.ts): extracted_relation | inferred_relation
# | confirmed_relation | graph_extraction | semantic.
# A PKG element sourced from onboarding or workspace ingestion is a confirmed
# import (source of truth); a labelled inference is inferred_relation.
_INFERRED = {"I-DED", "I-IND", "I-ABD"}


def _epistemic_class(inference_type: str, method: str) -> str:
    if inference_type in _INFERRED:
        return "inferred_relation"
    if method in {"declared", "imported", "ingested"}:
        return "confirmed_relation"
    return "extracted_relation"


def _promotion_state(inference_type: str) -> str:
    # Confirmed imports are accepted; inferences enter as candidates for review.
    return "candidate" if inference_type in _INFERRED else "confirmed"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _created_at(captured_at: str) -> str:
    return captured_at or _now()


def _external_props(external: tuple[ExternalLink, ...]) -> dict[str, Any]:
    """External links are reference-only; carry them as flat, auditable props."""
    props: dict[str, Any] = {}
    for i, x in enumerate(external):
        props[f"sameAs.{i}.kg"] = x.target_kg
        props[f"sameAs.{i}.id"] = x.target_id
        props[f"sameAs.{i}.confidence"] = x.confidence
        props[f"sameAs.{i}.trust"] = x.trust_class
        props[f"sameAs.{i}.direction"] = "reference_only"
    return props


def node_payload(n: Node) -> dict[str, Any]:
    """One GraphNode. Labels = [type, assertion_class]; provenance in properties."""
    props: dict[str, Any] = {
        "label": n.label,
        "provenance.source": n.provenance.source,
        "provenance.method": n.provenance.method,
        "provenance.captured_at": n.provenance.captured_at,
        "assertion_class": n.assertion_class,
        "provenance_tag": n.provenance_tag,       # P-RET | P-GEN
        "inference_type": n.inference_type,        # I-NON | I-DED | I-IND | I-ABD
        "memory_scope": n.memory_scope,
        "confidence": n.confidence,
    }
    props.update(_external_props(n.external))
    return {
        "id": n.id,
        "labels": [n.type, n.assertion_class],
        "properties": props,
        "createdAt": _created_at(n.provenance.captured_at),
    }


def edge_payload(e: Edge) -> dict[str, Any]:
    """One GraphEdge. rel → label; PKG provenance → mandatory epistemic fields."""
    return {
        "label": e.rel,
        "from": e.src,
        "to": e.dst,
        "properties": {
            # HellGraph-mandatory epistemic fields:
            "epistemicClass": _epistemic_class(e.inference_type, e.provenance.method),
            "confidence": e.confidence,
            "promotionState": _promotion_state(e.inference_type),
            "createdAt": _created_at(e.provenance.captured_at),
            # PKG provenance / scope carried through for audit + replay:
            "provenance.source": e.provenance.source,
            "provenance.method": e.provenance.method,
            "assertion_class": e.assertion_class,
            "provenance_tag": e.provenance_tag,
            "inference_type": e.inference_type,
            "memory_scope": e.memory_scope,
        },
    }


def to_hellgraph(g: PKG) -> dict[str, list[dict[str, Any]]]:
    """The full PKG as a HellGraph ingest bundle: {nodes:[...], edges:[...]}.

    Feed to the TS ingester, which replays each through HellGraphStore.addNode /
    .addEdge. Deterministic order (nodes before edges) so edge endpoints exist.
    """
    return {
        "nodes": [node_payload(n) for n in g.nodes.values()],
        "edges": [edge_payload(e) for e in g.edges],
    }
