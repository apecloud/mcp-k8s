"""Tests for the CLI executor module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from k8s_mcp_server.cli_executor import (
    check_cli_installed,
    execute_command,
    get_command_help,
    inject_context_namespace,
    is_auth_error,
)
from k8s_mcp_server.errors import (
    AuthenticationError,
    CommandExecutionError,
    CommandTimeoutError,
    CommandValidationError,
)
from k8s_mcp_server.security import is_safe_exec_command, validate_k8s_command, validate_pipe_command


def test_is_safe_exec_command():
    """Test the is_safe_exec_command function."""
    # Test basic functionality - detailed edge cases are in test_security.py
    # Safe exec commands
    assert is_safe_exec_command("kubectl exec pod-name -- ls") is True  # Non-shell command
    assert is_safe_exec_command("kubectl exec -it pod-name -- /bin/bash -c 'ls -la'") is True  # Shell with command
    assert is_safe_exec_command("kubectl exec pod-name -c container -- echo hello") is True  # Non-shell command

    # Interactive shells are considered safe if explicitly requested
    assert is_safe_exec_command("kubectl exec -it pod-name -- /bin/bash") is True
    assert is_safe_exec_command("kubectl exec -ti pod-name -- sh") is True

    # Unsafe exec commands - shells without explicit interactive mode or command
    assert is_safe_exec_command("kubectl exec pod-name -- /bin/bash") is False
    assert is_safe_exec_command("kubectl exec pod-name -- sh") is False

    # Help/version commands are always safe
    assert is_safe_exec_command("kubectl exec --help") is True
    assert is_safe_exec_command("kubectl exec -h") is True
    assert is_safe_exec_command("kubectl exec version") is True

    # Non-exec commands should always be safe
    assert is_safe_exec_command("kubectl get pods") is True
    assert is_safe_exec_command("kubectl logs pod-name") is True


@pytest.mark.parametrize(
    "command,expected_contains,not_expected_contains,context,namespace",
    [
        # Basic command injection
        (
            "kubectl get pods",
            ["kubectl", "--context=test-context", "--namespace=test-namespace", "get", "pods"],
            [],
            "test-context",
            "test-namespace",
        ),
        # Command with explicit namespace
        (
            "kubectl get pods -n default",
            ["kubectl", "--context=test-context", "get", "pods", "-n", "default"],
            ["--namespace=test-namespace"],
            "test-context",
            "test-namespace",
        ),
        # Command with explicit context
        (
            "kubectl --context=prod get pods",
            ["kubectl", "--context=prod", "--namespace=test-namespace", "get", "pods"],
            ["--context=test-context"],
            "test-context",
            "test-namespace",
        ),
        # Command with all namespaces flag
        (
            "kubectl get pods -A",
            ["kubectl", "--context=test-context", "get", "pods", "-A"],
            ["--namespace=test-namespace"],
            "test-context",
            "test-namespace",
        ),
        # Command with all namespaces long flag
        (
            "kubectl get pods --all-namespaces",
            ["kubectl", "--context=test-context", "get", "pods", "--all-namespaces"],
            ["--namespace=test-namespace"],
            "test-context",
            "test-namespace",
        ),
        # Non-namespaced resource
        (
            "kubectl get nodes",
            ["kubectl", "--context=test-context", "get", "nodes"],
            ["--namespace=test-namespace"],
            "test-context",
            "test-namespace",
        ),
        # Non-namespaced resource with abbreviation
        (
            "kubectl get ns",
            ["kubectl", "--context=test-context", "get", "ns"],
            ["--namespace=test-namespace"],
            "test-context",
            "test-namespace",
        ),
        # Cluster-scoped command
        (
            "kubectl cluster-info",
            ["kubectl", "--context=test-context", "cluster-info"],
            ["--namespace=test-namespace"],
            "test-context",
            "test-namespace",
        ),
        # API resources command
        (
            "kubectl api-resources",
            ["kubectl", "--context=test-context", "api-resources"],
            ["--namespace=test-namespace"],
            "test-context",
            "test-namespace",
        ),
        # Command with quotes
        (
            'kubectl get pods -l "app=nginx"',
            ["kubectl", "--context=test-context", "--namespace=test-namespace", "get", "pods", "-l"],
            [],
            "test-context",
            "test-namespace",
        ),
        # Non-kubectl command
        (
            "helm list",
            ["helm", "list"],
            ["--context=test-context", "--namespace=test-namespace"],
            "test-context",
            "test-namespace",
        ),
        # istioctl command
        (
            "istioctl analyze",
            ["istioctl", "--context=test-context", "--namespace=test-namespace", "analyze"],
            [],
            "test-context",
            "test-namespace",
        ),
        # Config command (cluster-scoped)
        (
            "kubectl config view",
            ["kubectl", "--context=test-context", "config", "view"],
            ["--namespace=test-namespace"],
            "test-context",
            "test-namespace",
        ),
        # Version command (cluster-scoped)
        (
            "kubectl version",
            ["kubectl", "--context=test-context", "version"],
            ["--namespace=test-namespace"],
            "test-context",
            "test-namespace",
        ),
        # Multi-resource command
        (
            "kubectl get pods,services",
            ["kubectl", "--context=test-context", "--namespace=test-namespace", "get", "pods,services"],
            [],
            "test-context",
            "test-namespace",
        ),
        # Specific resource name
        (
            "kubectl get pod nginx-pod",
            ["kubectl", "--context=test-context", "--namespace=test-namespace", "get", "pod", "nginx-pod"],
            [],
            "test-context",
            "test-namespace",
        ),
    ],
)
def test_inject_context_namespace_parametrized(command, expected_contains, not_expected_contains, context, namespace):
    """Test context and namespace injection with parametrized inputs."""
    with patch("k8s_mcp_server.cli_executor.K8S_CONTEXT", context):
        with patch("k8s_mcp_server.cli_executor.K8S_NAMESPACE", namespace):
            result = inject_context_namespace(command)

            # Check that all expected parts are in the result
            for expected_part in expected_contains:
                assert expected_part in result, f"Expected '{expected_part}' in result: {result}"

            # Check that none of the not expected parts are in the result
            for not_expected_part in not_expected_contains:
                assert not_expected_part not in result, f"Not expected '{not_expected_part}' in result: {result}"


def test_inject_context_namespace_empty_values():
    """Test context and namespace injection with empty values."""
    # Test with empty context
    with patch("k8s_mcp_server.cli_executor.K8S_CONTEXT", ""):
        with patch("k8s_mcp_server.cli_executor.K8S_NAMESPACE", "test-namespace"):
            result = inject_context_namespace("kubectl get pods")
            assert result == "kubectl --namespace=test-namespace get pods"

    # Test with empty namespace
    with patch("k8s_mcp_server.cli_executor.K8S_CONTEXT", "test-context"):
        with patch("k8s_mcp_server.cli_executor.K8S_NAMESPACE", ""):
            result = inject_context_namespace("kubectl get pods")
            assert result == "kubectl --context=test-context get pods"

    # Test with both empty
    with patch("k8s_mcp_server.cli_executor.K8S_CONTEXT", ""):
        with patch("k8s_mcp_server.cli_executor.K8S_NAMESPACE", ""):
            result = inject_context_namespace("kubectl get pods")
            assert result == "kubectl get pods"


def test_inject_context_namespace_error_handling():
    """Test error handling in the context and namespace injection."""
    with patch("k8s_mcp_server.cli_executor.K8S_CONTEXT", "test-context"):
        with patch("k8s_mcp_server.cli_executor.K8S_NAMESPACE", "test-namespace"):
            # Test with invalid command format
            with patch("k8s_mcp_server.cli_executor.logger") as mock_logger:
                command = 'kubectl get pods "unclosed quote'
                result = inject_context_namespace(command)
                mock_logger.warning.assert_called_once()
                assert result == command

            # Test with empty command
            assert inject_context_namespace("") == ""

            # Test with non-kubectl/istioctl command
            assert inject_context_namespace("helm list") == "helm list"

            # Test without shlex.join (Python < 3.8 compatibility)
            with patch("k8s_mcp_server.cli_executor.shlex.join", side_effect=ImportError):
                # Command with spaces that needs quoting
                result = inject_context_namespace("kubectl get pods -l app=my app")
                assert "--context=test-context" in result
                assert "--namespace=test-namespace" in result


def test_is_auth_error():
    """Test the is_auth_error function."""
    # Test authentication error detection
    assert is_auth_error("Unable to connect to the server") is True
    assert is_auth_error("Unauthorized") is True
    assert is_auth_error("Error: You must be logged in to the server (Unauthorized)") is True
    assert is_auth_error("Error: Error loading config file") is True
    assert is_auth_error("forbidden") is True
    assert is_auth_error("Invalid kubeconfig") is True
    assert is_auth_error("Unable to load authentication") is True
    assert is_auth_error("no configuration has been provided") is True
    assert is_auth_error("You must be logged in") is True
    assert is_auth_error("Error: Helm repo") is True

    # Test non-authentication errors
    assert is_auth_error("Pod not found") is False
    assert is_auth_error("No resources found") is False


def test_get_tool_from_command():
    """Test extracting CLI tool from command string."""
    from k8s_mcp_server.cli_executor import get_tool_from_command

    # Test valid commands
    assert get_tool_from_command("kubectl get pods") == "kubectl"
    assert get_tool_from_command("helm list") == "helm"
    assert get_tool_from_command("istioctl analyze") == "istioctl"
    assert get_tool_from_command("argocd app list") == "argocd"

    # Test commands with quotes and options
    assert get_tool_from_command('kubectl get pods -n "my namespace"') == "kubectl"
    assert get_tool_from_command("helm upgrade --install myrelease mychart") == "helm"

    # Test invalid commands
    assert get_tool_from_command("invalid-command arg") is None
    assert get_tool_from_command("") is None


def test_validate_k8s_command():
    """Test the validate_k8s_command function."""
    # Valid commands should not raise exceptions
    validate_k8s_command("kubectl get pods")
    validate_k8s_command("istioctl analyze")
    validate_k8s_command("helm list")
    validate_k8s_command("argocd app list")

    # Invalid commands should raise ValueError
    with pytest.raises(ValueError):
        validate_k8s_command("")

    with pytest.raises(ValueError):
        validate_k8s_command("invalid command")

    with pytest.raises(ValueError):
        validate_k8s_command("kubectl")  # Missing action

    # Test dangerous commands
    with pytest.raises(ValueError):
        validate_k8s_command("kubectl delete")  # Global delete

    # But specific delete should be allowed
    validate_k8s_command("kubectl delete pod my-pod")


def test_validate_pipe_command():
    """Test the validate_pipe_command function."""
    # Valid pipe commands
    validate_pipe_command("kubectl get pods | grep nginx")
    validate_pipe_command("helm list | grep mysql | wc -l")

    # Invalid pipe commands
    with pytest.raises(ValueError):
        validate_pipe_command("")

    with pytest.raises(ValueError):
        validate_pipe_command("grep nginx")  # First command must be a K8s CLI tool

    with pytest.raises(ValueError):
        validate_pipe_command("kubectl get pods | invalidcommand")  # Invalid second command

    with pytest.raises(ValueError):
        validate_pipe_command("kubectl | grep pods")  # Invalid first command (missing action)


@pytest.mark.asyncio
async def test_check_cli_installed():
    """Test the check_cli_installed function."""
    # Test when CLI is installed
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_subprocess:
        process_mock = AsyncMock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = (b"kubectl version", b"")
        mock_subprocess.return_value = process_mock

        result = await check_cli_installed("kubectl")
        assert result is True

    # Test when CLI is not installed
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_subprocess:
        process_mock = AsyncMock()
        process_mock.returncode = 1  # Error return code
        process_mock.communicate.return_value = (b"", b"command not found")
        mock_subprocess.return_value = process_mock

        result = await check_cli_installed("kubectl")
        assert result is False

    # Test exception handling
    with patch("asyncio.create_subprocess_exec", side_effect=Exception("Test exception")):
        result = await check_cli_installed("kubectl")
        assert result is False


@pytest.mark.asyncio
async def test_execute_command_success():
    """Test successful command execution."""
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_subprocess:
        # Mock a successful process
        process_mock = AsyncMock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = (b"Success output", b"")
        mock_subprocess.return_value = process_mock

        # Mock validation function to avoid dependency
        with patch("k8s_mcp_server.cli_executor.validate_command"):
            # Mock context injection
            with patch("k8s_mcp_server.cli_executor.inject_context_namespace", return_value="kubectl get pods"):
                result = await execute_command("kubectl get pods")

                assert result["status"] == "success"
                assert result["output"] == "Success output"
                mock_subprocess.assert_called_once()


@pytest.mark.asyncio
async def test_execute_command_error():
    """Test command execution error."""
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_subprocess:
        # Mock a failed process
        process_mock = AsyncMock()
        process_mock.returncode = 1
        process_mock.communicate.return_value = (b"", b"Error message")
        mock_subprocess.return_value = process_mock

        # Mock validation function to avoid dependency
        with patch("k8s_mcp_server.cli_executor.validate_command"):
            # Mock context injection
            with patch("k8s_mcp_server.cli_executor.inject_context_namespace", return_value="kubectl get pods"):
                with pytest.raises(CommandExecutionError) as exc_info:
                    await execute_command("kubectl get pods")

                assert "Error message" in str(exc_info.value)
                assert exc_info.value.code == "EXECUTION_ERROR"
                assert "command" in exc_info.value.details
                assert exc_info.value.details["command"] == "kubectl get pods"
                assert "exit_code" in exc_info.value.details
                assert exc_info.value.details["exit_code"] == 1


@pytest.mark.asyncio
async def test_execute_command_auth_error():
    """Test command execution with authentication error."""
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_subprocess:
        # Mock a process that returns auth error
        process_mock = AsyncMock()
        process_mock.returncode = 1
        process_mock.communicate.return_value = (b"", b"Unable to connect to the server")
        mock_subprocess.return_value = process_mock

        # Mock validation function to avoid dependency
        with patch("k8s_mcp_server.cli_executor.validate_command"):
            # Mock context injection
            with patch("k8s_mcp_server.cli_executor.inject_context_namespace", return_value="kubectl get pods"):
                with pytest.raises(AuthenticationError) as exc_info:
                    await execute_command("kubectl get pods")

                assert "Authentication error" in str(exc_info.value)
                assert "kubeconfig" in str(exc_info.value)
                assert exc_info.value.code == "AUTH_ERROR"
                assert "command" in exc_info.value.details
                assert exc_info.value.details["command"] == "kubectl get pods"


@pytest.mark.asyncio
async def test_execute_command_auth_error_no_tool():
    """Test authentication error without a recognizable CLI tool."""
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_subprocess:
        # Mock a process that returns auth error
        process_mock = AsyncMock()
        process_mock.returncode = 1
        process_mock.communicate.return_value = (b"", b"Unauthorized")
        mock_subprocess.return_value = process_mock

        with patch("k8s_mcp_server.cli_executor.validate_command"):
            with patch("k8s_mcp_server.cli_executor.inject_context_namespace", return_value="unknown-tool list"):
                with patch("k8s_mcp_server.cli_executor.get_tool_from_command", return_value=None):
                    with pytest.raises(AuthenticationError) as exc_info:
                        await execute_command("unknown-tool list")

                    assert "Authentication error" in str(exc_info.value)
                    assert "Unauthorized" in str(exc_info.value)
                    # Should not have any tool-specific message
                    assert "kubeconfig" not in str(exc_info.value)
                    assert "Please check your" not in str(exc_info.value)
                    assert exc_info.value.code == "AUTH_ERROR"

    # Test auth errors for different CLI tools
    for cli_tool, error_msg in [
        ("helm", "Please check your Helm repository configuration"),
        ("istioctl", "Please check your Istio configuration"),
        ("argocd", "Please check your ArgoCD login status"),
    ]:
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_subprocess:
            # Mock a process that returns auth error
            process_mock = AsyncMock()
            process_mock.returncode = 1
            process_mock.communicate.return_value = (b"", b"Unauthorized")
            mock_subprocess.return_value = process_mock

            # Mock validation and context injection
            with patch("k8s_mcp_server.cli_executor.validate_command"):
                with patch("k8s_mcp_server.cli_executor.inject_context_namespace", return_value=f"{cli_tool} list"):
                    with pytest.raises(AuthenticationError) as exc_info:
                        await execute_command(f"{cli_tool} list")

                    assert "Authentication error" in str(exc_info.value)
                    assert error_msg in str(exc_info.value)
                    assert exc_info.value.code == "AUTH_ERROR"


@pytest.mark.asyncio
async def test_execute_command_timeout():
    """Test command timeout."""
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_subprocess:
        # Mock a process that times out
        process_mock = AsyncMock()
        # Use a properly awaitable mock that raises TimeoutError
        communicate_mock = AsyncMock(side_effect=TimeoutError())
        process_mock.communicate = communicate_mock
        mock_subprocess.return_value = process_mock

        # Mock a regular function instead of an async one for process.kill
        process_mock.kill = MagicMock()

        # Mock validation function to avoid dependency
        with patch("k8s_mcp_server.cli_executor.validate_command"):
            # Mock context injection
            with patch("k8s_mcp_server.cli_executor.inject_context_namespace", return_value="kubectl get pods"):
                with pytest.raises(CommandTimeoutError) as exc_info:
                    await execute_command("kubectl get pods", timeout=1)

                # Check error details
                assert "timed out" in str(exc_info.value).lower()
                assert exc_info.value.code == "TIMEOUT_ERROR"
                assert "command" in exc_info.value.details
                assert exc_info.value.details["command"] == "kubectl get pods"
                assert "timeout" in exc_info.value.details
                assert exc_info.value.details["timeout"] == 1

                # Verify process was killed
                process_mock.kill.assert_called_once()


@pytest.mark.asyncio
async def test_execute_command_with_pipe():
    """Test pipe command execution using execute_command."""
    # Mock the validation and subprocess functions
    with patch("k8s_mcp_server.cli_executor.validate_command"):
        with patch("k8s_mcp_server.cli_executor.is_pipe_command", return_value=True):
            with patch("k8s_mcp_server.cli_executor.split_pipe_command", return_value=["kubectl get pods", "grep nginx"]):
                # Setup process mocks for each command in the pipe
                with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_subprocess:
                    # Create process mocks
                    first_process_mock = AsyncMock()
                    first_process_mock.stdout = AsyncMock()
                    first_process_mock.returncode = 0

                    last_process_mock = AsyncMock()
                    last_process_mock.returncode = 0
                    last_process_mock.communicate = AsyncMock(return_value=(b"Command output", b""))

                    # Configure mock to return different values on different calls
                    mock_subprocess.side_effect = [first_process_mock, last_process_mock]

                    # Mock context injection
                    with patch("k8s_mcp_server.cli_executor.inject_context_namespace", return_value="kubectl get pods --context=test"):
                        # Test with a pipe command
                        result = await execute_command("kubectl get pods | grep nginx")

                        # Verify the result
                        assert result["status"] == "success"
                        assert result["output"] == "Command output"
                        assert "execution_time" in result
                        assert result["exit_code"] == 0

                        # Verify both processes were created
                        assert mock_subprocess.call_count == 2


@pytest.mark.asyncio
async def test_execute_command_with_complex_pipe():
    """Test pipe command execution with multiple pipe stages."""
    # Mock the validation and subprocess functions
    pipe_commands = ["kubectl get pods", "grep nginx", "wc -l"]
    with patch("k8s_mcp_server.cli_executor.validate_command"):
        with patch("k8s_mcp_server.cli_executor.is_pipe_command", return_value=True):
            with patch("k8s_mcp_server.cli_executor.split_pipe_command", return_value=pipe_commands):
                # Setup process mocks for each command in the pipe
                with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_subprocess:
                    # Create process mocks
                    first_process = AsyncMock()
                    first_process.stdout = AsyncMock()
                    first_process.returncode = 0

                    middle_process = AsyncMock()
                    middle_process.stdout = AsyncMock()
                    middle_process.returncode = 0

                    last_process = AsyncMock()
                    last_process.returncode = 0
                    last_process.communicate = AsyncMock(return_value=(b"3", b""))

                    # Configure mock to return different values for each call
                    mock_subprocess.side_effect = [first_process, middle_process, last_process]

                    # Mock context injection
                    with patch("k8s_mcp_server.cli_executor.inject_context_namespace", return_value="kubectl get pods --context=test"):
                        # Test with a pipe command
                        result = await execute_command("kubectl get pods | grep nginx | wc -l")

                        # Verify the result
                        assert result["status"] == "success"
                        assert result["output"] == "3"

                        # Verify all three processes were created
                        assert mock_subprocess.call_count == 3


@pytest.mark.asyncio
async def test_execute_command_output_truncation():
    """Test output truncation when exceeding MAX_OUTPUT_SIZE."""
    large_output = "a" * 150000  # 150KB
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        process_mock = AsyncMock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = (large_output.encode(), b"")
        mock_subprocess.return_value = process_mock

        with patch("k8s_mcp_server.cli_executor.MAX_OUTPUT_SIZE", 100000):
            with patch("k8s_mcp_server.cli_executor.logger") as mock_logger:
                result = await execute_command("kubectl get pods")
                assert "truncated" in result["output"]
                assert len(result["output"]) <= 100000 + len("\n... (output truncated)")
                # Verify logging of output truncation
                mock_logger.info.assert_called_once()
                assert "Output truncated" in mock_logger.info.call_args[0][0]


@pytest.mark.asyncio
async def test_execute_command_output_not_truncated():
    """Test no output truncation when under MAX_OUTPUT_SIZE."""
    output = "a" * 1000  # Small output
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        process_mock = AsyncMock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = (output.encode(), b"")
        mock_subprocess.return_value = process_mock

        with patch("k8s_mcp_server.cli_executor.MAX_OUTPUT_SIZE", 10000):
            with patch("k8s_mcp_server.cli_executor.logger") as mock_logger:
                result = await execute_command("kubectl get pods")
                assert "truncated" not in result["output"]
                assert len(result["output"]) == 1000
                # Verify no logging of output truncation
                mock_logger.info.assert_not_called()


@pytest.mark.asyncio
async def test_execute_command_cancelled():
    """Test handling of CancelledError in execute_command."""
    with patch("k8s_mcp_server.cli_executor.validate_command"):
        with patch("k8s_mcp_server.cli_executor.inject_context_namespace", return_value="kubectl get pods"):
            with patch("asyncio.create_subprocess_exec", side_effect=asyncio.CancelledError()):
                with pytest.raises(asyncio.CancelledError):
                    await execute_command("kubectl get pods")


@pytest.mark.asyncio
async def test_execute_command_process_kill_error():
    """Test handling errors when killing a process during timeout."""
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_subprocess:
        # Mock a process that times out
        process_mock = AsyncMock()
        # Use a properly awaitable mock that raises TimeoutError
        communicate_mock = AsyncMock(side_effect=TimeoutError())
        process_mock.communicate = communicate_mock
        # Mock process.kill to raise an exception
        process_mock.kill = MagicMock(side_effect=Exception("Failed to kill process"))
        mock_subprocess.return_value = process_mock

        # Mock validation function to avoid dependency
        with patch("k8s_mcp_server.cli_executor.validate_command"):
            # Mock context injection
            with patch("k8s_mcp_server.cli_executor.inject_context_namespace", return_value="kubectl get pods"):
                with patch("k8s_mcp_server.cli_executor.logger") as mock_logger:
                    with pytest.raises(CommandTimeoutError) as exc_info:
                        await execute_command("kubectl get pods", timeout=1)

                    # Check error details
                    assert "timed out" in str(exc_info.value).lower()
                    assert exc_info.value.code == "TIMEOUT_ERROR"

                    # Verify error logging when kill fails
                    mock_logger.error.assert_called_once()


@pytest.mark.parametrize(
    "command, expected",
    [
        ("kubectl exec pod -- ls", True),
        ("kubectl exec pod -- /bin/bash", False),  # Should now be blocked
        ("kubectl exec -it pod -- /bin/bash", True),  # Explicit interactive mode is allowed
        ("kubectl exec pod -- /bin/bash -c 'ls'", True),  # With -c flag is allowed
        ("kubectl delete", False),
        ("helm uninstall", False),
    ],
)
def test_security_validation(command, expected):
    """Test security validation edge cases."""
    from k8s_mcp_server.security import validate_command

    if expected:
        validate_command(command)
    else:
        with pytest.raises(ValueError):
            validate_command(command)


@pytest.mark.asyncio
async def test_get_command_help():
    """Test getting command help."""
    # Mock execute_command to return a successful result
    with patch("k8s_mcp_server.cli_executor.execute_command", new_callable=AsyncMock) as mock_execute:
        mock_execute.return_value = {"status": "success", "output": "Help text"}

        result = await get_command_help("kubectl", "get")

        assert result.help_text == "Help text"
        mock_execute.assert_called_once_with("kubectl get --help")

    # Test with general help (no specific command)
    with patch("k8s_mcp_server.cli_executor.execute_command", new_callable=AsyncMock) as mock_execute:
        mock_execute.return_value = {"status": "success", "output": "General help text"}

        result = await get_command_help("kubectl")

        assert result.help_text == "General help text"
        mock_execute.assert_called_once_with("kubectl --help")

    # Test with validation error
    with patch("k8s_mcp_server.cli_executor.execute_command", side_effect=CommandValidationError("Invalid command")):
        result = await get_command_help("kubectl", "get")

        assert "Command validation error" in result.help_text
        assert result.status == "error"
        assert result.error["code"] == "VALIDATION_ERROR"

    # Test with execution error
    with patch("k8s_mcp_server.cli_executor.execute_command", side_effect=CommandExecutionError("Execution failed")):
        result = await get_command_help("kubectl", "get")

        assert "Command execution error" in result.help_text
        assert result.status == "error"
        assert result.error["code"] == "EXECUTION_ERROR"

    # Test with auth error
    from k8s_mcp_server.errors import AuthenticationError

    with patch("k8s_mcp_server.cli_executor.execute_command", side_effect=AuthenticationError("Auth failed")):
        result = await get_command_help("kubectl", "get")

        assert "Authentication error" in result.help_text
        assert result.status == "error"
        assert result.error["code"] == "AUTH_ERROR"

    # Test with timeout error
    from k8s_mcp_server.errors import CommandTimeoutError

    with patch("k8s_mcp_server.cli_executor.execute_command", side_effect=CommandTimeoutError("Command timed out")):
        result = await get_command_help("kubectl", "get")

        assert "Command timed out" in result.help_text
        assert result.status == "error"
        assert result.error["code"] == "TIMEOUT_ERROR"

    # Test with unexpected error
    with patch("k8s_mcp_server.cli_executor.execute_command", side_effect=Exception("Unexpected error")):
        result = await get_command_help("kubectl", "get")

        assert "Error retrieving help" in result.help_text
        assert result.status == "error"
        assert result.error["code"] == "INTERNAL_ERROR"

    # Test with unsupported CLI tool
    result = await get_command_help("unsupported_tool", "get")
    assert "Unsupported CLI tool" in result.help_text
    assert result.status == "error"

    # Test different CLI tools
    for cli_tool in ["helm", "istioctl", "argocd"]:
        with patch("k8s_mcp_server.cli_executor.execute_command", new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"status": "success", "output": f"{cli_tool} help text"}

            result = await get_command_help(cli_tool, "list")

            assert result.help_text == f"{cli_tool} help text"
            mock_execute.assert_called_once_with(f"{cli_tool} list --help")
