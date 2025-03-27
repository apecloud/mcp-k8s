# File: tests/integration/conftest.py
import os
import subprocess
import tempfile
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
def integration_cluster_fixture() -> Generator[str]:
    """Fixture to ensure a K8s cluster is available for integration tests.

    By default, creates a KWOK cluster for testing. This behavior can be overridden
    by setting the K8S_MCP_TEST_USE_EXISTING_CLUSTER environment variable to 'true'.

    Returns:
        str: The Kubernetes context name to use for tests
    """
    use_existing = os.environ.get("K8S_MCP_TEST_USE_EXISTING_CLUSTER", "false").lower() == "true"
    use_kwok = os.environ.get("K8S_MCP_TEST_USE_KWOK", "true").lower() == "true"

    if use_existing:
        print("\nAttempting to use existing KUBECONFIG context for integration tests.")
        try:
            # Verify connection to the existing cluster
            cmd = ["kubectl", "cluster-info"]
            context = os.environ.get("K8S_CONTEXT")
            if context:
                cmd.extend(["--context", context])

            result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=20)
            print(f"Existing cluster connection verified:\n{result.stdout[:200]}...")  # Print snippet

            # Return the current context if not explicitly specified
            if not context:
                context = subprocess.run(["kubectl", "config", "current-context"], check=True, capture_output=True, text=True).stdout.strip()

            yield context
            print("\nSkipping cluster teardown (using existing cluster).")

        except FileNotFoundError:
            pytest.fail("`kubectl` command not found. Cannot verify existing cluster connection.", pytrace=False)
        except subprocess.TimeoutExpired:
            pytest.fail("Timed out connecting to the existing Kubernetes cluster. Check KUBECONFIG or cluster status.", pytrace=False)
        except subprocess.CalledProcessError as e:
            pytest.fail(
                f"Failed to connect to the existing Kubernetes cluster (Command: {' '.join(e.cmd)}). Check KUBECONFIG or cluster status.\nError: {e.stderr}",
                pytrace=False,
            )
        except Exception as e:
            pytest.fail(f"An unexpected error occurred while verifying the existing cluster: {e}", pytrace=False)

    elif use_kwok:
        # Create a KWOK cluster for integration tests
        print("\nSetting up KWOK cluster for integration tests...")

        # Check if kwokctl is installed
        try:
            subprocess.run(["kwokctl", "--version"], check=True, capture_output=True, text=True)
        except FileNotFoundError:
            pytest.fail("kwokctl not found. Please install KWOK following the instructions at https://kwok.sigs.k8s.io/docs/user/install/", pytrace=False)

        # Create a unique cluster name
        cluster_name = f"k8s-mcp-test-{uuid.uuid4().hex[:8]}"
        kubeconfig_dir = tempfile.mkdtemp(prefix="kwok-kubeconfig-")
        kubeconfig_path = os.path.join(kubeconfig_dir, "kubeconfig")

        try:
            # Create KWOK cluster
            print(f"Creating KWOK cluster: {cluster_name}")
            create_cmd = ["kwokctl", "create", "cluster", "--name", cluster_name, "--kubeconfig", kubeconfig_path]
            subprocess.run(create_cmd, check=True, timeout=60)

            # Store the original KUBECONFIG value to restore later
            original_kubeconfig = os.environ.get("KUBECONFIG")

            # Set KUBECONFIG environment variable for the tests
            os.environ["KUBECONFIG"] = kubeconfig_path

            # Give the cluster a moment to fully initialize
            print("Waiting for KWOK cluster to initialize...")
            time.sleep(5)

            # Get the context name
            context_cmd = ["kubectl", "--kubeconfig", kubeconfig_path, "config", "current-context"]
            context = subprocess.run(context_cmd, check=True, capture_output=True, text=True).stdout.strip()

            print(f"KWOK cluster '{cluster_name}' created with context '{context}'")

            # Yield the context name to tests
            yield context

            # Teardown
            print(f"\nTearing down KWOK cluster: {cluster_name}")
            delete_cmd = ["kwokctl", "delete", "cluster", "--name", cluster_name]
            subprocess.run(delete_cmd, check=True, timeout=60)

            # Restore original KUBECONFIG if it existed
            if original_kubeconfig:
                os.environ["KUBECONFIG"] = original_kubeconfig
            else:
                os.environ.pop("KUBECONFIG", None)

            # Clean up the temporary directory
            try:
                import shutil

                shutil.rmtree(kubeconfig_dir, ignore_errors=True)
            except Exception as e:
                print(f"Warning: Failed to clean up temporary directory: {e}")

        except FileNotFoundError as e:
            pytest.fail(f"Command not found: {e}", pytrace=False)
        except subprocess.TimeoutExpired:
            pytest.fail("Timed out creating or deleting KWOK cluster", pytrace=False)
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to create or manage KWOK cluster: {e.stderr if hasattr(e, 'stderr') else str(e)}", pytrace=False)
        except Exception as e:
            pytest.fail(f"An unexpected error occurred while managing KWOK cluster: {e}", pytrace=False)

            # Attempt cleanup on failure
            try:
                subprocess.run(["kwokctl", "delete", "cluster", "--name", cluster_name], check=False, timeout=30)
            except Exception:
                pass
    else:
        # Assume cluster is provided by CI/external setup
        print("\nAssuming K8s cluster is provided by CI environment or external setup.")
        context = os.environ.get("K8S_CONTEXT")

        if not context:
            try:
                context = subprocess.run(["kubectl", "config", "current-context"], check=True, capture_output=True, text=True).stdout.strip()
            except Exception:
                context = None

        yield context
        print("\nSkipping cluster teardown (managed externally).")
