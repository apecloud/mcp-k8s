"""Tests for the main module."""

import os
from unittest.mock import patch

import pytest


@pytest.mark.unit
def test_main_function():
    """Test the main function that starts the MCP server."""
    # Mock the server's run method to prevent actually starting a server
    with patch("k8s_mcp_server.server.mcp.run") as mock_run:
        # Import after patching to avoid actual execution
        from k8s_mcp_server.__main__ import main

        # Test with default host and port
        main()
        mock_run.assert_called_once_with(host="0.0.0.0", port=8080)

        # Reset the mock for the next test
        mock_run.reset_mock()

        # Test with custom host and port from environment variables
        with patch.dict(os.environ, {"K8S_MCP_HOST": "127.0.0.1", "K8S_MCP_PORT": "9090"}):
            main()
            mock_run.assert_called_once_with(host="127.0.0.1", port=9090)
