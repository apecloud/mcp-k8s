#!/bin/bash

# K8s MCP Server 一键构建和运行脚本
set -e

echo "=== K8s MCP Server Docker 一键构建和运行 ==="

# 检查是否需要设置代理
if [ ! -z "$SET_PROXY" ]; then
    echo "设置代理环境变量..."
    export https_proxy=http://127.0.0.1:7890
    export http_proxy=http://127.0.0.1:7890
    export all_proxy=socks5://127.0.0.1:7890
    echo "代理已设置: $https_proxy"
fi

# 选择使用哪个Dockerfile
DOCKERFILE="${1:-Dockerfile.simple}"
IMAGE_NAME="${2:-k8s-mcp-server}"

echo "使用Dockerfile: $DOCKERFILE"
echo "镜像名称: $IMAGE_NAME"

# 构建镜像
echo "正在构建Docker镜像..."
docker build -t "$IMAGE_NAME" -f "$DOCKERFILE" .

if [ $? -eq 0 ]; then
    echo "✅ Docker镜像构建成功！"
else
    echo "❌ Docker镜像构建失败！"
    exit 1
fi

# 停止已运行的容器
echo "停止现有容器..."
docker stop "$IMAGE_NAME-container" 2>/dev/null || true
docker rm "$IMAGE_NAME-container" 2>/dev/null || true

# 运行容器
echo "启动新容器..."
docker run -d \
    --name "$IMAGE_NAME-container" \
    -p 9096:9096 \
    -v ~/.kube:/home/appuser/.kube:ro \
    "$IMAGE_NAME"

if [ $? -eq 0 ]; then
    echo "✅ 容器启动成功！"
    echo "📡 应用地址: http://localhost:9096"
    echo "🔍 健康检查: curl http://localhost:9096/health"
    echo "📝 查看日志: docker logs $IMAGE_NAME-container"
    echo "🛑 停止容器: docker stop $IMAGE_NAME-container"
else
    echo "❌ 容器启动失败！"
    exit 1
fi

# 等待几秒后检查健康状态
echo "等待应用启动..."
sleep 5

echo "检查应用健康状态..."
for i in {1..10}; do
    if curl -f http://localhost:9096/health >/dev/null 2>&1; then
        echo "✅ 应用健康检查通过！"
        echo "🎉 K8s MCP Server 已成功启动并运行在 http://localhost:9096"
        break
    else
        echo "⏳ 等待应用启动... ($i/10)"
        sleep 2
    fi
    
    if [ $i -eq 10 ]; then
        echo "⚠️  应用可能启动缓慢，请稍后手动检查"
        echo "📝 查看日志: docker logs $IMAGE_NAME-container"
    fi
done

echo ""
echo "=== 常用命令 ==="
echo "查看容器状态: docker ps"
echo "查看应用日志: docker logs -f $IMAGE_NAME-container"
echo "停止应用: docker stop $IMAGE_NAME-container"
echo "重启应用: docker restart $IMAGE_NAME-container"
echo "进入容器: docker exec -it $IMAGE_NAME-container /bin/bash" 