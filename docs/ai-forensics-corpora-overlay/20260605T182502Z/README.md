# AI Forensics Corpora Manifest Seed v0.2

Status: additive repo-side manifest seed. This file does not move, rename, delete, or edit Google Drive artifacts.

Purpose:
- Convert the current evidence-package discussion into structured manifest rows.
- Preserve claim boundaries.
- Register unresolved device and timeline reconciliation items before any Drive cleanup.
- Keep Prophet Mesh integration aligned with the AI Forensics Corpora no-overwrite doctrine.

Upstream Drive folder:
- AI Forensics Corpora
- Drive folder ID: 1IbGcAYOTB-dUOnwG7P8H1rLWsmf6gABP

Primary rule:
No artifact is promoted to exploit evidence without an explicit chain:
artifact -> observed behavior -> known advisory/CVE/TTP or documented platform mechanism -> confidence boundary.
