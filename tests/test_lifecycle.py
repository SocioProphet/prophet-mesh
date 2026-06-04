import pytest

from prophet_mesh.lifecycle import LIFECYCLE, Lifecycle, LifecycleTransitionError


def test_canonical_lifecycle_order_is_stable():
    assert LIFECYCLE == (
        "Draft",
        "Bound",
        "Built",
        "Attested",
        "Deployed",
        "Serving",
        "Degraded",
        "Retired",
    )


def test_lifecycle_transitions_emit_evidence():
    lifecycle = Lifecycle()
    event = lifecycle.transition(
        "Bound",
        principal="principal:socioprophet",
        motive="instantiate Michael Agent as Prophet Mesh",
        attestation="sha256:test",
    )
    assert lifecycle.state == "Bound"
    assert event.proof_tuple()[0] == "principal:socioprophet"
    assert event.proof_tuple()[1] == "lifecycle.transition"


def test_invalid_transition_is_rejected():
    lifecycle = Lifecycle()
    with pytest.raises(LifecycleTransitionError):
        lifecycle.transition(
            "Serving",
            principal="principal:socioprophet",
            motive="skip governance",
            attestation="none",
        )
