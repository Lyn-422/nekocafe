"""Reservation Service 配置"""

import os

APP_ENV = os.getenv("APP_ENV", "dev")
APP_NAME = "reservation-service"
APP_VERSION = "1.0.0"

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "nekocafe")
DB_PASSWORD = os.getenv("DB_PASSWORD", "nekocafe123")
DB_NAME = os.getenv("DB_NAME", "nekocafe_reservation")
DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/1")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://nekocafe:nekocafe123@localhost:5672/")

MEMBER_SERVICE_URL = os.getenv("MEMBER_SERVICE_URL", "http://localhost:8080")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-prod")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "internal-key-change-in-prod")

OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

# 预约业务规则
MAX_ACTIVE_RESERVATIONS = 3
FREE_CANCEL_HOURS = 2
NO_SHOW_MINUTES = 15
CHECK_IN_EARLY_MINUTES = 30
