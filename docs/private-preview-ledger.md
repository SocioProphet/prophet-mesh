# Prophet Mesh Private-Preview Cross-Repo Status Ledger

Maintained under Lane D. All verification states are **binary**: verified / unverified.
Conflicting references to the same artifact path with divergent content hashes must be flagged explicitly — never silently resolved.

Last updated: 2026-06-10

---

## Spine repos — commit state

| Repo | Branch | Head commit | Verification state |
|---|---|---|---|
| `SocioProphet/prophet-mesh` | `main` | `9431a9a` (Lanes C+D: runbook + ledger) | **verified** — `make validate` + 37 tests pass |
| `SocioProphet/agent-registry` | `main` | `590eb40` | **verified** — `make validate` + 42 tests pass |
| `SocioProphet/model-router` | `main` | `76eafe1` | **verified** — `make validate` + 11 tests pass |
| `SocioProphet/agentplane` | `main` | post-PR-#275 merge | **verified** — adapter validates, 114/114 tests pass |
| `SocioProphet/memory-mesh` | `main` | `37cf36f` (Lane G contract) | **verified** — `make validate-prophet-mesh-scope-mirror` passes; CI gate [PR #39](https://github.com/SocioProphet/memory-mesh/pull/39) pending merge |
| `SocioProphet/prophet-workspace` | `main` | latest | **referenced** — workspace action contracts (mail, calendar, tasks) ground `email_reply` and `operations_plan` action types; formal validator integration deferred |

---

## Agentplane adapter contract

| Field | Value | Verification state |
|---|---|---|
| Repo | `SocioProphet/agentplane` | verified |
| Path | `contracts/prophet-mesh/prophet-mesh-agentplane-adapter.v0.1.json` | verified |
| Merge commit | `faa767f42028ad0f2475c993700cdbef8490a38e` | verified — merged 2026-06-09, PR #274 |
| `content_sha256` | `38a3edb62813521a62f257f3f952271255d25dc3a05a14d6b96f04a6ff9b4268` | verified — `sha256sum` on local main at `faa767f` |
| `mode` | `dry_run_receipt_preview` | verified |
| `effect_enabled` | `false` | verified |
| `workspace_write_enabled` | `false` | verified |
| `executor_required` | `false` | verified |

---

## Memory-mesh scope mirror contract (Lane G)

| Field | Value | Verification state |
|---|---|---|
| Repo | `SocioProphet/memory-mesh` | verified |
| Path | `contracts/prophet-mesh/prophet-mesh-memory-scope.v0.1.json` | verified |
| Schema version | `memory-mesh.cross-repo-scope-mirror.v0.1` | verified |
| `scopePolicy.enforcement` | `reject_if_absent_or_empty` | verified |
| `effectBoundary.effectEnabled` | `false` | verified |
| `nonProductionBoundary.coveredModes` | `dry_run_receipt_preview`, `receipt_only` | verified |
| `crossRepoTraceability.prophetMeshAdapterRef.contentSha256` | `38a3edb62813521a...` (64-char) | verified — matches agentplane adapter pin |
| Validator | `scripts/validate-prophet-mesh-scope-mirror.mjs` | **verified passing** |
| CI gate | `.github/workflows/prophet-mesh-scope-mirror.yml` | **pending** — [memory-mesh PR #39](https://github.com/SocioProphet/memory-mesh/pull/39) |
| `make validate` inclusion | `validate-prophet-mesh-scope-mirror` wired in | **pending** — [memory-mesh PR #39](https://github.com/SocioProphet/memory-mesh/pull/39) |

---

## prophet-platform Health-AI demo readiness

| Item | State |
|---|---|
| `HealthAIDemoReadinessCard.vue` | **verified present** |
| `make validate-health-ai-demo-readiness` | **verified passing** |
| FogStack/SVF/Workroom P2 fixture-backed runtime parity evidence | **verified complete** |
| Lane F (live nonprod controller observations) | **unverified** — out of scope, requires explicit approval |

---

## Lane B — stray fixture finding

**Artifact**: `SocioProphet/agentplane` `tests/fixtures/receipts/integrity-evidence-result.valid.json`

**Finding**: Fixture used `docs/example.md` while `safe_root="repo"` requires the `repo/` prefix. This caused `test_valid_integrity_evidence_records_validate` to fail.

**Resolution**: Fixed in [agentplane PR #275](https://github.com/SocioProphet/agentplane/pull/275), merged. 114/114 tests now pass.

---

## Non-production claim boundaries

| Non-claim | Reason |
|---|---|
| Production deployment readiness | Spine is private-preview only; no customer data, no live services |
| Regulatory certification | No formal certification process has been run |
| Memory scope access beyond approved scopes | Validator enforces forbidden-scope rejection |
| External action without human approval | `email_reply` and `operations_plan` locked to `awaiting_approval` |
| Model availability as authorization | Authorization governed by policy gates independently of model availability |
| superconscious future runtime actions without approval | `TRUST_SURFACE.yaml` declares `approval_required_for_future_runtime_actions`; spine §4.6 mirrors the invariant |

---

## Lane completion state

| Lane | Item | State |
|---|---|---|
| Lane A | agentplane adapter back-ref in runtime release bundle | **Complete** — merged to prophet-mesh main (`9431a9a`) |
| Lane B | agentplane stray fixture | **Complete** — [agentplane PR #275](https://github.com/SocioProphet/agentplane/pull/275) merged |
| Lane C | Private-preview runbook (`docs/private-preview-spine.md`) | **Complete** — merged to prophet-mesh main (`9431a9a`) |
| Lane D | Cross-repo ledger (this document) | **Complete** — merged to prophet-mesh main (`9431a9a`) |
| Lane G | `prophet-mesh-memory-scope.v0.1.json` mirror in `memory-mesh` | **Complete** — contract + validator in main; CI gate [memory-mesh PR #39](https://github.com/SocioProphet/memory-mesh/pull/39) pending merge |
| Lane E | Health-AI demo packaging | Logged, not started |
| Lane F | Live nonprod controller observations | Out of scope — requires explicit approval |

---

*Cross-reference: [`docs/private-preview-spine.md`](private-preview-spine.md)*
