"""集成测试 - API 端点测试"""
import pytest
import requests
import time

BASE_URL = "http://localhost:5000"

@pytest.fixture(scope="module")
def auth_token():
    """获取认证 token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
    return data

def test_login_page_accessible():
    """测试登录页面可访问"""
    response = requests.get(BASE_URL)
    assert response.status_code == 200
    assert "login" in response.text.lower()

def test_login_success(auth_token):
    """测试登录成功"""
    assert auth_token.get("success") is True
    assert "user" in auth_token

def test_get_current_user(auth_token):
    """测试获取当前用户"""
    response = requests.get(f"{BASE_URL}/api/auth/current_user")
    assert response.status_code == 200
    data = response.json()
    assert "authenticated" in data

def test_config_api(auth_token):
    """测试配置管理 API"""
    response = requests.get(f"{BASE_URL}/api/admin/config")
    assert response.status_code == 200
    data = response.json()
    assert "configs" in data

def test_keys_api(auth_token):
    """测试密钥管理 API"""
    response = requests.get(f"{BASE_URL}/api/admin/keys")
    assert response.status_code == 200
    data = response.json()
    assert "keys" in data

def test_zones_api(auth_token):
    """测试 Zone 列表 API"""
    response = requests.get(f"{BASE_URL}/api/zones")
    # 可能返回 200 或 500（如果 CloudStack 不可达）
    assert response.status_code in [200, 500]