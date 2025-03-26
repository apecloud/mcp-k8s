"""Integration tests for Kubernetes CLI tools.

These tests require a functioning Kubernetes cluster and installed CLI tools.
The tests connect to an existing Kubernetes cluster using the provided context,
rather than setting up a cluster during the tests.
"""

import os
import subprocess
from collections.abc import Generator

import pytest

from k8s_mcp_server.server import (
    describe_kubectl,
    execute_helm,
    execute_kubectl,
)


@pytest.fixture
def ensure_cluster_running() -> Generator[str]:
    """Check if a Kubernetes cluster is available using the provided context.

    This fixture:
    1. Uses the K8S_CONTEXT environment variable (if set) to select a specific K8s context
    2. Verifies the cluster connection is working
    3. Yields the current context name on success
    4. Skip tests if no context can be found or connected to

    For local development, you can use:
    - k3s: https://k3s.io/ (lightweight single-node K8s)
    - k0s: https://k0sproject.io/ (zero-friction Kubernetes)
    - minikube: https://minikube.sigs.k8s.io/docs/start/
    - kind: https://kind.sigs.k8s.io/docs/user/quick-start/

    Returns:
        Current context name if cluster is running, raises skip exception otherwise
    """
    # Check if a specific context was provided
    k8s_context = os.environ.get("K8S_CONTEXT")
    context_args = []

    if k8s_context:
        context_args = ["--context", k8s_context]
        print(f"Using specified Kubernetes context: {k8s_context}")

    # Try to reach the Kubernetes API
    try:
        # Get current context if not specified
        if not k8s_context:
            result = subprocess.run(
                ["kubectl", "config", "current-context"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                k8s_context = result.stdout.strip()
                print(f"Using current Kubernetes context: {k8s_context}")
            else:
                pytest.skip("No Kubernetes context is currently set.")

        # Verify cluster connection
        cluster_cmd = ["kubectl", "cluster-info"] + context_args
        result = subprocess.run(cluster_cmd, capture_output=True, timeout=5)
        if result.returncode != 0:
            pytest.skip(f"Cannot connect to Kubernetes cluster with context '{k8s_context}'.")

        # Check if kubectl can access nodes
        nodes_cmd = ["kubectl", "get", "nodes"] + context_args
        result = subprocess.run(nodes_cmd, capture_output=True, timeout=5)
        if result.returncode != 0:
            pytest.skip(f"kubectl cannot list nodes with context '{k8s_context}'. Check your cluster access.")

        yield k8s_context
    except (subprocess.SubprocessError, FileNotFoundError):
        pytest.skip("kubectl command failed or is not installed.")


@pytest.fixture
def test_namespace(ensure_cluster_running) -> Generator[str]:
    """Create a test namespace and clean it up after tests.

    This fixture:
    1. Creates a dedicated test namespace
    2. Yields the namespace name for tests to use
    3. Cleans up the namespace after tests complete (unless K8S_SKIP_CLEANUP=true)

    Args:
        ensure_cluster_running: Fixture that provides current K8s context

    Environment Variables:
        K8S_SKIP_CLEANUP: If set to 'true', skip namespace cleanup after tests

    Returns:
        The name of the test namespace
    """
    k8s_context = ensure_cluster_running
    namespace = f"k8s-mcp-test-{os.getpid()}"  # Make namespace unique per test run
    context_args = ["--context", k8s_context] if k8s_context else []

    try:
        # Create namespace (will fail if it exists, which is fine)
        create_cmd = ["kubectl", "create", "namespace", namespace] + context_args
        create_result = subprocess.run(
            create_cmd,
            capture_output=True,
            check=False
        )

        if create_result.returncode != 0 and b"AlreadyExists" not in create_result.stderr:
            print(f"Warning: Failed to create namespace: {create_result.stderr.decode()}")
    except Exception as e:
        print(f"Warning: Error when setting up test namespace: {e}")

    yield namespace

    # Check if cleanup should be skipped
    skip_cleanup = os.environ.get("K8S_SKIP_CLEANUP", "").lower() in ("true", "1", "yes")

    if skip_cleanup:
        print(f"Note: Skipping cleanup of namespace '{namespace}' as requested by K8S_SKIP_CLEANUP")
        return

    try:
        # Clean up namespace
        print(f"Cleaning up test namespace: {namespace}")
        delete_cmd = ["kubectl", "delete", "namespace", namespace, "--wait=false"] + context_args
        subprocess.run(
            delete_cmd,
            capture_output=True
        )
    except Exception as e:
        print(f"Warning: Error when cleaning up test namespace: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_kubectl_version(ensure_cluster_running):
    """Test that kubectl version command works."""
    k8s_context = ensure_cluster_running
    result = await execute_kubectl(command=f"version --client --context {k8s_context}")

    assert result["status"] == "success"
    assert "Client Version" in result["output"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_kubectl_get_pods(ensure_cluster_running, test_namespace):
    """Test that kubectl can list pods in the test namespace."""
    k8s_context = ensure_cluster_running

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

    create_result = await execute_kubectl(
        command=f"apply -f /tmp/test-pod.yaml -n {test_namespace} --context {k8s_context}"
    )
    assert create_result["status"] == "success"

    # Give the pod some time to be created
    import asyncio

    await asyncio.sleep(2)

    # Now test listing pods
    result = await execute_kubectl(
        command=f"get pods -n {test_namespace} --context {k8s_context}"
    )

    assert result["status"] == "success"
    assert "test-pod" in result["output"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_kubectl_help(ensure_cluster_running):
    """Test that kubectl help command works."""
    result = await describe_kubectl(command="get")

    assert "help_text" in result
    assert "Display one or many resources" in result["help_text"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_helm_version(ensure_cluster_running):
    """Test that helm version command works."""
    k8s_context = ensure_cluster_running

    # Skip if helm is not installed
    try:
        subprocess.run(["helm", "version"], capture_output=True, timeout=5)
    except (subprocess.SubprocessError, FileNotFoundError):
        pytest.skip("helm is not installed")

    result = await execute_helm(command=f"version --kube-context {k8s_context}")

    assert result["status"] == "success"
    assert "version.BuildInfo" in result["output"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_helm_list(ensure_cluster_running):
    """Test that helm list command works."""
    k8s_context = ensure_cluster_running

    # Skip if helm is not installed
    try:
        subprocess.run(["helm", "version"], capture_output=True, timeout=5)
    except (subprocess.SubprocessError, FileNotFoundError):
        pytest.skip("helm is not installed")

    result = await execute_helm(command=f"list --kube-context {k8s_context}")

    assert result["status"] == "success"
    # We don't check specific output as the list might be empty
