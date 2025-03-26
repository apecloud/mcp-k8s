"""Main entry point for K8s MCP Server.

Running this module will start the K8s MCP Server.
"""

import logging
import os
import sys

# Configure logging before importing server
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("k8s-mcp-server")


def main() -> None:
    """Run the K8s MCP Server."""
    # Import here to avoid circular imports
    from k8s_mcp_server.server import mcp

    # Get server configuration from environment variables
    host = os.environ.get("K8S_MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("K8S_MCP_PORT", "8080"))

    # Start the server
    logger.info(f"Starting K8s MCP Server on {host}:{port}")
    mcp.run(host=host, port=port)


if __name__ == "__main__":
    main()
