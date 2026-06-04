"""Prophet Mesh reference package."""

from prophet_mesh.contracts import AgentBlueprint, Capability, TrustKernel
from prophet_mesh.lifecycle import LIFECYCLE, Lifecycle, LifecycleTransitionError

__all__ = [
    "AgentBlueprint",
    "Capability",
    "TrustKernel",
    "LIFECYCLE",
    "Lifecycle",
    "LifecycleTransitionError",
]

__version__ = "0.1.0"
