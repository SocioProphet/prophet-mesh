# Evidence Register Schema v0.1

| Field | Meaning |
|---|---|
| evidence_id | Stable evidence identifier |
| drive_id | Google Drive file/folder ID |
| current_title | Exact current Drive title |
| current_parent_id | Current parent folder ID |
| proposed_path | Non-destructive proposed canonical path |
| artifact_type | PA, AN, SY, LA, OM, RF |
| evidence_grade | E0-E5 |
| device_id | Canonical Device Registry ID |
| actor_provider_id | Canonical Actor Registry ID or UNKNOWN |
| event_time | When the event occurred |
| collection_time | When the artifact was collected |
| source_account | Account/system that produced artifact |
| sha256 | Hash if raw artifact is locally available |
| claim_supported | Exact claim supported by artifact |
| claim_boundary | observed, corroborated, strong_inference, weak_inference, hypothesis, excluded, unknown |
| privilege_flag | none, legal, attorney-client-review-needed |
| supersession_status | active, superseded, correction, duplicate, quarantine |
| source_url | Drive or external source URL |
