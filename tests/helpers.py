"""Helper utilities for K8s MCP Server tests."""

import asyncio
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


async def assert_command_executed(mock_obj, expected_command=None):
    """Assert that a command was executed with the mock."""
    assert mock_obj.called, "Command execution was not called"

    if expected_command:
        called_with = mock_obj.call_args[0][0]
        assert expected_command in called_with, f"Expected {expected_command} in {called_with}"

    return mock_obj.call_args


def create_test_pod_manifest(name="test-pod", namespace=None, image="nginx:alpine", labels=None, annotations=None):
    """Create a test pod manifest for integration tests.

    Args:
        name: Pod name
        namespace: Kubernetes namespace
        image: Container image
        labels: Optional dict of labels to add
        annotations: Optional dict of annotations to add

    Returns:
        Dictionary with the pod manifest
    """
    metadata = {"name": name}

    if namespace:
        metadata["namespace"] = namespace

    if labels:
        metadata["labels"] = labels

    if annotations:
        metadata["annotations"] = annotations

    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": metadata,
        "spec": {
            "containers": [
                {"name": name.replace("-", ""), "image": image, "resources": {"limits": {"memory": "128Mi", "cpu": "100m"}}, "ports": [{"containerPort": 80}]}
            ]
        },
    }


def create_test_deployment_manifest(namespace, name="test-deployment", replicas=1, image="nginx:alpine", labels=None):
    """Create a test deployment manifest for integration tests.

    Args:
        namespace: Kubernetes namespace
        name: Deployment name
        replicas: Number of replicas
        image: Container image
        labels: Optional dict of labels to add

    Returns:
        YAML manifest as string
    """
    app_label = name

    # Format additional labels if provided
    labels_yaml = f"    app: {app_label}\n"
    if labels:
        for k, v in labels.items():
            labels_yaml += f"    {k}: {v}\n"

    return f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
  namespace: {namespace}
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {app_label}
  template:
    metadata:
      labels:
{labels_yaml}    spec:
      containers:
      - name: {name.replace("-", "")}
        image: {image}
        resources:
          limits:
            memory: "128Mi"
            cpu: "100m"
        ports:
        - containerPort: 80
"""


def create_test_service_manifest(namespace, name="test-service", selector=None, port=80, target_port=80, service_type="ClusterIP"):
    """Create a test service manifest for integration tests.

    Args:
        namespace: Kubernetes namespace
        name: Service name
        selector: Dict of pod selector labels (defaults to app=name)
        port: Service port
        target_port: Target port on pods
        service_type: Kubernetes service type

    Returns:
        YAML manifest as string
    """
    if selector is None:
        selector = {"app": name}

    # Format selector
    selector_yaml = "  selector:\n"
    for k, v in selector.items():
        selector_yaml += f"    {k}: {v}\n"

    return f"""apiVersion: v1
kind: Service
metadata:
  name: {name}
  namespace: {namespace}
spec:
  type: {service_type}
{selector_yaml}  ports:
  - port: {port}
    targetPort: {target_port}
