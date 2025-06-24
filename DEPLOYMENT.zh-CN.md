# Deployment Guide (Cloud-Native)

[**English**](./DEPLOYMENT.md) | [**中文**](./DEPLOYMENT.zh-CN.md)

---

## 🇨🇳 中文

本指南提供了详细的、一步步的说明，用于将全栈 AI 分析助手应用部署到 Google Cloud Platform，并采用健壮的云原生架构。

### 部署策略

我们将采用一个现代化的、高效的服务组合：

- **后端 (Python/FastAPI)**: 部署于 **Cloud Run**，这是一个无服务器容器平台，能够自动扩缩容且成本效益高。
- **前端 (React/TypeScript)**: 托管于 **Firebase Hosting**，它提供全球 CDN 加速，以实现快速、低延迟的内容分发。
- **定时任务**: 由 **Cloud Scheduler** 管理，并由一个专属的 **IAM 服务账号**保障安全，以确保后台任务能够被可靠地触发。

---

### 第 0 部分：准备工作 - 安装本地工具

在开始之前，请确保您的本地计算机上已经安装了以下工具：

1.  **`gcloud` 命令行工具 (Google Cloud SDK)**: 用于在终端与 Google Cloud 交互的工具。

    - 请遵循[官方安装指南](https://cloud.google.com/sdk/docs/install)。
    - 安装后，请运行 `gcloud init` 登录并选择您的 Google Cloud 项目。

2.  **Docker Desktop**: 用于将我们的后端应用打包成容器镜像。

    - 请从 [Docker 官方网站](https://www.docker.com/products/docker-desktop/) 下载并安装。

3.  **Firebase 命令行工具**: 用于与 Firebase 交互的工具。
    - 请通过全局安装：`npm install -g firebase-tools`。

---

### 第 1 部分：将后端部署至 Cloud Run

这是最关键的一步，我们将打包并启动我们的 Python 应用。

#### 步骤 1.1：为生产环境准备后端

1.  **安装 Gunicorn**: Gunicorn 是一个生产级的 Python 应用服务器。

    ```bash
    # 进入 backend/ 目录并激活您的虚拟环境
    cd backend
    pip install gunicorn
    pip freeze > requirements.txt # 重新生成 requirements.txt 以包含 gunicorn
    ```

2.  **最终确定 `Dockerfile`**: 确保您 `backend/` 目录下的 `Dockerfile` 文件包含以下最终版本。此版本已为 Cloud Run 优化。

    ```dockerfile
    # 使用官方的 Python 3.11 slim 基础镜像
    FROM python:3.11-slim

    # 设置容器内的工作目录
    WORKDIR /code

    # 复制并安装依赖
    COPY requirements.txt .
    RUN pip install --no-cache-dir --upgrade -r requirements.txt

    # 复制所有的应用源代码
    COPY ./app ./app

    # 暴露 Cloud Run 将提供的端口
    EXPOSE 8080

    # 运行应用的最终命令，使用 gunicorn
    # -w 1 (单个工作进程) 对于内存中的调度器或有状态应用至关重要。
    # --timeout 标志为后台任务提供更长的完成时间。
    CMD ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8080", "--timeout", "90"]
    ```

#### 步骤 1.2：构建与部署

我们将使用一条 `gcloud` 命令来构建 Docker 镜像，将其推送到 Google 的 Artifact Registry，并部署到 Cloud Run。

1.  **启用必要的云服务 API**: (每个项目仅需运行一次)

    ```bash
    gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com cloudscheduler.googleapis.com appengine.googleapis.com
    ```

2.  **运行一键部署命令**:

    - 在您项目的**根目录**下（即包含 `frontend` 和 `backend` 的目录）运行此命令。
    - 请替换 `[YOUR_PROJECT_ID]` 和您真实的 API 密钥。

    ```bash
    gcloud run deploy ai-analyst-backend \
      --source ./backend \
      --platform=managed \
      --region=us-central1 \
      --allow-unauthenticated \
      --memory=1Gi \
      --set-env-vars="AI_API_KEY=[YOUR_GEMINI_API_KEY],GITHUB_TOKEN=[YOUR_GITHUB_TOKEN]"
    ```

    - **参数说明**:
      - `--source ./backend`: 告诉 gcloud 从 `backend` 文件夹构建。
      - `--allow-unauthenticated`: 允许公共访问您的 API，以便前端可以调用它。
      - `--memory=1Gi`: 分配足够的内存以防止崩溃。
      - `--set-env-vars`: 在云环境中安全地设置您的密钥。

3.  **保存 URL**: 几分钟后，命令将完成并打印出公开的 **Service URL**。请仔细复制并保存此 URL。

---

### 第 2 部分：将前端部署至 Firebase Hosting

后端上线后，我们来部署前端。

#### 步骤 2.1：更新 API 端点

1.  打开您的前端代码 `frontend/src/App.tsx`。
2.  找到 `API_BASE_URL` 常量。
3.  将其值替换为您在上一步中保存的后端 **Service URL**。
    ```typescript
    const API_BASE_URL =
      "[https://ai-analyst-backend-xxxxxxxx-uc.a.run.app](https://ai-analyst-backend-xxxxxxxx-uc.a.run.app)";
    ```

#### 步骤 2.2：构建与部署

1.  **构建生产环境的静态文件:**

    ```bash
    # 进入 frontend/ 目录
    cd frontend
    npm run build
    ```

2.  **在您的项目中初始化 Firebase:**

    ```bash
    firebase init hosting
    ```

    - **请按如下提示回答问题**:
      - `Please select an option:` -> **`Use an existing project`**
      - `Select a default Firebase project...:` -> 从列表中选择您的 Google Cloud 项目。
      - `What do you want to use as your public directory?` -> 输入 **`dist`**
      - `Configure as a single-page app...?` -> 输入 **`y`** (是)
      - `Set up automatic builds...?` -> 输入 **`n`** (否，我们暂时手动部署)
      - `File dist/index.html already exists. Overwrite?` -> 输入 **`N`** (否)

3.  **部署上线！**
    ```bash
    firebase deploy
    ```
    完成后，它将给您一个 **Hosting URL**。这是您线上应用的公开地址。

---

### 第 3 部分：设置 Cloud Scheduler

这是使您的应用自动化的最后一步。

#### 步骤 3.1：创建 App Engine 应用 (仅需运行一次)

Cloud Scheduler 需要一个 App Engine 应用来确定其区域。

```bash
# 选择一个靠近您的区域，例如 us-central
gcloud app create --region=us-central
```

#### 步骤 3.2：创建 Scheduler 作业

1.  **打开 [Google Cloud Scheduler 控制台](https://console.cloud.google.com/cloudscheduler)**。
2.  点击 **“创建作业”**。
3.  **填写表单**:
    - **名称**: `run-analysis-task`
    - **区域**: 选择与您的 Cloud Run 服务相同的区域 (例如 `us-central1`)。
    - **频率**: `*/10 * * * *` (此 cron 表达式表示“每 10 分钟运行一次”)。
    - **时区**: 选择您期望的时区。
    - **目标类型**: **HTTP**
    - **URL**: 粘贴您的后端 **Service URL** 并附加 `/api/internal/run-task`。
    - **HTTP 方法**: **POST**
    - 点击 **“显示更多”**。
    - **Auth 标头**: 选择 **“添加 OIDC 令牌”**。
    - **服务账号**: 选择 **“Compute Engine 默认服务账号”**。
    - **标头**: 点击“添加标头”。
      - 标头名称: `X-Cloud-Scheduler`
      - 标头值: `true`
4.  点击 **“创建”**。

#### 步骤 3.3：强制运行第一次任务

1.  在 Cloud Scheduler 作业列表中，找到 `run-analysis-task`。
2.  点击右侧的三点菜单，然后选择 **“强制运行”**。
3.  您现在可以前往 **Cloud Run 日志**监控后台任务的执行。一旦完成，刷新您的前端应用，您应该就能看到初始数据了！

恭喜！您已成功部署了一个生产级的全栈 AI 应用。
