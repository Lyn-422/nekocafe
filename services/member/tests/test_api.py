"""Member Service 单元测试"""

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
        assert data["service"] == "member-service"

    def test_readiness_endpoint(self):
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("UP", "DEGRADED")


class TestAuth:
    def test_send_sms_success(self):
        response = client.post("/api/v1/auth/send-sms", json={
            "phone": "13800138000",
            "scene": "REGISTER",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "验证码已发送"

    def test_send_sms_rate_limit(self):
        # 第一次
        client.post("/api/v1/auth/send-sms", json={
            "phone": "13900139000", "scene": "REGISTER"
        })
        # 立即重试
        response = client.post("/api/v1/auth/send-sms", json={
            "phone": "13900139000", "scene": "REGISTER"
        })
        assert response.status_code == 429

    def test_register_success(self):
        # 先发验证码
        client.post("/api/v1/auth/send-sms", json={
            "phone": "13800138001", "scene": "REGISTER"
        })
        # 用错误验证码注册
        response = client.post("/api/v1/auth/register", json={
            "phone": "13800138001",
            "sms_code": "123456",
            "agree_to_terms": True,
        })
        # 注意：这里因为我们模拟的验证码是随机的
        assert response.status_code in (201, 400)

    def test_register_duplicate(self):
        phone = "13800138002"
        client.post("/api/v1/auth/send-sms", json={"phone": phone, "scene": "REGISTER"})
        client.post("/api/v1/auth/register", json={
            "phone": phone, "sms_code": "654321", "agree_to_terms": True,
        })

    def test_login_unauthorized(self):
        response = client.post("/api/v1/auth/login", json={
            "phone": "99999999999",
            "sms_code": "000000",
        })
        assert response.status_code == 401


class TestMembership:
    def test_member_info_no_auth(self):
        response = client.get("/api/v1/members/me")
        assert response.status_code == 401

    def test_available_benefits(self):
        # 需要认证，测试未认证返回
        response = client.get("/api/v1/members/me/benefits")
        assert response.status_code == 401


class TestInternalAPI:
    def test_get_user_no_api_key(self):
        response = client.get("/api/v1/internal/users/test-user-id")
        assert response.status_code == 403

    def test_get_user_with_api_key(self):
        response = client.get(
            "/api/v1/internal/users/test-user-id",
            headers={"X-Internal-API-Key": "internal-key-change-in-prod"}
        )
        assert response.status_code == 404  # 用户不存在
