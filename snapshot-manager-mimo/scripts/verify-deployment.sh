#!/bin/bash
set -e

echo "=========================================="
echo "Ceph Snapshot Manager - Docker 部署验证"
echo "=========================================="

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "错误: Docker 未安装"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "错误: Docker Compose 未安装"
    exit 1
fi

echo "✓ Docker 已安装"

# 复制环境变量文件
if [ ! -f .env ]; then
    echo "创建 .env 文件..."
    cp .env.example .env
    echo "请编辑 .env 文件设置密码"
fi

# 构建镜像
echo ""
echo "构建 Docker 镜像..."
docker-compose build

# 启动服务
echo ""
echo "启动 Docker Compose 服务..."
docker-compose up -d

# 等待服务启动
echo ""
echo "等待服务启动 (30秒)..."
sleep 30

# 检查容器状态
echo ""
echo "容器状态:"
docker-compose ps

# 检查日志
echo ""
echo "最近日志:"
docker-compose logs --tail=50

# 验证 MySQL
echo ""
echo "验证 MySQL..."
if docker-compose exec mysql mysqladmin ping -h localhost &> /dev/null; then
    echo "✓ MySQL 运行正常"
else
    echo "✗ MySQL 连接失败"
fi

# 验证 Web 应用
echo ""
echo "验证 Web 应用..."
if curl -s http://localhost:5000 > /dev/null; then
    echo "✓ Web 应用可访问"
else
    echo "✗ Web 应用不可访问"
fi

echo ""
echo "=========================================="
echo "验证完成"
echo "=========================================="
echo ""
echo "访问 http://localhost:5000"
echo "默认用户: admin"
echo "默认密码: admin123"
