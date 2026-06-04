"""Swarm lifecycle semantics for Prophet Mesh."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable

LIFECYCLE: tuple[str, ...] = (
    "Draft",
    "Bound",
    "Built",
    "Attested",
    "Deployed",
    "Serving",
    "Degraded",
    "Retired",
)

_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "Draft": {"Bound"},
    "Bound": {"Built", "Retired"},
    "Built": {"Attested", "Retired"},
    "Attested": {"Deployed", "Retired"},
    "Deployed": {"Serving", "Degraded", "Retired"},
    "Serving": {"Degraded", "Retired"},
    "Degraded": {"Serving", "Retired"},
    "Retired": set(),
}


class LifecycleTransitionError(ValueError):
    """Raised when an invalid lifecycle transition is requested."""


@dataclass(frozen=True)
class EvidenceEvent:
    """Evidence emitted during a lifecycle transition."""

    principal: str
    motive: str
    from_state: str
    to_state: str
    attestation: str
    occurred_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def proof_tuple(self) -> tuple[str, str, str, str, str, str]:
        return (
            self.principal,
            "lifecycle.transition",
            f"{self.from_state}->{self.to_state}",
            "prophet-mesh",
            self.occurred_at,
            self.motive,
        )


@dataclass
class Lifecycle:
    """State machine with evidence-emitting transitions."""

    state: str = "Draft"
    events: list[EvidenceEvent] = field(default_factory=list)

    def transition(
        self,
        to_state: str,
        *,
        principal: str,
        motive: str,
        attestation: str,
    ) -> EvidenceEvent:
        if self.state not in LIFECYCLE:
            raise LifecycleTransitionError(f"unknown current state: {self.state}")
        if to_state not in LIFECYCLE:
            raise LifecycleTransitionError(f"unknown target state: {to_state}")
        if to_state not in _ALLOWED_TRANSITIONS[self.state]:
            raise LifecycleTransitionError(f"invalid transition: {self.state} -> {to_state}")
        event = EvidenceEvent(
            principal=principal,
            motive=motive,
            from_state=self.state,
            to_state=to_state,
            attestation=attestation,
        )
        self.state = to_state
        self.events.append(event)
        return event

    def walk(
        self,
        path: Iterable[str],
        *,
        principal: str,
        motive: str,
        attestation: str,
    ) -> list[EvidenceEvent]:
        return [
            self.transition(target, principal=principal, motive=motive, attestation=attestation)
            for target in path
        ]
