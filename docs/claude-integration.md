# Integrating with Claude Desktop

This guide details how to integrate K8s MCP Server with Claude Desktop.

## Setting Up Claude Desktop

1. **Locate the Claude Desktop configuration file**:
   - macOS: `/Users/YOUR_USER_NAME/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. **Edit the configuration file** to include the K8s MCP Server:
   ```json
   {
     "mcpServers": {
       "kubernetes": {
         "command": "docker",
         "args": [
           "run",
           "-i",
           "--rm",
           "-v",
           "/Users/YOUR_USER_NAME/.kube:/home/appuser/.kube:ro",
           "ghcr.io/alexei-led/k8s-mcp-server:latest"
         ]
       }
     }
   }
   ```

   > **Note**: Make sure to replace `/Users/YOUR_USER_NAME/.kube` with the absolute path to your Kubernetes configuration directory, and update the image name if using a custom image.

3. **Restart Claude Desktop** to apply the changes
   - After restarting, you should see a hammer 🔨 icon in the bottom right corner of the input box
   - This indicates that the K8s MCP Server is available for use

## Common Configuration Examples

### Basic Configuration with Specific Namespace

```json
{
  "mcpServers": {
    "kubernetes": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-v",
        "/Users/YOUR_USER_NAME/.kube:/home/appuser/.kube:ro",
        "-e",
        "K8S_CONTEXT=my-cluster",
        "-e",
        "K8S_NAMESPACE=my-namespace",
        "ghcr.io/alexei-led/k8s-mcp-server:latest"
      ]
    }
  }
}
```

### Permissive Mode Configuration

To run in permissive mode (allow all commands, including potentially dangerous ones):

```json
{
  "mcpServers": {
    "kubernetes": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-v",
        "/Users/YOUR_USER_NAME/.kube:/home/appuser/.kube:ro",
        "-e",
        "K8S_MCP_SECURITY_MODE=permissive",
        "ghcr.io/alexei-led/k8s-mcp-server:latest"
      ]
    }
  }
}
```

### Custom Security Configuration

To use a custom security configuration file:

```json
{
  "mcpServers": {
    "kubernetes": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-v",
        "/Users/YOUR_USER_NAME/.kube:/home/appuser/.kube:ro",
        "-v",
        "/path/to/my-security-config.yaml:/app/security_config.yaml:ro",
        "-e",
        "K8S_MCP_SECURITY_CONFIG=/app/security_config.yaml",
        "ghcr.io/alexei-led/k8s-mcp-server:latest"
      ]
    }
  }
}
```

## Using Kubernetes Tools in Claude

Once configured, you can ask Claude to perform Kubernetes operations:

- "Show me the pods in my default namespace using kubectl"
- "Help me deploy a new application with Helm"
- "Check the status of my Istio service mesh"
- "List all my Kubernetes deployments"

Claude will automatically use the appropriate Kubernetes CLI tools via the K8s MCP Server.

## Troubleshooting

1. **Missing Tools Icon**: If you don't see the hammer icon, check that:
   - Claude Desktop is properly restarted
   - The configuration file is correctly formatted
   - The specified paths are accessible

2. **Permission Issues**: Make sure that:
   - Your `.kube` directory has correct permissions (600 for the files)
   - The Docker container has read access to your configuration files

3. **Command Execution Fails**: Verify that:
   - Your Kubernetes context is valid and accessible
   - The command isn't being blocked by security rules (consider permissive mode for testing)
   - The timeout is sufficient for the command to complete