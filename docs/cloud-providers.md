# Cloud Provider Configuration

K8s MCP Server provides support for major cloud-managed Kubernetes services (EKS, GKE, AKS). This document details how to configure each provider.

## Amazon EKS

K8s MCP Server includes AWS CLI for seamless integration with Amazon Elastic Kubernetes Service (EKS).

### Prerequisites

1. AWS CLI credentials configured in your `~/.aws` directory
2. Access to an EKS cluster
3. `kubectl` configured to access your EKS cluster

### Configuration

1. **Mount AWS credentials** in your Claude Desktop configuration:
   ```json
   {
     "mcpServers": {
       "k8s-mcp-server": {
         "command": "docker",
         "args": [
           "run",
           "-i",
           "--rm",
           "-v",
           "/Users/YOUR_USER_NAME/.kube:/home/appuser/.kube:ro",
           "-v",
           "/Users/YOUR_USER_NAME/.aws:/home/appuser/.aws:ro",
           "ghcr.io/alexei-led/k8s-mcp-server:latest"
         ]
       }
     }
   }
   ```

2. **Set AWS environment variables** (optional):
   ```json
   {
     "mcpServers": {
       "k8s-mcp-server": {
         "command": "docker",
         "args": [
           "run",
           "-i",
           "--rm",
           "-v",
           "/Users/YOUR_USER_NAME/.kube:/home/appuser/.kube:ro",
           "-v",
           "/Users/YOUR_USER_NAME/.aws:/home/appuser/.aws:ro",
           "-e",
           "AWS_PROFILE=my-profile",
           "-e",
           "AWS_REGION=us-west-2",
           "ghcr.io/alexei-led/k8s-mcp-server:latest"
         ]
       }
     }
   }
   ```

3. **Update kubeconfig** for EKS cluster access (if not already done):
   ```bash
   aws eks update-kubeconfig --name my-cluster --region us-west-2
   ```

### Troubleshooting EKS

1. **Authentication issues**: 
   - Ensure AWS credentials are properly mounted
   - Check that your AWS profile has sufficient permissions
   - Verify your EKS cluster exists in the specified region

2. **Connection issues**:
   - Check that your kubeconfig is correctly configured for EKS
   - Ensure your network can reach the EKS API server

## Google GKE

K8s MCP Server includes Google Cloud SDK and GKE auth plugin for working with Google Kubernetes Engine.

### Prerequisites

1. gcloud CLI credentials configured in your `~/.config/gcloud` directory
2. Access to a GKE cluster
3. `kubectl` configured to access your GKE cluster

### Configuration

1. **Mount GCP credentials** in your Claude Desktop configuration:
   ```json
   {
     "mcpServers": {
       "k8s-mcp-server": {
         "command": "docker",
         "args": [
           "run",
           "-i",
           "--rm",
           "-v",
           "/Users/YOUR_USER_NAME/.kube:/home/appuser/.kube:ro",
           "-v",
           "/Users/YOUR_USER_NAME/.config/gcloud:/home/appuser/.config/gcloud:ro",
           "ghcr.io/alexei-led/k8s-mcp-server:latest"
         ]
       }
     }
   }
   ```

2. **Set GCP environment variables** (optional):
   ```json
   {
     "mcpServers": {
       "k8s-mcp-server": {
         "command": "docker",
         "args": [
           "run",
           "-i",
           "--rm",
           "-v",
           "/Users/YOUR_USER_NAME/.kube:/home/appuser/.kube:ro",
           "-v",
           "/Users/YOUR_USER_NAME/.config/gcloud:/home/appuser/.config/gcloud:ro",
           "-e",
           "CLOUDSDK_CORE_PROJECT=my-gcp-project",
           "-e",
           "CLOUDSDK_COMPUTE_REGION=us-central1",
           "ghcr.io/alexei-led/k8s-mcp-server:latest"
         ]
       }
     }
   }
   ```

3. **Update kubeconfig** for GKE cluster access (if not already done):
   ```bash
   gcloud container clusters get-credentials my-cluster --region=us-central1
   ```

### Troubleshooting GKE

1. **Authentication issues**:
   - Ensure GCP credentials are properly mounted
   - Check that your GCP service account or user has sufficient permissions
   - Verify your GKE cluster exists in the specified project and region

2. **Connection issues**:
   - Check that your kubeconfig is correctly configured for GKE
   - Ensure your network can reach the GKE API server

## Microsoft AKS

K8s MCP Server includes Azure CLI for working with Azure Kubernetes Service (AKS).

### Prerequisites

1. Azure CLI credentials configured in your `~/.azure` directory
2. Access to an AKS cluster
3. `kubectl` configured to access your AKS cluster

### Configuration

1. **Mount Azure credentials** in your Claude Desktop configuration:
   ```json
   {
     "mcpServers": {
       "k8s-mcp-server": {
         "command": "docker",
         "args": [
           "run",
           "-i",
           "--rm",
           "-v",
           "/Users/YOUR_USER_NAME/.kube:/home/appuser/.kube:ro",
           "-v",
           "/Users/YOUR_USER_NAME/.azure:/home/appuser/.azure:ro",
           "ghcr.io/alexei-led/k8s-mcp-server:latest"
         ]
       }
     }
   }
   ```

2. **Set Azure environment variables** (optional):
   ```json
   {
     "mcpServers": {
       "k8s-mcp-server": {
         "command": "docker",
         "args": [
           "run",
           "-i",
           "--rm",
           "-v",
           "/Users/YOUR_USER_NAME/.kube:/home/appuser/.kube:ro",
           "-v",
           "/Users/YOUR_USER_NAME/.azure:/home/appuser/.azure:ro",
           "-e",
           "AZURE_SUBSCRIPTION=my-subscription-id",
           "-e",
           "AZURE_DEFAULTS_LOCATION=eastus",
           "ghcr.io/alexei-led/k8s-mcp-server:latest"
         ]
       }
     }
   }
   ```

3. **Update kubeconfig** for AKS cluster access (if not already done):
   ```bash
   az aks get-credentials --resource-group myResourceGroup --name myAKSCluster
   ```

### Troubleshooting AKS

1. **Authentication issues**:
   - Ensure Azure credentials are properly mounted
   - Check that your Azure account has sufficient permissions
   - Verify your AKS cluster exists in the specified resource group

2. **Connection issues**:
   - Check that your kubeconfig is correctly configured for AKS
   - Ensure your network can reach the AKS API server