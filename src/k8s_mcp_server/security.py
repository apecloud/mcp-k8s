"""Security utilities for K8s MCP Server."""

import shlex

from k8s_mcp_server.tools import (
    is_pipe_command,
    is_valid_k8s_tool,
    split_pipe_command,
    validate_unix_command,
)

# Dictionary of potentially dangerous commands for each CLI tool
DANGEROUS_COMMANDS: dict[str, list[str]] = {
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
SAFE_PATTERNS: dict[str, list[str]] = {
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


def validate_k8s_command(command: str) -> None:
    """Validate that the command is a proper Kubernetes CLI command.

    Args:
        command: The Kubernetes CLI command to validate

    Raises:
        ValueError: If the command is invalid
    """
    cmd_parts = shlex.split(command)
    if not cmd_parts:
        raise ValueError("Empty command")

    cli_tool = cmd_parts[0]
    if not is_valid_k8s_tool(cli_tool):
        raise ValueError(
            "Command must start with a supported CLI tool: kubectl, istioctl, helm, argocd"
        )

    if len(cmd_parts) < 2:
        raise ValueError(f"Command must include a {cli_tool} action")

    # Special case for kubectl exec
    if cli_tool == "kubectl" and "exec" in cmd_parts:
        if not is_safe_exec_command(command):
            raise ValueError(
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

                raise ValueError(
                    "This command is restricted for safety reasons. "
                    "Please use a more specific form with resource type and name."
                )


def validate_pipe_command(pipe_command: str) -> None:
    """Validate a command that contains pipes.

    This checks both Kubernetes CLI commands and Unix commands within a pipe chain.

    Args:
        pipe_command: The piped command to validate

    Raises:
        ValueError: If any command in the pipe is invalid
    """
    commands = split_pipe_command(pipe_command)

    if not commands:
        raise ValueError("Empty command")

    # First command must be a Kubernetes CLI command
    validate_k8s_command(commands[0])

    # Subsequent commands should be valid Unix commands
    for i, cmd in enumerate(commands[1:], 1):
        cmd_parts = shlex.split(cmd)
        if not cmd_parts:
            raise ValueError(f"Empty command at position {i} in pipe")

        if not validate_unix_command(cmd):
            raise ValueError(
                f"Command '{cmd_parts[0]}' at position {i} in pipe is not allowed. "
                f"Only kubectl, istioctl, helm, argocd commands and basic Unix utilities are permitted."
            )


def validate_command(command: str) -> None:
    """Centralized validation for all commands.
    
    Args:
        command: The command to validate
        
    Raises:
        ValueError: If the command is invalid
    """
    if is_pipe_command(command):
        validate_pipe_command(command)
    else:
        validate_k8s_command(command)
