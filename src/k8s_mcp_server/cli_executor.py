"""Utility for executing Kubernetes CLI commands.

This module provides a function to execute shell commands for the SSE server.
It handles command execution with proper environment setup for kubeconfig.
"""

import asyncio
import logging
import os
from asyncio.subprocess import PIPE

from k8s_mcp_server.errors import CommandExecutionError

logger = logging.getLogger(__name__)


async def execute_command(
    command: str, *, kubeconfig_path: str, timeout: int
) -> asyncio.subprocess.Process:
    """Execute a shell command asynchronously and return the process.

    This function sets up the environment for command execution, including
    setting the KUBECONFIG environment variable. It does not wait for the
    command to complete but returns the process object for stream handling.

    Args:
        command: The shell command to execute.
        kubeconfig_path: The path to the kubeconfig file to use.
        timeout: Timeout in seconds.

    Returns:
        An asyncio.subprocess.Process instance.

    Raises:
        CommandExecutionError: If there's an issue creating the subprocess.
    """
    logger.debug(
        f"Executing command with kubeconfig '{kubeconfig_path}' "
        f"and timeout {timeout}s: {command}"
    )

    env = os.environ.copy()
    env["KUBECONFIG"] = kubeconfig_path

    try:
        # For streaming, we use create_subprocess_shell to handle complex commands
        # and pipes gracefully. The security.py module must provide robust validation
        # before this function is ever called.
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        return process
    except Exception as e:
        logger.exception(f"Failed to create subprocess for command: {command}")
        raise CommandExecutionError(
            f"Failed to execute command: {e}", {"command": command}
        ) from e
