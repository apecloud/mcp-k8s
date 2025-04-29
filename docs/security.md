# Security Configuration

K8s MCP Server includes several safety features and security configurations to ensure safe operation when interacting with Kubernetes clusters.

## Security Modes

K8s MCP Server supports two security modes:

- **Strict Mode** (default): All commands are validated against security rules
- **Permissive Mode**: Security validation is skipped, allowing all commands to execute

### Setting Security Mode

To run in permissive mode (allow all commands):

```json
{
  "mcpServers": {
    "k8s-mcp-server": {
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

## Security Features

- **Isolation**: When running in Docker, the server operates in an isolated container environment
- **Read-only access**: All credentials and configuration files are mounted as read-only
- **Non-root execution**: All processes run as a non-root user inside the container
- **Command validation**: Potentially dangerous commands require explicit resource names
- **Context separation**: Automatic context and namespace injection for commands

## Customizing Security Rules

Security rules can be customized using a YAML configuration file. This allows for more flexibility than the built-in rules.

1. **Create a Security Configuration File**:
   Create a YAML file with your custom rules (e.g., `security_config.yaml`):

   ```yaml
   # Security configuration for k8s-mcp-server
   
   # Potentially dangerous command patterns (prefix-based)
   dangerous_commands:
     kubectl:
       - "kubectl delete"
       - "kubectl drain"
       # Add your custom dangerous commands here
   
   # Safe pattern overrides (prefix-based)
   safe_patterns:
     kubectl:
       - "kubectl delete pod"
       - "kubectl delete deployment"
       # Add your custom safe patterns here
   
   # Advanced regex pattern rules
   regex_rules:
     kubectl:
       - pattern: "kubectl\\s+delete\\s+(-[A-Za-z]+\\s+)*--all\\b"
         description: "Deleting all resources of a type"
         error_message: "Deleting all resources is restricted. Specify individual resources to delete."
       # Add your custom regex rules here
   ```

2. **Mount the Configuration File in Docker**:
   ```json
   {
     "mcpServers": {
       "k8s-mcp-server": {
         "command": "docker",
         "args": [
           "run",
           "-i",
           "--rm",
           "-v",
           "/Users/YOUR_USER_NAME/.kube:/home/appuser/.kube:ro",
           "-v",
           "/path/to/security_config.yaml:/app/security_config.yaml:ro",
           "-e",
           "K8S_MCP_SECURITY_CONFIG=/app/security_config.yaml",
           "ghcr.io/alexei-led/k8s-mcp-server:latest"
         ]
       }
     }
   }
   ```

## Configuration Structure

The security configuration YAML file has three main sections:

1. **dangerous_commands**: Dictionary of command prefixes that are considered dangerous for each tool
2. **safe_patterns**: Dictionary of command prefixes that override dangerous commands (exceptions)
3. **regex_rules**: Advanced regex patterns for more complex validation rules

Each regex rule should include:
- **pattern**: Regular expression pattern to match against commands
- **description**: Description of what the rule checks for
- **error_message**: Custom error message to display when the rule is violated

## Examples

**Example 1: Restricting Namespace Operations**

```yaml
regex_rules:
  kubectl:
    - pattern: "kubectl\\s+.*\\s+--namespace=kube-system\\b"
      description: "Operations in kube-system namespace"
      error_message: "Operations in kube-system namespace are restricted."
```

**Example 2: Allowing Additional Safe Patterns**

```yaml
safe_patterns:
  kubectl:
    - "kubectl delete pod"
    - "kubectl delete job"
    - "kubectl delete cronjob"
```

**Example 3: Restricting Dangerous File System Access**

```yaml
regex_rules:
  kubectl:
    - pattern: "kubectl\\s+exec\\s+.*\\s+-[^-]*c\\s+.*(rm|mv|cp|curl|wget|chmod)\\b"
      description: "Dangerous file operations in exec"
      error_message: "File system operations within kubectl exec are restricted."
```