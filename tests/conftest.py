"""Test fixtures for the K8s MCP Server tests."""

from unittest.mock import AsyncMock, patch

import pytest


# Standard mock types for consistent mocking
@pytest.fixture
def standard_async_mock():
    """Create a standard AsyncMock with consistent default settings."""
    return AsyncMock()


@pytest.fixture
def successful_command_mock():
    """Create a mock for a successful command execution."""
    mock = AsyncMock()
    mock.return_value = {"status": "success", "output": "Command executed successfully"}
    return mock


@pytest.fixture
def error_command_mock():
    """Create a mock for a failed command execution."""
    mock = AsyncMock()
    mock.return_value = {"status": "error", "output": "Command execution failed"}
    return mock


@pytest.fixture
def mock_k8s_cli_installed():
    """Fixture that mocks the check_cli_installed function to always return True."""
    with patch("k8s_mcp_server.cli_executor.check_cli_installed", return_value=True):
        yield


@pytest.fixture
def mock_k8s_cli_status():
    """Fixture that mocks the CLI status dictionary to show all tools as installed."""
    status = {"kubectl": True, "istioctl": True, "helm": True, "argocd": True}
    with patch("k8s_mcp_server.server.cli_status", status):
        yield


@pytest.fixture
def mock_k8s_tools(monkeypatch):
    """Mock all K8s CLI tools as installed.

    This provides a single fixture to mock the CLI tool status and related checks.
    """
    # Mock CLI status
    status = {"kubectl": True, "istioctl": True, "helm": True, "argocd": True}
    monkeypatch.setattr("k8s_mcp_server.server.cli_status", status)

    # Mock installed check function
    monkeypatch.setattr("k8s_mcp_server.cli_executor.check_cli_installed", lambda _: True)

    return status


@pytest.fixture
def mock_execute_command():
    """Fixture that mocks the execute_command function."""
    mock = AsyncMock()
    mock.return_value = {"status": "success", "output": "Mocked command output"}
    with patch("k8s_mcp_server.cli_executor.execute_command", mock):
        yield mock


@pytest.fixture
def mock_get_command_help():
    """Fixture that mocks the get_command_help function."""
    from k8s_mcp_server.tools import CommandHelpResult

    mock = AsyncMock()
    mock.return_value = CommandHelpResult(help_text="Mocked help text", status="success")
    with patch("k8s_mcp_server.server.get_command_help", mock):
        yield mock


def mock_command_execution(return_value=None):
    """Create a context manager that mocks command execution."""
    if return_value is None:
        return_value = {"status": "success", "output": "Mocked command output"}

    return patch("k8s_mcp_server.cli_executor.execute_command", new_callable=AsyncMock, return_value=return_value)


# We use the default event_loop fixture provided by pytest-asyncio
# If we need custom loop handling, we can use pytest_asyncio.event_loop_policy fixture instead
# @pytest.fixture
# def event_loop():
#     """Fixture that yields an event loop for async tests."""
#     loop = asyncio.get_event_loop_policy().new_event_loop()
#     yield loop
#     loop.close()
