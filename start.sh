#!/bin/bash

# 启动 K8s MCP Server
# 确保使用正确的Python路径和参数

set -e

# 输出启动信息
echo "正在启动 K8s MCP Server..."
echo "监听地址: 0.0.0.0:9096"
echo "Python 模块: k8s_mcp_server.app:app"

# 启动应用
exec uvicorn k8s_mcp_server.app:app --host 0.0.0.0 --port 9096 