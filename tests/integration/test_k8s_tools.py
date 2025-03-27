"""Integration tests for Kubernetes CLI tools.

These tests require a functioning Kubernetes cluster and installed CLI tools.
The tests connect to an existing Kubernetes cluster using the provided context,
rather than setting up a cluster during the tests.
"""

import os
import subprocess
import uuid
from collections.abc import Generator

import pytest

from k8s_mcp_server.server import (
    describe_kubectl,
    execute_helm,
    execute_kubectl,
)


@pytest.fixture
def ensure_cluster_running(integration_cluster) -> Generator[str]:
    """Ensures cluster is running and returns context.

    This fixture simplifies access to the context provided by the integration_cluster fixture.
    The integration_cluster fixture now handles KWOK cluster creation by default.

    Returns:
        Current context name for use with kubectl commands
    """
    k8s_context = integration_cluster
    
    if not k8s_context:
        pytest.skip("No Kubernetes context available from integration_cluster fixture.")
        
    # Verify basic cluster functionality
    try:
        context_args = ["--context", k8s_context] if k8s_context else []
        
        # Verify cluster connection
        cluster_cmd = ["kubectl", "cluster-info"] + context_args
        result = subprocess.run(cluster_cmd, capture_output=True, text=True, timeout=5, check=True)
        print(f"Using Kubernetes context: {k8s_context}")
        
        # KWOK clusters may not have actual nodes, so we'll skip the node check
        # Instead, check if the API server is responding to a basic command
        api_cmd = ["kubectl", "api-resources", "--request-timeout=5s"] + context_args
        result = subprocess.run(api_cmd, capture_output=True, timeout=5, check=True)
        
        yield k8s_context
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        pytest.skip(f"Error verifying cluster: {str(e)}")


@pytest.fixture
def test_namespace(ensure_cluster_running) -> Generator[str]:
    """Create a test namespace and clean it up after tests.

    This fixture:
    1. Creates a dedicated test namespace in the test cluster (KWOK or real).
    2. Yields the namespace name for tests to use.
    3. Cleans up the namespace after tests complete (unless K8S_SKIP_CLEANUP=true).

    Args:
        ensure_cluster_running: Fixture that provides current K8s context.

    Environment Variables:
        K8S_SKIP_CLEANUP: If set to 'true', skip namespace cleanup after tests.

    Returns:
        The name of the test namespace.
    """
    k8s_context = ensure_cluster_running
    namespace = f"k8s-mcp-test-{uuid.uuid4().hex[:8]}"  # Unique namespace per test run
    context_args = ["--context", k8s_context] if k8s_context else []

    try:
        # Create namespace
        create_cmd = ["kubectl", "create", "namespace", namespace] + context_args
        create_result = subprocess.run(
            create_cmd,
            capture_output=True,
            check=True,
            timeout=10
        )
        print(f"Created test namespace: {namespace}")
    except subprocess.CalledProcessError as e:
        if b"AlreadyExists" in e.stderr:
            print(f"Namespace {namespace} already exists, reusing")
        else:
            print(f"Warning: Failed to create namespace: {e.stderr.decode()}")
            pytest.skip(f"Could not create test namespace: {e.stderr.decode()}")
    except Exception as e:
        print(f"Warning: Error when setting up test namespace: {e}")
        pytest.skip(f"Could not set up test namespace: {str(e)}")

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
            capture_output=True,
            check=False,
            timeout=10
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
    pod_manifest = f"""\
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

    assert hasattr(result, "help_text") # Check attribute existence for dataclass
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
