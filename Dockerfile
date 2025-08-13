# 使用官方 Python 3.11 slim 镜像作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LLM_PROVIDERS_CONFIG_FILE=providers_config.json

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY pyproject.toml setup.py MANIFEST.in ./
COPY README.md LICENSE ./
COPY canctool/ ./canctool/
COPY main.py ./

# 复制配置文件示例
COPY providers_config.json.example ./providers_config.json.example

# 安装 Python 依赖
RUN pip install --upgrade pip && \
    pip install -e .

# 创建非 root 用户
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# 暴露端口
EXPOSE 8001

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# 启动命令
CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "8001"]
