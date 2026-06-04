"""Member Service API 路由"""

import uuid
import random
import hashlib
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Header
from pydantic import BaseModel, Field
from models import (
    User, Member, PointsRecord, AuditLog,
    LEVEL_THRESHOLDS, LEVEL_DISCOUNTS, LEVEL_MULTIPLIERS,
)
from auth import create_access_token, create_refresh_token, verify_access_token

router = APIRouter(prefix="/api/v1")


# ============================================================
# Pydantic Schemas
# ============================================================

class RegisterRequest(BaseModel):
    phone: str = Field(pattern=r'^1[3-9]\d{9}$')
    sms_code: str = Field(pattern=r'^\d{6}$')
    nickname: str | None = Field(default=None, max_length=30)
    agree_to_terms: bool = Field(default=True)

    class Config:
        @staticmethod
        def validate_agree_to_terms(v):
            if not v:
                raise ValueError("必须同意用户协议")
            return v


class LoginRequest(BaseModel):
    phone: str = Field(pattern=r'^1[3-9]\d{9}$')
    sms_code: str | None = None
    password: str | None = None


class SendSmsRequest(BaseModel):
    phone: str = Field(pattern=r'^1[3-9]\d{9}$')
    scene: str = Field(pattern=r'^(REGISTER|LOGIN|RESET_PASSWORD)$')


class OAuthRequest(BaseModel):
    code: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UpdateProfileRequest(BaseModel):
    nickname: str | None = Field(default=None, max_length=30)
    avatar: str | None = None


class RedeemRequest(BaseModel):
    benefit_id: str | None = None
    points: int | None = Field(default=None, ge=100)


class EarnPointsRequest(BaseModel):
    amount: int = Field(ge=1)
    order_id: str


class PointsEarnResponse(BaseModel):
    user_id: str
    points_earned: int
    multiplier: float
    current_points: int
    level_changed: bool = False
    new_level: str | None = None


# ============================================================
# 辅助函数
# ============================================================

