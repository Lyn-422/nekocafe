# ============================================================
# Member Service Dockerfile - 多阶段构建
# 目标: 最终镜像 ≤ 200MB, 安全, 非 root 用户运行
# ============================================================

# Stage 1: Build (构建依赖)
FROM python:3.12-slim AS builder

WORKDIR /app

# 安装构建依赖
COPY src/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Development (本地开发)
FROM python:3.12-slim AS development

WORKDIR /app

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装开发工具
RUN pip install --no-cache-dir debugpy pytest pytest-cov

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]

# Stage 3: Production (精简运行)
FROM python:3.12-slim AS production

LABEL org.opencontainers.image.title="NekoCafé Member Service"
LABEL org.opencontainers.image.description="用户注册/登录、会员等级与积分管理"

# 创建非 root 用户
RUN groupadd -r nekocafe && useradd -r -g nekocafe -d /app nekocafe

WORKDIR /app

# 安装运行时依赖（仅 curl 用于健康检查）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/archives

# 从 builder 复制依赖
COPY --from=builder /root/.local /usr/local
ENV PATH=/usr/local/bin:$PATH

# 复制应用代码
COPY src/ .

# 设置文件权限
RUN chown -R nekocafe:nekocafe /app

# 切换到非 root 用户
USER nekocafe

# 健康检查
HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
