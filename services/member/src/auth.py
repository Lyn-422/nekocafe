"""JWT 认证模块"""

import uuid
from datetime import datetime, timedelta
import jwt
from config import JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS


def create_access_token(user_id: str) -> tuple[str, datetime]:
    """创建 Access Token (15分钟有效)"""
    now = datetime.utcnow()
    expires = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": expires,
        "type": "access",
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, expires


def create_refresh_token(user_id: str) -> tuple[str, datetime]:
    """创建 Refresh Token (7天有效)"""
    now = datetime.utcnow()
    expires = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": expires,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, expires


def decode_token(token: str) -> dict:
    """解码并验证 Token"""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def verify_access_token(token: str) -> dict | None:
    """验证 Access Token"""
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
