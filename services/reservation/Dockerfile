# ============================================================
# Reservation Service Dockerfile - 多阶段构建
# 目标: 最终镜像 ≤ 200MB, 安全, 非 root 用户运行
# ============================================================

# Stage 1: Build
FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Development
FROM python:3.12-slim AS development

WORKDIR /app

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir debugpy pytest pytest-cov

EXPOSE 8081

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8081", "--reload"]

# Stage 3: Production
FROM python:3.12-slim AS production

LABEL org.opencontainers.image.title="NekoCafé Reservation Service"
LABEL org.opencontainers.image.description="桌位可用性查询、预约生命周期管理"

RUN groupadd -r nekocafe && useradd -r -g nekocafe -d /app nekocafe

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/archives

COPY --from=builder /root/.local /usr/local
ENV PATH=/usr/local/bin:$PATH

COPY src/ .

RUN chown -R nekocafe:nekocafe /app
USER nekocafe

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

EXPOSE 8081

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8081", "--workers", "2"]
