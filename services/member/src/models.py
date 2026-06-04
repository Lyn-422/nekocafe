"""Member Service 数据模型"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, BigInteger, DateTime, Enum, Boolean, Text, Float
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    phone_encrypted = Column(Text)  # AES-256 加密存储
    nickname = Column(String(30))
    avatar = Column(String(255))
    password_hash = Column(String(255))
    wechat_openid = Column(String(64), unique=True, index=True)
    alipay_openid = Column(String(64), unique=True, index=True)
    preferences = Column(Text)  # JSON
    is_deactivated = Column(Boolean, default=False)
    deactivated_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Member(Base):
    __tablename__ = "members"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), unique=True, nullable=False, index=True)
    level = Column(Enum("NORMAL", "SILVER", "GOLD", "DIAMOND"), default="NORMAL")
    current_points = Column(BigInteger, default=0)
    total_points_earned = Column(BigInteger, default=0)
    activated_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PointsRecord(Base):
    __tablename__ = "points_records"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)
    type = Column(Enum("EARN", "REDEEM", "EXPIRE", "ADJUST"))
    amount = Column(Integer, nullable=False)
    balance_after = Column(BigInteger, nullable=False)
    source = Column(String(255))
    description = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), index=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(String(36))
    before_snapshot = Column(Text)  # JSON
    after_snapshot = Column(Text)   # JSON
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)


# 会员等级阈值
LEVEL_THRESHOLDS = {
    "NORMAL": (0, 999),
    "SILVER": (1000, 4999),
    "GOLD": (5000, 19999),
    "DIAMOND": (20000, float("inf")),
}

# 会员折扣率
LEVEL_DISCOUNTS = {
    "NORMAL": 1.0,
    "SILVER": 0.95,
    "GOLD": 0.90,
    "DIAMOND": 0.85,
}

# 积分倍数
LEVEL_MULTIPLIERS = {
    "NORMAL": 1.0,
    "SILVER": 1.2,
    "GOLD": 1.5,
    "DIAMOND": 2.0,
}
