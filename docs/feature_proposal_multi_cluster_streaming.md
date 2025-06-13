# K8s MCP Server 新功能提案：独立的 SSE 服务与动态多集群支持

## 1. 概述

本提案根据最新的需求进行修订，旨在将 K8s MCP Server 重构为一个**独立的、可通过网络访问的服务**。它将通过 Server-Sent Events (SSE) 提供流式响应，并允许在每次 API 请求中动态传入 `kubeconfig` 内容，以实现真正的多集群支持。

## 2. 核心架构变更

服务器将从一个由客户端（如 Claude Desktop）管理的临时 Docker 容器，转变为一个**长期运行的、独立部署的服务**。客户端将通过指定的 URL 与其通信。

### 客户端配置

客户端（如 Claude Desktop）将按如下方式配置以连接到此服务：

```json
{
  "mcpServers": {
    "kom": {
      "type": "sse",
      "url": "http://<服务器IP>:9096/sse"
    }
  }
}
```

*   `"type": "sse"`: 明确指出通信协议。
*   `"url"`: `k8s-mcp-server` 提供的 SSE 端点的完整 URL。

## 3. 功能实现方案

### 3.1. SSE API 端点

*   **Endpoint**: 服务器将监听一个 POST 端点，例如 `/sse`。
*   **协议**: 通信将通过 Server-Sent Events 进行。客户端发起连接后，服务器将保持连接打开，并持续推送事件数据。
*   **请求体 (Request Body)**: 每次向 `/sse` 发起的 POST 请求都应包含一个 JSON 对象，结构如下：

    ```json
    {
      "command": "kubectl get pods -n default",
      "kubeconfig": "apiVersion: v1\nclusters:\n- cluster: ...",
      "timeout": 300
    }
    ```
    *   `command` (string, required): 需要在服务器上执行的完整 shell 命令。
    *   `kubeconfig` (string, required): 目标 Kubernetes 集群的 `kubeconfig` 文件的完整内容。
    *   `timeout` (integer, optional): 命令执行的超时时间（秒），默认为 300。

*   **响应流 (Response Stream)**: 服务器将以 SSE 格式流式返回数据。每个事件都代表命令输出的一行或一个状态更新。

    ```
    event: stdout
    data: Pod a-1234 is running

    event: stdout
    data: Pod b-5678 is running

    event: stderr
    data: Error connecting to cluster a

    event: control
    data: {"status": "done", "exit_code": 0}

    ```
    *   `event: stdout`: 表示标准输出的一行。
    *   `event: stderr`: 表示标准错误的一行。
    *   `event: control`: 用于传输控制信号，例如任务完成、错误状态或退出码。

### 3.2. 动态 `kubeconfig` 处理

这是实现多集群支持的核心。

*   **接收**: 服务器从 API 请求体中获取 `kubeconfig` 字符串。
*   **临时存储**: 在处理请求期间，服务器会将接收到的 `kubeconfig` 内容写入一个**临时的、唯一的**文件中（例如，在容器内的 `/tmp/kubeconfig-xyz123.yaml`）。
*   **命令执行**: 服务器在执行 `kubectl` 或其他命令时，会将 `KUBECONFIG` 环境变量设置为指向这个临时文件的路径。
*   **清理**: 命令执行完毕（无论成功、失败或超时），服务器都必须**确保删除这个临时 `kubeconfig` 文件**，以避免凭据泄露和磁盘空间滥用。

### 3.3. 生产部署（保持不变）

为了支持其作为独立服务运行，提供官方的生产部署方案仍然至关重要。

*   **Helm Chart**: 创建一个 Helm Chart 用于在 Kubernetes 中部署 `k8s-mcp-server` 服务。
*   **Docker Compose**: 提供一个 Docker Compose 文件用于在 Docker 环境中快速启动服务。
*   **安全**: 文档需要强调网络安全（例如，保护 SSE 端点）、凭据处理安全以及最小权限原则。

## 4. 修订后实施计划

1.  **阶段 1: 核心服务与 API 实现**
    *   **优先级**:
        *   创建一个基于 Python Web 框架（如 FastAPI 或 Flask）的服务器应用。
        *   实现 `/sse` POST 端点，并能正确解析请求体。
        *   实现动态 `kubeconfig` 的临时文件处理逻辑（创建、使用、清理）。
        *   实现使用传入的 `kubeconfig` 执行命令的逻辑。
        *   实现 SSE 流式响应，能够区分 `stdout`, `stderr` 和 `control` 事件。
    *   **产出**: 一个功能性的 `k8s-mcp-server`，可以通过 `curl` 或类似工具进行测试。

2.  **阶段 2: 完善与打包**
    *   **优先级**:
        *   编写单元测试和集成测试，特别是针对 `kubeconfig` 处理和 SSE 流。
        *   创建 `Dockerfile` 用于构建服务镜像。
        *   创建 Helm Chart 和 Docker Compose 文件。
    *   **产出**: 可靠、可部署的 `k8s-mcp-server` 镜像和部署模板。

3.  **阶段 3: 文档更新**
    *   **优先级**:
        *   在代码和功能稳定后，**更新 `README.md`**，全面介绍新的独立服务架构、API 用法和客户端配置。
        *   创建详细的部署和安全指南。
    *   **产出**: 面向用户的完整文档。

## 5. 结论

这次修订使计划更加具体和可行，完全对齐了将 `k8s-mcp-server` 作为独立 SSE 服务运行的核心目标。这种架构提供了更大的灵活性、可扩展性和对多集群环境的真正支持。 