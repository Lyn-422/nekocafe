"""Reservation Service 单元测试"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from main import app

client = TestClient(app)


class TestHealth:
    def test_health_endpoint(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "UP"
        assert data["service"] == "reservation-service"


class TestAvailability:
    def test_get_availability(self):
        response = client.get(
            "/api/v1/stores/ST-BJ-001/availability",
            params={"date": "2026-05-20", "guest_count": 2}
        )
        assert response.status_code == 401  # 需要认证

    def test_store_not_found(self):
        response = client.get(
            "/api/v1/stores/INVALID/availability",
            params={"date": "2026-05-20"},
            headers={"Authorization": "Bearer test"}
        )
        assert response.status_code == 404


class TestReservation:
    def test_create_reservation_no_auth(self):
        response = client.post("/api/v1/reservations", json={
            "store_id": "ST-BJ-001",
            "table_id": "TBL-001",
            "date": "2026-05-20",
            "start_time": "18:00",
            "guest_count": 4,
        })
        assert response.status_code == 401

    def test_create_reservation_with_auth(self):
        response = client.post(
            "/api/v1/reservations",
            json={
                "store_id": "ST-BJ-001",
                "table_id": "TBL-001",
                "date": "2026-05-20",
                "start_time": "18:00",
                "guest_count": 4,
            },
            headers={"Authorization": "Bearer test-token-user-1"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "PENDING"
        assert data["store_id"] == "ST-BJ-001"
        assert "id" in data

    def test_create_reservation_slot_conflict(self):
        headers = {"Authorization": "Bearer test-token-user-2"}
        # 第一次
        resp1 = client.post("/api/v1/reservations", json={
            "store_id": "ST-BJ-001",
            "table_id": "TBL-001",
            "date": "2026-05-21",
            "start_time": "19:00",
            "guest_count": 2,
        }, headers=headers)
        assert resp1.status_code == 201

        # 第二次-相同桌位
        resp2 = client.post("/api/v1/reservations", json={
            "store_id": "ST-BJ-001",
            "table_id": "TBL-001",
            "date": "2026-05-21",
            "start_time": "19:00",
            "guest_count": 2,
        }, headers=headers)
        assert resp2.status_code == 409

    def test_get_reservation(self):
        # 先创建
        create_resp = client.post(
            "/api/v1/reservations",
            json={
                "store_id": "ST-BJ-001",
                "table_id": "TBL-002",
                "date": "2026-05-22",
                "start_time": "14:00",
                "guest_count": 3,
            },
            headers={"Authorization": "Bearer test-token-user-3"}
        )
        reservation_id = create_resp.json()["id"]

        # 获取详情
        get_resp = client.get(
            f"/api/v1/reservations/{reservation_id}",
            headers={"Authorization": "Bearer test-token-user-3"}
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == reservation_id

    def test_list_reservations(self):
        response = client.get(
            "/api/v1/reservations",
            headers={"Authorization": "Bearer test-token-user-3"}
        )
        assert response.status_code == 200
        assert "data" in response.json()
        assert "pagination" in response.json()
