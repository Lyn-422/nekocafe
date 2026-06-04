"""Reservation Service API 路由"""

import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, Header
from pydantic import BaseModel, Field
from models import MOCK_TABLES, TABLE_TYPE_CAPACITIES
from config import (
    MAX_ACTIVE_RESERVATIONS, FREE_CANCEL_HOURS,
    NO_SHOW_MINUTES, CHECK_IN_EARLY_MINUTES
)

router = APIRouter(prefix="/api/v1")

# 内存存储
_reservations: dict[str, dict] = {}
_table_slots: dict[str, dict] = {}  # key: "storeId_date_startTime_tableId"


# ============================================================
# Pydantic Schemas
# ============================================================

class CreateReservationRequest(BaseModel):
    store_id: str = Field(pattern=r'^ST-[A-Z]{2}-\d{3}$')
    table_id: str
    date: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    start_time: str = Field(pattern=r'^\d{2}:\d{2}$')
    guest_count: int = Field(ge=1, le=20)
    has_cat: bool = False
    cat_breed: str | None = Field(default=None, max_length=50)


class ModifyReservationRequest(BaseModel):
    date: str | None = Field(default=None, pattern=r'^\d{4}-\d{2}-\d{2}$')
    start_time: str | None = Field(default=None, pattern=r'^\d{2}:\d{2}$')
    guest_count: int | None = Field(default=None, ge=1, le=20)
    table_id: str | None = None


class CancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=200)


# ============================================================
# 辅助函数
# ============================================================

