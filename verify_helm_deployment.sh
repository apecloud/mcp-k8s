#!/bin/bash
#
# This script builds a Docker image from local code, deploys it using the Helm chart,
# and verifies the deployment.
#
# 请确保您已安装 Docker, Helm, 和 kubectl, 并且它们已正确配置以连接到您的 Kubernetes 集群。
# For local clusters like Minikube or Kind, you must first load the image into the cluster.

set -e
# --- Configuration ---
# Helm release name
RELEASE_NAME="mcp-server-test"
# Kubernetes namespace
NAMESPACE="default"
# Docker image name
IMAGE_NAME="k8s-mcp-server"
# Docker image tag
IMAGE_TAG="local-test"
# Chart path
CHART_PATH="./deploy/helm"
# Service port
SERVICE_PORT="9096"

# --- Script ---
echo "--- 1. Preparing Docker Environment ---"
echo "Pulling the latest base image to prevent cache issues..."
docker pull python:3.11-slim
echo "Pruning Docker build cache..."
docker builder prune -f

echo "--- 1b. Building local Docker image: ${IMAGE_NAME}:${IMAGE_TAG} ---"
docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" -f deploy/docker/Dockerfile .
echo "Image built successfully."

echo -e "\n--- 2. Loading image into Minikube cluster ---"
# This command loads the newly built image into your Minikube cluster's Docker daemon.
minikube image load "${IMAGE_NAME}:${IMAGE_TAG}"

echo -e "\n--- 3. Deploying with Helm ---"
# We set pullPolicy to Never to ensure the local image is used.
helm install "${RELEASE_NAME}" "${CHART_PATH}" \
  --namespace "${NAMESPACE}" \
  --set image.repository="${IMAGE_NAME}" \
  --set image.tag="${IMAGE_TAG}" \
  --set image.pullPolicy=Never

# --- Verification ---
echo -e "\n--- 4. Waiting for deployment to be ready ---"
kubectl rollout status deployment/"${RELEASE_NAME}-k8s-mcp-server" --namespace "${NAMESPACE}"

echo -e "\n--- 5. Port-forwarding service to localhost:${SERVICE_PORT} ---"
kubectl port-forward svc/"${RELEASE_NAME}-k8s-mcp-server" "${SERVICE_PORT}:${SERVICE_PORT}" --namespace "${NAMESPACE}" &
PF_PID=$!
# Wait a moment for port-forwarding to initialize
sleep 3

echo -e "\n--- 6. Verifying service with curl ---"
if curl --fail http://localhost:${SERVICE_PORT}/health; then
  echo -e "\nVerification successful! The service is up and running."
else
  echo -e "\nVerification failed!"
fi


# --- Cleanup ---
echo -e "\n--- 7. Cleaning up ---"
echo "Stopping port-forwarding (PID: ${PF_PID})..."
kill "${PF_PID}"
echo "Uninstalling Helm release '${RELEASE_NAME}'..."
helm uninstall "${RELEASE_NAME}" --namespace "${NAMESPACE}"

echo -e "\nScript finished." 