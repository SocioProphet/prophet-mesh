from pathlib import Path

from prophet_mesh.repo_state import validate_repo_state_file


def test_repo_state_yaml_validates():
    result = validate_repo_state_file(Path("specs/repo-state.yaml"))
    assert result.valid, result.errors
