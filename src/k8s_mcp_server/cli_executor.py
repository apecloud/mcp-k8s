"""Utility for executing Kubernetes CLI commands.

This module provides functions to validate and execute commands for various
Kubernetes CLI tools (kubectl, istioctl, helm, argocd) with proper error handling,
timeouts, and output processing. It handles command execution with proper security
validation, context/namespace injection, and resource limitations.
"""

import asyncio
import shlex
import time

from k8s_mcp_server.config import (
    DEFAULT_TIMEOUT,
    K8S_CONTEXT,
    K8S_NAMESPACE,
    MAX_OUTPUT_SIZE,
    SUPPORTED_CLI_TOOLS,
)
from k8s_mcp_server.errors import (
    AuthenticationError,
    CommandExecutionError,
    CommandTimeoutError,
    CommandValidationError,
)
from k8s_mcp_server.logging_utils import get_logger
from k8s_mcp_server.security import validate_command
from k8s_mcp_server.tools import (
    CommandHelpResult,
    CommandResult,
    is_pipe_command,
    split_pipe_command,
)

# Configure module logger
logger = get_logger("cli_executor")


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
        process = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
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
        AuthenticationError: If authentication fails
        CommandTimeoutError: If the command times out
    """
    # Validate the command
    try:
        validate_command(command)
    except ValueError as e:
        raise CommandValidationError(str(e), {"command": command}) from e

    # Handle piped commands
    is_piped = is_pipe_command(command)
    if is_piped:
        commands = split_pipe_command(command)
        first_command = inject_context_namespace(commands[0])
        if len(commands) > 1:
            # Reconstruct the pipe command with the modified first command
            command = first_command + " | " + " | ".join(commands[1:])
        else:
            command = first_command
    else:
        # Handle context and namespace for non-piped commands
        command = inject_context_namespace(command)

    # Set timeout
    if timeout is None:
        timeout = DEFAULT_TIMEOUT

    logger.debug(f"Executing {'piped ' if is_piped else ''}command: {command}")
    start_time = time.time()

    try:
        # Create subprocess with resource limits
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Wait for the process to complete with timeout
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
            logger.debug(f"Command completed with return code: {process.returncode}")
        except TimeoutError:
            logger.warning(f"Command timed out after {timeout} seconds: {command}")
            try:
                process.kill()
            except Exception as e:
                logger.error(f"Error killing process: {e}")

            execution_time = time.time() - start_time
            raise CommandTimeoutError(
                f"Command timed out after {timeout} seconds",
                {"command": command, "timeout": timeout}
            ) from None

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

            error_message = stderr_str or "Command failed with no error output"

            if is_auth_error(stderr_str):
                cli_tool = get_tool_from_command(command)
                auth_error_msg = f"Authentication error: {stderr_str}"

                match cli_tool:
                    case "kubectl":
                        auth_error_msg += "\nPlease check your kubeconfig."
                    case "istioctl":
                        auth_error_msg += "\nPlease check your Istio configuration."
                    case "helm":
                        auth_error_msg += "\nPlease check your Helm repository configuration."
                    case "argocd":
                        auth_error_msg += "\nPlease check your ArgoCD login status."

                raise AuthenticationError(
                    auth_error_msg,
                    {
                        "command": command,
                        "exit_code": process.returncode,
                        "stderr": stderr_str,
                    }
                )
            else:
                raise CommandExecutionError(
                    error_message,
                    {
                        "command": command,
                        "exit_code": process.returncode,
                        "stderr": stderr_str,
                    }
                )

        return CommandResult(
            status="success",
            output=stdout_str,
            exit_code=process.returncode,
            execution_time=execution_time
        )
    except asyncio.CancelledError:
        raise
    except (CommandValidationError, CommandExecutionError, AuthenticationError, CommandTimeoutError):
        # Re-raise specific exceptions so they can be caught and handled at the API boundary
        raise
    except Exception as e:
        logger.error(f"Failed to execute command: {str(e)}")
        raise CommandExecutionError(
            f"Failed to execute command: {str(e)}",
            {"command": command}
        ) from e


def inject_context_namespace(command: str) -> str:
    """Inject context and namespace flags into kubectl and istioctl commands if not already present,
    respecting flags already in the command.

    Args:
        command: The CLI command

    Returns:
        Command with context and namespace flags added if needed
    """
    if not (command.startswith("kubectl") or command.startswith("istioctl")):
        return command  # Only apply to kubectl and istioctl

    try:
        cmd_parts = shlex.split(command)
    except ValueError:
        # Handle potential parsing errors, e.g., unmatched quotes
        logger.warning(f"Could not parse command for context/namespace injection: {command}")
        return command

    if not cmd_parts:
        return command

    tool_name = cmd_parts[0]
    flags = []
    args = []
    has_context_flag = False
    has_namespace_flag = False
    targets_all_namespaces = False

    # Parse existing flags and arguments
    i = 1
    while i < len(cmd_parts):
        part = cmd_parts[i]
        if part.startswith("--"):
            flags.append(part)
            if part.startswith("--context"): # Handles --context and --context=...
                has_context_flag = True
            elif part.startswith("--namespace"): # Handles --namespace and --namespace=...
                has_namespace_flag = True
            elif part == "--all-namespaces":
                targets_all_namespaces = True
        elif part.startswith("-"):
            # Handle combined short flags like -itn or separate flags like -i -t -n
            flags.append(part)
            if 'n' in part[1:]: # Check if -n is present, potentially combined
                # Need to be careful: -name is not -n, but shlex should split correctly usually
                # A simple check might be sufficient for common cases
                if part == "-n":
                     has_namespace_flag = True
                # More robust check for combined flags like '-itn' requires iterating chars
                elif len(part) > 1 and part[0] == '-' and part[1] != '-': # Avoid '--'
                    if 'n' in part[1:]:
                        # Check if 'n' is followed by a value in the next part
                        is_n_flag_with_value = (
                            'n' == part[-1] and (i + 1) < len(cmd_parts) and not cmd_parts[i+1].startswith('-')
                        )
                        if not is_n_flag_with_value:
                            has_namespace_flag = True # Assume -n flag if not expecting value

            if part == "-A":
                targets_all_namespaces = True
        else:
            # Treat as argument
            args.append(part)
        i += 1


    # --- Inject Context ---
    if K8S_CONTEXT and not has_context_flag:
        # Insert context flag early, common convention
        flags.insert(0, f"--context={K8S_CONTEXT}")
        logger.debug(f"Injected context: --context={K8S_CONTEXT}")

    # --- Inject Namespace ---
    # Check if namespace injection is applicable
    resource_commands = ["get", "describe", "delete", "edit", "label", "annotate", "patch", "apply", "logs", "exec", "rollout", "scale", "autoscale", "expose"]
    # Check if any arg is a resource command (simple check)
    is_resource_command = any(arg in resource_commands for arg in args)

    # Some commands operate cluster-wide or don't need a namespace
    non_namespace_resources = [
        "nodes", "namespaces", "pv", "persistentvolumes", "storageclasses",
        "clusterroles", "clusterrolebindings", "apiservices", "certificatesigningrequests"
    ]
    targets_non_namespace_resource = any(arg in non_namespace_resources for arg in args)

    # Check if the command itself implies cluster scope (e.g., api-resources)
    is_cluster_scoped_command = any(arg in ["api-resources", "api-versions", "cluster-info"] for arg in args)


    if (K8S_NAMESPACE and
            not has_namespace_flag and
            not targets_all_namespaces and
            is_resource_command and
            not targets_non_namespace_resource and
            not is_cluster_scoped_command):
        # Add namespace flag
        flags.append(f"--namespace={K8S_NAMESPACE}")
        logger.debug(f"Injected namespace: --namespace={K8S_NAMESPACE}")

    # Reconstruct command: tool_name + flags + args
    # Use shlex.join for potentially safer reconstruction if available (Python 3.8+)
    # Otherwise, simple join is usually sufficient if parsing was okay.
    try:
        # Python 3.8+
        from shlex import join as shlex_join
        return shlex_join([tool_name] + flags + args)
    except ImportError:
        # Fallback for older Python versions
        return " ".join([tool_name] + flags + args)


async def get_command_help(cli_tool: str, command: str | None = None) -> CommandHelpResult:
    """Get help documentation for a Kubernetes CLI tool or command.

    Retrieves the help documentation for a specified CLI tool or command
    by executing the appropriate help command.

    Args:
        cli_tool: The CLI tool name (kubectl, istioctl, helm, argocd)
        command: Optional command within the CLI tool

    Returns:
        CommandHelpResult containing the help text
    """
    if cli_tool not in SUPPORTED_CLI_TOOLS:
        return CommandHelpResult(help_text=f"Unsupported CLI tool: {cli_tool}", status="error")

    # Build the help command
    help_flag = SUPPORTED_CLI_TOOLS[cli_tool]["help_flag"]
    if command:
        cmd_str = f"{cli_tool} {command} {help_flag}"
    else:
        cmd_str = f"{cli_tool} {help_flag}"

    try:
        logger.debug(f"Getting command help for: {cmd_str}")
        result = await execute_command(cmd_str)
        return CommandHelpResult(help_text=result["output"])
    except CommandValidationError as e:
        logger.warning(f"Help command validation error: {e}")
        return CommandHelpResult(
            help_text=f"Command validation error: {str(e)}",
            status="error",
            error={"message": str(e), "code": "VALIDATION_ERROR"},
        )
    except CommandExecutionError as e:
        logger.warning(f"Help command execution error: {e}")
        return CommandHelpResult(
            help_text=f"Command execution error: {str(e)}",
            status="error",
            error={"message": str(e), "code": "EXECUTION_ERROR"},
        )
    except AuthenticationError as e:
        logger.warning(f"Help command authentication error: {e}")
        return CommandHelpResult(
            help_text=f"Authentication error: {str(e)}",
            status="error",
            error={"message": str(e), "code": "AUTH_ERROR"},
        )
    except CommandTimeoutError as e:
        logger.warning(f"Help command timeout error: {e}")
        return CommandHelpResult(
            help_text=f"Command timed out: {str(e)}",
            status="error",
            error={"message": str(e), "code": "TIMEOUT_ERROR"},
        )
    except Exception as e:
        logger.error(f"Unexpected error while getting command help: {e}", exc_info=True)
        return CommandHelpResult(
            help_text=f"Error retrieving help: {str(e)}",
            status="error",
            error={"message": f"Error retrieving help: {str(e)}", "code": "INTERNAL_ERROR"},
        )
