"""
K8s MCP Server - A proper MCP server for Kubernetes CLI tools using fastapi-mcp.
"""
import asyncio
import base64
import logging
import os
import subprocess
import tempfile
import uuid
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field
from fastapi_mcp import FastApiMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supported CLI tools configuration
SUPPORTED_CLI_TOOLS = {
    "kubectl": "Kubernetes command-line tool",
    "helm": "Kubernetes package manager", 
    "istioctl": "Istio service mesh tool",
    "argocd": "ArgoCD CLI for GitOps",
}

# --- Pydantic Models ---
class CommandRequest(BaseModel):
    command: str = Field(..., description="The command to execute (without the tool name)")
    namespace: Optional[str] = Field(None, description="Optional Kubernetes namespace for kubectl/helm commands")
    kubeconfig: Optional[str] = Field(
        None, 
        description="Base64 encoded kubeconfig content. If provided, this kubeconfig will be used for the command, otherwise the server's default context will be used."
    )

class CommandResponse(BaseModel):
    success: bool = Field(..., description="Whether the command executed successfully")
    output: str = Field(..., description="Standard output from the command")
    error: Optional[str] = Field(None, description="Error message if command failed")
    exit_code: int = Field(..., description="Exit code from the command")

# --- FastAPI App ---
app = FastAPI(
    title="K8s MCP Server",
    description="A standard-compliant MCP server for Kubernetes tools (kubectl, helm, istioctl, argocd).",
    version="3.0.0"
)

# --- Command Execution Logic ---
async def execute_command_logic(
    tool: str, 
    command: str, 
    namespace: Optional[str],
    kubeconfig_b64: Optional[str] = None
) -> CommandResponse:
    """
    Execute a CLI command with the specified tool, optionally using a specific kubeconfig.

    This function handles the dynamic execution of commands like kubectl, helm, etc.
    If a base64 encoded `kubeconfig_b64` is provided, it is decoded and written to a
    temporary file. The `KUBECONFIG` environment variable is then set to this file's path,
    ensuring the command runs against the specified Kubernetes cluster. The temporary
    file is securely deleted after the command completes.

    Args:
        tool: The command-line tool to execute (e.g., 'kubectl').
        command: The command string to pass to the tool.
        namespace: The Kubernetes namespace to use (for applicable tools).
        kubeconfig_b64: An optional base64 encoded string of the kubeconfig file.

    Returns:
        A CommandResponse object containing the execution result.
    """
    kubeconfig_path = None
    env = os.environ.copy()
    
    try:
        # If kubeconfig is provided, decode it and save to a temporary file
        if kubeconfig_b64:
            try:
                kubeconfig_bytes = base64.b64decode(kubeconfig_b64)
                # Create a temporary file
                with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix=".yaml", encoding='utf-8') as temp_kubeconfig:
                    temp_kubeconfig.write(kubeconfig_bytes.decode('utf-8'))
                    kubeconfig_path = temp_kubeconfig.name
                
                logger.info(f"Using temporary kubeconfig at: {kubeconfig_path}")
                env["KUBECONFIG"] = kubeconfig_path
            except (base64.binascii.Error, UnicodeDecodeError) as e:
                return CommandResponse(
                    success=False, output="", error=f"Invalid base64 kubeconfig: {e}", exit_code=-1
                )

        # Split command into parts
        cmd_parts = [tool] + command.split()
        
        # Add namespace for kubectl and helm if provided
        if tool in ["kubectl", "helm"] and namespace:
            cmd_parts.insert(1, "-n")
            cmd_parts.insert(2, namespace)
        
        logger.info(f"Executing command: {' '.join(cmd_parts)}")
        
        # Execute the command
        process = await asyncio.create_subprocess_exec(
            *cmd_parts, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            env=env
        )
        stdout, stderr = await process.communicate()
        
        return CommandResponse(
            success=process.returncode == 0,
            output=stdout.decode('utf-8', errors='replace'),
            error=stderr.decode('utf-8', errors='replace') if stderr else None,
            exit_code=process.returncode
        )
    except FileNotFoundError:
        return CommandResponse(
            success=False, 
            output="", 
            error=f"Command '{tool}' not found. Please ensure {tool} is installed and in PATH.", 
            exit_code=-1
        )
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        return CommandResponse(
            success=False, 
            output="", 
            error=str(e), 
            exit_code=-1
        )
    finally:
        # Clean up the temporary kubeconfig file
        if kubeconfig_path and os.path.exists(kubeconfig_path):
            os.remove(kubeconfig_path)
            logger.info(f"Removed temporary kubeconfig: {kubeconfig_path}")

# --- Tool Endpoints ---
@app.post("/tools/kubectl", 
          response_model=CommandResponse,
          operation_id="kubectl",
          summary="Execute kubectl commands",
          description="Execute Kubernetes kubectl commands. Supports namespace parameter for resource operations.")
