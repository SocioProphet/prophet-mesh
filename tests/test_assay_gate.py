"""The gate path auto-records verdicts to the store as it admits/quarantines ops."""

from __future__ import annotations

from prophet_mesh.assay_fleet import load_standards
from prophet_mesh.assay_gate import gate_and_record
from prophet_mesh.assay_store import AssayStore
from prophet_mesh.pkg import Node, Provenance
from prophet_mesh.pkg_ops import EmittingPKG

NF = "urn:srcos:assay-standard:narration-fidelity:cfr-eval-001"


def _assay(judgment="supported", method="computed", binding="inline"):
    return {
        "id": "urn:srcos:reasoning-assay:g", "type": "ReasoningAssay",
        "runRef": "urn:srcos:reasoning-run:g", "method": method, "binding": binding,
        "verifier": {"judgment": judgment, "calibrationRef": NF},
        "authority": {"integrityVerified": True},
    }


def _node(node_id: str) -> Node:
    return Node(id=node_id, type="Fact", label=node_id,
               provenance=Provenance(source="test", method="declared"), assertion_class="Structural")


def test_gate_and_record_persists_verdicts_and_gates(tmp_path):
    store = AssayStore(tmp_path / "a.jsonl")
    standards = load_standards()
    ok_ref, sad_ref = "att:ok", "att:sad"
    assays = {ok_ref: _assay(), sad_ref: _assay(method="generated", binding="post-hoc")}  # sad projects sad

    # two distinct cloud nodes, each with one attested op
    a = EmittingPKG.seeded("self", replica_id="cloud-1", locus="burst_cloud")
    a.add_node(_node("good"), attestation_ref=ok_ref)
    b = EmittingPKG.seeded("self", replica_id="cloud-2", locus="burst_cloud")
    b.add_node(_node("weak"), attestation_ref=sad_ref)
    ops = a.log.ops + b.log.ops

    result = gate_and_record(ops, assays_by_ref=assays, standards=standards, store=store,
                             run_locus="burst_cloud")

    # verdicts persisted, keyed by node (replicaId); the unattested genesis ops are not recorded
    current = store.current()
    assert set(current) == {"cloud-1", "cloud-2"}
    assert current["cloud-1"]["verifier"]["judgment"] == "supported"

    # and the gate still did its job: ok admitted, sad quarantined
    admitted = {e["payload"]["crdt"]["attestationRef"] for e in result.canonical_ops}
    quarantined = {e["payload"]["crdt"]["attestationRef"] for e in result.quarantine_ops}
    assert ok_ref in admitted
    assert sad_ref in quarantined


def test_recorded_verdicts_flow_into_the_rollup(tmp_path):
    from prophet_mesh.assay import validate_assay_rollup
    from prophet_mesh.assay_fleet import build_fleet_snapshot

    store = AssayStore(tmp_path / "a.jsonl")
    standards = load_standards()
    assays = {"att:ok": _assay(), "att:ok2": _assay()}

    a = EmittingPKG.seeded("self", replica_id="node-a", locus="burst_cloud")
    a.add_node(_node("n1"), attestation_ref="att:ok")
    b = EmittingPKG.seeded("self", replica_id="node-b", locus="burst_cloud")
    b.add_node(_node("n2"), attestation_ref="att:ok2")

    gate_and_record(a.log.ops + b.log.ops, assays_by_ref=assays, standards=standards,
                    store=store, run_locus="burst_cloud")

    snap = build_fleet_snapshot(store=store)  # 2 nodes → no bootstrap
    assert snap["rollup"]["totalAssays"] == 2
    assert snap["rollup"]["distribution"]["ok"] == 2
    assert validate_assay_rollup(snap["rollup"]).valid is True
