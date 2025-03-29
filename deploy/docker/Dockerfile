# Multi-stage build with platform-specific configuration
ARG PYTHON_VERSION=3.13-slim

# =========== BUILDER STAGE ===========
FROM --platform=${TARGETPLATFORM} python:${PYTHON_VERSION} AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /build

# Copy package definition files
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

# Install package and dependencies with pip wheel
RUN pip install --no-cache-dir wheel && \
    pip wheel --no-cache-dir --wheel-dir=/wheels -e .

# =========== FINAL STAGE ===========
FROM --platform=${TARGETPLATFORM} python:${PYTHON_VERSION}

# Set target architecture argument
ARG TARGETPLATFORM
ARG TARGETARCH

# Step 1: Install system packages - keeping all original packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    unzip \
    curl \
    wget \
    less \
    groff \
    jq \
    gnupg \
    tar \
    gzip \
    zip \
    vim \
    net-tools \
    dnsutils \
    openssh-client \
    grep \
    sed \
    gawk \
    findutils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Step 2: Install kubectl based on architecture
# Use specific kubectl version (e.g., v1.29.2)
ENV KUBECTL_VERSION=v1.29.2
RUN if [ "${TARGETARCH}" = "arm64" ]; then \
        curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/arm64/kubectl"; \
    else \
        curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl"; \
    fi \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/

# Step 3: Install Helm
# Use specific Helm version
ENV HELM_VERSION=v3.14.0
RUN if [ "${TARGETARCH}" = "arm64" ]; then \
        curl -LO "https://get.helm.sh/helm-${HELM_VERSION}-linux-arm64.tar.gz" && \
        tar -zxvf helm-${HELM_VERSION}-linux-arm64.tar.gz && \
        mv linux-arm64/helm /usr/local/bin/helm && \
        rm -rf linux-arm64 helm-${HELM_VERSION}-linux-arm64.tar.gz; \
    else \
        curl -LO "https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz" && \
        tar -zxvf helm-${HELM_VERSION}-linux-amd64.tar.gz && \
        mv linux-amd64/helm /usr/local/bin/helm && \
        rm -rf linux-amd64 helm-${HELM_VERSION}-linux-amd64.tar.gz; \
    fi && chmod +x /usr/local/bin/helm

# Step 4: Install istioctl
# Use specific Istio version
ENV ISTIO_VERSION=1.21.0
RUN if [ "${TARGETARCH}" = "arm64" ]; then \
        ISTIO_ARCH="arm64"; \
    else \
        ISTIO_ARCH="amd64"; \
    fi \
    && curl -L https://istio.io/downloadIstio | ISTIO_VERSION=${ISTIO_VERSION} TARGET_ARCH=${ISTIO_ARCH} sh - \
    && mv istio-*/bin/istioctl /usr/local/bin/ \
    && rm -rf istio-*

# Step 5: Install ArgoCD CLI
# Use specific ArgoCD version
ENV ARGOCD_VERSION=v2.9.6
RUN if [ "${TARGETARCH}" = "arm64" ]; then \
        curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/download/${ARGOCD_VERSION}/argocd-linux-arm64; \
    else \
        curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/download/${ARGOCD_VERSION}/argocd-linux-amd64; \
    fi \
    && chmod +x argocd \
    && mv argocd /usr/local/bin/

# Set up application directory, user, and permissions
RUN mkdir -p /app/logs && chmod 777 /app/logs \
    && useradd -m -s /bin/bash -u 10001 appuser \
    && mkdir -p /home/appuser/.kube \
    && chmod 700 /home/appuser/.kube

WORKDIR /app

# Copy application code
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/
COPY deploy/docker/security_config.yaml ./security_config.yaml

# Copy wheels from builder and install
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels k8s-mcp-server && \
    rm -rf /wheels

# Set ownership after all files have been copied
RUN chown -R appuser:appuser /app /home/appuser/.kube

# Switch to non-root user
USER appuser

# Set all environment variables in one layer
ENV HOME="/home/appuser" \
    PATH="/usr/local/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    K8S_MCP_LOG_DIR=/app/logs \
    K8S_MCP_TRANSPORT=stdio \
    K8S_MCP_SECURITY_MODE=strict \
    K8S_MCP_SECURITY_CONFIG=/app/security_config.yaml

# Add metadata
LABEL maintainer="Alexei Ledenev" \
      description="Kubernetes Multi-Command Proxy Server" \
      org.opencontainers.image.source="https://github.com/alexei-led/k8s-mcp-server" \
      org.opencontainers.image.version="1.0.0"

# Expose the service port (only needed if using SSE transport)
EXPOSE 8080

# Set command to run the server
ENTRYPOINT ["python", "-m", "k8s_mcp_server"]
