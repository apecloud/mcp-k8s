"""Tests for tool-specific functions in the server module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from k8s_mcp_server.cli_executor import CommandExecutionError, CommandValidationError
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
    
    assert "help_text" in result
    mock_get_command_help.assert_called_once_with("kubectl", "get")
    
    # Test without command (general help)
    mock_get_command_help.reset_mock()
    result = await describe_kubectl()
    
    assert "help_text" in result
    mock_get_command_help.assert_called_once_with("kubectl", None)


@pytest.mark.asyncio
async def test_describe_kubectl_with_context(mock_get_command_help, mock_k8s_cli_status):
    """Test the describe_kubectl tool with context."""
    # Create a mock context
    mock_context = AsyncMock()
    
    # Test with valid command
    result = await describe_kubectl(command="get", ctx=mock_context)
    
    assert "help_text" in result
    mock_get_command_help.assert_called_once_with("kubectl", "get")
    mock_context.info.assert_called_once()


@pytest.mark.asyncio
async def test_describe_kubectl_with_error(mock_k8s_cli_status):
    """Test the describe_kubectl tool when get_command_help raises an error."""
    # Create a mock that raises an exception
    error_mock = AsyncMock(side_effect=Exception("Test error"))
    
    with patch("k8s_mcp_server.server.get_command_help", error_mock):
        result = await describe_kubectl(command="get")
        
        assert "help_text" in result
        assert "Error retrieving kubectl help" in result["help_text"]
        assert "Test error" in result["help_text"]


@pytest.mark.asyncio
async def test_describe_helm(mock_get_command_help, mock_k8s_cli_status):
    """Test the describe_helm tool."""
    # Test with valid command
    result = await describe_helm(command="list")
    
    assert "help_text" in result
    mock_get_command_help.assert_called_once_with("helm", "list")


@pytest.mark.asyncio
async def test_describe_istioctl(mock_get_command_help, mock_k8s_cli_status):
    """Test the describe_istioctl tool."""
    # Test with valid command
    result = await describe_istioctl(command="analyze")
    
    assert "help_text" in result
    mock_get_command_help.assert_called_once_with("istioctl", "analyze")


@pytest.mark.asyncio
async def test_describe_argocd(mock_get_command_help, mock_k8s_cli_status):
    """Test the describe_argocd tool."""
    # Test with valid command
    result = await describe_argocd(command="app")
    
    assert "help_text" in result
    mock_get_command_help.assert_called_once_with("argocd", "app")


@pytest.mark.asyncio
async def test_execute_kubectl(mock_execute_command, mock_k8s_cli_status):
    """Test the execute_kubectl tool."""
    # Test with valid command
    result = await execute_kubectl(command="get pods")
    
    assert "status" in result
    assert "output" in result
    assert result["status"] == "success"
    mock_execute_command.assert_called_once_with("kubectl get pods", None)
    
    # Test with command that doesn't start with kubectl
    mock_execute_command.reset_mock()
    result = await execute_kubectl(command="describe pod my-pod")
    
    assert result["status"] == "success"
    mock_execute_command.assert_called_once_with("kubectl describe pod my-pod", None)


@pytest.mark.asyncio
async def test_execute_kubectl_with_context(mock_execute_command, mock_k8s_cli_status):
    """Test the execute_kubectl tool with context."""
    # Create a mock context
    mock_context = AsyncMock()
    
    # Test with valid command
    result = await execute_kubectl(command="get pods", ctx=mock_context)
    
    assert "status" in result
    assert "output" in result
    assert result["status"] == "success"
    mock_execute_command.assert_called_once_with("kubectl get pods", None)
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
        assert "Command validation error" in result["output"]
        assert "Invalid command" in result["output"]


@pytest.mark.asyncio
async def test_execute_helm(mock_execute_command, mock_k8s_cli_status):
    """Test the execute_helm tool."""
    # Test with valid command
    result = await execute_helm(command="list")
    
    assert "status" in result
    assert "output" in result
    assert result["status"] == "success"
    mock_execute_command.assert_called_once_with("helm list", None)


@pytest.mark.asyncio
async def test_execute_istioctl(mock_execute_command, mock_k8s_cli_status):
    """Test the execute_istioctl tool."""
    # Test with valid command
    result = await execute_istioctl(command="analyze")
    
    assert "status" in result
    assert "output" in result
    assert result["status"] == "success"
    mock_execute_command.assert_called_once_with("istioctl analyze", None)


@pytest.mark.asyncio
async def test_execute_argocd(mock_execute_command, mock_k8s_cli_status):
    """Test the execute_argocd tool."""
    # Test with valid command
    result = await execute_argocd(command="app list")
    
    assert "status" in result
    assert "output" in result
    assert result["status"] == "success"
    mock_execute_command.assert_called_once_with("argocd app list", None)