def get_current_user_id(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未认证")
    # 简化：从 Authorization header 提取
    # 生产环境需解析 JWT
    return auth


def _count_active_reservations(user_id: str) -> int:
    count = 0
    for r in _reservations.values():
        if r["user_id"] == user_id and r["status"] in ("PENDING", "CONFIRMED"):
            count += 1
    return count


def _check_table_conflict(store_id: str, table_id: str, date: str, start_time: str) -> bool:
    """检查桌位是否冲突（简化：同一桌位同一日期同时段仅一个预约）"""
    key = f"{store_id}_{date}_{start_time}_{table_id}"
    if key in _table_slots:
        existing = _table_slots[key]
        if existing["status"] in ("PENDING", "CONFIRMED"):
            return True
    return False


def _calculate_end_time(start_time: str) -> str:
    """计算用餐结束时间（起2小时）"""
    h, m = map(int, start_time.split(":"))
    total_minutes = h * 60 + m + 120  # 2 hours
    end_h, end_m = divmod(total_minutes, 60)
    return f"{end_h % 24:02d}:{end_m:02d}"


# ============================================================
# 桌位可用性查询
# ============================================================

@router.get("/stores/{store_id}/availability")
async def get_store_availability(
    request: Request,
    store_id: str,
    date: str,
    guest_count: int = 2,
    table_type: str = None,
    has_cat: bool = False,
):
    """查询门店桌位可用性"""
    if not store_id.startswith("ST-"):
        raise HTTPException(status_code=404, detail="门店不存在")

    time_slots = []
    for hour in [10, 12, 14, 16, 18, 20]:
        start = f"{hour:02d}:00"
        end = f"{hour + 2:02d}:00"
        available_tables = []

        for t in MOCK_TABLES:
            if table_type and t["table_type"] != table_type:
                continue
            if has_cat and not t.get("cat_friendly"):
                continue
            if guest_count > t["max_capacity"]:
                continue

            key = f"{store_id}_{date}_{start}_{t['table_id']}"
            if key not in _table_slots:
                available_tables.append({
                    "table_id": t["table_id"],
                    "table_number": t["table_number"],
                    "table_type": t["table_type"],
                    "max_capacity": t["max_capacity"],
                    "cat_friendly": t.get("cat_friendly", False),
                    "cat_personalities": t.get("cat_personalities", []),
                    "price_estimate": {"amount": 5000, "currency": "CNY"},
                })

        if available_tables:
            time_slots.append({
                "start_time": start,
                "end_time": end,
                "available_tables": available_tables,
            })

    return {
        "store_id": store_id,
        "date": date,
        "time_slots": time_slots,
        "generated_at": datetime.utcnow().isoformat(),
    }


# ============================================================
# 预约 CRUD
# ============================================================

@router.get("/reservations")
async def list_reservations(request: Request, status: str = None, page: int = 1, size: int = 20):
    user_id = get_current_user_id(request)
    result = [r for r in _reservations.values() if r["user_id"] == user_id]
    if status:
        result = [r for r in result if r["status"] == status]

    start = (page - 1) * size
    page_data = result[start:start + size]

    return {
        "data": page_data,
        "pagination": {
            "page": page, "size": size,
            "total_elements": len(result),
            "total_pages": max(1, (len(result) + size - 1) // size),
        }
    }


@router.post("/reservations", status_code=201)
async def create_reservation(request: Request, req: CreateReservationRequest):
    user_id = get_current_user_id(request)

    # 1. 活跃预约数校验
    active_count = _count_active_reservations(user_id)
    if active_count >= MAX_ACTIVE_RESERVATIONS:
        raise HTTPException(status_code=422, detail="您当前已有3个活跃预约，无法创建新预约")

    # 2. 桌位冲突校验（模拟 Redis 分布式锁）
    if _check_table_conflict(req.store_id, req.table_id, req.date, req.start_time):
        raise HTTPException(status_code=409, detail="该桌位在指定时段已被预约")

    reservation_id = str(uuid.uuid4())
    end_time = _calculate_end_time(req.start_time)
    now = datetime.utcnow().isoformat()

    reservation = {
        "id": reservation_id,
        "user_id": user_id,
        "store_id": req.store_id,
        "store_name": f"猫咪咖啡馆({req.store_id})",
        "table_id": req.table_id,
        "table_type": "NORMAL",
        "date": req.date,
        "start_time": req.start_time,
        "end_time": end_time,
        "guest_count": req.guest_count,
        "has_cat": req.has_cat,
        "cat_breed": req.cat_breed,
        "status": "PENDING",
        "deposit": {"amount": 5000, "currency": "CNY"},
        "penalty": {"amount": 0, "currency": "CNY"},
        "created_at": now,
        "updated_at": now,
    }

    _reservations[reservation_id] = reservation
    key = f"{req.store_id}_{req.date}_{req.start_time}_{req.table_id}"
    _table_slots[key] = {"reservation_id": reservation_id, "status": "PENDING"}

    return reservation


@router.get("/reservations/{reservation_id}")
async def get_reservation(request: Request, reservation_id: str):
    user_id = get_current_user_id(request)
    r = _reservations.get(reservation_id)
    if not r:
        raise HTTPException(status_code=404, detail="预约不存在")
    return r


@router.put("/reservations/{reservation_id}")
async def modify_reservation(request: Request, reservation_id: str, req: ModifyReservationRequest):
    user_id = get_current_user_id(request)
    r = _reservations.get(reservation_id)
    if not r:
        raise HTTPException(status_code=404, detail="预约不存在")
    if r["status"] not in ("PENDING", "CONFIRMED"):
        raise HTTPException(status_code=422, detail="预约状态不允许修改")

    if req.date:
        r["date"] = req.date
    if req.start_time:
        r["start_time"] = req.start_time
        r["end_time"] = _calculate_end_time(req.start_time)
    if req.guest_count:
        r["guest_count"] = req.guest_count
    if req.table_id:
        r["table_id"] = req.table_id

    r["updated_at"] = datetime.utcnow().isoformat()
    return r


@router.post("/reservations/{reservation_id}/cancel")
async def cancel_reservation(request: Request, reservation_id: str, req: CancelRequest = None):
    user_id = get_current_user_id(request)
    r = _reservations.get(reservation_id)
    if not r:
        raise HTTPException(status_code=404, detail="预约不存在")
    if r["status"] not in ("PENDING", "CONFIRMED"):
        raise HTTPException(status_code=422, detail="预约状态不允许取消")

    # 计算是否超免费取消时限
    start_datetime = datetime.fromisoformat(f"{r['date']}T{r['start_time']}:00")
    hours_until_start = (start_datetime - datetime.utcnow()).total_seconds() / 3600

    if hours_until_start < 0:
        raise HTTPException(status_code=422, detail="已开始的预约不可取消")

    if hours_until_start >= FREE_CANCEL_HOURS:
        refund_amount = r["deposit"]["amount"]  # 全额退
        penalty = 0
    else:
        penalty = int(r["deposit"]["amount"] * 0.2)
        refund_amount = r["deposit"]["amount"] - penalty

    r["status"] = "CANCELLED"
    r["penalty"] = {"amount": penalty, "currency": "CNY"}
    r["updated_at"] = datetime.utcnow().isoformat()

    return {
        "reservation_id": reservation_id,
        "status": "CANCELLED",
        "deposit_refund": {"amount": refund_amount, "currency": "CNY"},
        "penalty_amount": {"amount": penalty, "currency": "CNY"},
        "refund_id": str(uuid.uuid4()),
    }


@router.post("/reservations/{reservation_id}/check-in")
async def check_in_reservation(request: Request, reservation_id: str):
    user_id = get_current_user_id(request)
    r = _reservations.get(reservation_id)
    if not r:
        raise HTTPException(status_code=404, detail="预约不存在")
    if r["status"] != "CONFIRMED":
        raise HTTPException(status_code=422, detail="仅已确认的预约可签到")

    r["status"] = "COMPLETED"
    r["updated_at"] = datetime.utcnow().isoformat()
    return r


@router.post("/reservations/{reservation_id}/complete")
async def complete_reservation(request: Request, reservation_id: str):
    user_id = get_current_user_id(request)
    r = _reservations.get(reservation_id)
    if not r:
        raise HTTPException(status_code=404, detail="预约不存在")

    r["status"] = "COMPLETED"
    r["updated_at"] = datetime.utcnow().isoformat()
    return r


# ============================================================
# 店员端操作
# ============================================================

@router.get("/stores/{store_id}/reservations/today")
async def get_today_reservations(request: Request, store_id: str, status: str = None):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    result = [
        r for r in _reservations.values()
        if r["store_id"] == store_id and r["date"] == today
    ]
    if status:
        result = [r for r in result if r["status"] == status]

    return {
        "data": result,
        "stats": {
            "total_reservations": len(result),
            "confirmed": sum(1 for r in result if r["status"] == "CONFIRMED"),
            "checked_in": sum(1 for r in result if r["status"] == "COMPLETED"),
            "completed": sum(1 for r in result if r["status"] == "COMPLETED"),
            "cancelled": sum(1 for r in result if r["status"] == "CANCELLED"),
            "no_show": sum(1 for r in result if r["status"] == "NO_SHOW"),
            "utilization_rate": 0.75,
        }
    }
