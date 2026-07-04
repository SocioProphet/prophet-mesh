"""CRDT Slice 4 — the locus / attestation merge gate.

Slices 1–3 make the graph *converge* (everyone sees the same ops). Slice 4 decides
*which converged sub-graph is authoritative*. This is where the correctness moat
plugs in: TEE/confidentiality proves an op ran privately; it says nothing about
whether the computation behind it is correct. The gate admits an op into the
**canonical view** iff:

  * its ``locus`` is ``local`` or ``trusted_private`` (authored where we already
    trust the execution locus), OR
  * its ``locus`` is ``attested_fog`` / ``burst_cloud`` **and** its
    ``attestationRef`` resolves to a **passing correctness receipt**.

Everything else lands in the **quarantine view** — still converged and retained
(longevity), just not authoritative. Fail-closed: a gated-locus op with no /
unresolved attestation is quarantined, and an untrusted retract therefore cannot
silently delete canonical data.

Emits a ``SyncCycleReceipt``-shaped receipt (sourceos-spec v2) per gate cycle.
Accretive: layers over pkg_ops, touches nothing below it.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterable

from .pkg import PKG
from .pkg_ops import materialize, OpLog

# Loci that require a passing correctness receipt to reach the canonical view.
GATED_LOCI = ("attested_fog", "burst_cloud")
TRUSTED_LOCI = ("local", "trusted_private")

# A resolver answers: does this attestationRef name a *passing* correctness receipt?
Resolver = Callable[[str], bool]


def deny_all(_ref: str) -> bool:
    """Default resolver — fail-closed. Nothing from a gated locus is admitted."""
    return False


def passing(*refs: str) -> Resolver:
    """Resolver that admits exactly the given (passing) attestation refs."""
    allowed = set(refs)
    return lambda ref: ref in allowed


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def graph_version(g: PKG) -> str:
    """Content hash of materialized graph state — the SyncCycleReceipt version."""
    nodes = sorted((n.id, n.label) for n in g.nodes.values())
    edges = sorted((e.src, e.rel, e.dst) for e in g.edges)
    return "sha256:" + hashlib.sha256(_canon({"nodes": nodes, "edges": edges}).encode("utf-8")).hexdigest()


def admit(env: dict, resolve: Resolver) -> bool:
    """Admission rule for a single op (fail-closed on gated loci)."""
    crdt = env["payload"]["crdt"]
    locus = crdt["locus"]
    if locus in TRUSTED_LOCI:
        return True
    if locus in GATED_LOCI:
        ref = crdt.get("attestationRef")
        return bool(ref) and resolve(ref)
    return False  # unknown locus → fail-closed


@dataclass
class GateResult:
    canonical: PKG                       # authoritative graph
    quarantine: PKG                      # held-back view (retained, not authoritative)
    canonical_ops: list[dict]
    quarantine_ops: list[dict]
    receipt: dict                        # SyncCycleReceipt-shaped

    @property
    def admitted(self) -> int:
        return len(self.canonical_ops)

    @property
    def quarantined(self) -> int:
        return len(self.quarantine_ops)


def gate(
    ops: Iterable[dict],
    *,
    resolve: Resolver = deny_all,
    self_id: str = "self",
    org: str = "self",
    content_view: str | None = None,
    lifecycle_env: str = "candidate",
    run_locus: str = "trusted_private",
    from_version: str | None = None,
    cycle_id: str | None = None,
    agentplane_run_ref: str | None = None,
) -> GateResult:
    """Split a converged op-log into canonical vs. quarantine and emit a receipt."""
    ops = ops.ops if isinstance(ops, OpLog) else list(ops)
    canonical_ops = [e for e in ops if admit(e, resolve)]
    quarantine_ops = [e for e in ops if not admit(e, resolve)]

    canonical = materialize(canonical_ops, self_id)
    quarantine = materialize(quarantine_ops, self_id)
    to_version = graph_version(canonical)

    n_admit, n_quar = len(canonical_ops), len(quarantine_ops)
    if not ops:
        outcome, gate_val, reason = "skipped", "no-op", "empty op-log"
    elif n_admit == 0:
        outcome, gate_val, reason = "denied", "denied", f"all {n_quar} op(s) held pending correctness attestation"
    elif n_quar:
        outcome, gate_val, reason = "applied", "partial", f"{n_admit} admitted, {n_quar} quarantined pending attestation"
    else:
        outcome, gate_val, reason = "applied", "allowed", f"{n_admit} op(s) admitted"

    steps = [{"step": "admit", "status": "ok", "reason": f"{n_admit} op(s) → canonical"}]
    if n_quar:
        steps.append({"step": "quarantine", "status": "skipped",
                      "reason": f"{n_quar} op(s) → quarantine (unattested gated-locus)"})

    receipt = {
        "id": f"urn:srcos:sync-receipt:{uuid.uuid4()}",
        "type": "SyncCycleReceipt",
        "specVersion": "2.0.0",
        "cycleId": cycle_id or f"pkg-gate-{uuid.uuid4()}",
        "engineId": "sourceos.sync.pkg-crdt-gate",
        "org": org,
        "contentView": content_view or f"pkg-{self_id}",
        "fromVersion": from_version,
        "toVersion": to_version,
        "lifecycleEnv": lifecycle_env,
        "locus": run_locus,
        "outcome": outcome,
        "policyGate": gate_val,
        "policyReason": reason,
        "steps": steps,
        "issuedAt": _now(),
        "auditId": f"urn:srcos:audit:{uuid.uuid4()}",
        "agentplaneRunRef": agentplane_run_ref,
    }

    return GateResult(canonical, quarantine, canonical_ops, quarantine_ops, receipt)
