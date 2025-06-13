"""Security utilities for K8s MCP Server."""

import logging
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from k8s_mcp_server.config import K8sMcpConfig

logger = logging.getLogger(__name__)

ALLOWED_K8S_TOOLS = ["kubectl", "helm", "istioctl", "argocd"]
ALLOWED_UNIX_TOOLS = ["grep", "sed", "awk", "jq", "yq", "cut", "sort", "head", "tail"]

DEFAULT_DANGEROUS_COMMANDS: dict[str, list[str]] = {
    "kubectl": [
        "kubectl delete",
        "kubectl drain",
        "kubectl replace --force",
        "kubectl exec",
        "kubectl port-forward",
        "kubectl cp",
        "kubectl delete pods --all",
    ],
    "istioctl": ["istioctl experimental", "istioctl proxy-config", "istioctl dashboard"],
    "helm": ["helm delete", "helm uninstall", "helm rollback", "helm upgrade"],
    "argocd": ["argocd app delete", "argocd cluster rm", "argocd repo rm", "argocd app set"],
}

DEFAULT_SAFE_PATTERNS: dict[str, list[str]] = {
    "kubectl": [
        "kubectl delete pod",
        "kubectl delete deployment",
        "kubectl delete service",
        "kubectl delete configmap",
        "kubectl delete secret",
        "kubectl exec --help",
        "kubectl exec -it",
        "kubectl exec pod",
        "kubectl exec deployment",
        "kubectl port-forward --help",
        "kubectl cp --help",
    ],
    "istioctl": ["istioctl experimental -h", "istioctl experimental --help", "istioctl proxy-config --help", "istioctl dashboard --help"],
    "helm": ["helm delete --help", "helm uninstall --help", "helm rollback --help", "helm upgrade --help"],
    "argocd": ["argocd app delete --help", "argocd cluster rm --help", "argocd repo rm --help", "argocd app set --help"],
}

@dataclass
class ValidationRule:
    pattern: str
    description: str
    error_message: str

@dataclass
class SecurityConfig:
    dangerous_commands: dict[str, list[str]]
    safe_patterns: dict[str, list[str]]
    regex_rules: dict[str, list[ValidationRule]]

def load_security_config(config_path_str: Optional[str]) -> SecurityConfig:
    dangerous_commands = DEFAULT_DANGEROUS_COMMANDS.copy()
    safe_patterns = DEFAULT_SAFE_PATTERNS.copy()
    regex_rules = {}

    if config_path_str:
        config_path = Path(config_path_str)
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config_data = yaml.safe_load(f)
                if config_data and isinstance(config_data, dict):
                    if config_data.get("dangerous_commands"):
                        dangerous_commands.update(config_data["dangerous_commands"])
                    if config_data.get("safe_patterns"):
                        safe_patterns.update(config_data["safe_patterns"])
                    if config_data.get("regex_rules"):
                        for tool, rules in config_data["regex_rules"].items():
                            if tool in ALLOWED_K8S_TOOLS:
                                regex_rules[tool] = [ValidationRule(**rule) for rule in rules]
                logger.info(f"Loaded security configuration from {config_path}")
            except Exception as e:
                logger.error(f"Error loading security configuration: {str(e)}, using defaults.")
    return SecurityConfig(dangerous_commands, safe_patterns, regex_rules)

def is_safe_exec_command(command: str) -> bool:
    if not command.startswith("kubectl exec"):
        return True
    if " --help" in command or " -h" in command:
        return True
    
    dangerous_shells = [" sh", " bash", " zsh", " ksh", " csh"]
    has_shell = any(f" --{shell.strip()}" in command for shell in dangerous_shells)
    has_interactive_flags = " -it " in command or " -ti " in command

    if has_shell and not has_interactive_flags and " -c " not in command:
        return False
    
    return True

def validate_k8s_command(command: str, sec_config: SecurityConfig) -> None:
    logger.debug(f"Validating K8s command: {command}")
    
    try:
        cmd_parts = shlex.split(command)
    except ValueError as e:
        raise ValueError(f"Invalid command syntax: {e}")
    
    if not cmd_parts:
        raise ValueError("Empty K8s command.")

    tool = cmd_parts[0]
    if tool not in ALLOWED_K8S_TOOLS:
        raise ValueError(f"Disallowed tool: '{tool}'. Only {ALLOWED_K8S_TOOLS} are supported.")

    if tool in sec_config.dangerous_commands:
        for dangerous in sec_config.dangerous_commands[tool]:
            if command.startswith(dangerous):
                is_safe = False
                if tool in sec_config.safe_patterns:
                    for safe in sec_config.safe_patterns[tool]:
                        if command.startswith(safe):
                            is_safe = True
                            break
                if not is_safe:
                    raise ValueError(f"Potentially dangerous command blocked: '{command}'")

    if tool in sec_config.regex_rules:
        for rule in sec_config.regex_rules[tool]:
            if re.search(rule.pattern, command):
                raise ValueError(rule.error_message)

    if tool == "kubectl" and "exec" in cmd_parts and not is_safe_exec_command(command):
        raise ValueError("Unsafe 'kubectl exec': interactive shells require '-it' flags.")

def validate_unix_command(command: str):
    if not command:
        raise ValueError("Empty pipe segment.")
    try:
        tool = shlex.split(command)[0]
    except (ValueError, IndexError):
        raise ValueError("Invalid pipe segment.")
    if tool not in ALLOWED_UNIX_TOOLS:
        raise ValueError(f"Disallowed Unix tool in pipe: '{tool}'")

def validate_pipe_command(full_command: str):
    parts = full_command.split("|")
    for part in parts[1:]:
        validate_unix_command(part.strip())

def check_command_safety(command: str, config: K8sMcpConfig):
    """Main entry point for security validation."""
    sec_config = load_security_config(config.K8S_MCP_SECURITY_CONFIG_PATH)
    
    parts = command.split("|")
    if not parts or not parts[0].strip():
        raise ValueError("Empty command.")
    
    k8s_command = parts[0].strip()
    validate_k8s_command(k8s_command, sec_config)

    if len(parts) > 1:
        validate_pipe_command(command)
