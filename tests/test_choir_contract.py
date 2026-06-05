from pathlib import Path

from prophet_mesh.choir import validate_choir_spec_file


def test_agent_choir_spec_is_valid():
    result = validate_choir_spec_file(Path("specs/agent-choir.yaml"))
    assert result.valid, result.errors
