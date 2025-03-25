"""Utility for executing Kubernetes CLI commands.

This module provides functions to validate and execute commands for various
Kubernetes CLI tools (kubectl, istioctl, helm, argocd) with proper error handling,
timeouts, and output processing.
"""

import asyncio
import shlex
import time
from typing import Dict, Optional, TypedDict

from k8s_mcp_server.config import DEFAULT_TIMEOUT, K8S_CONTEXT, K8S_NAMESPACE, MAX_OUTPUT_SIZE, SUPPORTED_CLI_TOOLS
from k8s_mcp_server.logging_utils import get_logger
from k8s_mcp_server.security import (
    is_safe_exec_command,
    validate_command,
    validate_k8s_command,
    validate_pipe_command,
)
from k8s_mcp_server.tools import (
    CommandResult,
    execute_piped_command,
    is_pipe_command,
    is_valid_k8s_tool,
    split_pipe_command,
)

# Configure module logger
logger = get_logger("cli_executor")


class CommandHelpResult(TypedDict):
    """Type definition for command help results."""

    help_text: str


class CommandValidationError(Exception):
    """Exception raised when a command fails validation.

    This exception is raised when a command doesn't meet the
    validation requirements, such as starting with a supported CLI tool.
    """

    pass


class CommandExecutionError(Exception):
    """Exception raised when a command fails to execute.

    This exception is raised when there's an error during command
    execution, such as timeouts or subprocess failures.
    """

    pass


class ErrorDetails(TypedDict, total=False):
    """Type definition for error details."""
    
    message: str
    code: str
    command: Optional[str]
    exit_code: Optional[int]
    stderr: Optional[str]




async def check_cli_installed(cli_tool: str) -> bool:
    """Check if a Kubernetes CLI tool is installed and accessible.

    Args:
        cli_tool: Name of the CLI tool to check (kubectl, istioctl, helm, argocd)

    Returns:
        True if the CLI tool is installed, False otherwise
    """
    if cli_tool not in SUPPORTED_CLI_TOOLS:
        logger.warning(f"Unsupported CLI tool: {cli_tool}")
        return False

    try:
        cmd = SUPPORTED_CLI_TOOLS[cli_tool]["check_cmd"]
        process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await process.communicate()
        return process.returncode == 0
    except Exception as e:
        logger.warning(f"Error checking if {cli_tool} is installed: {e}")
        return False






def is_auth_error(error_output: str) -> bool:
    """Detect if an error is related to authentication.

    Args:
        error_output: The error output from CLI tool

    Returns:
        True if the error is related to authentication, False otherwise
    """
    auth_error_patterns = [
        "Unable to connect to the server",
        "Unauthorized",
        "forbidden",
        "Invalid kubeconfig",
        "Unable to load authentication",
        "Error loading config",
        "no configuration has been provided",
        "You must be logged in",  # For argocd
        "Error: Helm repo",  # For Helm repo authentication
    ]
    return any(pattern.lower() in error_output.lower() for pattern in auth_error_patterns)


def get_tool_from_command(command: str) -> str | None:
    """Extract the CLI tool from a command string.

    Args:
        command: The command string

    Returns:
        The CLI tool name or None if not found
    """
    cmd_parts = shlex.split(command)
    if not cmd_parts:
        return None

    return cmd_parts[0] if cmd_parts[0] in SUPPORTED_CLI_TOOLS else None