"""


async def wait_for_pod_ready(namespace: str, name: str = "test-pod", timeout: int = 30, context: str = None) -> bool:
    """Wait for a pod to be ready or running, useful in integration tests.

    Args:
        namespace: Kubernetes namespace
        name: Pod name
        timeout: Timeout in seconds
        context: Kubernetes context (optional)

    Returns:
        True if pod is ready/running, False if timeout
    """
    logger.info(f"Waiting for pod {name} in namespace {namespace} to be ready (timeout: {timeout}s)")
    start_time = asyncio.get_event_loop().time()
    last_phase = None
    check_interval = 1  # Initial check interval
    retries = 0

    while (asyncio.get_event_loop().time() - start_time) < timeout:
        try:
            from k8s_mcp_server.server import execute_kubectl

            # Build command with optional context
            context_arg = f" --context={context}" if context else ""
            cmd = f"get pod {name} -n {namespace}{context_arg} -o json"

            result = await execute_kubectl(command=cmd)

            if result["status"] == "success":
                try:
                    pod_data = json.loads(result["output"])
                    phase = pod_data.get("status", {}).get("phase", "Unknown")

                    # If phase changed, log it
                    if phase != last_phase:
                        logger.info(f"Pod {name} phase: {phase}")
                        last_phase = phase

                    # Check if pod is running or completed
                    if phase in ("Running", "Succeeded"):
                        logger.info(f"Pod {name} is now {phase}")
                        return True

                    # Check for failures
                    if phase == "Failed":
                        logger.warning(f"Pod {name} has failed state: {pod_data.get('status', {})}")
                        return False

                except json.JSONDecodeError:
                    logger.warning(f"Could not parse pod JSON: {result['output'][:200]}...")
            else:
                # Check if error is because pod doesn't exist yet
                error_msg = result.get("error", {}).get("message", "")
                if "not found" in error_msg and retries < 5:
                    logger.info(f"Pod {name} not found yet, retrying...")
                else:
                    logger.warning(f"Error checking pod status: {error_msg}")
        except Exception as e:
            logger.warning(f"Exception while waiting for pod: {str(e)}")

        # Increase check interval with backoff, capped at 3 seconds
        retries += 1
        check_interval = min(3, 0.5 * retries)
        await asyncio.sleep(check_interval)

    logger.warning(f"Timeout waiting for pod {name} to be ready")
    return False


async def wait_for_deployment_ready(namespace: str, name: str, timeout: int = 60, expected_replicas: int = 1, context: str = None) -> bool:
    """Wait for a deployment to be ready, useful in integration tests.

    Args:
        namespace: Kubernetes namespace
        name: Deployment name
        timeout: Timeout in seconds
        expected_replicas: Expected number of ready replicas
        context: Kubernetes context (optional)

    Returns:
        True if deployment is ready, False if timeout
    """
    logger.info(f"Waiting for deployment {name} to have {expected_replicas} ready replicas (timeout: {timeout}s)")
    start_time = asyncio.get_event_loop().time()
    last_status = None
    check_interval = 1  # Initial check interval

    while (asyncio.get_event_loop().time() - start_time) < timeout:
        try:
            from k8s_mcp_server.server import execute_kubectl

            # Build command with optional context
            context_arg = f" --context={context}" if context else ""
            cmd = f"get deployment {name} -n {namespace}{context_arg} -o json"

            result = await execute_kubectl(command=cmd)

            if result["status"] == "success":
                try:
                    deployment_data = json.loads(result["output"])
                    status = deployment_data.get("status", {})
                    available_replicas = status.get("availableReplicas", 0)
                    ready_replicas = status.get("readyReplicas", 0)

                    # Create status summary
                    status_summary = f"available={available_replicas}, ready={ready_replicas}, expected={expected_replicas}"

                    # If status changed, log it
                    if status_summary != last_status:
                        logger.info(f"Deployment {name} status: {status_summary}")
                        last_status = status_summary

                    # Check if deployment is ready
                    if ready_replicas >= expected_replicas:
                        logger.info(f"Deployment {name} is ready with {ready_replicas} replicas")
                        return True

                except json.JSONDecodeError:
                    logger.warning(f"Could not parse deployment JSON: {result['output'][:200]}...")
            else:
                logger.warning(f"Error checking deployment status: {result.get('error', {}).get('message', '')}")
        except Exception as e:
            logger.warning(f"Exception while waiting for deployment: {str(e)}")

        # Use exponential backoff for check interval, capped at 5 seconds
        check_interval = min(5, check_interval * 1.5)
        await asyncio.sleep(check_interval)

    logger.warning(f"Timeout waiting for deployment {name} to be ready")
    return False


def capture_k8s_diagnostics(namespace: str, context: str = None, pod_name: str = None, output_dir: Path | None = None) -> dict[str, Any]:
    """Capture Kubernetes diagnostics for debugging.

    Args:
        namespace: Kubernetes namespace
        context: Kubernetes context (optional)
        pod_name: Specific pod name (optional)
        output_dir: Directory to save diagnostic files (optional)

    Returns:
        Dictionary with diagnostic information
    """
    diagnostics = {"timestamp": time.time(), "namespace": namespace, "context": context, "pod_name": pod_name, "results": {}}

    kubeconfig = os.environ.get("KUBECONFIG")
    context_args = ["--context", context] if context else []
    kubeconfig_args = ["--kubeconfig", kubeconfig] if kubeconfig else []
    namespace_args = ["--namespace", namespace] if namespace else []

    # Define commands to run for diagnostics
    commands = [
        {"name": "describe_namespace", "cmd": ["kubectl", "describe", "namespace", namespace] + context_args + kubeconfig_args, "skip_if_no_pod": False},
        {"name": "get_pods", "cmd": ["kubectl", "get", "pods"] + namespace_args + context_args + kubeconfig_args, "skip_if_no_pod": False},
        {"name": "describe_pod", "cmd": ["kubectl", "describe", "pod", pod_name] + namespace_args + context_args + kubeconfig_args, "skip_if_no_pod": True},
        {
            "name": "get_pod_yaml",
            "cmd": ["kubectl", "get", "pod", pod_name, "-o", "yaml"] + namespace_args + context_args + kubeconfig_args,
            "skip_if_no_pod": True,
        },
        {
            "name": "get_events",
            "cmd": ["kubectl", "get", "events", "--sort-by=.lastTimestamp"] + namespace_args + context_args + kubeconfig_args,
            "skip_if_no_pod": False,
        },
    ]

    # Run diagnostic commands
    for cmd_spec in commands:
        if pod_name is None and cmd_spec["skip_if_no_pod"]:
            continue

        try:
            result = subprocess.run(cmd_spec["cmd"], capture_output=True, text=True, timeout=10)
            cmd_result = {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "success": result.returncode == 0}

            # Save outputs to files if output_dir is provided
            if output_dir:
                output_dir.mkdir(exist_ok=True, parents=True)
                output_file = output_dir / f"{cmd_spec['name']}.txt"
                with open(output_file, "w") as f:
                    f.write(f"COMMAND: {' '.join(cmd_spec['cmd'])}\n")
                    f.write(f"RETURN CODE: {result.returncode}\n\n")
                    f.write("STDOUT:\n")
                    f.write(result.stdout or "")
                    f.write("\n\nSTDERR:\n")
                    f.write(result.stderr or "")

        except subprocess.TimeoutExpired:
            cmd_result = {"returncode": -1, "stdout": "", "stderr": "Command timed out", "success": False}
        except Exception as e:
            cmd_result = {"returncode": -1, "stdout": "", "stderr": f"Error: {str(e)}", "success": False}

        diagnostics["results"][cmd_spec["name"]] = cmd_result

    return diagnostics
