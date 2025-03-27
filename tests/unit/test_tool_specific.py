"""Tests for tool-specific functions in the server module."""

from unittest.mock import AsyncMock, patch

import pytest

from k8s_mcp_server.cli_executor import CommandValidationError
from k8s_mcp_server.server import (
    describe_argocd,
    describe_helm,
    describe_istioctl,
    describe_kubectl,
    execute_argocd,
    execute_helm,
    execute_istioctl,
    execute_kubectl,
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


@pytest.mark.asyncio
async def test_describe_kubectl_with_context(mock_get_command_help, mock_k8s_cli_status):
    """Test the describe_kubectl tool with context."""
    # Create a mock context
    mock_context = AsyncMock()

    # Test with valid command
    result = await describe_kubectl(command="get", ctx=mock_context)

    assert result.help_text == "Mocked help text"
    mock_get_command_help.assert_called_once_with("kubectl", "get")
    mock_context.info.assert_called_once()


@pytest.mark.asyncio
async def test_describe_kubectl_with_error(mock_k8s_cli_status):
    """Test the describe_kubectl tool when get_command_help raises an error."""
    # Create a mock that raises an exception
    error_mock = AsyncMock(side_effect=Exception("Test error"))

    with patch("k8s_mcp_server.server.get_command_help", error_mock):
        result = await describe_kubectl(command="get")

        assert "Error retrieving kubectl help" in result.help_text
        assert "Test error" in result.help_text


@pytest.mark.asyncio
async def test_describe_helm(mock_get_command_help, mock_k8s_cli_status):
    """Test the describe_helm tool."""
    # Test with valid command
    result = await describe_helm(command="list")

    assert result.help_text == "Mocked help text"
    mock_get_command_help.assert_called_once_with("helm", "list")


@pytest.mark.asyncio
async def test_describe_istioctl(mock_get_command_help, mock_k8s_cli_status):
    """Test the describe_istioctl tool."""
    # Test with valid command
    result = await describe_istioctl(command="analyze")

    assert result.help_text == "Mocked help text"
    mock_get_command_help.assert_called_once_with("istioctl", "analyze")


@pytest.mark.asyncio
async def test_describe_argocd(mock_get_command_help, mock_k8s_cli_status):
    """Test the describe_argocd tool."""
    # Test with valid command
    result = await describe_argocd(command="app")

    assert result.help_text == "Mocked help text"
    mock_get_command_help.assert_called_once_with("argocd", "app")


@pytest.mark.asyncio
async def test_execute_kubectl(mock_execute_command, mock_k8s_cli_status):
    """Test the execute_kubectl tool."""
    # Test with valid command
    with patch("k8s_mcp_server.server.execute_command", mock_execute_command):
        result = await execute_kubectl(command="get pods")

        assert result == mock_execute_command.return_value
        mock_execute_command.assert_called_once()

    # Test with command that doesn't start with kubectl
    mock_execute_command.reset_mock()
    with patch("k8s_mcp_server.server.execute_command", mock_execute_command):
        result = await execute_kubectl(command="describe pod my-pod")

        assert result == mock_execute_command.return_value
        mock_execute_command.assert_called_once()


@pytest.mark.asyncio
async def test_execute_kubectl_with_context(mock_execute_command, mock_k8s_cli_status):
    """Test the execute_kubectl tool with context."""
    # Create a mock context
    mock_context = AsyncMock()

    # Test with valid command
    with patch("k8s_mcp_server.server.execute_command", mock_execute_command):
        result = await execute_kubectl(command="get pods", ctx=mock_context)

        assert result == mock_execute_command.return_value
        mock_execute_command.assert_called_once()
        mock_context.info.assert_called()


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
async def test_execute_helm(mock_execute_command, mock_k8s_cli_status):
    """Test the execute_helm tool."""
    # Test with valid command
    with patch("k8s_mcp_server.server.execute_command", mock_execute_command):
        result = await execute_helm(command="list")

        assert result == mock_execute_command.return_value
        mock_execute_command.assert_called_once()


@pytest.mark.asyncio
async def test_execute_istioctl(mock_execute_command, mock_k8s_cli_status):
    """Test the execute_istioctl tool."""
    # Test with valid command
    with patch("k8s_mcp_server.server.execute_command", mock_execute_command):
        result = await execute_istioctl(command="analyze")

        assert result == mock_execute_command.return_value
        mock_execute_command.assert_called_once()


@pytest.mark.asyncio
async def test_execute_argocd(mock_execute_command, mock_k8s_cli_status):
    """Test the execute_argocd tool."""
    # Test with valid command
    with patch("k8s_mcp_server.server.execute_command", mock_execute_command):
        result = await execute_argocd(command="app list")

        assert result == mock_execute_command.return_value
        mock_execute_command.assert_called_once()
