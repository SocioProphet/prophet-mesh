from pathlib import Path

from prophet_mesh.memory_scope import (
    load_memory_scope_policy,
    validate_memory_scope_policy_file,
    validate_request_memory_scope,
)


def test_memory_scope_policy_validates():
    result = validate_memory_scope_policy_file(Path("specs/memory-scope.yaml"))
    assert result.valid, result.errors


def test_relationship_context_allowed_for_email_reply():
    policy = load_memory_scope_policy(Path("specs/memory-scope.yaml"))
    result = validate_request_memory_scope(
        {"task": "email_reply", "memory_scope": "relationship_context:approved"},
        policy,
    )
    assert result.valid, result.errors


def test_unscoped_memory_is_forbidden():
    policy = load_memory_scope_policy(Path("specs/memory-scope.yaml"))
    result = validate_request_memory_scope({"task": "email_reply", "memory_scope": "unscoped"}, policy)
    assert not result.valid
    assert "forbidden" in " ".join(result.errors)


def test_unknown_memory_scope_is_rejected():
    policy = load_memory_scope_policy(Path("specs/memory-scope.yaml"))
    result = validate_request_memory_scope(
        {"task": "email_reply", "memory_scope": "unknown_context:approved"},
        policy,
    )
    assert not result.valid
    assert "not allowed" in " ".join(result.errors)


def test_relationship_context_not_allowed_for_coding():
    policy = load_memory_scope_policy(Path("specs/memory-scope.yaml"))
    result = validate_request_memory_scope(
        {"task": "coding", "memory_scope": "relationship_context:approved"},
        policy,
    )
    assert not result.valid
    assert "not allowed for task" in " ".join(result.errors)
