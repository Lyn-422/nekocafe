"""Reservation Service 数据模型"""

from datetime import datetime

try:
    from sqlalchemy import (
        Column, String, Integer, DateTime, Enum, Float
    )
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()

    class Reservation(Base):
        __tablename__ = "reservations"
        id = Column(String(36), primary_key=True)
        user_id = Column(String(36), nullable=False, index=True)
        store_id = Column(String(20), nullable=False, index=True)
        store_name = Column(String(100))
        table_id = Column(String(20), nullable=False)
        table_type = Column(Enum("NORMAL", "CAT_INTERACTION", "VIP", "WINDOW_VIEW"))
        date = Column(String(10), nullable=False)
        start_time = Column(String(5), nullable=False)
        end_time = Column(String(5))
        guest_count = Column(Integer, nullable=False)
        status = Column(
            Enum("PENDING", "CONFIRMED", "CANCELLED", "COMPLETED", "NO_SHOW"),
            default="PENDING", index=True
        )
        has_cat = Column(Integer, default=0)
        cat_breed = Column(String(50))
        deposit_amount = Column(Integer, default=0)
        penalty_amount = Column(Integer, default=0)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
except ImportError:
    pass  # SQLAlchemy not installed, skip ORM models


# 桌位类型映射
TABLE_TYPE_CAPACITIES = {
    "NORMAL": (2, 6),
    "CAT_INTERACTION": (2, 4),
    "VIP": (2, 8),
    "WINDOW_VIEW": (2, 6),
}

# 模拟桌位数据
MOCK_TABLES = [
    {"table_id": "TBL-001", "table_number": "A-01", "table_type": "NORMAL",
     "max_capacity": 4, "cat_friendly": False},
    {"table_id": "TBL-002", "table_number": "A-02", "table_type": "NORMAL",
     "max_capacity": 6, "cat_friendly": False},
    {"table_id": "TBL-010", "table_number": "C-01", "table_type": "CAT_INTERACTION",
     "max_capacity": 4, "cat_friendly": True,
     "cat_personalities": ["ACTIVE", "FRIENDLY"]},
    {"table_id": "TBL-020", "table_number": "V-01", "table_type": "VIP",
     "max_capacity": 8, "cat_friendly": True},
    {"table_id": "TBL-030", "table_number": "W-01", "table_type": "WINDOW_VIEW",
     "max_capacity": 4, "cat_friendly": False},
]
