"""Tests for the prompts module."""

from unittest.mock import MagicMock

from k8s_mcp_server.prompts import register_prompts


def test_register_prompts():
    """Test that prompts register correctly."""
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Call the register_prompts function
    register_prompts(mock_mcp)

    # Verify that prompt was called for each prompt template
    expected_prompt_count = 10  # Update this if you change the number of prompts
    assert mock_mcp.prompt.call_count == expected_prompt_count

    # Verify that all prompts were registered with the server
    # Each call to mcp.prompt() returns a decorator, which is then called with the function
    for i in range(expected_prompt_count):
        assert mock_mcp.prompt.return_value.call_count >= i + 1


def test_prompt_templates():
    """Test that prompt templates generate expected strings."""
    # Create a mock MCP server that captures the decorated functions
    prompt_functions = {}

    def mock_prompt_decorator(func):
        prompt_functions[func.__name__] = func
        return func

    mock_mcp = MagicMock()
    mock_mcp.prompt.return_value = mock_prompt_decorator

    # Register the prompts
    register_prompts(mock_mcp)

    # Test k8s_resource_status prompt
    status_prompt = prompt_functions["k8s_resource_status"]
    result = status_prompt("pods", "monitoring")
    assert "status of pods" in result
    assert "in the monitoring namespace" in result

    # Test k8s_deploy_application prompt
    deploy_prompt = prompt_functions["k8s_deploy_application"]
    result = deploy_prompt("nginx", "nginx:latest", "web", 3)
    assert "deploy an application named 'nginx'" in result
    assert "image 'nginx:latest'" in result
    assert "with 3 replicas" in result
    assert "in the web namespace" in result

    # Test k8s_troubleshoot prompt
    troubleshoot_prompt = prompt_functions["k8s_troubleshoot"]
    result = troubleshoot_prompt("pod", "web-server", "default")
    assert "troubleshoot issues with the pod" in result
    assert "named 'web-server'" in result
    assert "in the default namespace" in result

    # Test k8s_resource_inventory prompt with namespace
    inventory_prompt = prompt_functions["k8s_resource_inventory"]
    result = inventory_prompt("kube-system")
    assert "in the kube-system namespace" in result

    # Test k8s_resource_inventory prompt without namespace (all namespaces)
    result = inventory_prompt()
    assert "across all namespaces" in result

    # Test istio_service_mesh prompt
    istio_prompt = prompt_functions["istio_service_mesh"]
    result = istio_prompt("istio-system")
    assert "manage and analyze the Istio service mesh" in result
    assert "in the istio-system namespace" in result

    # Test helm_chart_management prompt with release name
    helm_prompt = prompt_functions["helm_chart_management"]
    result = helm_prompt("mysql", "database")
    assert "for release 'mysql'" in result
    assert "in the database namespace" in result

    # Test argocd_application prompt
    argocd_prompt = prompt_functions["argocd_application"]
    result = argocd_prompt("my-app")
    assert "for application 'my-app'" in result
    assert "in the argocd namespace" in result

    # Test argocd_application prompt without app name
    result = argocd_prompt()
    assert "for all applications" in result

    # Test k8s_security_check prompt with namespace
    security_prompt = prompt_functions["k8s_security_check"]
    result = security_prompt("production")
    assert "in the production namespace" in result

    # Test k8s_security_check prompt without namespace (all namespaces)
    result = security_prompt()
    assert "across the entire cluster" in result

    # Test k8s_resource_scaling prompt
    scaling_prompt = prompt_functions["k8s_resource_scaling"]
    result = scaling_prompt("deployment", "api-server", "services")
    assert "scale the deployment" in result
    assert "named 'api-server'" in result
    assert "in the services namespace" in result

    # Test k8s_logs_analysis prompt with container
    logs_prompt = prompt_functions["k8s_logs_analysis"]
    result = logs_prompt("backend", "app", "api")
    assert "container 'api' in" in result
    assert "pod 'backend'" in result
    assert "in the app namespace" in result

    # Test k8s_logs_analysis prompt without container
    result = logs_prompt("backend", "app")
    assert "container" not in result
    assert "pod 'backend'" in result
