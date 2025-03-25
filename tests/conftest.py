"""Test fixtures for the K8s MCP Server tests."""

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, patch

import pytest


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
def mock_execute_command():
    """Fixture that mocks the execute_command function."""
    mock = AsyncMock()
    mock.return_value = {"status": "success", "output": "Mocked command output"}
    with patch("k8s_mcp_server.cli_executor.execute_command", mock):
        yield mock


@pytest.fixture
def mock_get_command_help():
    """Fixture that mocks the get_command_help function."""
    mock = AsyncMock()
    mock.return_value = {"help_text": "Mocked help text"}
    with patch("k8s_mcp_server.cli_executor.get_command_help", mock):
        yield mock


@pytest.fixture
def event_loop():
    """Fixture that yields an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
