"""Tests for the CLI executor module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from k8s_mcp_server.cli_executor import (
    CommandExecutionError,
    CommandValidationError,
    check_cli_installed,
    execute_command,
    execute_pipe_command,
    get_command_help,
    inject_context_namespace,
    is_auth_error,
    is_safe_exec_command,
    validate_k8s_command,
    validate_pipe_command,
)


def test_is_safe_exec_command():
    """Test the is_safe_exec_command function."""
    # Safe exec commands
    assert is_safe_exec_command("kubectl exec pod-name -- ls") is True
    assert is_safe_exec_command("kubectl exec -it pod-name -- /bin/bash -c 'ls -la'") is True
    assert is_safe_exec_command("kubectl exec pod-name -c container -- echo hello") is True

    # Unsafe exec commands (interactive shells without explicit flags)
    assert is_safe_exec_command("kubectl exec pod-name -- /bin/bash") is False
    assert is_safe_exec_command("kubectl exec pod-name -- sh") is False
    
    # Non-exec commands should always be safe
    assert is_safe_exec_command("kubectl get pods") is True
    assert is_safe_exec_command("kubectl logs pod-name") is True


def test_inject_context_namespace():
    """Test the inject_context_namespace function."""
    # Mock context and namespace settings
    with patch("k8s_mcp_server.cli_executor.K8S_CONTEXT", "test-context"):
        with patch("k8s_mcp_server.cli_executor.K8S_NAMESPACE", "test-namespace"):
            # Basic kubectl command should get both context and namespace
            assert "kubectl --context=test-context --namespace=test-namespace get pods" == inject_context_namespace("kubectl get pods")
            
            # Command with explicit namespace should not get namespace injected
            assert "kubectl --context=test-context get pods -n default" == inject_context_namespace("kubectl get pods -n default")
            
            # Command with explicit context should not get context injected
            assert "kubectl --context=prod get pods --namespace=test-namespace" == inject_context_namespace("kubectl --context=prod get pods")
            
            # Command targeting non-namespaced resources should not get namespace injected
            assert "kubectl --context=test-context get nodes" == inject_context_namespace("kubectl get nodes")
            
            # Non-kubectl commands should not be modified
            assert "helm list" == inject_context_namespace("helm list")
            
            # istioctl should also get context and namespace
            assert "istioctl --context=test-context --namespace=test-namespace analyze" == inject_context_namespace("istioctl analyze")


def test_is_auth_error():
    """Test the is_auth_error function."""
    # Test authentication error detection
    assert is_auth_error("Unable to connect to the server") is True
    assert is_auth_error("Unauthorized") is True
    assert is_auth_error("Error: You must be logged in to the server (Unauthorized)") is True
    assert is_auth_error("Error: Error loading config file") is True
    
    # Test non-authentication errors
    assert is_auth_error("Pod not found") is False
    assert is_auth_error("No resources found") is False


def test_validate_k8s_command():
    """Test the validate_k8s_command function."""
    # Valid commands should not raise exceptions
    validate_k8s_command("kubectl get pods")
    validate_k8s_command("istioctl analyze")
    validate_k8s_command("helm list")
    validate_k8s_command("argocd app list")
    
    # Invalid commands should raise CommandValidationError
    with pytest.raises(CommandValidationError):
        validate_k8s_command("")
    
    with pytest.raises(CommandValidationError):
        validate_k8s_command("invalid command")
    
    with pytest.raises(CommandValidationError):
        validate_k8s_command("kubectl")  # Missing action
    
    # Test dangerous commands
    with pytest.raises(CommandValidationError):
        validate_k8s_command("kubectl delete")  # Global delete
    
    # But specific delete should be allowed
    validate_k8s_command("kubectl delete pod my-pod")


def test_validate_pipe_command():
    """Test the validate_pipe_command function."""
    # Valid pipe commands
    validate_pipe_command("kubectl get pods | grep nginx")
    validate_pipe_command("helm list | grep mysql | wc -l")
    
    # Invalid pipe commands
    with pytest.raises(CommandValidationError):
        validate_pipe_command("")
    
    with pytest.raises(CommandValidationError):
        validate_pipe_command("grep nginx")  # First command must be a K8s CLI tool
    
    with pytest.raises(CommandValidationError):
        validate_pipe_command("kubectl get pods | invalidcommand")  # Invalid second command
    
    with pytest.raises(CommandValidationError):
        validate_pipe_command("kubectl | grep pods")  # Invalid first command (missing action)


@pytest.mark.asyncio
async def test_check_cli_installed():
    """Test the check_cli_installed function."""
    # Test when CLI is installed
    with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock) as mock_subprocess:
        process_mock = AsyncMock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = (b"kubectl version", b"")
        mock_subprocess.return_value = process_mock

        result = await check_cli_installed("kubectl")
        assert result is True

    # Test when CLI is not installed
    with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock) as mock_subprocess:
        process_mock = AsyncMock()
        process_mock.returncode = 1  # Error return code
        process_mock.communicate.return_value = (b"", b"command not found")
        mock_subprocess.return_value = process_mock

        result = await check_cli_installed("kubectl")
        assert result is False

    # Test exception handling
    with patch("asyncio.create_subprocess_shell", side_effect=Exception("Test exception")):
        result = await check_cli_installed("kubectl")
        assert result is False


@pytest.mark.asyncio
async def test_execute_command_success():
    """Test successful command execution."""
    with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock) as mock_subprocess:
        # Mock a successful process
        process_mock = AsyncMock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = (b"Success output", b"")
        mock_subprocess.return_value = process_mock

        # Mock validation function to avoid dependency
        with patch("k8s_mcp_server.cli_executor.validate_k8s_command"):
            with patch("k8s_mcp_server.cli_executor.inject_context_namespace", return_value="kubectl get pods"):
                result = await execute_command("kubectl get pods")

                assert result["status"] == "success"
                assert result["output"] == "Success output"
                mock_subprocess.assert_called_once_with("kubectl get pods", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)


@pytest.mark.asyncio
async def test_execute_command_error():
    """Test command execution error."""
    with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock) as mock_subprocess:
        # Mock a failed process
        process_mock = AsyncMock()
        process_mock.returncode = 1
        process_mock.communicate.return_value = (b"", b"Error message")
        mock_subprocess.return_value = process_mock

        # Mock validation function to avoid dependency
        with patch("k8s_mcp_server.cli_executor.validate_k8s_command"):
            with patch("k8s_mcp_server.cli_executor.inject_context_namespace", return_value="kubectl get pods"):
                result = await execute_command("kubectl get pods")

                assert result["status"] == "error"
                assert result["output"] == "Error message"


@pytest.mark.asyncio
async def test_execute_command_auth_error():
    """Test command execution with authentication error."""
    with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock) as mock_subprocess:
        # Mock a process that returns auth error
        process_mock = AsyncMock()
        process_mock.returncode = 1
        process_mock.communicate.return_value = (b"", b"Unable to connect to the server")
        mock_subprocess.return_value = process_mock

        # Mock validation function to avoid dependency
        with patch("k8s_mcp_server.cli_executor.validate_k8s_command"):
            with patch("k8s_mcp_server.cli_executor.inject_context_namespace", return_value="kubectl get pods"):
                result = await execute_command("kubectl get pods")

                assert result["status"] == "error"
                assert "Authentication error" in result["output"]
                assert "kubeconfig" in result["output"]


@pytest.mark.asyncio
async def test_execute_command_timeout():
    """Test command timeout."""
    with patch("asyncio.create_subprocess_shell", new_callable=AsyncMock) as mock_subprocess:
        # Mock a process that times out
        process_mock = AsyncMock()
        # Use a properly awaitable mock that raises TimeoutError
        communicate_mock = AsyncMock(side_effect=asyncio.TimeoutError())
        process_mock.communicate = communicate_mock
        mock_subprocess.return_value = process_mock

        # Mock a regular function instead of an async one for process.kill
        process_mock.kill = MagicMock()

        # Mock validation function to avoid dependency
        with patch("k8s_mcp_server.cli_executor.validate_k8s_command"):
            with patch("k8s_mcp_server.cli_executor.inject_context_namespace", return_value="kubectl get pods"):
                with pytest.raises(CommandExecutionError) as excinfo:
                    await execute_command("kubectl get pods", timeout=1)

                # Check error message
                assert "Command timed out after 1 seconds" in str(excinfo.value)

                # Verify process was killed
                process_mock.kill.assert_called_once()


@pytest.mark.asyncio
async def test_execute_pipe_command():
    """Test pipe command execution."""
    # Mock the validate and execute functions
    with patch("k8s_mcp_server.cli_executor.validate_pipe_command"):
        with patch("k8s_mcp_server.cli_executor.execute_piped_command", new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"status": "success", "output": "Piped output"}
            
            with patch("k8s_mcp_server.cli_executor.inject_context_namespace", return_value="kubectl get pods --context=test"):
                result = await execute_pipe_command("kubectl get pods | grep nginx")
                
                assert result["status"] == "success"
                assert result["output"] == "Piped output"
                # Check that the modified command was used
                mock_execute.assert_called_once_with("kubectl get pods --context=test | grep nginx", None)


@pytest.mark.asyncio
async def test_get_command_help():
    """Test getting command help."""
    # Mock execute_command to return a successful result
    with patch("k8s_mcp_server.cli_executor.execute_command", new_callable=AsyncMock) as mock_execute:
        mock_execute.return_value = {"status": "success", "output": "Help text"}
        
        result = await get_command_help("kubectl", "get")
        
        assert result["help_text"] == "Help text"
        mock_execute.assert_called_once_with("kubectl get --help")
        
    # Test with validation error
    with patch("k8s_mcp_server.cli_executor.execute_command", side_effect=CommandValidationError("Invalid command")):
        result = await get_command_help("kubectl", "get")
        
        assert "Command validation error" in result["help_text"]
        
    # Test with execution error
    with patch("k8s_mcp_server.cli_executor.execute_command", side_effect=CommandExecutionError("Execution failed")):
        result = await get_command_help("kubectl", "get")
        
        assert "Error retrieving help" in result["help_text"]
        
    # Test with unexpected error
    with patch("k8s_mcp_server.cli_executor.execute_command", side_effect=Exception("Unexpected error")):
        result = await get_command_help("kubectl", "get")
        
        assert "Error retrieving help" in result["help_text"]
