# Kubernetes MCP Server Specification

## Project Overview

The **Kubernetes MCP Server** provides a lightweight interface enabling AI assistants to execute Kubernetes CLI tools through the Model Context Protocol (MCP). This service bridges AI assistants like Claude Desktop with essential Kubernetes tooling (`kubectl`, `istioctl`, `helm`, `argocd`), allowing AI systems to help with Kubernetes deployments, configurations, troubleshooting, and optimization.

### Key Objectives

- **Command Documentation**: Provide detailed help information for Kubernetes CLI tools
- **Command Execution**: Execute commands for Kubernetes tools, returning raw results
- **MCP Compliance**: Fully implement the standard Model Context Protocol
- **Piped Commands**: Support Unix pipe operations to filter and transform command output
- **Secure Execution**: Execute commands with proper security measures
- **Tool Extensibility**: Maintain a design that easily accommodates new Kubernetes-related CLI tools
- **Consistent Output**: Preserve original tool output format for AI processing
- **Open Source**: Release under MIT license as a community resource

## Core Features

### 1. Tool-Specific Command Documentation

Each supported tool has a dedicated documentation function:

#### `describe_kubectl`
Retrieves help information for kubectl commands:

```json
{
  "name": "describe_kubectl",
  "description": "Get documentation and help text for kubectl commands",
  "parameters": {
    "command": {
      "type": "string",
      "description": "Specific command or subcommand to get help for (e.g., 'get pods')",
      "required": false
    }
  },
  "returns": {
    "help_text": "string",
    "status": "string",
    "error": "string (if status is error)"
  }
}
```

#### `describe_helm`
Retrieves help information for Helm commands.

#### `describe_istioctl`
Retrieves help information for Istio commands.

#### `describe_argocd`
Retrieves help information for ArgoCD commands.

**Example Usage:**
```
describe_kubectl({"command": "get pods"})
// Returns specific documentation for the kubectl get pods command
```

### 2. Tool-Specific Command Execution

Each supported tool has a dedicated execution function:

#### `execute_kubectl`
Executes kubectl commands:

```json
{
  "name": "execute_kubectl",
  "description": "Execute kubectl commands with support for Unix pipes",
  "parameters": {
    "command": {
      "type": "string",
      "description": "Complete kubectl command to execute (including any pipes and flags)",
      "required": true
    },
    "timeout": {
      "type": "integer",
      "description": "Maximum execution time in seconds (default: 300)",
      "required": false,
      "minimum": 1,
      "maximum": 1800
    }
  },
  "returns": {
    "output": "string",
    "error": "string",
    "status": "string",
    "exit_code": "integer",
    "execution_time": "number"
  }
}
```

#### `execute_helm`
Executes Helm commands.

#### `execute_istioctl`
Executes Istio commands.

#### `execute_argocd`
Executes ArgoCD commands.

**Example Usage:**
```
execute_kubectl({"command": "get pods -o json"})
// Returns JSON format output for pods

execute_helm({"command": "list", "timeout": 60})
// Lists all Helm releases with a 60-second timeout
```

### 3. AI-Driven Format Selection

The server relies on AI clients to specify output formats:

- AI clients are responsible for adding appropriate format flags (`-o json`, `-o yaml`, etc.)
- No automatic output format transformation by the server
- Raw command output is returned exactly as produced by the CLI tools
- AI clients can use pipe operators to process output as needed

**Examples:**
```
# JSON format for structured data processing
execute_kubectl({"command": "get pods -o json"})

# YAML format for configuration purposes
execute_kubectl({"command": "get deployment nginx -o yaml"})

# Wide output for human review
execute_kubectl({"command": "get pods -o wide"})
```

### 4. Context Management

The server provides capabilities for managing Kubernetes contexts:

- Support context switching through command parameters
- Clear error messages for authentication and context issues
- Support for multi-cluster environments

**Examples:**
```
execute_kubectl({"command": "config use-context dev-cluster"})
// Switches to the dev-cluster context

execute_kubectl({"command": "config get-contexts"})
// Lists all available contexts

execute_kubectl({"command": "--context=prod-cluster get pods"})
// Runs the command against the prod-cluster without changing the default context
```

### 5. Command Piping

Support for Unix command piping enhances functionality:

- Standard Unix utilities can be piped with Kubernetes commands
- Common filtering tools are supported (`grep`, `awk`, `sed`, etc.)
- Data manipulation tools like `jq` and `yq` are available

