"""Utility for executing Kubernetes CLI commands.

This module provides functions to validate and execute commands for various
Kubernetes CLI tools (kubectl, istioctl, helm, argocd) with proper error handling,
timeouts, and output processing.
"""

import asyncio
import logging
import shlex
from typing import Dict, List, Optional, TypedDict

from k8s_mcp_server.config import DEFAULT_TIMEOUT, K8S_CONTEXT, K8S_NAMESPACE, MAX_OUTPUT_SIZE, SUPPORTED_CLI_TOOLS
from k8s_mcp_server.tools import (
    CommandResult,
    execute_piped_command,
    is_pipe_command,
    is_valid_k8s_tool,
    split_pipe_command,
    validate_unix_command,
)

# Configure module logger
logger = logging.getLogger(__name__)


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


# Dictionary of potentially dangerous commands for each CLI tool
DANGEROUS_COMMANDS: Dict[str, List[str]] = {
    "kubectl": [
        "kubectl delete",  # Global delete without specific resource
        "kubectl drain",
        "kubectl replace --force",
        "kubectl exec",  # Handled specially to prevent interactive shells
    ],
    "istioctl": [
        "istioctl experimental",
        "istioctl proxy-config",  # Can access sensitive information
    ],
    "helm": [
        "helm delete",
        "helm uninstall",
        "helm rollback",
    ],
    "argocd": [
        "argocd app delete",
        "argocd cluster rm",
        "argocd repo rm",
    ],
}

# Dictionary of safe patterns that override the dangerous commands
SAFE_PATTERNS: Dict[str, List[str]] = {
    "kubectl": [
        "kubectl delete pod",
        "kubectl delete deployment",
        "kubectl delete service",
        "kubectl delete configmap",
        "kubectl delete secret",
        # Specific exec commands that are safe
        "kubectl exec --help",
        "kubectl exec -it",  # Allow interactive mode that's explicitly requested
    ],
    "istioctl": [
        "istioctl experimental -h",
        "istioctl experimental --help",
        "istioctl proxy-config --help",
    ],
    "helm": [
        "helm delete --help",
        "helm uninstall --help",
        "helm rollback --help",
    ],
    "argocd": [
        "argocd app delete --help",
        "argocd cluster rm --help",
        "argocd repo rm --help",
    ],
}


def is_safe_exec_command(command: str) -> bool:
    """Check if a kubectl exec command is safe to execute.

    We consider a kubectl exec command safe if it doesn't try to start an interactive shell
    without explicit -it flags and doesn't use dangerous commands like bash/sh without args.

    Args:
        command: The kubectl exec command

    Returns:
        True if the command is safe, False otherwise
    """
    if not command.startswith("kubectl exec"):
        return True  # Not an exec command

    # Check for explicit interactive mode
    has_interactive = "-i" in command or "--stdin" in command or "-it" in command or "-ti" in command

    # Check for shell commands that might be used without proper args
    dangerous_shell_patterns = [" -- sh", " -- bash", " -- /bin/sh", " -- /bin/bash"]
    has_dangerous_shell = any(pattern in command + " " for pattern in dangerous_shell_patterns)

    # If interactive is explicitly requested AND not trying to just get a shell, it's safe
    # Or if it's non-interactive (like running a specific command), it's safe
    return (has_interactive and not has_dangerous_shell) or (not has_interactive)


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


