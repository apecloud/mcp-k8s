"""Tests for the main module."""

import os
import signal
from unittest.mock import call, patch

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


@pytest.mark.unit
def test_graceful_shutdown_handler():
    """Test the graceful shutdown handler for SIGINT signal."""
    from importlib import reload

    import k8s_mcp_server.__main__

    # Reload to ensure we have the latest version
    reload(k8s_mcp_server.__main__)

    # Mock sys.exit to prevent the test from exiting
    with patch("sys.exit") as mock_exit:
        # Create a mock logger
        with patch("k8s_mcp_server.__main__.logger") as mock_logger:
            # Call the interrupt handler
            k8s_mcp_server.__main__.handle_interrupt(signal.SIGINT, None)

            # Verify the logger was called with the correct message
            mock_logger.info.assert_called_once_with(f"Received signal {signal.SIGINT}, shutting down gracefully...")

            # Verify sys.exit was called with 0
            mock_exit.assert_called_once_with(0)


@pytest.mark.unit
def test_keyboard_interrupt_handling():
    """Test that keyboard interrupts are handled gracefully."""
    # Import required modules
    from importlib import reload

    import k8s_mcp_server.__main__

    # Reload to ensure we have the latest version
    reload(k8s_mcp_server.__main__)

    # Mock sys.exit to prevent the test from exiting
    with patch("sys.exit") as mock_exit:
        # Create a mock logger
        with patch("k8s_mcp_server.__main__.logger") as mock_logger:
            # Mock the server run method to raise KeyboardInterrupt
            with patch("k8s_mcp_server.server.mcp.run", side_effect=KeyboardInterrupt):
                # Call the main function
                k8s_mcp_server.__main__.main()

                # Verify the logger was called with the shutdown message
                mock_logger.info.assert_any_call("Keyboard interrupt received. Shutting down gracefully...")

                # Verify sys.exit was called with 0
                mock_exit.assert_called_once_with(0)


@pytest.mark.unit
def test_signal_handler_registration():
    """Test that the signal handler is registered correctly."""
    # Import required modules
    from importlib import reload

    import k8s_mcp_server.__main__

    # Reload to ensure we have the latest version
    reload(k8s_mcp_server.__main__)

    # Mock signal.signal to verify it's called correctly
    with patch("signal.signal") as mock_signal:
        # Mock server.mcp.run to prevent execution
        with patch("k8s_mcp_server.server.mcp.run"):
            # Call the main function
            k8s_mcp_server.__main__.main()

            # Verify both signal handlers were registered
            assert mock_signal.call_count == 2
            mock_signal.assert_has_calls(
                [call(signal.SIGINT, k8s_mcp_server.__main__.handle_interrupt), call(signal.SIGTERM, k8s_mcp_server.__main__.handle_interrupt)], any_order=True
            )
