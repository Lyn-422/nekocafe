"""Member Service 配置"""

import os

# 应用
APP_ENV = os.getenv("APP_ENV", "dev")
APP_NAME = "member-service"
APP_VERSION = "1.0.0"

# 数据库
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "nekocafe")
DB_PASSWORD = os.getenv("DB_PASSWORD", "nekocafe123")
DB_NAME = os.getenv("DB_NAME", "nekocafe_member")
DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# RabbitMQ
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://nekocafe:nekocafe123@localhost:5672/")

# JWT
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-prod")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# OpenTelemetry
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

# 短信验证码（模拟）
SMS_CODE_LENGTH = 6
SMS_CODE_TTL = 60  # 秒

# PIPL 合规
ACCOUNT_DELETION_HOURS = 72
