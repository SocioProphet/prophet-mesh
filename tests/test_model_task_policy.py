from pathlib import Path

from prophet_mesh.model_policy import validate_model_task_policy_file


def test_model_task_policy_validates():
    result = validate_model_task_policy_file(Path("specs/model-task-policy.yaml"))
    assert result.valid, result.errors