async def execute_command(command: str, timeout: int | None = None) -> CommandResult:
    """Execute a Kubernetes CLI command and return the result.

    Validates, executes, and processes the results of a CLI command,
    handling timeouts and output size limits.

    Args:
        command: The CLI command to execute (must start with supported CLI tool)
        timeout: Optional timeout in seconds (defaults to DEFAULT_TIMEOUT)

    Returns:
        CommandResult containing output and status

    Raises:
        CommandValidationError: If the command is invalid
        CommandExecutionError: If the command fails to execute
    """
    # Check if this is a piped command
    if is_pipe_command(command):
        return await execute_pipe_command(command, timeout)

    # Validate the command
    try:
        validate_k8s_command(command)
    except ValueError as e:
        raise CommandValidationError(str(e)) from e

    # Handle context and namespace for kubectl commands
    command = inject_context_namespace(command)

    # Set timeout
    if timeout is None:
        timeout = DEFAULT_TIMEOUT

    logger.debug(f"Executing command: {command}")
    start_time = time.time()

    try:
        # Create subprocess
        process = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

        # Wait for the process to complete with timeout
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
            logger.debug(f"Command completed with return code: {process.returncode}")
        except TimeoutError as timeout_error:
            logger.warning(f"Command timed out after {timeout} seconds: {command}")
            try:
                process.kill()
            except Exception as e:
                logger.error(f"Error killing process: {e}")
            execution_time = time.time() - start_time
            error_details = {
                "message": f"Command timed out after {timeout} seconds",
                "code": "TIMEOUT_ERROR",
                "command": command
            }
            raise CommandExecutionError(f"Command timed out after {timeout} seconds") from timeout_error

        # Process output
        stdout_str = stdout.decode("utf-8", errors="replace")
        stderr_str = stderr.decode("utf-8", errors="replace")
        execution_time = time.time() - start_time

        # Truncate output if necessary
        if len(stdout_str) > MAX_OUTPUT_SIZE:
            logger.info(f"Output truncated from {len(stdout_str)} to {MAX_OUTPUT_SIZE} characters")
            stdout_str = stdout_str[:MAX_OUTPUT_SIZE] + "\n... (output truncated)"

        if process.returncode != 0:
            logger.warning(f"Command failed with return code {process.returncode}: {command}")
            logger.debug(f"Command error output: {stderr_str}")

            error_code = "EXECUTION_ERROR"
            error_message = stderr_str or "Command failed with no error output"

            if is_auth_error(stderr_str):
                error_code = "AUTH_ERROR"
                cli_tool = get_tool_from_command(command)
                auth_error_msg = f"Authentication error: {stderr_str}"

                if cli_tool == "kubectl":
                    auth_error_msg += "\nPlease check your kubeconfig."
                elif cli_tool == "istioctl":
                    auth_error_msg += "\nPlease check your Istio configuration."
                elif cli_tool == "helm":
                    auth_error_msg += "\nPlease check your Helm repository configuration."
                elif cli_tool == "argocd":
                    auth_error_msg += "\nPlease check your ArgoCD login status."

                error_message = auth_error_msg

            error_details = {
                "message": error_message,
                "code": error_code,
                "command": command,
                "exit_code": process.returncode,
                "stderr": stderr_str
            }

            return CommandResult(
                status="error", 
                output=error_message,
                error=error_details,
                exit_code=process.returncode,
                execution_time=execution_time
            )

        return CommandResult(
            status="success", 
            output=stdout_str,
            exit_code=process.returncode,
            execution_time=execution_time
        )
    except asyncio.CancelledError:
        raise
    except Exception as e:
        raise CommandExecutionError(f"Failed to execute command: {str(e)}") from e


