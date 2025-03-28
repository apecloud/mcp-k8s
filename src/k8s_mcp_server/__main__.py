"""Main entry point for K8s MCP Server.

Running this module will start the K8s MCP Server.
"""

import logging
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
    from k8s_mcp_server.config import MCP_TRANSPORT
    from k8s_mcp_server.server import mcp

    # Validate transport protocol
    if MCP_TRANSPORT not in ["stdio", "sse"]:
        logger.error(f"Invalid transport protocol: {MCP_TRANSPORT}. Using stdio instead.")
        transport = "stdio"
    else:
        transport = MCP_TRANSPORT

    # Start the server
    logger.info(f"Starting K8s MCP Server with {transport} transport")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
