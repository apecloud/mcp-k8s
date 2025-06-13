# K8s MCP Server Docker 快速使用

## 一键启动

**需要代理：**
```bash
make quick-start-proxy
```

**不需要代理：**
```bash
make quick-start
```

## 手动构建

```bash
# 设置代理（如需要）
export https_proxy=http://127.0.0.1:7890 http_proxy=http://127.0.0.1:7890 all_proxy=socks5://127.0.0.1:7890

# 构建镜像
docker build -t k8s-mcp-server -f Dockerfile.simple .

# 运行容器
docker run -d --name k8s-mcp-server-container -p 9096:9096 k8s-mcp-server
```

## 验证

```bash
curl http://localhost:9096/health
```

## 核心文件

- `Dockerfile.simple` - 简化版Dockerfile（推荐）
- `build_and_run.sh` - 一键构建运行脚本
- `start.sh` - 应用启动脚本
- `docker-compose.yml` - Docker Compose配置 