def get_current_user_id(request: Request) -> str:
    """从 Authorization Header 提取用户ID"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未认证")
    token = auth[7:]
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")
    return payload["sub"]


def calculate_level(total_points: int) -> str:
    """根据累计积分计算等级"""
    for level, (lo, hi) in LEVEL_THRESHOLDS.items():
        if lo <= total_points <= hi:
            return level
    return "NORMAL"


async def write_audit_log(db, user_id: str, action: str, resource_type: str,
                          resource_id: str, before_snap: dict = None,
                          after_snap: dict = None):
    """写入审计日志"""
    import json
    log = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        before_snapshot=json.dumps(before_snap) if before_snap else None,
        after_snapshot=json.dumps(after_snap) if after_snap else None,
    )
    # 异步写入（简化：同步）
    # 生产环境应通过消息队列异步写入专用审计服务


# ============================================================
# 模拟数据存储（生产环境替换为真实数据库操作）
# ============================================================

# 内存存储（开发阶段）
_users: dict[str, dict] = {}
_members: dict[str, dict] = {}
_sms_codes: dict[str, dict] = {}  # phone -> {code, expires_at}


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _generate_sms_code() -> str:
    return f"{random.randint(100000, 999999)}"


# ============================================================
# Auth 路由
# ============================================================

@router.post("/auth/send-sms", status_code=200)
async def send_sms(req: SendSmsRequest):
    """发送短信验证码"""
    now = datetime.utcnow()
    if req.phone in _sms_codes:
        last_sent = _sms_codes[req.phone]["created_at"]
        if (now - last_sent).seconds < 60:
            raise HTTPException(status_code=429, detail="发送频率超限，请60秒后重试")

    code = _generate_sms_code()
    _sms_codes[req.phone] = {
        "code": code,
        "scene": req.scene,
        "created_at": now,
        "expires_at": int(now.timestamp()) + 60,
    }

    return {
        "message": "验证码已发送",
        "phone": req.phone[:3] + "****" + req.phone[7:],
        "expires_in": 60
    }


@router.post("/auth/register", status_code=201)
async def register(req: RegisterRequest):
    """手机号注册"""
    # 验证短信验证码
    sms = _sms_codes.get(req.phone)
    if not sms or sms["code"] != req.sms_code:
        raise HTTPException(status_code=400, detail="验证码错误")
    if datetime.utcnow().timestamp() > sms["expires_at"]:
        raise HTTPException(status_code=400, detail="验证码已过期")

    if req.phone in _users:
        raise HTTPException(status_code=409, detail="手机号已注册")

    user_id = str(uuid.uuid4())
    _users[req.phone] = {
        "id": user_id,
        "phone": req.phone,
        "nickname": req.nickname or f"用户{req.phone[-4:]}",
        "avatar": None,
        "created_at": datetime.utcnow().isoformat(),
    }

    # 创建普通用户
    _members[user_id] = {
        "user_id": user_id,
        "level": "NORMAL",
        "current_points": 0,
        "total_points_earned": 0,
        "discount_rate": 1.0,
        "points_multiplier": 1.0,
    }

    access_token, _ = create_access_token(user_id)
    refresh_token, _ = create_refresh_token(user_id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": 900,
        "token_type": "Bearer",
    }


@router.post("/auth/login")
async def login(req: LoginRequest):
    """手机号+验证码登录"""
    if req.phone not in _users:
        raise HTTPException(status_code=401, detail="手机号未注册")

    if req.sms_code:
        sms = _sms_codes.get(req.phone)
        if not sms or sms["code"] != req.sms_code:
            raise HTTPException(status_code=401, detail="验证码错误")

    user = _users[req.phone]
    access_token, _ = create_access_token(user["id"])
    refresh_token, _ = create_refresh_token(user["id"])

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": 900,
        "token_type": "Bearer",
    }


@router.post("/auth/oauth/{provider}")
async def oauth_login(provider: str, req: OAuthRequest):
    """第三方 OAuth 登录"""
    mock_openid = f"{provider}_{hashlib.md5(req.code.encode()).hexdigest()[:16]}"
    user_id = str(uuid.uuid4())

    if provider == "wechat":
        _users[f"wechat_{mock_openid}"] = {
            "id": user_id,
            "phone": None,
            "nickname": f"微信用户{mock_openid[:6]}",
            "avatar": None,
            "created_at": datetime.utcnow().isoformat(),
        }
    elif provider == "alipay":
        _users[f"alipay_{mock_openid}"] = {
            "id": user_id,
            "phone": None,
            "nickname": f"支付宝用户{mock_openid[:6]}",
            "avatar": None,
            "created_at": datetime.utcnow().isoformat(),
        }

    _members[user_id] = {
        "user_id": user_id,
        "level": "NORMAL",
        "current_points": 0,
        "total_points_earned": 0,
        "discount_rate": 1.0,
        "points_multiplier": 1.0,
    }

    access_token, _ = create_access_token(user_id)
    refresh_token, _ = create_refresh_token(user_id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": 900,
        "token_type": "Bearer",
    }


@router.post("/auth/refresh")
async def refresh_token(request: Request, req: RefreshRequest):
    try:
        import jwt as pyjwt
        from config import JWT_SECRET, JWT_ALGORITHM
        payload = pyjwt.decode(req.refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="无效的 Refresh Token")
        user_id = payload["sub"]
        access_token, _ = create_access_token(user_id)
        new_refresh, _ = create_refresh_token(user_id)
        return {
            "access_token": access_token,
            "refresh_token": new_refresh,
            "expires_in": 900,
            "token_type": "Bearer",
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")


@router.post("/auth/logout", status_code=204)
async def logout(request: Request):
    user_id = get_current_user_id(request)
    # 生产环境：将 token JTI 加入黑名单
    return None


# ============================================================
# 用户信息路由
# ============================================================

@router.get("/users/me")
async def get_current_user(request: Request):
    user_id = get_current_user_id(request)
    # 找到用户
    user = None
    for u in _users.values():
        if u["id"] == user_id:
            user = u
            break
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    member = _members.get(user_id, {})
    return {
        "id": user["id"],
        "phone": user.get("phone", "")[:3] + "****" + user.get("phone", "")[7:] if user.get("phone") else None,
        "nickname": user.get("nickname"),
        "avatar": user.get("avatar"),
        "member_level": member.get("level", "NORMAL"),
        "created_at": user.get("created_at"),
    }


@router.put("/users/me")
async def update_profile(request: Request, req: UpdateProfileRequest):
    user_id = get_current_user_id(request)
    for u in _users.values():
        if u["id"] == user_id:
            if req.nickname is not None:
                u["nickname"] = req.nickname
            if req.avatar is not None:
                u["avatar"] = req.avatar
            return {
                "id": u["id"],
                "nickname": u["nickname"],
                "avatar": u["avatar"],
                "member_level": _members.get(user_id, {}).get("level", "NORMAL"),
            }
    raise HTTPException(status_code=404, detail="用户不存在")


@router.post("/users/me/deactivate", status_code=202)
async def deactivate_account(request: Request):
    user_id = get_current_user_id(request)
    return {
        "message": f"注销请求已受理，将在72小时内完成所有数据删除",
        "estimated_completion": (datetime.utcnow().isoformat()),
    }


# ============================================================
# 会员路由
# ============================================================

@router.get("/members/me")
async def get_member_info(request: Request):
    user_id = get_current_user_id(request)
    member = _members.get(user_id)
    if not member:
        return {
            "user_id": user_id,
            "member_level": "NORMAL",
            "current_points": 0,
            "total_points_earned": 0,
            "next_level_threshold": 1000,
            "discount_rate": 1.0,
            "points_multiplier": 1.0,
            "activated_at": None,
        }

    next_threshold = {"NORMAL": 1000, "SILVER": 5000, "GOLD": 20000, "DIAMOND": None}
    return {
        "user_id": user_id,
        "member_level": member["level"],
        "current_points": member["current_points"],
        "total_points_earned": member["total_points_earned"],
        "next_level_threshold": next_threshold.get(member["level"]),
        "discount_rate": LEVEL_DISCOUNTS.get(member["level"], 1.0),
        "points_multiplier": LEVEL_MULTIPLIERS.get(member["level"], 1.0),
        "activated_at": member.get("activated_at"),
    }


@router.post("/members/me/activate", status_code=201)
async def activate_membership(request: Request):
    user_id = get_current_user_id(request)
    member = _members.get(user_id, {})
    if member.get("level") != "NORMAL":
        return {
            "user_id": user_id,
            "member_level": member["level"],
            "current_points": member.get("current_points", 0),
            "total_points_earned": member.get("total_points_earned", 0),
            "next_level_threshold": 1000,
            "discount_rate": LEVEL_DISCOUNTS.get(member["level"], 1.0),
            "points_multiplier": LEVEL_MULTIPLIERS.get(member["level"], 1.0),
            "activated_at": datetime.utcnow().isoformat(),
        }

    _members[user_id] = {
        "user_id": user_id,
        "level": "NORMAL",
        "current_points": 0,
        "total_points_earned": 0,
        "discount_rate": 1.0,
        "points_multiplier": 1.0,
        "activated_at": datetime.utcnow().isoformat(),
    }

    return {
        "user_id": user_id,
        "member_level": "NORMAL",
        "current_points": 0,
        "total_points_earned": 0,
        "next_level_threshold": 1000,
        "discount_rate": 1.0,
        "points_multiplier": 1.0,
        "activated_at": _members[user_id]["activated_at"],
    }


@router.get("/members/me/points")
async def get_points_history(request: Request):
    user_id = get_current_user_id(request)
    member = _members.get(user_id, {})
    sample_records = [
        {
            "id": str(uuid.uuid4()),
            "type": "EARN",
            "amount": 150,
            "balance_after": 150,
            "source": "ORDER_O-001",
            "description": "消费返积分",
            "created_at": datetime.utcnow().isoformat(),
        }
    ]

    return {
        "data": sample_records,
        "pagination": {"page": 1, "size": 20, "total_elements": 1, "total_pages": 1},
        "summary": {
            "current_balance": member.get("current_points", 0),
            "total_earned": member.get("total_points_earned", 0),
            "total_redeemed": 0,
            "expiring_soon": 0,
        }
    }


@router.post("/members/me/redeem")
async def redeem_points(request: Request, req: RedeemRequest):
    user_id = get_current_user_id(request)
    member = _members.get(user_id, {})
    current = member.get("current_points", 0)

    points_to_use = req.points or 100
    if current < points_to_use:
        raise HTTPException(status_code=422, detail="积分不足")

    # 积分兑换不能超过余额的80%
    if points_to_use > current * 0.8:
        raise HTTPException(status_code=422, detail="本次兑换积分不能超过当前余额的80%")

    member["current_points"] -= points_to_use
    _members[user_id] = member

    return {
        "redemption_id": str(uuid.uuid4()),
        "benefit_name": "优惠券",
        "points_used": points_to_use,
        "remaining_points": member["current_points"],
        "expires_at": (datetime.utcnow()).isoformat(),
    }


@router.get("/members/me/benefits")
async def get_available_benefits(request: Request):
    user_id = get_current_user_id(request)
    member = _members.get(user_id, {})

    benefits = [
        {"benefit_id": "B-001", "benefit_name": "9折优惠券", "benefit_type": "COUPON",
         "points_cost": 500, "description": "单次消费享受9折优惠"},
        {"benefit_id": "B-002", "benefit_name": "猫咪周边礼盒", "benefit_type": "GIFT",
         "points_cost": 1000, "description": "限量版猫咪主题周边"},
        {"benefit_id": "B-003", "benefit_name": "生日特权", "benefit_type": "BIRTHDAY",
         "points_cost": 0, "description": "生日当月免费猫咪互动一次"},
    ]
    return {"data": benefits}


# ============================================================
# 内部服务间路由
# ============================================================

@router.get("/internal/users/{user_id}")
async def get_user_by_id(user_id: str, x_internal_api_key: str = Header(...)):
    if x_internal_api_key != "internal-key-change-in-prod":
        raise HTTPException(status_code=403, detail="禁止访问")

    for u in _users.values():
        if u["id"] == user_id:
            return {"id": u["id"], "nickname": u.get("nickname"), "avatar": u.get("avatar")}
    raise HTTPException(status_code=404, detail="用户不存在")


@router.get("/internal/members/{user_id}")
async def get_member_by_user_id(user_id: str, x_internal_api_key: str = Header(...)):
    if x_internal_api_key != "internal-key-change-in-prod":
        raise HTTPException(status_code=403, detail="禁止访问")

    member = _members.get(user_id, {"level": "NORMAL", "current_points": 0})
    return {
        "user_id": user_id,
        "level": member["level"],
        "discount_rate": LEVEL_DISCOUNTS.get(member["level"], 1.0),
        "points_balance": member.get("current_points", 0),
    }


@router.post("/internal/members/{user_id}/points/earn")
async def earn_points(user_id: str, req: EarnPointsRequest, x_internal_api_key: str = Header(...)):
    if x_internal_api_key != "internal-key-change-in-prod":
        raise HTTPException(status_code=403, detail="禁止访问")

    member = _members.get(user_id, {"level": "NORMAL", "current_points": 0, "total_points_earned": 0})
    multiplier = LEVEL_MULTIPLIERS.get(member["level"], 1.0)
    points_earned = int(req.amount * multiplier / 100)  # 1 point per 1 yuan × multiplier

    old_level = member["level"]
    member["current_points"] = member.get("current_points", 0) + points_earned
    member["total_points_earned"] = member.get("total_points_earned", 0) + points_earned

    new_level = calculate_level(member["total_points_earned"])
    level_changed = False
    if new_level != old_level:
        member["level"] = new_level
        level_changed = True

    _members[user_id] = member

    return PointsEarnResponse(
        user_id=user_id,
        points_earned=points_earned,
        multiplier=multiplier,
        current_points=member["current_points"],
        level_changed=level_changed,
        new_level=new_level if level_changed else None,
    )
