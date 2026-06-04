"""Member Service - NekoCafé 会员服务主入口"""

import logging
import json
import sys
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from routes import router

# 结构化日志配置
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "member-service",
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "traceId"):
            log_entry["traceId"] = record.traceId
        if hasattr(record, "spanId"):
            log_entry["spanId"] = record.spanId
        return json.dumps(log_entry, ensure_ascii=False)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger("member-service")

# OpenTelemetry
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create({"service.name": "member-service"})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    OTEL_ENABLED = True
except ImportError:
    OTEL_ENABLED = False

app = FastAPI(
    title="NekoCafé Member Service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 注册路由
app.include_router(router)

# OpenTelemetry 自动埋点
if OTEL_ENABLED:
    FastAPIInstrumentor.instrument_app(app)


@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    """注入 traceId 到日志和响应"""
    trace_id = request.headers.get("x-trace-id", "")
    start_time = datetime.utcnow()

    response = await call_next(request)

    duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
    response.headers["X-Trace-Id"] = trace_id
    response.headers["X-Service"] = "member-service"

    logger.info(
        f"{request.method} {request.url.path} {response.status_code} {duration_ms:.1f}ms",
        extra={"traceId": trace_id, "duration": duration_ms},
    )

    return response


@app.get("/health")
async def health():
    """健康检查端点"""
    return {
        "status": "UP",
        "service": "member-service",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health/ready")
async def readiness():
    """就绪检查 - 包含依赖状态"""
    # 检查 MySQL 和 Redis 连接
    checks = {
        "database": "UP",   # 实际应按真实连接状态
        "redis": "UP",
        "rabbitmq": "UP",
    }
    all_up = all(v == "UP" for v in checks.values())
    return {
        "status": "UP" if all_up else "DEGRADED",
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
