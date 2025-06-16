#!/bin/bash

# This script provides a unified way to run and test the server
# either locally or within a Docker container.
#
# Usage:
#   ./build_run_test.sh local   - To run and test on the local machine
#   ./build_run_test.sh docker  - To build, run, and test the Docker image

set -e

MODE=$1

if [ -z "$MODE" ] || { [ "$MODE" != "local" ] && [ "$MODE" != "docker" ]; }; then
  echo "Usage: $0 [local|docker]"
  exit 1
fi

# --- Common variables ---
SERVER_URL="http://localhost:9096/tools/kubectl"
KUBECONFIG_PATH="/Users/cccmmmddd/GolandProjects/apecloud/dev-kubeconfig"
LOG_FILE="server.log"
SERVER_PID=""
CONTAINER_NAME="mcp-server-local"
JSON_PAYLOAD_FILE=$(mktemp) # Create a temporary file for the JSON payload

# --- Cleanup function ---
# This function is called on script exit to ensure servers/containers are stopped.
cleanup() {
  echo ""
  echo "--- Cleaning up ---"
  if [ "$MODE" == "local" ] && [ ! -z "$SERVER_PID" ]; then
    echo "Stopping local server (PID: $SERVER_PID)..."
    # Kill the process; '|| true' prevents script failure if process is already gone
    kill $SERVER_PID || true
  elif [ "$MODE" == "docker" ]; then
    echo "Stopping Docker container ($CONTAINER_NAME)..."
    docker stop $CONTAINER_NAME > /dev/null || true
  fi
  rm -f "$JSON_PAYLOAD_FILE"
  echo "Cleanup complete."
}
trap cleanup EXIT


# --- Main logic ---
if [ "$MODE" == "local" ]; then
  echo "--- Running in LOCAL mode ---"
  
  echo "[1/3] Installing/syncing dependencies with uv..."
  uv sync
  
  echo "[2/3] Starting server locally in the background..."
  uv run uvicorn src.k8s_mcp_server.app:app --host 0.0.0.0 --port 9096 > "$LOG_FILE" 2>&1 &
  SERVER_PID=$!
  echo "Server started with PID: ${SERVER_PID}. Logs at ${LOG_FILE}"
  
  echo "[3/3] Waiting for server to start (5 seconds)..."
  sleep 5
  if ! ps -p $SERVER_PID > /dev/null; then
    echo "Server failed to start. Check logs:"
    cat "$LOG_FILE"
    exit 1
  fi
  echo "Server is running."

elif [ "$MODE" == "docker" ]; then
  echo "--- Running in DOCKER mode ---"
  IMAGE_NAME="k8s-mcp-server-local:latest"

  echo "[1/3] Building Docker image: ${IMAGE_NAME}..."
  docker build -f deploy/docker/Dockerfile -t ${IMAGE_NAME} .
  
  echo "[2/3] Running Docker container: ${CONTAINER_NAME}..."
  docker run -d --rm -p 9096:9096 --name ${CONTAINER_NAME} ${IMAGE_NAME}
  
  echo "[3/3] Waiting for server to start (5 seconds)..."
  sleep 2 # Give container a moment to initialize before grabbing logs
  docker logs -f ${CONTAINER_NAME} > "$LOG_FILE" 2>&1 &
  sleep 3

  if ! docker ps -f name="^/${CONTAINER_NAME}$" --format "{{.Names}}" | grep -q ${CONTAINER_NAME}; then
    echo "Container failed to start. Check logs:"
    cat "$LOG_FILE"
    exit 1
  fi
  echo "Container is running."
fi

# --- Test execution (common for both modes) ---
echo ""
echo "--- Preparing to test server at ${SERVER_URL} ---"

if [ ! -f "$KUBECONFIG_PATH" ]; then
  echo "Error: Kubeconfig file not found at ${KUBECONFIG_PATH}"
  echo "Please ensure you have a valid kubeconfig file to test the server."
  exit 1
fi
KUBECONFIG_CONTENT=$(cat "${KUBECONFIG_PATH}")

# Create the JSON payload in the temporary file
# Using jo would be safer, but for now, manual JSON creation with escaped newlines.
# Update: Using a more robust printf to build the JSON and avoid escaping issues.
printf '{"command": "get pods", "kubeconfig": %s}' "$(awk -v ORS='\\n' '1' "${KUBECONFIG_PATH}" | sed 's/"/\\"/g' | tr -d '\n' | xargs -0 printf '"%s"') " > "$JSON_PAYLOAD_FILE"

echo "--- Testing server with 'kubectl get pods' ---"
# Temporarily disable 'exit on error' to allow us to capture the exit code and logs
set +e
RESPONSE=$(curl -s --fail -X POST ${SERVER_URL} \
  -H "Content-Type: application/json" \
  -d @"$JSON_PAYLOAD_FILE"
)
CURL_EXIT_CODE=$?
set -e # Re-enable 'exit on error'

if [ $CURL_EXIT_CODE -ne 0 ]; then
    echo "❌ Test failed: curl command failed with exit code $CURL_EXIT_CODE (Likely HTTP 4xx/5xx error)."
    echo "This could mean the server is not reachable or the request was rejected."
    echo ""
    echo "--- Server logs (${LOG_FILE}) ---"
    cat "$LOG_FILE"
    exit 1
fi

# We expect a JSON response with success field
if echo "$RESPONSE" | grep -q '"success"'; then
  echo "✅ Test successful: Server responded with JSON result."
  echo "--- Full response ---"
  echo "$RESPONSE"
else
  echo "❌ Test failed: Did not receive the expected JSON response."
  echo "--- Full response ---"
  echo "$RESPONSE"
  echo ""
  echo "--- Server logs (${LOG_FILE}) ---"
  cat "$LOG_FILE"
  exit 1
fi

echo ""
echo "--- Script finished successfully for mode: $MODE ---" 