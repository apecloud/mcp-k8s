# Getting Started with K8s MCP Server

This guide will help you quickly set up and configure K8s MCP Server to work with your Kubernetes clusters.

## Prerequisites

Before starting, ensure you have:

- Docker installed on your system
- Valid Kubernetes configuration file (`~/.kube/config`)
- Claude Desktop application installed (if using with Claude)

## Quick Start

### 1. Run K8s MCP Server Using Docker

The simplest way to run K8s MCP Server:

```bash
docker run -i --rm \
  -v ~/.kube:/home/appuser/.kube:ro \
  ghcr.io/alexei-led/k8s-mcp-server:latest
```

### 2. Configure Claude Desktop

To integrate with Claude Desktop, edit your Claude Desktop configuration file (see [Claude Integration](./claude-integration.md) for details).

### 3. Test the Connection

Once configured, prompt Claude with a simple Kubernetes command like:

"Show me the pods in my default namespace using kubectl"

## Basic Configuration Options

K8s MCP Server can be configured using environment variables:

```bash
docker run -i --rm \
  -v ~/.kube:/home/appuser/.kube:ro \
  -e K8S_CONTEXT=my-cluster \
  -e K8S_NAMESPACE=my-namespace \
  -e K8S_MCP_TIMEOUT=600 \
  ghcr.io/alexei-led/k8s-mcp-server:latest
```

Common environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `K8S_CONTEXT` | Kubernetes context to use | *current context* |
| `K8S_NAMESPACE` | Default namespace | `default` |
| `K8S_MCP_TIMEOUT` | Command timeout (seconds) | `300` |
| `K8S_MCP_SECURITY_MODE` | Security mode ("strict"/"permissive") | `strict` |

See [Environment Variables](./environment-variables.md) for a complete list.

## Cloud Provider Configuration

K8s MCP Server supports major cloud Kubernetes providers:

### AWS EKS

```bash
docker run -i --rm \
  -v ~/.kube:/home/appuser/.kube:ro \
  -v ~/.aws:/home/appuser/.aws:ro \
  -e AWS_REGION=us-west-2 \
  ghcr.io/alexei-led/k8s-mcp-server:latest
```

### Google GKE

```bash
docker run -i --rm \
  -v ~/.kube:/home/appuser/.kube:ro \
  -v ~/.config/gcloud:/home/appuser/.config/gcloud:ro \
  -e CLOUDSDK_CORE_PROJECT=my-project \
  -e CLOUDSDK_COMPUTE_REGION=us-central1 \
  ghcr.io/alexei-led/k8s-mcp-server:latest
```

### Azure AKS

```bash
docker run -i --rm \
  -v ~/.kube:/home/appuser/.kube:ro \
  -v ~/.azure:/home/appuser/.azure:ro \
  -e AZURE_SUBSCRIPTION=my-subscription-id \
  ghcr.io/alexei-led/k8s-mcp-server:latest
```

For more detailed information about cloud provider configuration, see [Cloud Provider Documentation](./cloud-providers.md).

## Security Configuration

By default, K8s MCP Server runs in strict security mode, which prevents potentially dangerous Kubernetes commands.

To run in permissive mode:

```bash
docker run -i --rm \
  -v ~/.kube:/home/appuser/.kube:ro \
  -e K8S_MCP_SECURITY_MODE=permissive \
  ghcr.io/alexei-led/k8s-mcp-server:latest
```

For custom security rules, see [Security Documentation](./security.md).

## What's Next?

- Learn about [Claude Integration](./claude-integration.md)
- Explore [Supported CLI Tools](./supported-tools.md)
- Understand [Security Features](./security.md)
- See all [Environment Variables](./environment-variables.md)