"""Configuration settings for the K8s MCP Server.

This module contains configuration settings for the K8s MCP Server,
loaded from environment variables using Pydantic.
"""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class K8sMcpConfig(BaseSettings):
    """
    Defines all configuration settings for the server.
    Settings are loaded from environment variables (case-insensitive).
    Example: set K8S_MCP_TIMEOUT=600 to override the default.
    """
    # Command execution settings
    K8S_MCP_TIMEOUT: int = 300
    K8S_MCP_MAX_OUTPUT_SIZE: int = 100000
    K8S_MCP_SSE_TIMEOUT: int = 60  # Timeout for SSE connection if no event is received

    # Kubernetes specific settings
    K8S_CONTEXT: Optional[str] = None
    K8S_NAMESPACE: str = "default"

    # Security settings
    K8S_MCP_SECURITY_MODE: str = "strict"  # "strict" or "permissive"
    K8S_MCP_SECURITY_CONFIG_PATH: Optional[str] = None


# --- Application-level constants below ---

SUPPORTED_CLI_TOOLS = {
    "kubectl": {
        "description": "Kubernetes command-line tool",
        "check_cmd": "kubectl version --client",
        "help_flag": "--help",
    },
    "istioctl": {
        "description": "Command-line tool for Istio service mesh",
        "check_cmd": "istioctl version --remote=false",
        "help_flag": "--help",
    },
    "helm": {
        "description": "Kubernetes package manager",
        "check_cmd": "helm version",
        "help_flag": "--help",
    },
    "argocd": {
        "description": "GitOps continuous delivery tool for Kubernetes",
        "check_cmd": "argocd version --client",
        "help_flag": "--help",
    },
}

# Instructions are not used by the SSE server but could be useful for a future help endpoint.
INSTRUCTIONS = """
K8s MCP Server provides a simple interface to Kubernetes CLI tools.

Supported CLI tools:
- kubectl: Kubernetes command-line tool
- istioctl: Command-line tool for Istio service mesh
- helm: Kubernetes package manager
- argocd: GitOps continuous delivery tool for Kubernetes
"""

# Application paths
BASE_DIR = Path(__file__).parent.parent.parent
