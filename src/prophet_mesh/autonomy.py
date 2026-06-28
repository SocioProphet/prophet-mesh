"""AI-driven-development autonomy ladder: validation + runtime gate engine.

This is the executable counterpart to ``specs/ai-driven-development.yaml``. It
reframes the Gartner (2018) "Applying AI to the Development Process" autonomy
ladder as the governed Agent Choir, and it does two jobs:

1. ``validate_ai_driven_development`` — structural conformance of the spec,
   matching the other Prophet Mesh validators.
2. ``evaluate_autonomy`` — the fail-closed runtime decision. A choir role
   requests an autonomy level; the engine first caps at the role's declared
   ceiling (authorization), then admits the highest level whose evidence gate
   is satisfied (admission), demoting toward L0 rather than failing open.

Autonomy is never granted once; it is re-admitted per task through the trust
kernel. This module is the single deterministic source of that decision so
Noetica (surface), tritfabric (SHACL promotion) and prophet-platform (runtime
admission) can all defer to one contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REQUIRED_INVARIANTS = frozenset(
    {
        "autonomy_is_governed_not_granted",
        "every_autonomy_level_has_an_explicit_gate",
        "no_trust_kernel_bypass",
        "build_ladder_is_the_platform_stack",
        "work_ladder_is_the_agent_choir",
        "verified_compute_is_a_distinct_arm",
        "evidence_required_scales_with_autonomy",
        "demotion_is_always_available",
    }
)

REQUIRED_LEVELS = ("L0", "L1", "L2", "L3", "L4", "L5")

TRUST_KERNEL_GATE_ORDER = (
    "identity",
    "policy",
    "evidence",
    "attestation",
    "revocation",
    "audit",
)

REQUIRED_LEVEL_FIELDS = frozenset(
    {"level", "label", "description", "choir_roles", "gate", "enforced_at", "evidence_required"}
)

REQUIRED_BUILD_RUNGS = frozenset(
    {"ai_infrastructure", "ai_frameworks", "ai_platforms", "ai_services"}
)

# Evidence tokens that satisfy no gate.
_NO_GATE = frozenset({"none", "", None})


# --------------------------------------------------------------------------- #
# Spec loading + validation
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class AutonomyValidationResult:
    valid: bool
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "errors": self.errors}


def load_ai_driven_development(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("ai-driven-development spec must be a YAML object")
    return data


def _level_rank(level: str) -> int:
    """L0..L5 -> 0..5; -1 if unparseable."""
    try:
        return int(str(level).lstrip("Ll"))
    except (ValueError, TypeError):
        return -1


def validate_ai_driven_development(data: dict[str, Any]) -> AutonomyValidationResult:
    errors: list[str] = []

    if data.get("name") != "prophet-mesh-ai-driven-development":
        errors.append("name must be prophet-mesh-ai-driven-development")
    if data.get("product") != "Prophet Mesh":
        errors.append("product must be Prophet Mesh")

    invariants = data.get("invariants", [])
    if not isinstance(invariants, list):
        errors.append("invariants must be a list")
        invariants = []
    missing_inv = REQUIRED_INVARIANTS - {v for v in invariants if isinstance(v, str)}
    if missing_inv:
        errors.append("missing invariants: " + ", ".join(sorted(missing_inv)))

    # --- build ladder (Gartner left column -> platform stack) ---
    build = data.get("build_ladder", [])
    if not isinstance(build, list) or not build:
        errors.append("build_ladder must be a non-empty list")
        build = []
    build_rungs = {r.get("rung") for r in build if isinstance(r, dict)}
    missing_rungs = REQUIRED_BUILD_RUNGS - build_rungs
    if missing_rungs:
        errors.append("build_ladder missing rungs: " + ", ".join(sorted(missing_rungs)))

    # --- autonomy ladder (Gartner right column -> governed choir) ---
    ladder = data.get("autonomy_ladder", [])
    if not isinstance(ladder, list) or not ladder:
        errors.append("autonomy_ladder must be a non-empty list")
        ladder = []

    seen_levels: list[str] = []
    for index, level in enumerate(ladder):
        if not isinstance(level, dict):
            errors.append(f"autonomy_ladder[{index}] must be an object")
            continue
        missing_fields = REQUIRED_LEVEL_FIELDS - set(level)
        if missing_fields:
            errors.append(
                f"autonomy_ladder[{index}] missing fields: " + ", ".join(sorted(missing_fields))
            )
        name = level.get("level")
        if isinstance(name, str):
            seen_levels.append(name)
        roles = level.get("choir_roles")
        if not isinstance(roles, list):
            errors.append(f"autonomy_ladder[{index}].choir_roles must be a list")
        gate = level.get("gate")
        # Invariant: every level above L0 must declare a real gate.
        if _level_rank(name) >= 1 and (gate in _NO_GATE):
            errors.append(f"autonomy_ladder[{index}] ({name}) above L0 must declare a gate")

    missing_levels = set(REQUIRED_LEVELS) - set(seen_levels)
    if missing_levels:
        errors.append("autonomy_ladder missing levels: " + ", ".join(sorted(missing_levels)))

    # --- governed-autonomy axis (the trust-kernel spine) ---
    axis = data.get("governed_autonomy_axis", {})
    if not isinstance(axis, dict):
        errors.append("governed_autonomy_axis must be an object")
        axis = {}
    order = axis.get("trust_kernel_gate_order", [])
    if list(order) != list(TRUST_KERNEL_GATE_ORDER):
        errors.append(
            "trust_kernel_gate_order must be exactly "
            + " -> ".join(TRUST_KERNEL_GATE_ORDER)
        )

    return AutonomyValidationResult(valid=not errors, errors=errors)


def validate_ai_driven_development_file(path: str | Path) -> AutonomyValidationResult:
    return validate_ai_driven_development(load_ai_driven_development(path))


# --------------------------------------------------------------------------- #
# Runtime autonomy gate engine
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class AutonomyLevel:
    level: str
    label: str
    rank: int
    choir_roles: tuple[str, ...]
    gate: str
    evidence_required: str
    enforced_at: str


@dataclass(frozen=True)
class AutonomyDecision:
    role: str
    requested_level: str
    role_ceiling: str
    granted_level: str
    granted_label: str
    gate: str
    evidence_required: str
    enforced_at: str
    demoted: bool
    reason: str
    trust_kernel_gate_order: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "requested_level": self.requested_level,
            "role_ceiling": self.role_ceiling,
            "granted_level": self.granted_level,
            "granted_label": self.granted_label,
            "gate": self.gate,
            "evidence_required": self.evidence_required,
            "enforced_at": self.enforced_at,
            "demoted": self.demoted,
            "reason": self.reason,
            "trust_kernel_gate_order": list(self.trust_kernel_gate_order),
        }


class AutonomyLadder:
    """In-memory ladder built from the spec, with the gate decision engine."""

    def __init__(self, levels: list[AutonomyLevel]) -> None:
        self._by_rank: dict[int, AutonomyLevel] = {lvl.rank: lvl for lvl in levels}
        if 0 not in self._by_rank:
            raise ValueError("autonomy ladder must define L0 (manual baseline)")

    @classmethod
    def from_spec(cls, data: dict[str, Any]) -> "AutonomyLadder":
        levels: list[AutonomyLevel] = []
        for entry in data.get("autonomy_ladder", []):
            if not isinstance(entry, dict):
                continue
            name = entry.get("level")
            rank = _level_rank(name)
            if rank < 0:
                continue
            roles = entry.get("choir_roles") or []
            levels.append(
                AutonomyLevel(
                    level=str(name),
                    label=str(entry.get("label", "")),
                    rank=rank,
                    choir_roles=tuple(r for r in roles if isinstance(r, str)),
                    gate=str(entry.get("gate", "none")),
                    evidence_required=str(entry.get("evidence_required", "none")),
                    enforced_at=str(entry.get("enforced_at", "")),
                )
            )
        return cls(levels)

    @classmethod
    def from_file(cls, path: str | Path) -> "AutonomyLadder":
        return cls.from_spec(load_ai_driven_development(path))

    def level(self, rank: int) -> AutonomyLevel:
        return self._by_rank[rank]

    def role_ceiling(self, role: str) -> int:
        """Highest rank at which ``role`` is declared in the spec (else L0)."""
        ceiling = 0
        for rank, lvl in self._by_rank.items():
            if role in lvl.choir_roles and rank > ceiling:
                ceiling = rank
        return ceiling

    @staticmethod
    def _evidence_satisfied(level: AutonomyLevel, available: set[str]) -> bool:
        required = level.evidence_required
        return required in _NO_GATE or required in available

    def evaluate(
        self,
        role: str,
        requested_level: str,
        available_evidence: set[str] | None = None,
    ) -> AutonomyDecision:
        """Authorize (role ceiling) then admit (evidence gate), failing closed.

        Returns the highest level <= min(requested, role_ceiling) whose evidence
        gate is satisfied. L0 is always grantable, so a decision always exists.
        """
        available = available_evidence or set()
        requested_rank = _level_rank(requested_level)
        if requested_rank < 0:
            requested_rank = 0
        ceiling = self.role_ceiling(role)
        capped = min(requested_rank, ceiling)

        reasons: list[str] = []
        if requested_rank > ceiling:
            reasons.append(
                f"role {role!r} not authorized above L{ceiling}; capped from L{requested_rank}"
            )

        granted_rank = 0
        for rank in range(capped, -1, -1):
            candidate = self._by_rank.get(rank)
            if candidate is None:
                continue
            if self._evidence_satisfied(candidate, available):
                granted_rank = rank
                break
            reasons.append(
                f"L{rank} gate '{candidate.gate}' needs evidence "
                f"'{candidate.evidence_required}' (absent) -> demote"
            )

        granted = self._by_rank[granted_rank]
        demoted = granted_rank < requested_rank
        if not demoted and not reasons:
            reasons.append(f"granted at requested level {granted.level}")

        return AutonomyDecision(
            role=role,
            requested_level=f"L{requested_rank}",
            role_ceiling=f"L{ceiling}",
            granted_level=granted.level,
            granted_label=granted.label,
            gate=granted.gate,
            evidence_required=granted.evidence_required,
            enforced_at=granted.enforced_at,
            demoted=demoted,
            reason="; ".join(reasons),
            trust_kernel_gate_order=TRUST_KERNEL_GATE_ORDER,
        )


def evaluate_autonomy_file(
    spec_path: str | Path,
    role: str,
    requested_level: str,
    available_evidence: set[str] | None = None,
) -> AutonomyDecision:
    ladder = AutonomyLadder.from_file(spec_path)
    return ladder.evaluate(role, requested_level, available_evidence)
