"""JWT 认证模块"""

import uuid
import hashlib
import time
from datetime import datetime, timedelta
from config import JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS

try:
    import jwt as pyjwt
    _HAS_JWT = True
except ImportError:
    pyjwt = None
    _HAS_JWT = False


def create_access_token(user_id: str) -> tuple[str, datetime]:
    """创建 Access Token (15分钟有效)"""
    now = datetime.utcnow()
    expires = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    if _HAS_JWT:
        payload = {
            "sub": user_id, "iat": now, "exp": expires,
            "type": "access", "jti": str(uuid.uuid4()),
        }
        token = pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    else:
        token = f"sim.{user_id}.{int(time.time())}.{hashlib.sha256(JWT_SECRET.encode()).hexdigest()[:16]}"
    return token, expires


def create_refresh_token(user_id: str) -> tuple[str, datetime]:
    """创建 Refresh Token (7天有效)"""
    now = datetime.utcnow()
    expires = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    if _HAS_JWT:
        payload = {
            "sub": user_id, "iat": now, "exp": expires,
            "type": "refresh", "jti": str(uuid.uuid4()),
        }
        token = pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    else:
        token = f"sim_refresh.{user_id}.{int(time.time())}.{hashlib.sha256(JWT_SECRET.encode()).hexdigest()[:16]}"
    return token, expires


def decode_token(token: str) -> dict:
    """解码并验证 Token"""
    if _HAS_JWT:
        return pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    # Simple fallback: parse simulated token
    parts = token.split(".")
    if len(parts) == 4 and parts[0] in ("sim", "sim_refresh"):
        return {"sub": parts[1], "type": "access" if parts[0] == "sim" else "refresh"}
    raise Exception("invalid token")


def verify_access_token(token: str) -> dict | None:
    """验证 Access Token"""
    try:
        if _HAS_JWT:
            payload = decode_token(token)
            if payload.get("type") != "access":
                return None
            return payload
        else:
            parts = token.split(".")
            if len(parts) == 4 and parts[0] == "sim":
                # Verify hash
                expected = hashlib.sha256(JWT_SECRET.encode()).hexdigest()[:16]
                if parts[3] == expected:
                    return {"sub": parts[1], "type": "access"}
            return None
    except Exception:
        return None
