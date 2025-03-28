"""Tests for the main module."""

import os
from unittest.mock import patch

import pytest


@pytest.mark.unit
def test_main_function():
    """Test the main function that starts the MCP server."""
    # Mock the server's run method to prevent actually starting a server
    with patch("k8s_mcp_server.server.mcp.run") as mock_run:
        # Test with default transport (stdio)
        with patch.dict(os.environ, {"K8S_MCP_TRANSPORT": "stdio"}):
            # Import after patching to avoid actual execution
            from importlib import reload

            import k8s_mcp_server.__main__
            import k8s_mcp_server.config

            # Reload the module to pick up the environment variable
            reload(k8s_mcp_server.config)
            reload(k8s_mcp_server.__main__)

            # Call the main function
            k8s_mcp_server.__main__.main()
            mock_run.assert_called_once_with(transport="stdio")

        # Reset the mock for the next test
        mock_run.reset_mock()

        # Test with custom transport from environment variable
        with patch.dict(os.environ, {"K8S_MCP_TRANSPORT": "sse"}):
            # Reload the modules to pick up the new environment variable
            reload(k8s_mcp_server.config)
            reload(k8s_mcp_server.__main__)

            # Call the main function
            k8s_mcp_server.__main__.main()
            mock_run.assert_called_once_with(transport="sse")

        # Reset the mock for the next test
        mock_run.reset_mock()

        # Test with invalid transport from environment variable (should default to stdio)
        with patch.dict(os.environ, {"K8S_MCP_TRANSPORT": "invalid"}):
            # Reload the modules to pick up the new environment variable
            reload(k8s_mcp_server.config)
            reload(k8s_mcp_server.__main__)

            # Call the main function
            k8s_mcp_server.__main__.main()
            mock_run.assert_called_once_with(transport="stdio")
