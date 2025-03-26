"""Tests for the tools module."""

from k8s_mcp_server.tools import (
    is_pipe_command,
    is_valid_k8s_tool,
    split_pipe_command,
    validate_unix_command,
)


def test_is_valid_k8s_tool():
    """Test the is_valid_k8s_tool function."""
    # Valid tools
    assert is_valid_k8s_tool("kubectl") is True
    assert is_valid_k8s_tool("istioctl") is True
    assert is_valid_k8s_tool("helm") is True
    assert is_valid_k8s_tool("argocd") is True

    # Invalid tools
    assert is_valid_k8s_tool("aws") is False
    assert is_valid_k8s_tool("docker") is False
    assert is_valid_k8s_tool("kubect") is False  # Typo
    assert is_valid_k8s_tool("") is False
    assert is_valid_k8s_tool("KUBECTL") is False  # Case sensitive


def test_validate_unix_command():
    """Test the validate_unix_command function."""
    # Valid Unix commands
    assert validate_unix_command("grep error") is True
    assert validate_unix_command("cat file.txt") is True
    assert validate_unix_command("jq .items") is True
    assert validate_unix_command("sort") is True

    # Invalid Unix commands
    assert validate_unix_command("invalidcommand") is False
    assert validate_unix_command("") is False
    assert validate_unix_command("rm -rf /") is True  # Allowed but would be caught by validation later
    assert validate_unix_command("kubectl get pods") is False  # Not a Unix command


def test_is_pipe_command():
    """Test the is_pipe_command function."""
    # Commands with pipes
    assert is_pipe_command("kubectl get pods | grep nginx") is True
    assert is_pipe_command("helm list | grep mysql | wc -l") is True
    assert is_pipe_command("istioctl analyze | grep Warning") is True

    # Commands without pipes
    assert is_pipe_command("kubectl get pods") is False
    assert is_pipe_command("helm list") is False
    assert is_pipe_command("") is False

    # Commands with quoted pipes (should not be detected as pipe commands)
    assert is_pipe_command("kubectl describe pod 'nginx|app'") is False
    assert is_pipe_command('echo "This | is not a pipe"') is False


def test_split_pipe_command():
    """Test the split_pipe_command function."""
    # Simple pipe command
    assert split_pipe_command("kubectl get pods | grep nginx") == ["kubectl get pods", "grep nginx"]

    # Multiple pipe command
    assert split_pipe_command("kubectl get pods | grep nginx | wc -l") == ["kubectl get pods", "grep nginx", "wc -l"]

    # Command with quotes
    assert split_pipe_command("kubectl get pods -l 'app=nginx' | grep Running") == [
        "kubectl get pods -l 'app=nginx'",
        "grep Running",
    ]

    # Command with no pipes
    assert split_pipe_command("kubectl get pods") == ["kubectl get pods"]

    # Empty command
    assert split_pipe_command("") == [""]

    # Complex command with nested quotes
    complex_cmd = 'kubectl get pods -o jsonpath="{.items[*].metadata.name}" | grep "^nginx-" | sort'
    expected = ['kubectl get pods -o jsonpath="{.items[*].metadata.name}"', 'grep "^nginx-"', "sort"]
    assert split_pipe_command(complex_cmd) == expected
