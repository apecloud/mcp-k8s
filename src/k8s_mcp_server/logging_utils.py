"""Logging utilities for K8s MCP Server.

This module provides standardized logging configuration and logger creation
for consistent logging across the application.
"""

import logging
import sys
from pathlib import Path

from k8s_mcp_server.config import LOG_DIR


def configure_root_logger():
    """Configure the root logger for the application.
    
    Sets up logging with a consistent format and handlers for both
    console output and file logging.
    """
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    
    # File handler
    log_file = LOG_DIR / "k8s_mcp_server.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Log startup information
    root_logger.info(f"Logging initialized. Log file: {log_file}")


def get_logger(name):
    """Get a standardized logger with the application prefix.
    
    Args:
        name: The name of the module or component
        
    Returns:
        A logger instance with the application prefix
    """
    return logging.getLogger(f"k8s-mcp-server.{name}")