def inject_context_namespace(command: str) -> str:
    """Inject context and namespace flags into kubectl and istioctl commands if not already present.

    Args:
        command: The CLI command

    Returns:
        Command with context and namespace flags added if needed
    """
    if not (command.startswith("kubectl") or command.startswith("istioctl")):
        return command  # Only apply to kubectl and istioctl

    cmd_parts = shlex.split(command)

    # Check if we need to add context
    if K8S_CONTEXT and "--context" not in command and not any(p == "--context" for p in cmd_parts):
        cmd_parts.insert(1, f"--context={K8S_CONTEXT}")

    # Check if we need to add namespace for commands that operate on resources
    # but skip global commands like 'kubectl get namespaces'
    resource_commands = ["get", "describe", "delete", "edit", "label", "annotate", "patch", "apply", "logs"]
    is_resource_command = any(cmd in cmd_parts for cmd in resource_commands)
    # Don't add namespace if command explicitly targets all namespaces or specifies a namespace
    skips_namespace = "-A" in cmd_parts or "--all-namespaces" in cmd_parts or "-n" in cmd_parts or "--namespace" in cmd_parts

    # Some kubectl operations don't require a namespace (get nodes, get namespaces, etc.)
    non_namespace_resources = ["nodes", "namespaces", "clusterroles", "clusterrolebindings"]
    targets_non_namespace_resource = any(resource in cmd_parts for resource in non_namespace_resources)

    if is_resource_command and not skips_namespace and not targets_non_namespace_resource:
        cmd_parts.insert(1, f"--namespace={K8S_NAMESPACE}")

    return " ".join(cmd_parts)


async def execute_pipe_command(pipe_command: str, timeout: int | None = None) -> CommandResult:
    """Execute a command that contains pipes.

    Validates and executes a piped command where output is fed into subsequent commands.
    The first command must be a Kubernetes CLI command, and subsequent commands must be
    allowed Unix utilities.

    Args:
        pipe_command: The piped command to execute
        timeout: Optional timeout in seconds (defaults to DEFAULT_TIMEOUT)

    Returns:
        CommandResult containing output and status

    Raises:
        CommandValidationError: If any command in the pipe is invalid
        CommandExecutionError: If the command fails to execute
    """
    # Validate the pipe command
    try:
        validate_pipe_command(pipe_command)
    except ValueError as e:
        raise CommandValidationError(f"Invalid pipe command: {str(e)}") from e

    # Handle context and namespace injection
    commands = split_pipe_command(pipe_command)
    first_command = inject_context_namespace(commands[0])
    if len(commands) > 1:
        # Reconstruct the pipe command with the modified first command
        pipe_command = first_command + " | " + " | ".join(commands[1:])
    else:
        pipe_command = first_command

    logger.debug(f"Executing piped command: {pipe_command}")

    try:
        # Execute the piped command using our tools module
        return await execute_piped_command(pipe_command, timeout)
    except Exception as e:
        raise CommandExecutionError(f"Failed to execute piped command: {str(e)}") from e


async def get_command_help(cli_tool: str, command: str | None = None) -> CommandHelpResult:
    """Get help documentation for a Kubernetes CLI tool or command.

    Retrieves the help documentation for a specified CLI tool or command
    by executing the appropriate help command.

    Args:
        cli_tool: The CLI tool name (kubectl, istioctl, helm, argocd)
        command: Optional command within the CLI tool

    Returns:
        CommandHelpResult containing the help text

    Raises:
        CommandExecutionError: If the help command fails
    """
    if cli_tool not in SUPPORTED_CLI_TOOLS:
        return CommandHelpResult(help_text=f"Unsupported CLI tool: {cli_tool}")

    # Build the help command
    help_flag = SUPPORTED_CLI_TOOLS[cli_tool]["help_flag"]
    if command:
        cmd_str = f"{cli_tool} {command} {help_flag}"
    else:
        cmd_str = f"{cli_tool} {help_flag}"

    try:
        logger.debug(f"Getting command help for: {cmd_str}")
        result = await execute_command(cmd_str)

        help_text = result["output"] if result["status"] == "success" else f"Error: {result['output']}"

        return CommandHelpResult(help_text=help_text)
    except CommandValidationError as e:
        logger.warning(f"Command validation error while getting help: {e}")
        return CommandHelpResult(help_text=f"Command validation error: {str(e)}")
    except CommandExecutionError as e:
        logger.warning(f"Command execution error while getting help: {e}")
        return CommandHelpResult(help_text=f"Error retrieving help: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error while getting command help: {e}", exc_info=True)
        return CommandHelpResult(help_text=f"Error retrieving help: {str(e)}")
