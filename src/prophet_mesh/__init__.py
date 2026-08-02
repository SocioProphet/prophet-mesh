"""Prophet Mesh reference package."""

from prophet_mesh.contracts import AgentBlueprint, Capability, TrustKernel
from prophet_mesh.lifecycle import LIFECYCLE, Lifecycle, LifecycleTransitionError

__all__ = [
    "LIFECYCLE",
    "AgentBlueprint",
    "Capability",
    "Lifecycle",
    "LifecycleTransitionError",
    "TrustKernel",
]

__version__ = "0.1.0"
