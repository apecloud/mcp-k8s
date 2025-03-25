"""Integration tests for Kubernetes CLI tools.

These tests require a functioning Kubernetes cluster and installed CLI tools.
For local development, we recommend using minikube, kind, or k3d to set up a local cluster.
"""

import os
import pytest
import subprocess
from typing import Generator

from k8s_mcp_server.server import (
    describe_kubectl,
    execute_kubectl,
    describe_helm,
    execute_helm,
)


@pytest.fixture
def ensure_cluster_running() -> Generator[bool, None, None]:
    """Check if a Kubernetes cluster is available and running.
    
    For local development, you can use:
    - minikube: https://minikube.sigs.k8s.io/docs/start/
    - kind: https://kind.sigs.k8s.io/docs/user/quick-start/
    - k3d: https://k3d.io/
    
    Returns:
        True if cluster is running, raises skip exception otherwise
    """
    # Try to reach the Kubernetes API
    try:
        result = subprocess.run(
            ["kubectl", "cluster-info"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            timeout=5
        )
        if result.returncode != 0:
            pytest.skip("Kubernetes cluster is not available.")
        
        # Check if kubectl is working
        result = subprocess.run(
            ["kubectl", "get", "nodes"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            timeout=5
        )
        if result.returncode != 0:
            pytest.skip("kubectl cannot list nodes. Check your cluster setup.")
            
        yield True
    except (subprocess.SubprocessError, FileNotFoundError):
        pytest.skip("kubectl command failed or is not installed.")


@pytest.fixture
def test_namespace() -> Generator[str, None, None]:
    """Create a test namespace and clean it up after tests.
    
    Returns:
        The name of the test namespace
    """
    namespace = "k8s-mcp-test"
    
    # Create namespace
    subprocess.run(
        ["kubectl", "create", "namespace", namespace],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    yield namespace
    
    # Clean up namespace
    subprocess.run(
        ["kubectl", "delete", "namespace", namespace, "--wait=false"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_kubectl_version(ensure_cluster_running):
    """Test that kubectl version command works."""
    result = await execute_kubectl(command="version --client")
    
    assert result["status"] == "success"
    assert "Client Version" in result["output"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_kubectl_get_pods(ensure_cluster_running, test_namespace):
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
async def test_kubectl_help(ensure_cluster_running):
    """Test that kubectl help command works."""
    result = await describe_kubectl(command="get")
    
    assert "help_text" in result
    assert "Display one or many resources" in result["help_text"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_helm_version(ensure_cluster_running):
    """Test that helm version command works."""
    # Skip if helm is not installed
    try:
        subprocess.run(["helm", "version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
    except (subprocess.SubprocessError, FileNotFoundError):
        pytest.skip("helm is not installed")
    
    result = await execute_helm(command="version")
    
    assert result["status"] == "success"
    assert "version.BuildInfo" in result["output"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_helm_list(ensure_cluster_running):
    """Test that helm list command works."""
    # Skip if helm is not installed
    try:
        subprocess.run(["helm", "version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
    except (subprocess.SubprocessError, FileNotFoundError):
        pytest.skip("helm is not installed")
    
    result = await execute_helm(command="list")
    
    assert result["status"] == "success"
    # We don't check specific output as the list might be empty