"""Tests for the error handling module."""

from k8s_mcp_server.errors import (
    AuthenticationError,
    CommandExecutionError,
    CommandTimeoutError,
    CommandValidationError,
    K8sMCPError,
    create_error_result,
)


def test_base_error():
    """Test the base error class."""
    error = K8sMCPError("Test error")
    assert str(error) == "Test error"
    assert error.code == "INTERNAL_ERROR"
    assert error.details == {}

    error_with_details = K8sMCPError("Test error", "TEST_CODE", {"key": "value"})
    assert str(error_with_details) == "Test error"
    assert error_with_details.code == "TEST_CODE"
    assert error_with_details.details == {"key": "value"}


def test_command_validation_error():
    """Test the command validation error class."""
    error = CommandValidationError("Invalid command")
    assert str(error) == "Invalid command"
    assert error.code == "VALIDATION_ERROR"
    assert error.details == {}

    error_with_details = CommandValidationError("Invalid command", {"command": "kubectl get pods"})
    assert str(error_with_details) == "Invalid command"
    assert error_with_details.code == "VALIDATION_ERROR"
    assert error_with_details.details == {"command": "kubectl get pods"}


def test_command_execution_error():
    """Test the command execution error class."""
    error = CommandExecutionError("Command failed")
    assert str(error) == "Command failed"
    assert error.code == "EXECUTION_ERROR"
    assert error.details == {}


def test_authentication_error():
    """Test the authentication error class."""
    error = AuthenticationError("Auth failed")
    assert str(error) == "Auth failed"
    assert error.code == "AUTH_ERROR"
    assert error.details == {}


def test_timeout_error():
    """Test the timeout error class."""
    error = CommandTimeoutError("Command timed out")
    assert str(error) == "Command timed out"
    assert error.code == "TIMEOUT_ERROR"
    assert error.details == {}


def test_create_error_result():
    """Test the create_error_result function."""
    error = CommandValidationError("Invalid command", {"command": "kubectl get pods"})
    result = create_error_result(error, command="kubectl get pods", exit_code=1, stderr="Error output")

    assert result["status"] == "error"
    assert result["output"] == "Invalid command"
    assert result["exit_code"] == 1
    assert result["error"]["message"] == "Invalid command"
    assert result["error"]["code"] == "VALIDATION_ERROR"
    assert result["error"]["details"]["command"] == "kubectl get pods"
    assert result["error"]["details"]["exit_code"] == 1
    assert result["error"]["details"]["stderr"] == "Error output"


def test_create_error_result_with_custom_details():
    """Test that custom details from the error are included in the result."""
    error = CommandExecutionError("Command failed", {"custom_key": "custom_value"})
    result = create_error_result(error)

    assert result["status"] == "error"
    assert result["output"] == "Command failed"
    assert result["error"]["message"] == "Command failed"
    assert result["error"]["code"] == "EXECUTION_ERROR"
    assert result["error"]["details"]["custom_key"] == "custom_value"
