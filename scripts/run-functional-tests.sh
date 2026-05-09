#!/bin/bash
set -e

echo "=========================================="
echo "Ceph Snapshot Manager - 功能测试"
echo "=========================================="

BASE_URL="${BASE_URL:-http://localhost:5000}"

echo "测试目标: $BASE_URL"
echo ""

# 测试 1: 登录页面可访问
echo "[测试 1] 登录页面可访问..."
if curl -s "$BASE_URL/" | grep -q "login"; then
    echo "✓ 登录页面可访问"
else
    echo "✗ 登录页面不可访问"
    exit 1
fi

# 测试 2: 登录功能
echo ""
echo "[测试 2] 登录功能..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin123"}')

if echo "$LOGIN_RESPONSE" | grep -q "success"; then
    echo "✓ 登录成功"
else
    echo "✗ 登录失败"
    echo "响应: $LOGIN_RESPONSE"
fi

# 测试 3: 获取当前用户
echo ""
echo "[测试 3] 获取当前用户..."
RESPONSE=$(curl -s "$BASE_URL/api/auth/current_user")
if echo "$RESPONSE" | grep -q "authenticated"; then
    echo "✓ 获取当前用户成功"
else
    echo "✗ 获取当前用户失败"
fi

# 测试 4: 配置管理 API
echo ""
echo "[测试 4] 配置管理 API..."
CONFIG_RESPONSE=$(curl -s "$BASE_URL/api/admin/config")
if echo "$CONFIG_RESPONSE" | grep -q "configs"; then
    echo "✓ 配置 API 正常"
else
    echo "✗ 配置 API 异常"
fi

# 测试 5: SSH 密钥列表 API
echo ""
echo "[测试 5] SSH 密钥列表 API..."
KEYS_RESPONSE=$(curl -s "$BASE_URL/api/admin/keys")
if echo "$KEYS_RESPONSE" | grep -q "keys"; then
    echo "✓ 密钥列表 API 正常"
else
    echo "✗ 密钥列表 API 异常"
fi

echo ""
echo "=========================================="
echo "功能测试完成"
echo "=========================================="