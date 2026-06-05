from pathlib import Path

from prophet_mesh.router import validate_router_interface_file


def test_model_router_interface_spec_is_valid():
    result = validate_router_interface_file(Path("specs/model-router-interface.yaml"))
    assert result.valid, result.errors
