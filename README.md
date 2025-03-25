# K8s MCP Server

[![CI Status](https://github.com/yourusername/k8s-mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/k8s-mcp-server/actions/workflows/ci.yml)
[![Release Status](https://github.com/yourusername/k8s-mcp-server/actions/workflows/release.yml/badge.svg)](https://github.com/yourusername/k8s-mcp-server/actions/workflows/release.yml)
[![codecov](https://codecov.io/gh/yourusername/k8s-mcp-server/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/k8s-mcp-server)
[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker Pulls](https://img.shields.io/docker/pulls/yourusername/k8s-mcp-server.svg)](https://github.com/yourusername/k8s-mcp-server/pkgs/container/k8s-mcp-server)

K8s MCP Server is a server for [Anthropic's MCP (Model Context Protocol)](https://www.anthropic.com/news/introducing-mcp) that allows running Kubernetes CLI tools such as `kubectl`, `istioctl`, `helm`, and `argocd` in a safe, containerized environment.

## Features

- Execute Kubernetes CLI commands securely with proper validation, timeouts and error handling
- Support for multiple Kubernetes CLI tools:
  - `kubectl`: Kubernetes command-line tool
  - `istioctl`: Command-line tool for Istio service mesh
  - `helm`: Kubernetes package manager
  - `argocd`: GitOps continuous delivery tool for Kubernetes
- Command piping capabilities with popular Linux CLI tools
- Detailed command validation and safety checks
- Configurable timeouts and output limits
- Comprehensive documentation and help retrieval
- Context and namespace management
- Pre-built prompt templates for common Kubernetes operations

## Installation

### Option 1: Docker (Recommended)

The Docker deployment is the recommended approach for security, isolation, and resilience:

```bash
# Pull the pre-built image
docker pull ghcr.io/yourusername/k8s-mcp-server:latest

# Run with your Kubernetes configuration mounted
docker run -p 8080:8080 -v ~/.kube:/home/appuser/.kube:ro ghcr.io/yourusername/k8s-mcp-server:latest
```

Or using Docker Compose:

```bash
# Clone the repository
git clone https://github.com/yourusername/k8s-mcp-server.git
cd k8s-mcp-server

# Start the server
docker-compose -f deploy/docker/docker-compose.yml up -d
```

### Option 2: Python Package

For development or when Docker is not available:

```bash
# Install the package
pip install k8s-mcp-server

# Start the server
python -m k8s_mcp_server
```

## Requirements

### For Docker deployment:
- Docker
- Valid Kubernetes configuration in `~/.kube/config`

### For Python package:
- Python 3.13 or later
- kubectl, istioctl, helm, and/or argocd binaries installed and in PATH
- Active kubeconfig configuration

## Configuration

K8s MCP Server can be configured via environment variables:

| Environment Variable | Description | Default |
|----------------------|-------------|---------|
| `K8S_MCP_HOST` | Host to bind the server | `0.0.0.0` |
| `K8S_MCP_PORT` | Port to run the server on | `8080` |
| `K8S_MCP_TIMEOUT` | Default timeout for commands (seconds) | `300` |
| `K8S_MCP_MAX_OUTPUT` | Maximum output size (characters) | `100000` |
| `K8S_CONTEXT` | Kubernetes context to use | *current context* |
| `K8S_NAMESPACE` | Default Kubernetes namespace | `default` |
| `K8S_MCP_LOG_DIR` | Directory for logs | `./logs` |

### Setting Environment Variables

#### With Docker:

```bash
docker run -p 8080:8080 \
  -v ~/.kube:/home/appuser/.kube:ro \
  -e K8S_CONTEXT=my-cluster \
  -e K8S_NAMESPACE=my-namespace \
  -e K8S_MCP_TIMEOUT=600 \
  ghcr.io/yourusername/k8s-mcp-server:latest
```

#### With Docker Compose:

Edit the environment section in `deploy/docker/docker-compose.yml`:

```yaml
environment:
  - K8S_CONTEXT=my-cluster
  - K8S_NAMESPACE=my-namespace
  - K8S_MCP_TIMEOUT=600
```

#### With Python:

```bash
export K8S_CONTEXT=my-cluster
export K8S_NAMESPACE=my-namespace
python -m k8s_mcp_server
```

## API Reference

The server implements the [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/agents-and-tools/model-context-protocol-mcp/) and provides the following tools:

### Documentation Tools

Each Kubernetes CLI tool has its own documentation function:

- `describe_kubectl(command=None)`: Get documentation for kubectl commands
- `describe_helm(command=None)`: Get documentation for Helm commands
- `describe_istioctl(command=None)`: Get documentation for Istio commands
- `describe_argocd(command=None)`: Get documentation for ArgoCD commands

### Execution Tools

Each Kubernetes CLI tool has its own execution function:

- `execute_kubectl(command, timeout=None)`: Execute kubectl commands
- `execute_helm(command, timeout=None)`: Execute Helm commands
- `execute_istioctl(command, timeout=None)`: Execute Istio commands
- `execute_argocd(command, timeout=None)`: Execute ArgoCD commands

### Command Piping

All execution tools support Unix command piping to filter and transform output:

```python
execute_kubectl(command="get pods -o json | jq '.items[].metadata.name'")
execute_helm(command="list | grep nginx")
```

## Supported Tools and Commands

### kubectl

Execute and manage Kubernetes resources:

```
kubectl get pods
kubectl get deployments
kubectl describe pod my-pod
```

### istioctl

Manage Istio service mesh configuration:

```
istioctl analyze
istioctl proxy-status
istioctl dashboard
```

### helm

Manage Helm charts and releases:

```
helm list
helm install my-release my-chart
helm upgrade my-release my-chart
```

### argocd

Manage ArgoCD applications:

```
argocd app list
argocd app get my-app
argocd app sync my-app
```

## Security Considerations

The server includes several safety features:

- **Isolation**: When running in Docker, the server operates in an isolated container environment
- **Read-only access**: Mount Kubernetes configuration as read-only (`-v ~/.kube:/home/appuser/.kube:ro`)
- **Non-root execution**: All processes run as a non-root user inside the container
- **Command validation**: Potentially dangerous commands require explicit resource names
- **Context separation**: Automatic context and namespace injection for commands

## Development

### Setting Up the Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/k8s-mcp-server.git
cd k8s-mcp-server

# Set up a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

### Running Tests

For unit tests (no Kubernetes cluster required):

```bash
# Run all unit tests only
pytest -m unit

# Run all tests (including both unit and integration)
pytest

# Run specific test file
pytest tests/unit/test_server.py

# Run specific test function
pytest tests/unit/test_server.py::test_describe_command

# Run with coverage report 
pytest -m unit --cov=k8s_mcp_server --cov-report=term-missing
```

### Running Integration Tests

Integration tests require a functioning Kubernetes cluster. You can either use an existing cluster or set up a local one.

#### Option 1: Using an Existing Kubernetes Cluster

The simplest approach is to use an existing Kubernetes cluster by specifying which context to use:

```bash
# Run integration tests with the currently active context
pytest -m integration

# Run with a specific context
K8S_CONTEXT=my-cluster-context pytest -m integration

# Run specific integration test file
pytest tests/integration/test_k8s_tools.py
```

Benefits of this approach:
- No need to set up a separate cluster for testing
- Works with any Kubernetes distribution (EKS, GKE, AKS, k3s, k0s, etc.)
- Tests run against the same environment you're developing for
- Faster test execution since there's no cluster setup/teardown

#### Option 2: Setting Up a Local Kubernetes Cluster for Development

For local development, we recommend setting up a lightweight Kubernetes cluster:

**Using k3s (Recommended for Linux):**

[k3s](https://k3s.io/) is a certified lightweight Kubernetes distribution:

```bash
# Install k3s
curl -sfL https://get.k3s.io | sh -

# Get kubeconfig (sudo is required to read the config)
sudo cat /etc/rancher/k3s/k3s.yaml > ~/.kube/k3s-config
# Fix permissions
chmod 600 ~/.kube/k3s-config
# Set KUBECONFIG to use this file
export KUBECONFIG=~/.kube/k3s-config

# Verify it's running
kubectl get nodes
```

**Using k0s (Recommended for all platforms):**

[k0s](https://k0sproject.io/) is a zero-friction Kubernetes distribution:

```bash
# Install k0s
curl -sSLf https://get.k0s.sh | sh

# Create a single-node cluster
sudo k0s install controller --single
sudo k0s start

# Get kubeconfig
sudo k0s kubeconfig admin > ~/.kube/k0s-config
chmod 600 ~/.kube/k0s-config
export KUBECONFIG=~/.kube/k0s-config

# Verify it's running
kubectl get nodes
```

**Using Minikube:**

[Minikube](https://minikube.sigs.k8s.io/docs/start/) creates a local Kubernetes cluster within a VM or container:

```bash
# Install Minikube
# macOS with Homebrew:
brew install minikube

# Start a cluster
minikube start

# Verify it's running
kubectl get nodes
```

**Using Kind (Kubernetes in Docker):**

[Kind](https://kind.sigs.k8s.io/docs/user/quick-start/) runs Kubernetes clusters using Docker containers as nodes:

```bash
# Install Kind
# macOS with Homebrew:
brew install kind

# Create a cluster
kind create cluster --name k8s-mcp-test

# Verify it's running
kubectl get nodes
```

**Using K3d (Lightweight Kubernetes):**

[K3d](https://k3d.io/) is a lightweight wrapper to run [k3s](https://k3s.io/) in Docker:

```bash
# Install K3d
# macOS with Homebrew:
brew install k3d

# Create a cluster
k3d cluster create k8s-mcp-test

# Verify it's running
kubectl get nodes
```

### Integration Test Process

Integration tests validate the functionality of k8s-mcp-server against a real Kubernetes cluster. They:

1. Verify that CLI tools work correctly when executed through the server
2. Test namespace creation and management
3. Deploy test pods to verify resource creation works
4. Test help text retrieval for commands
5. Verify tool-specific features (kubectl, helm, etc.)

Integration tests are automatically skipped if:
- No Kubernetes cluster is available
- Required CLI tools (kubectl, helm, etc.) aren't installed

#### Environment Variables for Integration Tests

You can customize the integration tests with these environment variables:

| Environment Variable | Description | Default |
|----------------------|-------------|---------|
| `K8S_CONTEXT` | Kubernetes context to use for tests | *current context* |
| `K8S_SKIP_CLEANUP` | Skip cleanup of test resources | `False` |

Example usage:

```bash
# Use a specific context
K8S_CONTEXT=my-dev-cluster pytest -m integration

# Skip cleanup of test resources (useful for debugging)
K8S_SKIP_CLEANUP=true pytest -m integration
```

#### Continuous Integration with GitHub Actions

The project includes GitHub Actions workflows that automatically run integration tests:

1. **CI Workflow**: Runs unit tests on every PR to ensure code quality
2. **Integration Tests Workflow**: Sets up a Kind (Kubernetes in Docker) cluster and runs integration tests against it

The integration test workflow:
- Sets up a single-node Kind cluster
- Installs all required CLI tools (kubectl, helm, istioctl, argocd)
- Runs all tests marked with the 'integration' marker

You can also manually trigger the integration tests from the GitHub Actions tab, with an option to enable debugging if needed.

## Building from Source

### Building the Docker Image

```bash
# Clone the repository
git clone https://github.com/yourusername/k8s-mcp-server.git
cd k8s-mcp-server

# Build the image
docker build -t k8s-mcp-server -f deploy/docker/Dockerfile .

# For multi-architecture builds
docker buildx create --name mybuilder --use
docker buildx build --platform linux/amd64,linux/arm64 \
  -t yourusername/k8s-mcp-server:latest \
  -f deploy/docker/Dockerfile .
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please make sure your code passes the existing tests and linting. Add new tests for new functionality.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.