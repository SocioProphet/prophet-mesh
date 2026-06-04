"""Core contracts for Prophet Mesh agent blueprints."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REQUIRED_STATE_CHANNELS = frozenset(
    {
        "belief_state",
        "evidence_packet",
        "causal_attribution_delta",
        "counterexample",
        "equation_candidate",
        "human_digital_twin_state",
    }
)

REQUIRED_AU_BUNDLES = frozenset({"state", "cap", "net", "id", "time", "policy"})
REQUIRED_TRUST_INVARIANTS = frozenset(
    {"identity", "policy", "evidence", "attestation", "revocation", "audit"}
)


@dataclass(frozen=True)
class Capability:
    """A named capability exposed by an agent."""

    name: str
    description: str
    evidence_required: bool = True
    policy_gate: str = "default"


@dataclass(frozen=True)
class TrustKernel:
    """The non-negotiable Michael-derived trust kernel."""

    identity: str
    policy: str
    evidence: str
    attestation: str
    revocation: str
    audit: str

    @classmethod
    def default(cls) -> "TrustKernel":
        return cls(
            identity="principal-bound identity and scoped delegation",
            policy="policy checks before capability execution",
            evidence="evidence packet emitted for claims and transitions",
            attestation="signed transition and artifact attestation",
            revocation="short-lived grants with explicit revoke path",
            audit="append-only governance trace",
        )

    def invariant_names(self) -> set[str]:
        return set(REQUIRED_TRUST_INVARIANTS)


@dataclass
class AgentBlueprint:
    """Serializable contract for Michael and premium custom agents."""

    name: str
    archetype: str
    version: str
    principal: str
    motive: str
    edition: str
    state_channels: set[str]
    au_bundles: set[str]
    capabilities: list[Capability] = field(default_factory=list)
    trust_kernel: TrustKernel = field(default_factory=TrustKernel.default)
    premium_customization: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentBlueprint":
        caps = [Capability(**item) for item in data.get("capabilities", [])]
        kernel_data = data.get("trust_kernel") or {}
        kernel = TrustKernel(**kernel_data) if kernel_data else TrustKernel.default()
        return cls(
            name=data["name"],
            archetype=data["archetype"],
            version=str(data["version"]),
            principal=data["principal"],
            motive=data["motive"],
            edition=data.get("edition", "michael-agent"),
            state_channels=set(data.get("state_channels", [])),
            au_bundles=set(data.get("au_bundles", [])),
            capabilities=caps,
            trust_kernel=kernel,
            premium_customization=data.get("premium_customization", {}),
        )

    @classmethod
    def from_yaml(cls, path: str | Path) -> "AgentBlueprint":
        with Path(path).open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        return cls.from_dict(data)

    def validate(self) -> list[str]:
        errors: list[str] = []
        missing_channels = REQUIRED_STATE_CHANNELS - self.state_channels
        missing_bundles = REQUIRED_AU_BUNDLES - self.au_bundles
        if missing_channels:
            missing = ", ".join(sorted(missing_channels))
            errors.append(f"missing required Michael state channels: {missing}")
        if missing_bundles:
            missing = ", ".join(sorted(missing_bundles))
            errors.append(f"missing required AgentUnit bundles: {missing}")
        if not self.capabilities:
            errors.append("at least one capability is required")
        for capability in self.capabilities:
            if not capability.evidence_required:
                errors.append(f"capability {capability.name!r} disables evidence_required")
        if set(REQUIRED_TRUST_INVARIANTS) != self.trust_kernel.invariant_names():
            errors.append("trust kernel invariants were changed")
        return errors

    def is_valid(self) -> bool:
        return not self.validate()
