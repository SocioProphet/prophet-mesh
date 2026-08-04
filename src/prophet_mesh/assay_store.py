"""Persistent assay store — append-only JSONL, latest-verdict-per-node.

The fleet rollup aggregates real verdicts from here instead of a hardcoded seed. Each
node contributes its current ReasoningAssay; a newer record for the same node
supersedes the old on read (last-writer-wins), matching the append-only,
converge-on-read discipline of pkg_ops. Nodes ingest verdicts via POST /fleet/assay,
which appends here; GET /fleet/rollup folds the log to the current verdict per node.

Path from PROPHET_MESH_ASSAY_STORE (default <repo>/artifacts/runtime/assays.jsonl,
which is gitignored — runtime state, not source).
"""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
_DEFAULT_PATH = _REPO / "artifacts" / "runtime" / "assays.jsonl"


class AssayStore:
    """Append-only JSONL log of per-node assays, folded LWW-by-nodeRef on read."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def record(self, node_ref: str, assay: dict[str, Any]) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        entry = {"nodeRef": node_ref, "recordedAt": datetime.now(UTC).isoformat(), "assay": assay}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
        return entry

    def _entries(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        out: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def current(self) -> dict[str, dict[str, Any]]:
        """Current verdict per node — last append wins (file order == append order)."""
        latest: dict[str, dict[str, Any]] = {}
        for entry in self._entries():
            latest[entry["nodeRef"]] = entry["assay"]
        return latest

    def count(self) -> int:
        return len(self.current())


def default_store() -> AssayStore:
    return AssayStore(os.environ.get("PROPHET_MESH_ASSAY_STORE", str(_DEFAULT_PATH)))
