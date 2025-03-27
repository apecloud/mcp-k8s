"""Helper utilities for K8s MCP Server tests."""

import asyncio


async def assert_command_executed(mock_obj, expected_command=None):
    """Assert that a command was executed with the mock."""
    assert mock_obj.called, "Command execution was not called"

    if expected_command:
        called_with = mock_obj.call_args[0][0]
        assert expected_command in called_with, f"Expected {expected_command} in {called_with}"

    return mock_obj.call_args


def create_test_pod_manifest(namespace, name="test-pod", image="nginx:alpine"):
    """Create a test pod manifest for integration tests."""
    return f"""\napiVersion: v1
kind: Pod
metadata:
  name: {name}
  namespace: {namespace}
spec:
  containers:
  - name: {name.replace("-", "")}
    image: {image}
"""


async def wait_for_pod_ready(namespace, name="test-pod", timeout=30):
    """Wait for a pod to be ready, useful in integration tests."""
    start_time = asyncio.get_event_loop().time()

    while (asyncio.get_event_loop().time() - start_time) < timeout:
        from k8s_mcp_server.server import execute_kubectl

        result = await execute_kubectl(f"get pod {name} -n {namespace} -o jsonpath='{{.status.phase}}'")

        if result["status"] == "success" and "Running" in result["output"]:
            return True

        await asyncio.sleep(1)

    return False
