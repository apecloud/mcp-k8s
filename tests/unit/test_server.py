"""Tests for the server module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from k8s_mcp_server.cli_executor import CommandExecutionError, CommandValidationError
from k8s_mcp_server.server import describe_command, execute_command


@pytest.mark.unit
@pytest.mark.asyncio
async def test_describe_command(mock_get_command_help, mock_k8s_cli_status):
    """Test the describe_command tool."""
    # Test with valid CLI tool and command
    result = await describe_command(cli_tool="kubectl", command="get")
    
    assert "help_text" in result
    mock_get_command_help.assert_called_once_with("kubectl", "get")
    
    # Test without command (general help)
    mock_get_command_help.reset_mock()
    result = await describe_command(cli_tool="kubectl")
    
    assert "help_text" in result
    mock_get_command_help.assert_called_once_with("kubectl", None)
    
    # Test with invalid CLI tool
    mock_get_command_help.reset_mock()
    result = await describe_command(cli_tool="invalid")
    
    assert "help_text" in result
    assert "Unsupported CLI tool" in result["help_text"]
    mock_get_command_help.assert_not_called()


@pytest.mark.asyncio
async def test_describe_command_with_context(mock_get_command_help, mock_k8s_cli_status):
    """Test the describe_command tool with context."""
    # Create a mock context
    mock_context = AsyncMock()
    
    # Test with valid CLI tool and command
    result = await describe_command(cli_tool="kubectl", command="get", ctx=mock_context)
    
    assert "help_text" in result
    mock_get_command_help.assert_called_once_with("kubectl", "get")
    mock_context.info.assert_called_once()
    
    # Test with invalid CLI tool
    mock_get_command_help.reset_mock()
    mock_context.reset_mock()
    result = await describe_command(cli_tool="invalid", ctx=mock_context)
    
    assert "help_text" in result
    assert "Unsupported CLI tool" in result["help_text"]
    mock_get_command_help.assert_not_called()
    mock_context.error.assert_called_once()


@pytest.mark.asyncio
async def test_describe_command_with_error(mock_k8s_cli_status):
    """Test the describe_command tool when get_command_help raises an error."""
    # Create a mock that raises an exception
    error_mock = AsyncMock(side_effect=Exception("Test error"))
    
    with patch("k8s_mcp_server.server.get_command_help", error_mock):
        result = await describe_command(cli_tool="kubectl", command="get")
        
        assert "help_text" in result
        assert "Error retrieving help" in result["help_text"]
        assert "Test error" in result["help_text"]


@pytest.mark.asyncio
async def test_execute_command(mock_execute_command, mock_k8s_cli_status):
    """Test the execute_command tool."""
    # Test with valid command
    result = await execute_command(command="kubectl get pods")
    
    assert "status" in result
    assert "output" in result
    assert result["status"] == "success"
    mock_execute_command.assert_called_once_with("kubectl get pods", None)
    
    # Test with timeout
    mock_execute_command.reset_mock()
    result = await execute_command(command="kubectl get pods", timeout=30)
    
    assert "status" in result
    assert "output" in result
    assert result["status"] == "success"
    mock_execute_command.assert_called_once_with("kubectl get pods", 30)
    
    # Test with invalid CLI tool
    mock_execute_command.reset_mock()
    result = await execute_command(command="invalid get pods")
    
    assert "status" in result
    assert "output" in result
    assert result["status"] == "error"
    assert "Unsupported CLI tool" in result["output"]
    mock_execute_command.assert_not_called()


@pytest.mark.asyncio
async def test_execute_command_with_context(mock_execute_command, mock_k8s_cli_status):
    """Test the execute_command tool with context."""
    # Create a mock context
    mock_context = AsyncMock()
    
    # Test with valid command
    result = await execute_command(command="kubectl get pods", ctx=mock_context)
    
    assert "status" in result
    assert "output" in result
    assert result["status"] == "success"
    mock_execute_command.assert_called_once_with("kubectl get pods", None)
    mock_context.info.assert_called()
    
    # Test with invalid CLI tool
    mock_execute_command.reset_mock()
    mock_context.reset_mock()
    result = await execute_command(command="invalid get pods", ctx=mock_context)
    
    assert "status" in result
    assert "output" in result
    assert result["status"] == "error"
    assert "Unsupported CLI tool" in result["output"]
    mock_execute_command.assert_not_called()
    mock_context.error.assert_called_once()


@pytest.mark.asyncio
async def test_execute_command_with_validation_error(mock_k8s_cli_status):
    """Test the execute_command tool when validation fails."""
    # Create a mock that raises a validation error
    error_mock = AsyncMock(side_effect=CommandValidationError("Invalid command"))
    
    with patch("k8s_mcp_server.server.execute_command", error_mock):
        result = await execute_command(command="kubectl get pods")
        
        assert "status" in result
        assert "output" in result
        assert result["status"] == "error"
        assert "Command validation error" in result["output"]
        assert "Invalid command" in result["output"]


@pytest.mark.asyncio
async def test_execute_command_with_execution_error(mock_k8s_cli_status):
    """Test the execute_command tool when execution fails."""
    # Create a mock that raises an execution error
    error_mock = AsyncMock(side_effect=CommandExecutionError("Execution failed"))
    
    with patch("k8s_mcp_server.server.execute_command", error_mock):
        result = await execute_command(command="kubectl get pods")
        
        assert "status" in result
        assert "output" in result
        assert result["status"] == "error"
        assert "Command execution error" in result["output"]
        assert "Execution failed" in result["output"]


@pytest.mark.asyncio
async def test_execute_command_with_unexpected_error(mock_k8s_cli_status):
    """Test the execute_command tool when an unexpected error occurs."""
    # Create a mock that raises an unexpected error
    error_mock = AsyncMock(side_effect=Exception("Unexpected error"))
    
    with patch("k8s_mcp_server.server.execute_command", error_mock):
        result = await execute_command(command="kubectl get pods")
        
        assert "status" in result
        assert "output" in result
        assert result["status"] == "error"
        assert "Unexpected error" in result["output"]
