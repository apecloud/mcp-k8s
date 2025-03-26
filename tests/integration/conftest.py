# File: tests/integration/cluster_fixture.py
import os
import subprocess
from collections.abc import Generator

import pytest


@pytest.fixture(scope="session", name="integration_cluster")
def integration_cluster_fixture() -> Generator[None]:
    """Fixture to ensure a K8s cluster is available for integration tests.

    Checks the K8S_MCP_TEST_USE_EXISTING_CLUSTER environment variable.
    If 'true', it verifies connection to the cluster configured via KUBECONFIG.
    If 'false' or not set (default), it assumes a cluster is provided externally
    (e.g., by the CI environment like kind-action) and does nothing.

    Setup and teardown of the cluster itself is handled outside this fixture
    (e.g., by GitHub Actions workflow or manual setup for local testing).
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
