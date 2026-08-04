"""Wire the locus gate to the assay store — attested gate decisions persist verdicts.

pkg_gate.gate() consults an assay_resolver to admit gated (cloud-locus) ops: an op
reaches the canonical view only if its attestation resolves to an assay that projects
'ok'. `gate_and_record` runs that same gate AND records each attested op's ReasoningAssay
to the AssayStore, keyed by the op's node (replicaId), so the fleet rollup reflects real
gate traffic automatically — no separate POST /fleet/assay call. The store keeps the
latest verdict per node (LWW), which is exactly what GET /fleet/rollup wants.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .assay import assay_resolver
from .assay_store import AssayStore, default_store
from .pkg_gate import GateResult, gate
from .pkg_ops import OpLog


def gate_and_record(
    ops: Iterable[dict] | OpLog,
    *,
    assays_by_ref: dict[str, dict[str, Any]],
    standards: dict[str, dict[str, Any]],
    store: AssayStore | None = None,
    **gate_kwargs: Any,
) -> GateResult:
    """Run the locus gate with an assay-backed resolver, persisting each attested
    op's verdict to the store first. Returns the usual GateResult."""
    store = store or default_store()
    ops_list = ops.ops if isinstance(ops, OpLog) else list(ops)

    for env in ops_list:
        crdt = env.get("payload", {}).get("crdt", {})
        ref = crdt.get("attestationRef")
        if ref and ref in assays_by_ref:
            store.record(crdt.get("replicaId", "unknown"), assays_by_ref[ref])

    return gate(ops_list, resolve=assay_resolver(assays_by_ref, standards), **gate_kwargs)
