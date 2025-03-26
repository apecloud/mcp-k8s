# File: tests/integration/conftest.py
import os
import subprocess
import time
import uuid
from collections.abc import Generator
from contextlib import contextmanager

import pytest


class KubernetesClusterManager:
    """Manager class for Kubernetes cluster operations during tests."""
    
    def __init__(self):
        self.context = os.environ.get("K8S_CONTEXT")
        self.use_existing = os.environ.get("K8S_MCP_TEST_USE_EXISTING_CLUSTER", "false").lower() == "true"
        self.skip_cleanup = os.environ.get("K8S_SKIP_CLEANUP", "").lower() == "true"
        
    def get_context_args(self):
        """Get the command line arguments for kubectl context."""
        return ["--context", self.context] if self.context else []
        
    def verify_connection(self):
        """Verify connection to the Kubernetes cluster."""
        try:
            cmd = ["kubectl", "cluster-info"] + self.get_context_args()
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=20)
            print(f"Cluster connection verified:\n{result.stdout[:200]}...")
            return True
        except Exception as e:
            print(f"Cluster connection failed: {str(e)}")
            return False
            
    def create_namespace(self, name=None):
        """Create a test namespace with optional name."""
        if name is None:
            name = f"k8s-mcp-test-{uuid.uuid4().hex[:8]}"
            
        try:
            cmd = ["kubectl", "create", "namespace", name] + self.get_context_args()
            subprocess.run(cmd, check=True, capture_output=True, timeout=10)
            print(f"Created test namespace: {name}")
            return name
        except subprocess.CalledProcessError as e:
            if b"AlreadyExists" in e.stderr:
                print(f"Namespace {name} already exists, reusing")
                return name
            raise
            
    def delete_namespace(self, name):
        """Delete the specified namespace."""
        if self.skip_cleanup:
            print(f"Skipping cleanup of namespace {name} as requested")
            return
            
        try:
            cmd = ["kubectl", "delete", "namespace", name, "--wait=false"] + self.get_context_args()
            subprocess.run(cmd, check=True, capture_output=True, timeout=10)
            print(f"Deleted test namespace: {name}")
        except Exception as e:
            print(f"Warning: Failed to delete namespace {name}: {str(e)}")
    
    @contextmanager
    def temp_namespace(self):
        """Context manager for a temporary namespace."""
        name = self.create_namespace()
        try:
            yield name
        finally:
            self.delete_namespace(name)


@pytest.fixture(scope="session")
def k8s_cluster():
    """Fixture that provides a KubernetesClusterManager."""
    manager = KubernetesClusterManager()
    
    # Skip tests if we can't connect to the cluster
    if not manager.verify_connection():
        pytest.skip("Cannot connect to Kubernetes cluster")
        
    return manager


@pytest.fixture
def k8s_namespace(k8s_cluster):
    """Fixture that provides a temporary namespace for tests."""
    with k8s_cluster.temp_namespace() as name:
        yield name


@pytest.fixture(scope="session", name="integration_cluster")
def integration_cluster_fixture() -> Generator[None]:
    """Legacy fixture for backward compatibility with existing tests.
    
    Checks the K8S_MCP_TEST_USE_EXISTING_CLUSTER environment variable.
    If 'true', it verifies connection to the cluster configured via KUBECONFIG.
    If 'false' or not set (default), it assumes a cluster is provided externally
    (e.g., by the CI environment like kind-action) and does nothing.
    """
    use_existing = os.environ.get("K8S_MCP_TEST_USE_EXISTING_CLUSTER", "false").lower() == "true"

    if use_existing:
        print("\nAttempting to use existing KUBECONFIG context for integration tests.")
        try:
            # Verify connection to the existing cluster
            cmd = ["kubectl", "cluster-info"]
            context = os.environ.get("K8S_CONTEXT")
            if context:
                cmd.extend(["--context", context])

            result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=20)
            print(f"Existing cluster connection verified:\n{result.stdout[:200]}...") # Print snippet
            yield # Yield control to tests
            print("\nSkipping cluster teardown (using existing cluster).")

        except FileNotFoundError:
            pytest.fail("`kubectl` command not found. Cannot verify existing cluster connection.", pytrace=False)
        except subprocess.TimeoutExpired:
            pytest.fail("Timed out connecting to the existing Kubernetes cluster. Check KUBECONFIG or cluster status.", pytrace=False)
        except subprocess.CalledProcessError as e:
            pytest.fail(
                f"Failed to connect to the existing Kubernetes cluster (Command: {' '.join(e.cmd)}). "
                f"Check KUBECONFIG or cluster status.\nError: {e.stderr}",
                pytrace=False
            )
        except Exception as e:
             pytest.fail(f"An unexpected error occurred while verifying the existing cluster: {e}", pytrace=False)

    else:
        # Assume cluster is provided by CI/external setup (like kind-action)
        print("\nAssuming K8s cluster is provided by CI environment or external setup.")
        # Optionally, could add a quick check here too, but kind-action usually waits.
        yield # Yield control to tests
        print("\nSkipping cluster teardown (managed externally).")
