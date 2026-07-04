"""CRDT Slice 4 — locus / attestation merge gate.

Proves: trusted loci admitted, gated loci fail-closed without a passing receipt,
attested gated ops admitted, an untrusted retract cannot delete canonical data,
nothing is lost, and the emitted receipt conforms to SyncCycleReceipt v2.
"""
from __future__ import annotations

from prophet_mesh.pkg import PKG, Node, Provenance
from prophet_mesh.pkg_ops import EmittingPKG, merge
from prophet_mesh.pkg_gate import gate, passing, deny_all

PASS_REF = "urn:srcos:reasoning-receipt:pass-001"


def _prov(src="workspace:contacts"):
    return Provenance(source=src, method="ingested")


def _node(nid, label, src="workspace:contacts"):
    return Node(id=nid, type="Person", label=label, provenance=_prov(src))


def _trusted():
    t = EmittingPKG.seeded("self", replica_id="device-a", locus="trusted_private")
    t.add_node(_node("person:ada", "Ada"))
    return t


def _cloud():
    """A burst_cloud replica emitting one attested + one unattested claim."""
    c = EmittingPKG(PKG(self_id="self"), replica_id="cloud-1", locus="burst_cloud")
    c.add_node(_node("claim:cpi", "CPI figure", src="cloud:analysis"), attestation_ref=PASS_REF)
    c.add_node(_node("claim:gdp", "GDP figure", src="cloud:analysis"))  # no attestation
    return c


def _ids(g: PKG):
    return {n.id for n in g.nodes.values()}


# ── admission ───────────────────────────────────────────────────────────────
def test_trusted_loci_are_admitted():
    t = _trusted()
    res = gate(t.log.ops)  # default deny_all resolver — but these are trusted_private
    assert _ids(res.canonical) == {"self", "person:ada"}
    assert res.quarantined == 0


def test_unattested_gated_op_is_quarantined_fail_closed():
    merged = merge(_trusted().log, _cloud().log)
    res = gate(merged, resolve=deny_all)  # nothing from cloud can pass
    assert "claim:gdp" not in _ids(res.canonical)
    assert "claim:cpi" not in _ids(res.canonical)   # even attested — resolver denies
    assert "claim:gdp" in _ids(res.quarantine)


def test_attested_gated_op_is_admitted():
    merged = merge(_trusted().log, _cloud().log)
    res = gate(merged, resolve=passing(PASS_REF))
    assert "claim:cpi" in _ids(res.canonical)        # attested → canonical
    assert "claim:gdp" not in _ids(res.canonical)    # unattested → still quarantined
    assert "claim:gdp" in _ids(res.quarantine)


# ── security property ─────────────────────────────────────────────────────────
def test_untrusted_retract_cannot_delete_canonical_data():
    t = _trusted()                                   # self + Ada (trusted_private)
    ada_add = [e for e in t.log.ops if e["payload"].get("node", {}).get("id") == "person:ada"][0]

    attacker = EmittingPKG(PKG(self_id="self"), replica_id="cloud-evil", locus="burst_cloud")
    attacker.apply_remote(ada_add)                   # observes Ada's tag
    attacker.retract_node("person:ada")              # unattested burst_cloud retract

    merged = merge(t.log, attacker.log)
    res = gate(merged, resolve=deny_all)
    assert "person:ada" in _ids(res.canonical)       # the untrusted retract was quarantined
    assert res.quarantined >= 1


# ── longevity: nothing lost ──────────────────────────────────────────────────
def test_nothing_is_lost():
    merged = merge(_trusted().log, _cloud().log)
    res = gate(merged, resolve=passing(PASS_REF))
    assert res.admitted + res.quarantined == len(merged)


# ── receipt conformance ──────────────────────────────────────────────────────
_ALLOWED = {  # SyncCycleReceipt.json top-level keys (additionalProperties:false)
    "id", "type", "specVersion", "cycleId", "engineId", "org", "contentView",
    "fromVersion", "toVersion", "lifecycleEnv", "locus", "outcome", "policyGate",
    "policyReason", "steps", "nixCacheUrl", "flakeRef", "durationMs", "issuedAt",
    "auditId", "agentplaneRunRef",
}
_REQUIRED = {"id", "type", "specVersion", "cycleId", "engineId", "org", "contentView",
             "toVersion", "lifecycleEnv", "locus", "outcome", "steps", "issuedAt", "auditId"}
_OUTCOMES = {"planned", "dry_run", "applied", "skipped", "denied", "failed"}
_STEP_STATUS = {"dry_run", "ok", "failed", "skipped", "timeout"}
_LOCI = {"local", "trusted_private", "attested_fog", "burst_cloud"}


def test_receipt_is_synccyclereceipt_conformant():
    res = gate(merge(_trusted().log, _cloud().log), resolve=passing(PASS_REF))
    r = res.receipt
    assert set(r.keys()) <= _ALLOWED
    assert _REQUIRED <= set(r.keys())
    assert r["type"] == "SyncCycleReceipt"
    assert r["id"].startswith("urn:srcos:sync-receipt:")
    assert r["engineId"].startswith("sourceos.sync.")
    assert r["auditId"].startswith("urn:srcos:audit:")
    assert r["outcome"] in _OUTCOMES
    assert r["locus"] in _LOCI
    assert r["toVersion"].startswith("sha256:")
    for step in r["steps"]:
        assert {"step", "status"} <= set(step.keys())
        assert step["status"] in _STEP_STATUS


def test_receipt_outcome_reflects_gate_decision():
    # all quarantined → denied; mixed → applied/partial
    denied = gate(_cloud().log, resolve=deny_all).receipt
    assert denied["outcome"] == "denied" and denied["policyGate"] == "denied"

    mixed = gate(merge(_trusted().log, _cloud().log), resolve=passing(PASS_REF)).receipt
    assert mixed["outcome"] == "applied" and mixed["policyGate"] == "partial"
