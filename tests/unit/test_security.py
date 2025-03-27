"""Tests for the security module."""

import pytest
from unittest.mock import patch

from k8s_mcp_server.security import (
    DANGEROUS_COMMANDS,
    SAFE_PATTERNS,
    ValidationRule,
    is_safe_exec_command,
    validate_command,
    validate_k8s_command,
    validate_pipe_command,
)


def test_validation_rule_class():
    """Test the ValidationRule dataclass."""
    # Create a validation rule instance
    rule = ValidationRule(
        pattern="kubectl get",
        description="Get Kubernetes resources",
        error_message="Invalid get command",
    )
    
    # Check the attributes
    assert rule.pattern == "kubectl get"
    assert rule.description == "Get Kubernetes resources"
    assert rule.error_message == "Invalid get command"


def test_is_safe_exec_command_edge_cases():
    """Test is_safe_exec_command with edge cases."""
    # Edge case: empty command
    assert is_safe_exec_command("") is True  # Not an exec command

    # Edge case: exec with quotes
    assert is_safe_exec_command("kubectl exec pod-name -- 'echo hello'") is True

    # Edge case: exec with double quotes
    assert is_safe_exec_command('kubectl exec pod-name -- "echo hello"') is True

    # Edge case: exec with various shells
    assert is_safe_exec_command("kubectl exec pod-name -- csh") is False
    assert is_safe_exec_command("kubectl exec pod-name -- ksh") is False
    assert is_safe_exec_command("kubectl exec pod-name -- zsh") is False

    # Edge case: exec with full paths
    assert is_safe_exec_command("kubectl exec pod-name -- /usr/bin/bash") is False
    assert is_safe_exec_command("kubectl exec -it pod-name -- /usr/bin/bash") is True

    # Edge case: exec with complex commands
    assert is_safe_exec_command("kubectl exec pod-name -- bash -c 'for i in {1..5}; do echo $i; done'") is True

    # Edge case: exec with shell but with -c flag
    assert is_safe_exec_command("kubectl exec pod-name -- /bin/bash -c 'ls -la'") is True
    assert is_safe_exec_command("kubectl exec pod-name -- sh -c 'find / -name config'") is True


def test_dangerous_and_safe_commands():
    """Test the DANGEROUS_COMMANDS and SAFE_PATTERNS dictionaries."""
    # Check that all CLI tools in DANGEROUS_COMMANDS have corresponding SAFE_PATTERNS
    for cli_tool in DANGEROUS_COMMANDS:
        assert cli_tool in SAFE_PATTERNS, f"{cli_tool} exists in DANGEROUS_COMMANDS but not in SAFE_PATTERNS"
    
    # Check for specific patterns we expect to be in the dictionaries
    assert "kubectl delete" in DANGEROUS_COMMANDS["kubectl"]
    assert "kubectl exec" in DANGEROUS_COMMANDS["kubectl"]
    assert "kubectl delete pod" in SAFE_PATTERNS["kubectl"]
    assert "kubectl exec -it" in SAFE_PATTERNS["kubectl"]
    
    # Check for Helm dangerous commands
    assert "helm delete" in DANGEROUS_COMMANDS["helm"]
    assert "helm delete --help" in SAFE_PATTERNS["helm"]


def test_validate_k8s_command_edge_cases():
    """Test validate_k8s_command with edge cases."""
    # Commands with exec shells should be checked by is_safe_exec_command
    with pytest.raises(ValueError):
        validate_k8s_command("kubectl exec pod-name -- /bin/bash")

    # But commands with exec and explicit interactive flags should be allowed
    validate_k8s_command("kubectl exec -it pod-name -- /bin/bash")

    # Commands with exec and -c flag should be allowed
    validate_k8s_command("kubectl exec pod-name -- /bin/bash -c 'ls -la'")

    # Command with help should be allowed
    validate_k8s_command("kubectl exec --help")

    # Command with empty string should raise ValueError
    with pytest.raises(ValueError):
        validate_k8s_command("")

    # Check that non-kubectl commands are verified properly
    validate_k8s_command("helm list")
    validate_k8s_command("istioctl version")
    
    # Test dangerous commands
    with pytest.raises(ValueError):
        validate_k8s_command("helm delete")
    
    # Test safe override of dangerous command
    validate_k8s_command("helm delete --help")


def test_validate_pipe_command_edge_cases():
    """Test validate_pipe_command with edge cases."""
    # Pipe command with kubectl exec should still be checked for safety
    with pytest.raises(ValueError):
        validate_pipe_command("kubectl exec pod-name -- /bin/bash | grep root")

    # But pipe command with kubectl exec and -it should be allowed
    validate_pipe_command("kubectl exec -it pod-name -- /bin/bash -c 'ls -la' | grep root")

    # Test pipe commands with missing parts
    with pytest.raises(ValueError):
        validate_pipe_command("| grep root")  # Missing first command

    # Test with empty commands list
    with patch("k8s_mcp_server.security.split_pipe_command", return_value=[]):
        with pytest.raises(ValueError, match="Empty command"):
            validate_pipe_command("kubectl get pods | grep nginx")


def test_validate_command():
    """Test the main validate_command function."""
    # Test with pipe command
    with patch("k8s_mcp_server.security.is_pipe_command", return_value=True):
        with patch("k8s_mcp_server.security.validate_pipe_command") as mock_validate_pipe:
            validate_command("kubectl get pods | grep nginx")
            mock_validate_pipe.assert_called_once_with("kubectl get pods | grep nginx")

    # Test with non-pipe command
    with patch("k8s_mcp_server.security.is_pipe_command", return_value=False):
        with patch("k8s_mcp_server.security.validate_k8s_command") as mock_validate_k8s:
            validate_command("kubectl get pods")
            mock_validate_k8s.assert_called_once_with("kubectl get pods")
    
    # Test with actual commands
    validate_command("kubectl get pods")
    validate_command("kubectl get pods | grep nginx")
    
    with pytest.raises(ValueError):
        validate_command("kubectl delete")
        
    with pytest.raises(ValueError):
        validate_command("kubectl exec pod-name -- /bin/bash")