**Supported Unix Commands:**
- Text processing: `grep`, `sed`, `awk`, `cut`, `sort`, `uniq`, `wc`, `head`, `tail`
- Data manipulation: `jq`, `yq`, `xargs`
- File operations: `ls`, `cat`, `find`

**Examples:**
```
execute_kubectl({"command": "get pods -o json | jq '.items[].metadata.name'"})
// Extracts just the pod names from JSON output

execute_kubectl({"command": "get pods | grep Running | wc -l"})
// Counts the number of running pods
```

### 6. Tool Extension Approach

The server follows a standard pattern for adding new Kubernetes-related CLI tools:

- Consistent interface design across all supported tools
- Well-defined parameter patterns and return formats
- Standardized error handling

**Tool Configuration Principles:**
- Each tool must define its allowed commands
- Each tool provides its own documentation function
- Each tool provides its own execution function

## Architecture

### Component Overview

The Kubernetes MCP Server consists of these logical components:

```
┌─────────────────┐         ┌─────────────────┐
│   MCP Client    │         │  MCP Interface  │
│  (AI Assistant) │         │                 │
└─────────────────┘         └────────┬────────┘
        ▲                            │
        │                            ▼
        │                   ┌─────────────────┐
        │                   │  Tool Commands  │
        │                   │ (Execution and  │
        │                   │ Documentation)  │
        │                   └────────┬────────┘
        │                            │
        │                            ▼
        │                   ┌─────────────────┐
        │                   │Security Validator│
        │                   └────────┬────────┘
        │                            │
        │                            ▼
        │                   ┌─────────────────┐
        │                   │  CLI Executor   │
        │                   └────────┬────────┘
        │                            │
        └────────────────────────────┘
```

### Component Responsibilities

1. **MCP Interface**
   - Implements MCP protocol endpoints
   - Handles tool requests and responses
   - Manages client connections and capability negotiation

2. **Tool Commands**
   - Processes documentation requests
   - Processes execution requests
   - Validates parameters and formats responses

3. **Security Validator**
   - Validates commands against security policies
   - Checks for prohibited operations
   - Enforces command restrictions

4. **CLI Executor**
   - Executes CLI commands securely
   - Captures standard output and error streams
   - Handles timeouts and resource limitations

### Security Model

Security principles for the Kubernetes MCP Server include:

1. **Command Validation**
   - Allowlist-based approach for permitted commands
   - Validation of all command inputs against injection attacks
   - Pipe chain validation for authorized utilities only

2. **Execution Security**
   - Resource limitations (CPU, memory, time)
   - Restricted permissions for command execution
   - Isolation of command execution environments

3. **Authentication Security**
   - Read-only access to kubeconfig
   - No storage of sensitive credentials
   - Validation of authentication contexts

### Error Handling Framework

A consistent error handling approach ensures clear communication:

1. **Error Categories**
   - Command validation errors
   - Authentication errors
   - Execution errors
   - Resource errors
   - Internal system errors

2. **Standard Error Format**
   ```json
   {
     "status": "error",
     "error": {
       "message": "Clear error message",
       "code": "ERROR_CODE",
       "details": {
         "command": "original command",
         "exit_code": 1,
         "stderr": "detailed error output"
       }
     }
   }
   ```

3. **Common Error Messages**
   - Invalid tool: "Tool not found. Available tools: kubectl, helm, istioctl, argocd."
   - Restricted command: "Command is restricted for security reasons."
   - Context errors: "Context not found in kubeconfig. Available contexts: [list]."
   - Timeout errors: "Command timed out after N seconds."

### Configuration Principles

Configuration for the Kubernetes MCP Server follows these principles:

1. **Core Configuration Areas**
   - Server settings (host, port, logging)
   - Tool settings (paths, allowed commands)
   - Security settings (restrictions, allowed pipes)
   - Authentication settings (kubeconfig handling)

2. **Configuration Layering**
   - Default sensible configurations built-in
   - Configuration overrides through external means
   - Environment-specific settings

## Conclusion

This Kubernetes MCP Server specification outlines a focused approach to providing Kubernetes CLI capabilities to AI assistants through the Model Context Protocol. By emphasizing clean interfaces, security, and flexibility, the specification supports a system that can serve as a bridge between AI assistants and Kubernetes environments.

The design prioritizes tool-specific commands rather than generic interfaces, enabling clearer usage patterns and more robust parameter validation. The security model focuses on principles rather than implementation details, allowing for various secure implementations. The error handling framework ensures consistent and clear communication of issues to clients.

By removing implementation details like directory structures, deployment configurations, and specific code examples, this specification serves as a conceptual guide that can be implemented in various programming languages and deployment environments.