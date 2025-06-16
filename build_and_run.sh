#!/bin/bash
# 该脚本用于构建并运行k8s-mcp-server的Docker镜像，包含了代理设置。

# --- 配置 ---
set -e # 如果命令失败则立即退出
IMAGE_NAME="k8s-mcp-server-proxy:latest"
CONTAINER_NAME="k8s-mcp-server-proxy-container"

# --- 代理设置 ---
# 使用 host.docker.internal 来允许 Docker 容器连接到宿主机的代理
PROXY_HOST="host.docker.internal"
PROXY_PORT="7890"

export https_proxy="http://${PROXY_HOST}:${PROXY_PORT}"
export http_proxy="http://${PROXY_HOST}:${PROXY_PORT}"
export all_proxy="socks5://${PROXY_HOST}:${PROXY_PORT}"

# --- 脚本主体 ---

echo "--- [1/4] 正在使用代理构建Docker镜像: ${IMAGE_NAME} ---"
# 使用--no-cache确保获取最新的依赖
docker build \
    --build-arg "http_proxy=${http_proxy}" \
    --build-arg "https_proxy=${https_proxy}" \
    --build-arg "all_proxy=${all_proxy}" \
    --no-cache -f deploy/docker/Dockerfile -t ${IMAGE_NAME} .
echo "✅ 镜像构建完成。"

# 检查容器是否已在运行，如果是则停止并删除
if [ "$(docker ps -a -q -f name=^/${CONTAINER_NAME}$)" ]; then
    echo "--- [2/4] 正在停止并删除已存在的容器: ${CONTAINER_NAME} ---"
    docker stop ${CONTAINER_NAME} >/dev/null
    docker rm ${CONTAINER_NAME} >/dev/null
    echo "✅ 旧容器已清理。"
else
    echo "--- [2/4] 无需清理旧容器。 ---"
fi

echo "--- [3/4] 正在运行新的Docker容器: ${CONTAINER_NAME} ---"
docker run -d -p 9096:9096 --name ${CONTAINER_NAME} ${IMAGE_NAME}
echo "✅ 容器已启动。"

echo "--- [4/4] 等待服务器启动并进行健康检查 (等待15秒) ---"
sleep 15

echo "--- 检查容器日志 ---"
# 显示最后20行日志，避免日志过多
docker logs ${CONTAINER_NAME} | tail -n 20

echo ""
echo "--- 检查容器状态 ---"
docker ps -f name="^/${CONTAINER_NAME}$"

echo ""
echo "--- 测试 /health 端点 ---"
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9096/health)
if [ "$HEALTH_STATUS" -eq 200 ]; then
    echo "✅ 健康检查成功，服务器正在运行！"
    curl -s http://localhost:9096/health
    echo ""
    echo "🎉 K8s MCP Server 已成功启动并运行在 http://localhost:9096"
else
    echo "❌ 健康检查失败，HTTP状态码: $HEALTH_STATUS"
    echo "请检查容器日志以获取详细信息。"
    exit 1
fi

echo ""
echo "=== 常用命令 ==="
echo "查看容器状态: docker ps"
echo "查看应用日志: docker logs -f $CONTAINER_NAME"
echo "停止应用: docker stop $CONTAINER_NAME"
echo "重启应用: docker restart $CONTAINER_NAME"
echo "进入容器: docker exec -it $CONTAINER_NAME /bin/bash" 