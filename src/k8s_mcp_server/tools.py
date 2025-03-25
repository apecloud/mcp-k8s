"""Command execution utilities for K8s MCP Server.

This module provides utilities for validating and executing commands, including:
- Kubernetes CLI tool commands (kubectl, istioctl, helm, argocd)
- Basic Unix commands
- Command pipes (piping output from one command to another)
"""

import asyncio
import shlex
import time
from typing import TypedDict

from k8s_mcp_server.config import DEFAULT_TIMEOUT, MAX_OUTPUT_SIZE
from k8s_mcp_server.logging_utils import get_logger

# Configure module logger
logger = get_logger("tools")

# List of allowed Unix commands that can be used in a pipe
ALLOWED_UNIX_COMMANDS = [
    # File operations
    "cat",
    "ls",
    "cd",
    "pwd",
    "cp",
    "mv",
    "rm",
    "mkdir",
    "touch",
    "chmod",
    "chown",
    # Text processing
    "grep",
    "sed",
    "awk",
    "cut",
    "sort",
    "uniq",
    "wc",
    "head",
    "tail",
    "tr",
    "find",
    # System information
    "ps",
    "top",
    "df",
    "du",
    "uname",
    "whoami",
    "date",
    "which",
    "echo",
    # Networking
    "ping",
    "ifconfig",
    "netstat",
    "curl",
    "wget",
    "dig",
    "nslookup",
    "ssh",
    "scp",
    # Other utilities
    "man",
    "less",
    "tar",
    "gzip",
    "gunzip",
    "zip",
    "unzip",
    "xargs",
    "jq",
    "yq",  # Added for YAML processing
    "tee",
]

# List of allowed Kubernetes CLI tools
ALLOWED_K8S_TOOLS = [
    "kubectl",
    "istioctl",
    "helm",
    "argocd",
]


class CommandResult(TypedDict, total=False):
    """Type definition for command execution results."""

    status: str
    output: str
    error: dict[str, str] | None
    exit_code: int | None
    execution_time: float | None


def is_valid_k8s_tool(command: str) -> bool:
    """Check if a command starts with a valid Kubernetes CLI tool.

    Args:
        command: The command to check

    Returns:
        True if the command starts with a valid Kubernetes CLI tool, False otherwise
    """
    cmd_parts = shlex.split(command)
    if not cmd_parts:
        return False

    return cmd_parts[0] in ALLOWED_K8S_TOOLS


def validate_unix_command(command: str) -> bool:
    """Validate that a command is an allowed Unix command.

    Args:
        command: The Unix command to validate

    Returns:
        True if the command is valid, False otherwise
    """
    cmd_parts = shlex.split(command)
    if not cmd_parts:
        return False

    # Check if the command is in the allowed list
    return cmd_parts[0] in ALLOWED_UNIX_COMMANDS


def is_pipe_command(command: str) -> bool:
    """Check if a command contains a pipe operator.

    Args:
        command: The command to check

    Returns:
        True if the command contains a pipe operator, False otherwise
    """
    # Simple check for pipe operator that's not inside quotes
    in_single_quote = False
    in_double_quote = False

    for i, char in enumerate(command):
        if char == "'" and (i == 0 or command[i - 1] != "\\"):
            in_single_quote = not in_single_quote
        elif char == '"' and (i == 0 or command[i - 1] != "\\"):
            in_double_quote = not in_double_quote
        elif char == "|" and not in_single_quote and not in_double_quote:
            return True

    return False


def split_pipe_command(pipe_command: str) -> list[str]:
    """Split a piped command into individual commands.

    Args:
        pipe_command: The piped command string

    Returns:
        List of individual command strings
    """
    commands = []
    current_command = ""
    in_single_quote = False
    in_double_quote = False

    for i, char in enumerate(pipe_command):
        if char == "'" and (i == 0 or pipe_command[i - 1] != "\\"):
            in_single_quote = not in_single_quote
            current_command += char
        elif char == '"' and (i == 0 or pipe_command[i - 1] != "\\"):
            in_double_quote = not in_double_quote
            current_command += char
        elif char == "|" and not in_single_quote and not in_double_quote:
            commands.append(current_command.strip())
            current_command = ""
        else:
            current_command += char

    if current_command.strip():
        commands.append(current_command.strip())

    return commands


async def execute_piped_command(pipe_command: str, timeout: int | None = None) -> CommandResult:
    """Execute a command that contains pipes.

    Args:
        pipe_command: The piped command to execute
        timeout: Optional timeout in seconds (defaults to DEFAULT_TIMEOUT)

    Returns:
        CommandResult containing output and status
    """
    # Set timeout
    if timeout is None:
        timeout = DEFAULT_TIMEOUT

    logger.debug(f"Executing piped command: {pipe_command}")
    start_time = time.time()

    try:
        # Create subprocess with shell=True to handle pipes
        process = await asyncio.create_subprocess_shell(pipe_command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

        # Wait for the process to complete with timeout
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
            logger.debug(f"Piped command completed with return code: {process.returncode}")
        except TimeoutError:
            logger.warning(f"Piped command timed out after {timeout} seconds: {pipe_command}")
            try:
                process.kill()
            except Exception as e:
                logger.error(f"Error killing process: {e}")
            execution_time = time.time() - start_time
            return CommandResult(
                status="error",
                output=f"Command timed out after {timeout} seconds",
                error={"message": f"Command timed out after {timeout} seconds", "code": "TIMEOUT_ERROR"},
                execution_time=execution_time
            )

        # Process output
        stdout_str = stdout.decode("utf-8", errors="replace")
        stderr_str = stderr.decode("utf-8", errors="replace")
        execution_time = time.time() - start_time

        # Truncate output if necessary
        if len(stdout_str) > MAX_OUTPUT_SIZE:
            logger.info(f"Output truncated from {len(stdout_str)} to {MAX_OUTPUT_SIZE} characters")
            stdout_str = stdout_str[:MAX_OUTPUT_SIZE] + "\n... (output truncated)"

        if process.returncode != 0:
            logger.warning(f"Piped command failed with return code {process.returncode}: {pipe_command}")
            logger.debug(f"Command error output: {stderr_str}")
            return CommandResult(
                status="error",
                output=stderr_str or "Command failed with no error output",
                error={
                    "message": stderr_str or "Command failed with no error output",
                    "code": "EXECUTION_ERROR",
                    "command": pipe_command,
                    "exit_code": process.returncode,
                    "stderr": stderr_str
                },
                exit_code=process.returncode,
                execution_time=execution_time
            )

        return CommandResult(
            status="success",
            output=stdout_str,
            exit_code=process.returncode,
            execution_time=execution_time
        )
    except Exception as e:
        logger.error(f"Failed to execute piped command: {str(e)}")
        return CommandResult(status="error", output=f"Failed to execute command: {str(e)}")
