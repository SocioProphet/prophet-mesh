from pathlib import Path

from prophet_mesh.contracts import AgentBlueprint


def test_michael_blueprint_is_valid():
    blueprint = AgentBlueprint.from_yaml(Path("blueprints/michael-agent.yaml"))
    assert blueprint.name == "michael-agent"
    assert blueprint.is_valid(), blueprint.validate()


def test_premium_blueprint_inherits_trust_kernel():
    blueprint = AgentBlueprint.from_yaml(Path("blueprints/premium-custom-agent.yaml"))
    assert blueprint.edition == "premium-custom-agent"
    assert blueprint.is_valid(), blueprint.validate()
    assert blueprint.premium_customization["customer_surface"] == "customizable"
