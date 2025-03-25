"""Logging utilities for K8s MCP Server."""

import logging
import sys


def configure_root_logger():
    """Configure the root logger for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)]
    )


def get_logger(name):
    """Get a standardized logger with the application prefix."""
    return logging.getLogger(f"k8s-mcp-server.{name}")
