"""Integration tests for Kubernetes CLI tools.

These tests require a functioning Kubernetes cluster and installed CLI tools.
When running with the 'integration' marker, the k0s_cluster fixture will automatically 
set up a lightweight k0s cluster for testing.
"""

import subprocess
from collections.abc import Generator

import pytest

from k8s_mcp_server.server import (
    describe_kubectl,
    execute_helm,
    execute_kubectl,
)

try:
    from tests.integration.k0s_fixture import k0s_cluster
except ImportError:
    # This allows the module to be imported even if k0s_fixture is not available
    pass


@pytest.fixture
def ensure_cluster_running(pytestconfig) -> Generator[bool]:
    """Check if a Kubernetes cluster is available and running.

    When tests are run with the 'integration' marker, this fixture will:
    1. Use the k0s_cluster fixture to set up a temporary test cluster if available
    2. Skip tests if no cluster can be found

    For manual cluster setup, you can use:
    - minikube: https://minikube.sigs.k8s.io/docs/start/
    - kind: https://kind.sigs.k8s.io/docs/user/quick-start/
    - k3d: https://k3d.io/
    - k0s: https://k0sproject.io/

    Returns:
        True if cluster is running, raises skip exception otherwise
    """
    # Try to reach the Kubernetes API
    try:
        result = subprocess.run(["kubectl", "cluster-info"], capture_output=True, timeout=5)
        if result.returncode != 0:
            pytest.skip("Kubernetes cluster is not available.")

        # Check if kubectl is working
        result = subprocess.run(["kubectl", "get", "nodes"], capture_output=True, timeout=5)
        if result.returncode != 0:
            pytest.skip("kubectl cannot list nodes. Check your cluster setup.")

        yield True
    except (subprocess.SubprocessError, FileNotFoundError):
        pytest.skip("kubectl command failed or is not installed.")


@pytest.fixture
def test_namespace(ensure_cluster_running) -> Generator[str]:
    """Create a test namespace and clean it up after tests.

    This fixture:
    1. Creates a dedicated test namespace
    2. Yields the namespace name for tests to use
    3. Cleans up the namespace after tests complete

    Args:
        ensure_cluster_running: Fixture that ensures a cluster is available

    Returns:
        The name of the test namespace
    """
    namespace = "k8s-mcp-test"

    try:
        # Check if namespace already exists
        result = subprocess.run(
            ["kubectl", "get", "namespace", namespace],
            capture_output=True,
            check=False
        )

        if result.returncode != 0:
            # Create namespace if it doesn't exist
            create_result = subprocess.run(
                ["kubectl", "create", "namespace", namespace],
                capture_output=True,
                check=False
            )

            if create_result.returncode != 0:
                print(f"Warning: Failed to create namespace: {create_result.stderr.decode()}")
    except Exception as e:
        print(f"Warning: Error when setting up test namespace: {e}")

    yield namespace

    try:
        # Clean up namespace
        subprocess.run(
            ["kubectl", "delete", "namespace", namespace, "--wait=false"],
            capture_output=True
        )
    except Exception as e:
        print(f"Warning: Error when cleaning up test namespace: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_kubectl_version(k0s_cluster, ensure_cluster_running):
    """Test that kubectl version command works."""
    result = await execute_kubectl(command="version --client")

    assert result["status"] == "success"
    assert "Client Version" in result["output"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_kubectl_get_pods(k0s_cluster, ensure_cluster_running, test_namespace):
    """Test that kubectl can list pods in the test namespace."""
    # First create a test pod
    pod_manifest = f"""
    apiVersion: v1
    kind: Pod
    metadata:
      name: test-pod
      namespace: {test_namespace}
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
    """

    with open("/tmp/test-pod.yaml", "w") as f:
        f.write(pod_manifest)

    create_result = await execute_kubectl(command=f"apply -f /tmp/test-pod.yaml -n {test_namespace}")
    assert create_result["status"] == "success"

    # Give the pod some time to be created
    import asyncio

    await asyncio.sleep(2)

    # Now test listing pods
    result = await execute_kubectl(command=f"get pods -n {test_namespace}")

    assert result["status"] == "success"
    assert "test-pod" in result["output"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_kubectl_help(k0s_cluster, ensure_cluster_running):
    """Test that kubectl help command works."""
    result = await describe_kubectl(command="get")

    assert "help_text" in result
    assert "Display one or many resources" in result["help_text"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_helm_version(k0s_cluster, ensure_cluster_running):
    """Test that helm version command works."""
    # Skip if helm is not installed
    try:
        subprocess.run(["helm", "version"], capture_output=True, timeout=5)
    except (subprocess.SubprocessError, FileNotFoundError):
        pytest.skip("helm is not installed")

    result = await execute_helm(command="version")

    assert result["status"] == "success"
    assert "version.BuildInfo" in result["output"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_helm_list(k0s_cluster, ensure_cluster_running):
    """Test that helm list command works."""
    # Skip if helm is not installed
    try:
        subprocess.run(["helm", "version"], capture_output=True, timeout=5)
    except (subprocess.SubprocessError, FileNotFoundError):
        pytest.skip("helm is not installed")

    result = await execute_helm(command="list")

    assert result["status"] == "success"
    # We don't check specific output as the list might be empty
