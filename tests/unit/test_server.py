"""Tests for the server module."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from k8s_mcp_server.cli_executor import (
    AuthenticationError,
    CommandExecutionError,
    CommandTimeoutError,
    CommandValidationError,
)
from k8s_mcp_server.server import (
    describe_argocd,
    describe_helm,
    describe_istioctl,
    describe_kubectl,
    execute_argocd,
    execute_helm,
    execute_istioctl,
    execute_kubectl,
    run_startup_checks,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_describe_kubectl(mock_get_command_help, mock_k8s_cli_status):
    """Test the describe_kubectl tool."""
    # Test with valid command
    result = await describe_kubectl(command="get")

    assert result.help_text == "Mocked help text"
    mock_get_command_help.assert_called_once_with("kubectl", "get")

    # Test without command (general help)
    mock_get_command_help.reset_mock()
    result = await describe_kubectl()

    assert result.help_text == "Mocked help text"
    mock_get_command_help.assert_called_once()

    # Note: Invalid CLI tools are now handled via separate tool functions


@pytest.mark.asyncio
async def test_describe_kubectl_with_context(mock_get_command_help, mock_k8s_cli_status):
    """Test the describe_kubectl tool with context."""
    # Create a mock context
    mock_context = AsyncMock()

    # Test with valid command
    result = await describe_kubectl(command="get", ctx=mock_context)

    assert hasattr(result, "help_text")
    mock_get_command_help.assert_called_once_with("kubectl", "get")
    mock_context.info.assert_called_once()


@pytest.mark.asyncio
async def test_describe_kubectl_with_error(mock_k8s_cli_status):
    """Test the describe_kubectl tool when get_command_help raises an error."""
    # Create a mock that raises an exception
    error_mock = AsyncMock(side_effect=Exception("Test error"))

    with patch("k8s_mcp_server.server.get_command_help", error_mock):
        result = await describe_kubectl(command="get")

        assert hasattr(result, "help_text")
        assert "Error retrieving" in result.help_text
        assert "Test error" in result.help_text


@pytest.mark.asyncio
async def test_describe_kubectl_tool_not_installed():
    """Test describe_kubectl when kubectl is not installed."""
    # Mock the CLI status dictionary to report kubectl as not installed
    mock_status = {"kubectl": False}
    with patch("k8s_mcp_server.server.cli_status", mock_status):
        # Create a mock context for testing ctx parameter
        mock_context = AsyncMock()

        result = await describe_kubectl(command="get", ctx=mock_context)

        assert "not installed" in result.help_text
        mock_context.error.assert_called_once()


@pytest.mark.asyncio
async def test_execute_kubectl(mock_execute_command, mock_k8s_cli_status):
    """Test the execute_kubectl tool."""
    # Mock the execute_command function for this test specifically
    with patch("k8s_mcp_server.server.execute_command", mock_execute_command):
        # Test with valid command
        result = await execute_kubectl(command="get pods")

        # Since we're using the mock_execute_command, we should get its value
        assert result == mock_execute_command.return_value
        mock_execute_command.assert_called_once()

    # Test with timeout
    mock_execute_command.reset_mock()
    with patch("k8s_mcp_server.server.execute_command", mock_execute_command):
        result = await execute_kubectl(command="get pods", timeout=30)

        # Since we're using the mock_execute_command, we should get its value
        assert result == mock_execute_command.return_value
        mock_execute_command.assert_called_once()

    # Note: Invalid commands are handled by validation at different layer


@pytest.mark.asyncio
async def test_execute_kubectl_with_context(mock_execute_command, mock_k8s_cli_status):
    """Test the execute_kubectl tool with context."""
    # Create a mock context
    mock_context = AsyncMock()

    # Test with valid command
    with patch("k8s_mcp_server.server.execute_command", mock_execute_command):
        result = await execute_kubectl(command="get pods", ctx=mock_context)

        # Since we're using the mock_execute_command, we should get its value
        assert result == mock_execute_command.return_value
        mock_execute_command.assert_called_once()
        mock_context.info.assert_called()

    # Note: Invalid commands are handled by validation at a different layer


@pytest.mark.asyncio
async def test_execute_kubectl_with_validation_error(mock_k8s_cli_status):
    """Test the execute_kubectl tool when validation fails."""
    # Create a mock that raises a validation error
    error_mock = AsyncMock(side_effect=CommandValidationError("Invalid command"))

    with patch("k8s_mcp_server.server.execute_command", error_mock):
        result = await execute_kubectl(command="get pods")

        assert "status" in result
        assert "output" in result
        assert result["status"] == "error"
        assert "Invalid command" in result["output"]
        assert "error" in result
        assert result["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_execute_kubectl_with_execution_error(mock_k8s_cli_status):
    """Test the execute_kubectl tool when execution fails."""
    # Create a mock that raises an execution error
    error_mock = AsyncMock(side_effect=CommandExecutionError("Execution failed"))

    with patch("k8s_mcp_server.server.execute_command", error_mock):
        result = await execute_kubectl(command="get pods")

        assert "status" in result
        assert "output" in result
        assert result["status"] == "error"
        assert "Execution failed" in result["output"]
        assert "error" in result
        assert result["error"]["code"] == "EXECUTION_ERROR"


@pytest.mark.asyncio
async def test_tool_command_preprocessing(mock_execute_command, mock_k8s_cli_status):
    """Test automatic tool prefix addition."""
    with patch("k8s_mcp_server.server.execute_command", mock_execute_command):
        # Test without tool prefix
        await execute_kubectl("get pods")
        called_command = mock_execute_command.call_args[0][0]
        assert called_command.startswith("kubectl")

        # Test with existing prefix
        mock_execute_command.reset_mock()
        await execute_kubectl("kubectl get pods")
        called_command = mock_execute_command.call_args[0][0]
        assert called_command == "kubectl get pods"


def test_server_initialization():
    """Test server startup and prompt registration."""
    from k8s_mcp_server.server import mcp

    # Only verify that the server has been created with the correct name
    assert mcp.name == "K8s MCP Server"
    # Verify the existence of tool functions separately
    from k8s_mcp_server.server import describe_kubectl, execute_kubectl

    assert callable(describe_kubectl)
    assert callable(execute_kubectl)


@pytest.mark.asyncio
async def test_concurrent_command_execution(mock_k8s_cli_status):
    """Test parallel command execution safety."""
    from k8s_mcp_server.server import execute_kubectl

    # Patch execute_command within the server module's scope
    with patch("k8s_mcp_server.server.execute_command", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {"status": "success", "output": "test"}

        async def run_command():
            return await execute_kubectl("get pods")

        # Run 10 concurrent commands
        results = await asyncio.gather(*[run_command() for _ in range(10)])
        assert all(r["status"] == "success" for r in results)
        assert mock_exec.call_count == 10


@pytest.mark.asyncio
async def test_long_running_command(mock_k8s_cli_status):
    """Test timeout handling for near-limit executions."""
    # Patch execute_command within the server module's scope
    with patch("k8s_mcp_server.server.execute_command", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = {"status": "error", "output": "Command timed out after 0.1 seconds"}
        result = await execute_kubectl("get pods", timeout=0.1)
        assert "timed out" in result["output"].lower()
        # Check that the timeout value was passed correctly to the patched function
        mock_exec.assert_called_once_with("kubectl get pods", timeout=0.1)


@pytest.mark.asyncio
async def test_execute_kubectl_with_unexpected_error(mock_k8s_cli_status):
    """Test the execute_kubectl tool when an unexpected error occurs."""
    # Create a mock that raises an unexpected error
    error_mock = AsyncMock(side_effect=Exception("Unexpected error"))

    with patch("k8s_mcp_server.server.execute_command", error_mock):
        result = await execute_kubectl(command="get pods")

        assert "status" in result
        assert "output" in result
        assert result["status"] == "error"
        assert "Unexpected error" in result["output"]


@pytest.mark.asyncio
async def test_execute_tool_command_tool_not_installed():
    """Test _execute_tool_command when the requested tool is not installed."""
    from k8s_mcp_server.server import _execute_tool_command

    # Mock the CLI status dictionary to report tool as not installed
    mock_status = {"kubectl": True, "helm": False}
    with patch("k8s_mcp_server.server.cli_status", mock_status):
        # Create a mock context for testing ctx parameter
        mock_context = AsyncMock()

        result = await _execute_tool_command(tool="helm", command="list", timeout=30, ctx=mock_context)

        assert result["status"] == "error"
        assert "not installed" in result["output"]
        mock_context.error.assert_called_once()


@pytest.mark.asyncio
async def test_execute_tool_command_with_field_info_timeout():
    """Test _execute_tool_command with a FieldInfo timeout parameter."""
    from pydantic import Field

    from k8s_mcp_server.server import _execute_tool_command

    # Create a Field object for timeout parameter
    timeout_field = Field(default=None)

    # Mock CLI status and execute_command
    with patch("k8s_mcp_server.server.cli_status", {"kubectl": True}):
        with patch("k8s_mcp_server.server.execute_command", new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"status": "success", "output": "Command succeeded"}

            # Execute with FieldInfo timeout
            await _execute_tool_command(tool="kubectl", command="get pods", timeout=timeout_field, ctx=None)

            # Verify execute_command was called with DEFAULT_TIMEOUT
            from k8s_mcp_server.config import DEFAULT_TIMEOUT

            mock_execute.assert_called_once_with("kubectl get pods", timeout=DEFAULT_TIMEOUT)


@pytest.mark.parametrize(
    "kubectl_installed,other_tools_installed",
    [
        (True, True),  # All tools installed
        (True, False),  # Only kubectl installed
    ],
)
def test_run_startup_checks(kubectl_installed, other_tools_installed):
    """Test run_startup_checks with different installation scenarios."""
    from k8s_mcp_server.config import SUPPORTED_CLI_TOOLS

    def mock_check_cli_installed_factory(kubectl_status, other_status):
        """Create a mock for check_cli_installed."""

        async def mock_check_cli_installed(cli_tool):
            if cli_tool == "kubectl":
                return kubectl_status
            return other_status

        return mock_check_cli_installed

    mock_check = mock_check_cli_installed_factory(kubectl_installed, other_tools_installed)

    with patch("k8s_mcp_server.server.check_cli_installed", new=AsyncMock(side_effect=mock_check)):
        with patch("k8s_mcp_server.server.logger") as mock_logger:
            # Run the function
            result = run_startup_checks()

            # Verify the result
            assert "kubectl" in result
            assert result["kubectl"] == kubectl_installed

            # Check all other tools are in the result
            for tool in SUPPORTED_CLI_TOOLS:
                assert tool in result
                if tool == "kubectl":
                    assert result[tool] == kubectl_installed
                else:
                    assert result[tool] == other_tools_installed

            # Verify logging
            if kubectl_installed:
                mock_logger.info.assert_any_call("kubectl is installed and available")
            else:
                mock_logger.warning.assert_any_call("kubectl is not installed or not in PATH")


def test_run_startup_checks_kubectl_missing():
    """Test run_startup_checks when kubectl is not installed."""

    async def mock_check_cli_installed(cli_tool):
        return False  # All tools missing

    with patch("k8s_mcp_server.server.check_cli_installed", new=AsyncMock(side_effect=mock_check_cli_installed)):
        with patch("k8s_mcp_server.server.sys.exit") as mock_exit:
            # Run the function
            run_startup_checks()

            # Verify sys.exit was called
            mock_exit.assert_called_once_with(1)


# Tests for execute_kubectl_auth_error
@pytest.mark.asyncio
async def test_execute_kubectl_auth_error():
    """Test the execute_kubectl tool with an authentication error."""
    # Mock CLI status
    with patch("k8s_mcp_server.server.cli_status", {"kubectl": True}):
        # Mock an authentication error
        with patch("k8s_mcp_server.server.execute_command", new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = AuthenticationError("Authentication error", {"command": "kubectl get pods"})

            # Test with auth error
            result = await execute_kubectl(command="get pods")

            assert result["status"] == "error"
            assert "Authentication error" in result["error"]["message"]
            assert result["error"]["code"] == "AUTH_ERROR"
            assert "command" in result["error"]["details"]

            # The default timeout is 300
            mock_execute.assert_called_once_with("kubectl get pods", timeout=300)


# Tests for describe_helm
@pytest.mark.asyncio
async def test_describe_helm():
    """Test the describe_helm tool."""
    # Mock CLI status
    with patch("k8s_mcp_server.server.cli_status", {"helm": True}):
        # Test with valid command
        from k8s_mcp_server.tools import CommandHelpResult

        with patch("k8s_mcp_server.server.get_command_help", new_callable=AsyncMock) as mock_help:
            mock_help.return_value = CommandHelpResult(help_text="Helm help text", status="success")

            result = await describe_helm(command="list")

            assert result.help_text == "Helm help text"
            mock_help.assert_called_once_with("helm", "list")

            # We'll skip testing the default parameter case (when command=None)
            # since the Field() object makes it complex to mock correctly


@pytest.mark.asyncio
async def test_describe_helm_with_context():
    """Test the describe_helm tool with context."""
    # Mock CLI status
    with patch("k8s_mcp_server.server.cli_status", {"helm": True}):
        # Create a mock context
        mock_context = AsyncMock()

        # Test with valid command
        with patch("k8s_mcp_server.server.get_command_help", new_callable=AsyncMock) as mock_help:
            mock_help.return_value = {"status": "success", "help_text": "Helm help text"}

            result = await describe_helm(command="list", ctx=mock_context)

            assert hasattr(result, "help_text")
            mock_help.assert_called_once_with("helm", "list")
            mock_context.info.assert_called_once()


@pytest.mark.asyncio
async def test_describe_helm_not_installed():
    """Test the describe_helm tool when helm is not installed."""
    # Mock CLI status to simulate helm not installed
    with patch("k8s_mcp_server.server.cli_status", {"helm": False}):
        # Test with helm not installed
        result = await describe_helm(command="list")

        assert result.status == "error"
        assert "not installed" in result.help_text


# Tests for execute_helm
@pytest.mark.asyncio
async def test_execute_helm():
    """Test the execute_helm tool."""
    # Mock CLI status
    with patch("k8s_mcp_server.server.cli_status", {"helm": True}):
        with patch("k8s_mcp_server.server.execute_command", new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"status": "success", "output": "Chart list", "execution_time": 0.5}

            # Test with basic command
            result = await execute_helm(command="list")

            assert result["status"] == "success"
            assert result["output"] == "Chart list"
            mock_execute.assert_called_once_with("helm list", timeout=300)

            # Test with command without helm prefix
            mock_execute.reset_mock()
            mock_execute.return_value = {"status": "success", "output": "Chart list", "execution_time": 0.5}

            result = await execute_helm(command="list --all-namespaces")

            assert result["status"] == "success"
            mock_execute.assert_called_once_with("helm list --all-namespaces", timeout=300)


@pytest.mark.asyncio
async def test_execute_helm_not_installed():
    """Test the execute_helm tool when helm is not installed."""
    # Mock CLI status to simulate helm not installed
    with patch("k8s_mcp_server.server.cli_status", {"helm": False}):
        # Test with helm not installed
        result = await execute_helm(command="list")

        assert result["status"] == "error"
        assert "not installed" in result["output"]


@pytest.mark.asyncio
async def test_execute_helm_error():
    """Test the execute_helm tool with an error."""
    # Mock CLI status
    with patch("k8s_mcp_server.server.cli_status", {"helm": True}):
        with patch("k8s_mcp_server.server.execute_command", new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = CommandExecutionError("Execution error", {"command": "helm list"})

            # Test with execution error
            result = await execute_helm(command="list")

            assert result["status"] == "error"
            assert result["error"]["code"] == "EXECUTION_ERROR"
            assert "Execution error" in result["error"]["message"]
            mock_execute.assert_called_once_with("helm list", timeout=300)


@pytest.mark.asyncio
async def test_execute_helm_validation_error():
    """Test the execute_helm tool with a validation error."""
    # Mock CLI status
    with patch("k8s_mcp_server.server.cli_status", {"helm": True}):
        with patch("k8s_mcp_server.server.execute_command", new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = CommandValidationError("Validation error", {"command": "helm list"})

            # Test with validation error
            result = await execute_helm(command="list")

            assert result["status"] == "error"
            assert result["error"]["code"] == "VALIDATION_ERROR"
            assert "Validation error" in result["error"]["message"]
            mock_execute.assert_called_once_with("helm list", timeout=300)


@pytest.mark.asyncio
async def test_execute_helm_timeout():
    """Test the execute_helm tool with a timeout error."""
    # Mock CLI status
    with patch("k8s_mcp_server.server.cli_status", {"helm": True}):
        with patch("k8s_mcp_server.server.execute_command", new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = CommandTimeoutError("Command timed out", {"command": "helm list", "timeout": 30})

            # Test with timeout error
            result = await execute_helm(command="list", timeout=30)

            assert result["status"] == "error"
            assert result["error"]["code"] == "TIMEOUT_ERROR"
            assert "timed out" in result["error"]["message"]
            mock_execute.assert_called_once_with("helm list", timeout=30)


@pytest.mark.asyncio
async def test_execute_helm_auth_error():
    """Test the execute_helm tool with an authentication error."""
    # Mock CLI status
    with patch("k8s_mcp_server.server.cli_status", {"helm": True}):
        with patch("k8s_mcp_server.server.execute_command", new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = AuthenticationError("Authentication error", {"command": "helm list"})

            # Test with auth error
            result = await execute_helm(command="list")

            assert result["status"] == "error"
            assert result["error"]["code"] == "AUTH_ERROR"
            assert "Authentication error" in result["error"]["message"]
            mock_execute.assert_called_once_with("helm list", timeout=300)


# Tests for describe_istioctl
@pytest.mark.asyncio
async def test_describe_istioctl():
    """Test the describe_istioctl tool."""
    # Mock CLI status
    with patch("k8s_mcp_server.server.cli_status", {"istioctl": True}):
        # Test with valid command
        from k8s_mcp_server.tools import CommandHelpResult

        with patch("k8s_mcp_server.server.get_command_help", new_callable=AsyncMock) as mock_help:
            mock_help.return_value = CommandHelpResult(help_text="Istio help text", status="success")

            result = await describe_istioctl(command="analyze")

            assert result.help_text == "Istio help text"
            mock_help.assert_called_once_with("istioctl", "analyze")


@pytest.mark.asyncio
async def test_describe_istioctl_not_installed():
    """Test the describe_istioctl tool when istioctl is not installed."""
    # Mock CLI status to simulate istioctl not installed
    with patch("k8s_mcp_server.server.cli_status", {"istioctl": False}):
        # Test with istioctl not installed
        result = await describe_istioctl(command="analyze")

        assert result.status == "error"
        assert "not installed" in result.help_text


# Tests for execute_istioctl
@pytest.mark.asyncio
async def test_execute_istioctl():
    """Test the execute_istioctl tool."""
    # Mock CLI status
    with patch("k8s_mcp_server.server.cli_status", {"istioctl": True}):
        with patch("k8s_mcp_server.server.execute_command", new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"status": "success", "output": "Istio analyze", "execution_time": 0.5}

            # Test with basic command
            result = await execute_istioctl(command="analyze")

            assert result["status"] == "success"
            assert result["output"] == "Istio analyze"
            mock_execute.assert_called_once_with("istioctl analyze", timeout=300)


@pytest.mark.asyncio
async def test_execute_istioctl_not_installed():
    """Test the execute_istioctl tool when istioctl is not installed."""
    # Mock CLI status to simulate istioctl not installed
    with patch("k8s_mcp_server.server.cli_status", {"istioctl": False}):
        # Test with istioctl not installed
        result = await execute_istioctl(command="analyze")

        assert result["status"] == "error"
        assert "not installed" in result["output"]


# Tests for describe_argocd
@pytest.mark.asyncio
async def test_describe_argocd():
    """Test the describe_argocd tool."""
    # Mock CLI status
    with patch("k8s_mcp_server.server.cli_status", {"argocd": True}):
        # Test with valid command
        from k8s_mcp_server.tools import CommandHelpResult

        with patch("k8s_mcp_server.server.get_command_help", new_callable=AsyncMock) as mock_help:
            mock_help.return_value = CommandHelpResult(help_text="ArgoCD help text", status="success")

            result = await describe_argocd(command="app list")

            assert result.help_text == "ArgoCD help text"
            mock_help.assert_called_once_with("argocd", "app list")


@pytest.mark.asyncio
async def test_describe_argocd_not_installed():
    """Test the describe_argocd tool when argocd is not installed."""
    # Mock CLI status to simulate argocd not installed
    with patch("k8s_mcp_server.server.cli_status", {"argocd": False}):
        # Test with argocd not installed
        result = await describe_argocd(command="app list")

        assert result.status == "error"
        assert "not installed" in result.help_text


# Tests for execute_argocd
@pytest.mark.asyncio
async def test_execute_argocd():
    """Test the execute_argocd tool."""
    # Mock CLI status
    with patch("k8s_mcp_server.server.cli_status", {"argocd": True}):
        with patch("k8s_mcp_server.server.execute_command", new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"status": "success", "output": "ArgoCD app list", "execution_time": 0.5}

            # Test with basic command
            result = await execute_argocd(command="app list")

            assert result["status"] == "success"
            assert result["output"] == "ArgoCD app list"
            mock_execute.assert_called_once_with("argocd app list", timeout=300)


@pytest.mark.asyncio
async def test_execute_argocd_not_installed():
    """Test the execute_argocd tool when argocd is not installed."""
    # Mock CLI status to simulate argocd not installed
    with patch("k8s_mcp_server.server.cli_status", {"argocd": False}):
        # Test with argocd not installed
        result = await execute_argocd(command="app list")

        assert result["status"] == "error"
        assert "not installed" in result["output"]


@pytest.mark.asyncio
async def test_execute_tool_command_with_none_timeout():
    """Test _execute_tool_command with None timeout."""
    from k8s_mcp_server.server import _execute_tool_command

    # Mock CLI status
    with patch("k8s_mcp_server.server.cli_status", {"kubectl": True}):
        with patch("k8s_mcp_server.server.execute_command", new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"status": "success", "output": "Command output"}

            # Test with None timeout
            result = await _execute_tool_command("kubectl", "get pods", None, None)

            assert result["status"] == "success"
            assert result["output"] == "Command output"
            mock_execute.assert_called_once()


@pytest.mark.asyncio
async def test_execute_tool_command_info_logs():
    """Test _execute_tool_command context logging."""
    from k8s_mcp_server.server import _execute_tool_command

    # Mock CLI status
    with patch("k8s_mcp_server.server.cli_status", {"kubectl": True}):
        with patch("k8s_mcp_server.server.execute_command", new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"status": "success", "output": "Command output"}

            # Create mock context
            mock_ctx = AsyncMock()

            # Test with piped command
            await _execute_tool_command("kubectl", "get pods | grep nginx", 30, mock_ctx)

            # Verify context info was called for the pipe command
            assert mock_ctx.info.call_count >= 2
            assert any("piped" in str(call) for call in mock_ctx.info.call_args_list)

            # Test with successful command
            mock_ctx.reset_mock()
            await _execute_tool_command("kubectl", "get pods", 30, mock_ctx)

            # Verify context info was called for success
            assert any("executed successfully" in str(call) for call in mock_ctx.info.call_args_list)


@pytest.mark.asyncio
async def test_execute_tool_command_warning_logs():
    """Test _execute_tool_command context warning logging."""
    from k8s_mcp_server.server import _execute_tool_command

    # Mock CLI status
    with patch("k8s_mcp_server.server.cli_status", {"kubectl": True}):
        with patch("k8s_mcp_server.server.execute_command", new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"status": "error", "output": "Command failed"}

            # Create mock context
            mock_ctx = AsyncMock()

            # Test with failed command
            await _execute_tool_command("kubectl", "get pods", 30, mock_ctx)

            # Verify context warning was called
            mock_ctx.warning.assert_called_once()
            assert "failed" in str(mock_ctx.warning.call_args[0][0])


@pytest.mark.asyncio
async def test_execute_tool_command_unexpected_error():
    """Test _execute_tool_command with unexpected error."""
    from k8s_mcp_server.server import _execute_tool_command

    # Mock CLI status
    with patch("k8s_mcp_server.server.cli_status", {"kubectl": True}):
        with patch("k8s_mcp_server.server.execute_command", side_effect=Exception("Unexpected error")):
            # Create mock context
            mock_ctx = AsyncMock()

            # Test with unexpected error
            result = await _execute_tool_command("kubectl", "get pods", 30, mock_ctx)

            # Verify error handling
            assert result["status"] == "error"
            assert "Unexpected error" in result["error"]["message"]
            mock_ctx.error.assert_called_once()
            assert "Unexpected error" in str(mock_ctx.error.call_args[0][0])


@pytest.mark.asyncio
async def test_execute_tool_command_validation_error():
    """Test _execute_tool_command with validation error."""
    from k8s_mcp_server.server import _execute_tool_command

    # Mock CLI status
    with patch("k8s_mcp_server.server.cli_status", {"kubectl": True}):
        with patch("k8s_mcp_server.server.execute_command", side_effect=CommandValidationError("Validation error", {"command": "kubectl invalid"})):
            # Create mock context
            mock_ctx = AsyncMock()

            # Test with validation error
            result = await _execute_tool_command("kubectl", "invalid", 30, mock_ctx)

            # Verify error handling
            assert result["status"] == "error"
            assert "Validation error" in result["error"]["message"]
            mock_ctx.error.assert_called_once()
            assert "Command validation error" in str(mock_ctx.error.call_args[0][0])


@pytest.mark.asyncio
async def test_execute_tool_command_authentication_error():
    """Test _execute_tool_command with authentication error."""
    from k8s_mcp_server.server import _execute_tool_command

    # Mock CLI status
    with patch("k8s_mcp_server.server.cli_status", {"kubectl": True}):
        with patch("k8s_mcp_server.server.execute_command", side_effect=AuthenticationError("Auth error", {"command": "kubectl get pods"})):
            # Create mock context
            mock_ctx = AsyncMock()

            # Test with authentication error
            result = await _execute_tool_command("kubectl", "get pods", 30, mock_ctx)

            # Verify error handling
            assert result["status"] == "error"
            assert "Auth error" in result["error"]["message"]
            mock_ctx.error.assert_called_once()
            assert "Authentication error" in str(mock_ctx.error.call_args[0][0])


@pytest.mark.asyncio
async def test_execute_tool_command_timeout_error():
    """Test _execute_tool_command with timeout error."""
    from k8s_mcp_server.server import _execute_tool_command

    # Mock CLI status
    with patch("k8s_mcp_server.server.cli_status", {"kubectl": True}):
        with patch("k8s_mcp_server.server.execute_command", side_effect=CommandTimeoutError("Timeout error", {"command": "kubectl get pods", "timeout": 30})):
            # Create mock context
            mock_ctx = AsyncMock()

            # Test with timeout error
            result = await _execute_tool_command("kubectl", "get pods", 30, mock_ctx)

            # Verify error handling
            assert result["status"] == "error"
            assert "Timeout error" in result["error"]["message"]
            mock_ctx.error.assert_called_once()
            assert "Command timed out" in str(mock_ctx.error.call_args[0][0])


@pytest.mark.asyncio
async def test_describe_tool_unexpected_error():
    """Test describe_kubectl with an unexpected error."""
    # Mock CLI status
    with patch("k8s_mcp_server.server.cli_status", {"kubectl": True}):
        # Mock command help to raise an unexpected error
        with patch("k8s_mcp_server.server.get_command_help", side_effect=Exception("Unexpected help error")):
            # Mock context
            mock_ctx = AsyncMock()
            # Test with unexpected error
            result = await describe_kubectl(command="get", ctx=mock_ctx)

            # Verify error handling
            assert result.status == "error"
            assert "Error retrieving kubectl help" in result.help_text
            assert result.error["code"] == "INTERNAL_ERROR"
            mock_ctx.error.assert_called_once()
            assert "Unexpected error" in str(mock_ctx.error.call_args[0][0])
