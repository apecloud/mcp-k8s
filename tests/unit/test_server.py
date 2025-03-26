"""Tests for the server module."""

from unittest.mock import AsyncMock, patch

import pytest

from k8s_mcp_server.cli_executor import CommandExecutionError, CommandValidationError
from k8s_mcp_server.server import describe_kubectl, execute_kubectl


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
        assert "Command validation error" in result["output"]
        assert "Invalid command" in result["output"]


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
        assert "Command execution error" in result["output"]
        assert "Execution failed" in result["output"]


@pytest.mark.asyncio
async def test_tool_command_preprocessing(mock_execute_command, mock_k8s_cli_status):
    """Test automatic tool prefix addition."""
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
    from k8s_mcp_server.server import mcp, SERVER_INFO
    assert mcp.name == "K8s MCP Server"
    assert mcp.version == SERVER_INFO["version"]
    assert len(mcp.prompts) > 0  # Verify prompts registered

@pytest.mark.asyncio
async def test_concurrent_command_execution(mock_execute_command, mock_k8s_cli_status):
    """Test parallel command execution safety."""
    from k8s_mcp_server.server import execute_kubectl
    
    async def run_command():
        return await execute_kubectl("get pods")
    
    # Run 10 concurrent commands
    results = await asyncio.gather(*[run_command() for _ in range(10)])
    assert all(r["status"] == "success" for r in results)

@pytest.mark.asyncio
async def test_long_running_command(mock_execute_command, mock_k8s_cli_status):
    """Test timeout handling for near-limit executions."""
    mock_execute_command.side_effect = asyncio.TimeoutError()
    result = await execute_kubectl("get pods", timeout=0.1)
    assert "timeout" in result["output"].lower()

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
