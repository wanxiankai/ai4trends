# 使用官方的 Python 3.11 精简版作为基础
FROM python:3.11-slim

# 在容器内创建一个叫 /code 的工作目录
WORKDIR /code

# 复制依赖文件到容器里
COPY requirements.txt .

# 安装所有 Python 依赖
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# 复制你所有的后端应用代码 (app/ 文件夹和里面的所有文件)
COPY ./app ./app

# Cloud Run 会自动提供一个端口，我们让容器监听这个端口
EXPOSE 8080

# 最终的运行命令：使用 gunicorn 启动你的 FastAPI 应用
# -w 4 表示启动 4 个工作进程
# -k uvicorn.workers.UvicornWorker 指定使用 uvicorn 作为工作模式
# --bind 0.0.0.0:8080 监听所有网络接口的 8080 端口
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8080"]