def validate_k8s_command(command: str) -> None:
    """Validate that the command is a proper Kubernetes CLI command.

    Args:
        command: The Kubernetes CLI command to validate

    Raises:
        CommandValidationError: If the command is invalid
    """
    cmd_parts = shlex.split(command)
    if not cmd_parts:
        raise CommandValidationError("Empty command")

    cli_tool = cmd_parts[0]
    if not is_valid_k8s_tool(cli_tool):
        raise CommandValidationError(
            f"Command must start with a supported CLI tool: {', '.join(SUPPORTED_CLI_TOOLS.keys())}"
        )

    if len(cmd_parts) < 2:
        raise CommandValidationError(f"Command must include a {cli_tool} action")

    # Special case for kubectl exec
    if cli_tool == "kubectl" and "exec" in cmd_parts:
        if not is_safe_exec_command(command):
            raise CommandValidationError(
                "Interactive shells via kubectl exec are restricted. "
                "Use explicit commands or proper flags (-it, --command, etc)."
            )

    # Check against dangerous commands
    if cli_tool in DANGEROUS_COMMANDS:
        for dangerous_cmd in DANGEROUS_COMMANDS[cli_tool]:
            if command.startswith(dangerous_cmd):
                # Check if it matches a safe pattern
                if cli_tool in SAFE_PATTERNS:
                    if any(command.startswith(safe_pattern) for safe_pattern in SAFE_PATTERNS[cli_tool]):
                        return  # Safe pattern match, allow command

                raise CommandValidationError(
                    f"This command is restricted for safety reasons. "
                    f"Please use a more specific form with resource type and name."
                )


def validate_pipe_command(pipe_command: str) -> None:
    """Validate a command that contains pipes.

    This checks both Kubernetes CLI commands and Unix commands within a pipe chain.

    Args:
        pipe_command: The piped command to validate

    Raises:
        CommandValidationError: If any command in the pipe is invalid
    """
    commands = split_pipe_command(pipe_command)

    if not commands:
        raise CommandValidationError("Empty command")

    # First command must be a Kubernetes CLI command
    validate_k8s_command(commands[0])

    # Subsequent commands should be valid Unix commands
    for i, cmd in enumerate(commands[1:], 1):
        cmd_parts = shlex.split(cmd)
        if not cmd_parts:
            raise CommandValidationError(f"Empty command at position {i} in pipe")

        if not validate_unix_command(cmd):
            cli_tools_str = ", ".join(SUPPORTED_CLI_TOOLS.keys())
            raise CommandValidationError(
                f"Command '{cmd_parts[0]}' at position {i} in pipe is not allowed. "
                f"Only {cli_tools_str} commands and basic Unix utilities are permitted."
            )


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


def get_tool_from_command(command: str) -> Optional[str]:
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
    validate_k8s_command(command)

    # Handle context and namespace for kubectl commands
    command = inject_context_namespace(command)

    # Set timeout
    if timeout is None:
        timeout = DEFAULT_TIMEOUT

    logger.debug(f"Executing command: {command}")

    try:
        # Create subprocess
        process = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

        # Wait for the process to complete with timeout
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
            logger.debug(f"Command completed with return code: {process.returncode}")
        except asyncio.TimeoutError as timeout_error:
            logger.warning(f"Command timed out after {timeout} seconds: {command}")
            try:
                process.kill()
            except Exception as e:
                logger.error(f"Error killing process: {e}")
            raise CommandExecutionError(f"Command timed out after {timeout} seconds") from timeout_error

        # Process output
        stdout_str = stdout.decode("utf-8", errors="replace")
        stderr_str = stderr.decode("utf-8", errors="replace")

        # Truncate output if necessary
        if len(stdout_str) > MAX_OUTPUT_SIZE:
            logger.info(f"Output truncated from {len(stdout_str)} to {MAX_OUTPUT_SIZE} characters")
            stdout_str = stdout_str[:MAX_OUTPUT_SIZE] + "\n... (output truncated)"

        if process.returncode != 0:
            logger.warning(f"Command failed with return code {process.returncode}: {command}")
            logger.debug(f"Command error output: {stderr_str}")

            if is_auth_error(stderr_str):
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
                
                return CommandResult(status="error", output=auth_error_msg)

            return CommandResult(status="error", output=stderr_str or "Command failed with no error output")

        return CommandResult(status="success", output=stdout_str)
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
    except CommandValidationError as e:
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