async def run_kubectl(req: CommandRequest, x_kubeconfig: Optional[str] = Header(None, alias="X-Kubeconfig")):
    """
    Execute a kubectl command.

    This endpoint receives a command and optionally a namespace and a kubeconfig.
    Kubeconfig can be provided either through request body or X-Kubeconfig header.
    Header takes precedence over request body parameter.
    """
    # Use header kubeconfig if provided, otherwise fall back to request body
    kubeconfig = x_kubeconfig or req.kubeconfig
    return await execute_command_logic("kubectl", req.command, req.namespace, kubeconfig)

@app.post("/tools/helm", 
          response_model=CommandResponse,
          operation_id="helm",
          summary="Execute helm commands", 
          description="Execute Helm package manager commands. Supports namespace parameter for deployments.")
async def run_helm(req: CommandRequest, x_kubeconfig: Optional[str] = Header(None, alias="X-Kubeconfig")):
    """
    Execute a helm command.

    This endpoint receives a command and optionally a namespace and a kubeconfig.
    Kubeconfig can be provided either through request body or X-Kubeconfig header.
    Header takes precedence over request body parameter.
    """
    # Use header kubeconfig if provided, otherwise fall back to request body
    kubeconfig = x_kubeconfig or req.kubeconfig
    return await execute_command_logic("helm", req.command, req.namespace, kubeconfig)

@app.post("/tools/istioctl", 
          response_model=CommandResponse,
          operation_id="istioctl",
          summary="Execute istioctl commands",
          description="Execute Istio service mesh commands for managing Istio configuration and troubleshooting.")
async def run_istioctl(req: CommandRequest, x_kubeconfig: Optional[str] = Header(None, alias="X-Kubeconfig")):
    """
    Execute an istioctl command.

    This endpoint receives a command and optionally a namespace and a kubeconfig.
    Kubeconfig can be provided either through request body or X-Kubeconfig header.
    Header takes precedence over request body parameter.
    """
    # Use header kubeconfig if provided, otherwise fall back to request body
    kubeconfig = x_kubeconfig or req.kubeconfig
    return await execute_command_logic("istioctl", req.command, req.namespace, kubeconfig)

@app.post("/tools/argocd", 
          response_model=CommandResponse,
          operation_id="argocd",
          summary="Execute argocd commands",
          description="Execute ArgoCD CLI commands for GitOps workflow management.")
async def run_argocd(req: CommandRequest, x_kubeconfig: Optional[str] = Header(None, alias="X-Kubeconfig")):
    """
    Execute an argocd command.

    This endpoint receives a command and optionally a namespace and a kubeconfig.
    Kubeconfig can be provided either through request body or X-Kubeconfig header.
    Header takes precedence over request body parameter.
    """
    # Use header kubeconfig if provided, otherwise fall back to request body
    kubeconfig = x_kubeconfig or req.kubeconfig
    return await execute_command_logic("argocd", req.command, req.namespace, kubeconfig)

# --- Health Check ---
@app.get("/health", 
         summary="Health check",
         description="Check if the server is running and healthy.")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "3.0.0"}

# --- Tool Status Check ---
@app.get("/tools/status",
         summary="Check tool availability", 
         description="Check which CLI tools are available on the system.")
async def check_tools_status():
    """Check which CLI tools are available."""
    status = {}
    
    # Different tools use different version commands
    version_commands = {
        "kubectl": ["version", "--client"],
        "helm": ["version"],
        "istioctl": ["version"],
        "argocd": ["version"]
    }
    
    for tool, description in SUPPORTED_CLI_TOOLS.items():
        try:
            version_cmd = version_commands.get(tool, ["--version"])
            process = await asyncio.create_subprocess_exec(
                tool, *version_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                status[tool] = {
                    "available": True,
                    "description": description,
                    "version": stdout.decode('utf-8', errors='replace').strip()
                }
            else:
                status[tool] = {
                    "available": False,
                    "description": description,
                    "error": stderr.decode('utf-8', errors='replace').strip()
                }
        except FileNotFoundError:
            status[tool] = {
                "available": False,
                "description": description,
                "error": f"{tool} not found in PATH"
            }
        except Exception as e:
            status[tool] = {
                "available": False,
                "description": description,
                "error": str(e)
            }
    
    return {"tools": status}

# --- Create and Mount MCP Server ---
# Create MCP server from the FastAPI app
mcp = FastApiMCP(
    app,
    name="K8s MCP Server",
    description="MCP server for Kubernetes CLI tools (kubectl, helm, istioctl, argocd)",
    include_operations=["kubectl", "helm", "istioctl", "argocd"]  # Only expose the tool endpoints as MCP tools
)

# Mount the MCP server to the FastAPI app
mcp.mount()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "9096"))
    host = os.getenv("HOST", "0.0.0.0")
    logger.info(f"Starting K8s MCP Server on {host}:{port}")
    logger.info(f"MCP endpoint available at: http://{host}:{port}/mcp")
    uvicorn.run(app, host=host, port=port) 