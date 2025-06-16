#!/bin/bash

# 启动 K8s MCP Server
# 确保使用正确的Python路径和参数

set -e

# --- 验证所需工具 ---
echo "正在验证所需的CLI工具..."
REQUIRED_TOOLS="kubectl helm istioctl argocd"
for tool in $REQUIRED_TOOLS; do
    if ! command -v "$tool" &> /dev/null; then
        echo "错误: 必需的工具 '$tool' 未找到或不在PATH中。" >&2
        exit 1
    fi
    echo "  - $tool: 已找到"
done
echo "所有必需的工具都已找到。"
echo ""

# 输出启动信息
echo "正在启动 K8s MCP Server..."
echo "监听地址: 0.0.0.0:9096"
echo "Python 模块: k8s_mcp_server.app:app"

# 启动应用
exec uvicorn k8s_mcp_server.app:app --host 0.0.0.0 --port 9096 