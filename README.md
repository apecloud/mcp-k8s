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
# Install uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the package using uv
uv pip install k8s-mcp-server

# Or install directly from source
git clone https://github.com/yourusername/k8s-mcp-server.git
cd k8s-mcp-server
uv pip install -e .

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

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Set up a virtual environment and install dependencies in one step with uv
uv venv -p 3.13

# Activate the virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
uv pip install -e ".[dev]"

# Alternatively, use the Makefile
make dev-install
```

### Running Tests

For unit tests (no Kubernetes cluster required):

```bash
# Run all unit tests only
pytest -m unit
# Or use the Makefile
make test-unit

# Run all tests (including both unit and integration)
pytest
# Or use the Makefile
make test

# Run specific test file
pytest tests/unit/test_server.py

# Run specific test function
pytest tests/unit/test_server.py::test_describe_command

# Run with coverage report 
pytest -m unit --cov=k8s_mcp_server --cov-report=term-missing
# Or use the Makefile
make test-coverage
```

### Running Integration Tests

Integration tests validate the command execution and response handling of k8s-mcp-server. By default, the tests use KWOK (Kubernetes Without Kubelet) to create a lightweight simulated Kubernetes cluster for testing.

#### Prerequisites

Integration tests require:
- `kubectl` installed and in your PATH
- `kwokctl` installed for the default KWOK-based testing (see below)
- Optional: `helm` for Helm-related tests
- Optional: A real Kubernetes cluster for advanced testing scenarios

#### Option 1: Using KWOK (Recommended)

[KWOK (Kubernetes Without Kubelet)](https://kwok.sigs.k8s.io/) provides a lightweight simulation of a Kubernetes cluster without requiring actual node or container execution. This is the default and recommended approach for running the integration tests.

1. **Install KWOK**:
   ```bash
   # For macOS with Homebrew:
   brew install kwokctl
   
   # For Linux or manual installation:
   KWOK_VERSION=$(curl -s https://api.github.com/repos/kubernetes-sigs/kwok/releases/latest | grep tag_name | cut -d '"' -f 4)
   curl -Lo kwokctl https://github.com/kubernetes-sigs/kwok/releases/download/${KWOK_VERSION}/kwokctl-$(go env GOOS)-$(go env GOARCH)
   curl -Lo kwok https://github.com/kubernetes-sigs/kwok/releases/download/${KWOK_VERSION}/kwok-$(go env GOOS)-$(go env GOARCH)
   chmod +x kwokctl kwok
   sudo mv kwokctl kwok /usr/local/bin/
   ```

2. **Run Integration Tests**:
   ```bash
   # Run all integration tests (KWOK cluster will be created automatically)
   pytest tests/integration -v
   
   # Run specific test
   pytest tests/integration/test_k8s_tools.py::test_kubectl_version -v
   
   # Skip cleanup of KWOK cluster for debugging
   K8S_SKIP_CLEANUP=true pytest tests/integration -v
   ```

The test framework will:
1. Automatically create a KWOK cluster for your tests
2. Run all integration tests against this cluster
3. Delete the cluster when tests complete (unless `K8S_SKIP_CLEANUP=true`)

Benefits of using KWOK:
- Extremely lightweight (no real containers or nodes)
- Fast startup and shutdown (seconds vs. minutes)
- Consistent and reproducible test environment
- No external dependencies or complex infrastructure

#### Option 2: Using Rancher Desktop

If you need to test against a real Kubernetes implementation, [Rancher Desktop](https://rancherdesktop.io/) provides a convenient way to run Kubernetes locally:

1. **Enable Kubernetes in Rancher Desktop**:
   - Open Rancher Desktop
   - Go to Preferences → Kubernetes
   - Ensure Kubernetes is enabled and running

2. **Configure Environment Variables**:
   ```bash
   # Required: Tell tests to use your existing cluster instead of KWOK
   export K8S_MCP_TEST_USE_EXISTING_CLUSTER=true
   
   # Optional: Specify Rancher Desktop context
   export K8S_CONTEXT=rancher-desktop
   
   # Optional: Skip cleanup of test namespaces
   export K8S_SKIP_CLEANUP=true
   ```

3. **Run Integration Tests**:
   ```bash
   pytest tests/integration -v
   ```

#### Option 3: Using Another Existing Kubernetes Cluster

For testing against production-like environments or specific Kubernetes distributions:

```bash
# Set required environment variables
export K8S_MCP_TEST_USE_EXISTING_CLUSTER=true

# Optionally specify a context
export K8S_CONTEXT=my-cluster-context

# Run the tests
pytest -m integration
```

This approach works with any Kubernetes distribution (EKS, GKE, AKS, k3s, k0s, etc.).

#### Option 4: Setting Up a Local Kubernetes Cluster for Development

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
| `K8S_MCP_TEST_USE_KWOK` | Use KWOK to create a test cluster | `true` |
| `K8S_MCP_TEST_USE_EXISTING_CLUSTER` | Use existing cluster instead of creating a new one | `false` |
| `K8S_CONTEXT` | Kubernetes context to use for tests | *current context* |
| `K8S_SKIP_CLEANUP` | Skip cleanup of test resources | `false` |

Example usage:

```bash
# Force using KWOK even if other variables are set
export K8S_MCP_TEST_USE_KWOK=true
pytest -m integration

# Use existing cluster with a specific context
export K8S_MCP_TEST_USE_EXISTING_CLUSTER=true
export K8S_CONTEXT=my-dev-cluster
pytest -m integration

# Skip cleanup of test resources (useful for debugging)
export K8S_SKIP_CLEANUP=true
pytest -m integration
```

#### Troubleshooting Integration Tests

1. **Authentication Issues**:
   - Ensure your kubeconfig is properly set up
   - Verify you can run `kubectl get pods` outside the tests

2. **Cluster Connection Errors**:
   - Check if your cluster is running with `kubectl cluster-info`
   - Verify networking between your machine and the cluster

3. **Permission Issues**:
   - The tests require permissions to create resources
   - Ensure your user/credentials have appropriate RBAC permissions

4. **Tool Installation**:
   - Some tests require specific tools like `helm`
   - Skip specific tests if you don't have all tools installed

#### Continuous Integration with GitHub Actions

The project includes GitHub Actions workflows that automatically run integration tests:

1. **CI Workflow**: Runs unit tests on every PR to ensure code quality
2. **Integration Tests Workflow**: Sets up a KWOK cluster and runs integration tests against it

The integration test workflow:
- Installs KWOK on the CI runner
- Creates a lightweight simulated Kubernetes cluster
- Installs all required CLI tools (kubectl, helm, istioctl, argocd)
- Runs all tests marked with the 'integration' marker
- Cleans up the KWOK cluster when done

You can also manually trigger the integration tests from the GitHub Actions tab, with an option to enable debugging if needed.

#### Why KWOK for Testing?

KWOK (Kubernetes Without Kubelet) provides significant advantages for testing Kubernetes command execution:

1. **Lightweight and Fast**: KWOK clusters start in seconds without requiring container runtime
2. **Focus on API Interaction**: Perfect for testing Kubernetes CLI commands and API responses
3. **Consistent Environment**: Provides deterministic responses for predictable testing
4. **Resource Efficiency**: Eliminates the overhead of running actual containers or nodes
5. **CI/CD Friendly**: Ideal for continuous integration pipelines with minimal resource requirements

Since our integration tests primarily validate command formation, execution, and output parsing rather than actual workload behavior, KWOK provides an ideal balance of fidelity and efficiency.

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