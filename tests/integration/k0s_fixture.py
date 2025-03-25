"""Fixture for setting up and tearing down a k0s Kubernetes cluster for integration tests.

This module provides pytest fixtures that automatically handle:
1. Installing k0s if not already present
2. Creating a temporary k0s cluster for testing
3. Tearing down the cluster after tests complete

This fixture is only used when running tests with the 'integration' marker:
```
pytest -m integration
```
"""

import os
import shutil
import subprocess
import time
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def k0s_cluster() -> Generator[None]:
    """Create a single-node k0s cluster for testing and tear it down after tests complete.

    This fixture:
    1. Initializes a new k0s cluster in server+controller mode
    2. Waits for the cluster to be ready
    3. Configures kubectl to use this cluster
    4. Tears down the cluster after tests are complete

    This fixture will only be used when running with the 'integration' marker.
    """
    # Skip setup if we're not running integration tests
    markers = os.environ.get("PYTEST_CURRENT_TEST", "")
    if "integration" not in markers:
        yield
        return

    # Find k0s binary
    k0s_cmd = shutil.which("k0s")
    if k0s_cmd:
        k0s_path = Path(k0s_cmd)
    else:
        # Create directory for k0s binary
        tmp_dir = Path("/tmp/k0s-test")
        tmp_dir.mkdir(exist_ok=True)
        k0s_path = tmp_dir / "k0s"

        if not k0s_path.exists():
            print("Downloading k0s...")
            # Get the latest k0s version
            download_cmd = [
                "curl", "-L", "https://get.k0s.sh", "|",
                "sh"
            ]

            # Execute the download command
            try:
                subprocess.run(
                    " ".join(download_cmd),
                    shell=True,
                    cwd=tmp_dir,
                    check=True
                )
                # Move the downloaded binary to our location
                download_path = tmp_dir / "k0s"
                if download_path.exists():
                    os.chmod(download_path, 0o755)  # Make executable
            except subprocess.CalledProcessError as e:
                pytest.skip(f"Failed to download k0s: {e}")

        if not k0s_path.exists():
            pytest.skip("Could not find or download k0s")

    cluster_name = "k8s-mcp-test"
    data_dir = Path("/tmp/k0s-test-data")
    kubeconfig_path = data_dir / "kubeconfig"

    # Create data directory
    data_dir.mkdir(exist_ok=True)

    # Check if a cluster is already running
    try:
        result = subprocess.run(
            ["kubectl", "cluster-info"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            print("Using existing Kubernetes cluster")
            yield
            return
    except Exception:
        # No existing cluster, continue with setup
        pass

    print(f"Setting up k0s cluster: {cluster_name}")

    # Initialize the k0s cluster
    try:
        # Start k0s
        subprocess.run(
            [
                str(k0s_path), "install", "controller",
                "--data-dir", str(data_dir)
            ],
            check=True,
            capture_output=True
        )

        # Start the k0s service
        subprocess.run(
            [
                str(k0s_path), "start",
                "--data-dir", str(data_dir)
            ],
            check=True,
            capture_output=True
        )

        # Get kubeconfig
        subprocess.run(
            [
                str(k0s_path), "kubeconfig", "create", "--data-dir", str(data_dir),
                "--save", str(kubeconfig_path)
            ],
            check=True,
            capture_output=True
        )

        # Export kubeconfig for other tools to use
        os.environ["KUBECONFIG"] = str(kubeconfig_path)

        # Wait for cluster to be ready
        max_attempts = 10
        attempt = 0
        while attempt < max_attempts:
            try:
                result = subprocess.run(
                    ["kubectl", "get", "nodes"],
                    env={"KUBECONFIG": str(kubeconfig_path)},
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0 and b"Ready" in result.stdout:
                    break
            except Exception:
                pass

            print(f"Waiting for k0s cluster to be ready (attempt {attempt+1}/{max_attempts})...")
            time.sleep(3)
            attempt += 1

        if attempt >= max_attempts:
            # Attempt to stop the cluster before skipping
            try:
                subprocess.run(
                    [str(k0s_path), "stop", "--data-dir", str(data_dir)],
                    capture_output=True
                )
                subprocess.run(
                    [str(k0s_path), "reset", "--data-dir", str(data_dir)],
                    capture_output=True
                )
            except Exception:
                pass
            pytest.skip("Timed out waiting for k0s cluster to be ready")

        print("k0s cluster is ready!")
        yield

    except subprocess.CalledProcessError as e:
        pytest.skip(f"Failed to set up k0s cluster: {e}")
        return
    finally:
        # Teardown the cluster
        print(f"Tearing down k0s cluster: {cluster_name}")
        try:
            subprocess.run(
                [str(k0s_path), "stop", "--data-dir", str(data_dir)],
                capture_output=True
            )
            subprocess.run(
                [str(k0s_path), "reset", "--data-dir", str(data_dir)],
                capture_output=True
            )
        except Exception as e:
            print(f"Error during k0s cluster teardown: {e}")
