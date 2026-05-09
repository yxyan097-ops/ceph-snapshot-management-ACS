# Ceph Snapshot Manager - 企业级架构迁移实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Ceph 快照管理系统从 SQLite + SSH 密码架构迁移至 MySQL + Docker + SSH Key 管理的企业级架构

**Architecture:** Docker Compose 部署三容器架构（MySQL + SSH Agent + Web-App），配置和密钥存储于 MySQL，SSH Agent 通过 UNIX Socket 与 Web-App 通信

**Tech Stack:** Docker, Docker Compose, MySQL 8.0, Paramiko, Flask, apache-libcloud

---

## 文件结构

```
docker-enterprise/
├── docker-compose.yml           # Docker Compose 配置
├── Dockerfile                  # Web 应用镜像
├── Dockerfile.ssh-agent        # SSH Agent 镜像
├── .env.example                # 环境变量模板
├── plans/                      # 本实施计划
│
├── scripts/
│   ├── init-mysql.sql           # MySQL 初始化 Schema + 种子数据
│   └── ssh-agent-entrypoint.sh  # SSH Agent 容器启动脚本
│
├── ceph_snapshot_manager/
│   ├── config/
│   │   └── settings.py          # 重构：从 MySQL 读取配置
│   ├── models/
│   │   ├── zone_key.py          # 新增：Zone SSH 密钥模型
│   │   └── app_config.py        # 新增：应用配置模型
│   ├── services/
│   │   ├── ssh_agent_service.py # 新增：SSH Agent 通信模块
│   │   └── ceph_service.py      # 重构：使用 SSH Agent
│   └── routes/
│       └── admin/               # 新增：管理路由
│           ├── keys.py          # 密钥管理 API
│           └── config.py        # 配置管理 API
│
├── templates/admin/             # 新增：管理页面
│   ├── keys.html
│   └── config.html
│
├── tests/
│   ├── unit/
│   │   ├── test_zone_key_model.py
│   │   ├── test_app_config_model.py
│   │   └── test_ssh_agent_service.py
│   └── migration/
│       └── sqlite_to_mysql.py   # 数据迁移脚本
```

---

## Phase 1: 基础设施

### Task 1: 创建 .env.example 环境变量模板

**Files:**
- Create: `docker-enterprise/.env.example`

- [ ] **Step 1: 创建文件**

```
# MySQL Configuration
MYSQL_ROOT_PASSWORD=your_secure_password_here

# CloudStack Configuration (初始值，占位符)
CLOUDSTACK_URL=http://172.16.100.9:8080/client/api
CLOUDSTACK_API_KEY=your_api_key
CLOUDSTACK_SECRET_KEY=your_secret_key

# Application Configuration
APP_SECRET_KEY=change-me-in-production
DEFAULT_KEEP=3
```

- [ ] **Step 2: 提交**

```bash
git add docker-enterprise/.env.example
git commit -m "docs: add .env.example template"
```

---

### Task 2: 创建 MySQL 初始化脚本

**Files:**
- Create: `docker-enterprise/scripts/init-mysql.sql`

- [ ] **Step 1: 编写 Schema 初始化脚本**

```sql
-- =====================================================
-- Ceph Snapshot Manager - MySQL Schema
-- =====================================================

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'operator', 'viewer') DEFAULT 'viewer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Zone SSH 密钥表
CREATE TABLE IF NOT EXISTS zone_keys (
    id INT AUTO_INCREMENT PRIMARY KEY,
    zone_id VARCHAR(255) NOT NULL,
    zone_name VARCHAR(255) NOT NULL,
    ssh_user VARCHAR(255) NOT NULL DEFAULT 'root',
    private_key TEXT NOT NULL,
    public_key TEXT,
    fingerprint VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_zone_id (zone_id)
);

-- 应用配置表
CREATE TABLE IF NOT EXISTS app_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(255) UNIQUE NOT NULL,
    config_value TEXT,
    description VARCHAR(512),
    is_secret BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 审计日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    username VARCHAR(255) NOT NULL,
    action VARCHAR(50) NOT NULL,
    zone_id VARCHAR(255),
    zone_name VARCHAR(255),
    volume_id VARCHAR(255),
    volume_name VARCHAR(255),
    snapshot_name VARCHAR(255),
    ceph_pool VARCHAR(255),
    full_snapshot_name VARCHAR(512),
    keep_count INT,
    dry_run TINYINT(1),
    result VARCHAR(20),
    message TEXT,
    commands TEXT,
    client_ip VARCHAR(45)
);

-- 索引
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_username ON audit_logs(username);
CREATE INDEX idx_zone_keys_zone_id ON zone_keys(zone_id);

-- =====================================================
-- 初始配置数据
-- =====================================================
INSERT INTO app_config (config_key, config_value, description, is_secret) VALUES
('cloudstack_url', 'http://172.16.100.9:8080/client/api', 'CloudStack API URL', FALSE),
('cloudstack_api_key', '', 'CloudStack API Key', TRUE),
('cloudstack_secret_key', '', 'CloudStack Secret Key', TRUE),
('snap_trim_script', '/scripts/snap-trim.sh', 'Snapshot trim script path', FALSE),
('default_keep', '3', 'Default snapshot retention count', FALSE),
('app_secret_key', 'change-me-in-production', 'Flask secret key', TRUE);

-- 默认管理员用户 (密码: admin123)
INSERT INTO users (username, password_hash, role) VALUES
('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyDAiWWwFgk8ES', 'admin');
```

- [ ] **Step 2: 提交**

```bash
git add docker-enterprise/scripts/init-mysql.sql
git commit -m "feat: add MySQL initialization script with schema"
```

---

### Task 3: 创建 SSH Agent 入口脚本

**Files:**
- Create: `docker-enterprise/scripts/ssh-agent-entrypoint.sh`

- [ ] **Step 1: 编写启动脚本**

```bash
#!/bin/bash
set -e

KEYS_DIR="/app/keys"
SOCKET_PATH="/tmp/ceph-ssh-agent.sock"

echo "[SSH Agent] Starting..."

# 创建密钥目录
mkdir -p $KEYS_DIR

# 启动 SSH Agent
echo "[SSH Agent] Initializing SSH agent..."
eval $(ssh-agent -s)
echo "[SSH Agent] Agent PID: $SSH_AGENT_PID"

# 将 Agent PID 写入文件供监控使用
echo $SSH_AGENT_PID > /tmp/ssh-agent.pid

# 从持久化目录加载已有密钥
echo "[SSH Agent] Loading keys from $KEYS_DIR..."
for keyfile in $KEYS_DIR/*/id_rsa; do
    if [ -f "$keyfile" ]; then
        zone=$(dirname "$keyfile" | xargs basename)
        echo "[SSH Agent] Adding key for zone: $zone"
        ssh-add "$keyfile" 2>/dev/null || echo "[SSH Agent] Warning: Failed to add $keyfile"
    fi
done

# 列出已加载的密钥
echo "[SSH Agent] Currently loaded keys:"
ssh-add -l || echo "[SSH Agent] No keys loaded"

echo "[SSH Agent] SSH Agent ready on socket: $SOCKET_PATH"

# 保持容器运行
echo "[SSH Agent] Holding container open..."
tail -f /dev/null
```

- [ ] **Step 2: 提交**

```bash
git add docker-enterprise/scripts/ssh-agent-entrypoint.sh
git commit -m "feat: add SSH agent entrypoint script"
```

---

### Task 4: 创建 Dockerfile.ssh-agent

**Files:**
- Create: `docker-enterprise/Dockerfile.ssh-agent`

- [ ] **Step 1: 编写 Dockerfile**

```dockerfile
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    openssh-client \
    netcat \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash agent && \
    mkdir -p /app/keys && \
    chown agent:agent /app/keys

COPY scripts/ssh-agent-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER agent
WORKDIR /app

ENTRYPOINT ["/entrypoint.sh"]
```

- [ ] **Step 2: 提交**

```bash
git add docker-enterprise/Dockerfile.ssh-agent
git commit -m "feat: add SSH agent Dockerfile"
```

---

### Task 5: 创建 Web 应用 Dockerfile

**Files:**
- Create: `docker-enterprise/Dockerfile`

- [ ] **Step 1: 编写 Dockerfile**

```dockerfile
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安装依赖
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# 复制应用代码
COPY ceph_snapshot_manager/ ./ceph_snapshot_manager/
COPY templates/ ./templates/
COPY static/ ./static/
COPY app.py .

# 复制快照清理脚本
COPY scripts/snap-trim.sh /scripts/snap-trim.sh
RUN chmod +x /scripts/snap-trim.sh

EXPOSE 5000

CMD ["python", "app.py"]
```

- [ ] **Step 2: 创建 requirements-docker.txt**

```
Flask>=2.3.0
Flask-Login>=0.6.0
paramiko>=3.0.0
bcrypt>=4.1.0
apache-libcloud>=3.8.0
PyMySQL>=1.1.0
SQLAlchemy>=2.0.0
```

- [ ] **Step 3: 提交**

```bash
git add docker-enterprise/Dockerfile docker-enterprise/requirements-docker.txt
git commit -m "feat: add web app Dockerfile"
```

---

### Task 6: 创建 docker-compose.yml

**Files:**
- Create: `docker-enterprise/docker-compose.yml`

- [ ] **Step 1: 编写 docker-compose.yml**

```yaml
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    container_name: ceph-snapshot-mysql
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ceph_snapshot
    volumes:
      - mysql_data:/app/mysql/data
      - ./scripts/init-mysql.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - ceph-snapshot-net
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

  ssh-key-agent:
    build:
      context: .
      dockerfile: Dockerfile.ssh-agent
    container_name: ceph-snapshot-ssh-agent
    restart: unless-stopped
    volumes:
      - ssh_keys:/app/keys
    networks:
      - ceph-snapshot-net
    depends_on:
      mysql:
        condition: service_healthy

  web-app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ceph-snapshot-web
    restart: unless-stopped
    environment:
      DATABASE_URL: mysql+pymysql://root:${MYSQL_ROOT_PASSWORD}@mysql:3306/ceph_snapshot
      SSH_AGENT_SOCKET: /tmp/ceph-ssh-agent.sock
    volumes:
      - app_data:/app/data
    networks:
      - ceph-snapshot-net
    depends_on:
      mysql:
        condition: service_healthy
      ssh-key-agent:
        condition: service_started
    ports:
      - "5000:5000"

networks:
  ceph-snapshot-net:
    driver: bridge

volumes:
  mysql_data:
  ssh_keys:
  app_data:
```

- [ ] **Step 2: 提交**

```bash
git add docker-enterprise/docker-compose.yml
git commit -m "feat: add docker-compose.yml"
```

---

## Phase 2: 数据库模型

### Task 7: 创建 app_config 模型

**Files:**
- Create: `docker-enterprise/ceph_snapshot_manager/models/app_config.py`
- Test: `docker-enterprise/tests/unit/test_app_config_model.py`

- [ ] **Step 1: 编写测试**

```python
import pytest
from ceph_snapshot_manager.models.app_config import AppConfigModel

def test_get_config_returns_value():
    """测试获取配置值"""
    model = AppConfigModel()
    value = model.get('cloudstack_url')
    assert value is not None

def test_get_config_returns_none_for_missing():
    """测试获取不存在的配置返回 None"""
    model = AppConfigModel()
    value = model.get('nonexistent_key')
    assert value is None

def test_set_config_updates_value():
    """测试设置配置值"""
    model = AppConfigModel()
    model.set('test_key', 'test_value', description='Test', is_secret=False)
    value = model.get('test_key')
    assert value == 'test_value'

def test_get_secret_masks_value():
    """测试敏感配置返回 None（不返回实际值）"""
    model = AppConfigModel()
    model.set('secret_key', 'secret_value', is_secret=True)
    # 敏感配置需要特殊接口获取
    value = model.get_secret('secret_key')
    assert value == 'secret_value'
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/unit/test_app_config_model.py -v`
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: 实现模型**

```python
"""应用配置模型 - 从 MySQL 读取配置"""
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool

class AppConfigModel:
    """应用配置管理"""

    def __init__(self, database_url: str = None):
        import os
        self.database_url = database_url or os.environ.get(
            'DATABASE_URL',
            'mysql+pymysql://root:password@localhost:3306/ceph_snapshot'
        )
        self._engine = None

    @property
    def engine(self):
        if self._engine is None:
            self._engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=5,
                pool_recycle=3600
            )
        return self._engine

    def get(self, key: str) -> Optional[str]:
        """获取配置值（敏感配置返回 None）"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT config_value, is_secret FROM app_config WHERE config_key = :key"),
                {"key": key}
            )
            row = result.fetchone()
            if not row:
                return None
            if row[1]:  # is_secret
                return None
            return row[0]

    def get_secret(self, key: str) -> Optional[str]:
        """获取敏感配置值"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT config_value FROM app_config WHERE config_key = :key AND is_secret = TRUE"),
                {"key": key}
            )
            row = result.fetchone()
            return row[0] if row else None

    def set(self, key: str, value: str, description: str = None, is_secret: bool = False):
        """设置配置值"""
        with self.engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO app_config (config_key, config_value, description, is_secret)
                    VALUES (:key, :value, :desc, :secret)
                    ON DUPLICATE KEY UPDATE
                        config_value = :value,
                        description = COALESCE(:desc, description),
                        is_secret = :secret
                """),
                {"key": key, "value": value, "desc": description, "secret": is_secret}
            )
            conn.commit()

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """获取所有配置"""
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM app_config"))
            configs = {}
            for row in result:
                configs[row[1]] = {
                    'value': row[2] if not row[3] else None,
                    'description': row[4],
                    'is_secret': row[3]
                }
            return configs
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/unit/test_app_config_model.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add ceph_snapshot_manager/models/app_config.py tests/unit/test_app_config_model.py
git commit -m "feat: add AppConfig model for database-backed config"
```

---

### Task 8: 创建 zone_key 模型

**Files:**
- Create: `docker-enterprise/ceph_snapshot_manager/models/zone_key.py`
- Test: `docker-enterprise/tests/unit/test_zone_key_model.py`

- [ ] **Step 1: 编写测试**

```python
import pytest
from ceph_snapshot_manager.models.zone_key import ZoneKeyModel

def test_add_key_for_zone():
    """测试为 Zone 添加密钥"""
    model = ZoneKeyModel()
    model.add_key(
        zone_id='zone-123',
        zone_name='zone1',
        ssh_user='root',
        private_key='-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----',
        public_key='ssh-rsa AAAAB3...',
        fingerprint='xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx'
    )

def test_get_key_by_zone():
    """测试获取 Zone 的密钥"""
    model = ZoneKeyModel()
    key = model.get_by_zone_id('zone-123')
    assert key is not None
    assert key['zone_id'] == 'zone-123'

def test_get_nonexistent_zone_returns_none():
    """测试获取不存在的 Zone 返回 None"""
    model = ZoneKeyModel()
    key = model.get_by_zone_id('nonexistent')
    assert key is None

def test_delete_key():
    """测试删除 Zone 密钥"""
    model = ZoneKeyModel()
    model.delete_by_zone_id('zone-123')
    key = model.get_by_zone_id('zone-123')
    assert key is None
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/unit/test_zone_key_model.py -v`
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: 实现模型**

```python
"""Zone SSH 密钥模型"""
from typing import Optional, Dict, List
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool

class ZoneKeyModel:
    """Zone SSH 密钥管理"""

    def __init__(self, database_url: str = None):
        import os
        self.database_url = database_url or os.environ.get(
            'DATABASE_URL',
            'mysql+pymysql://root:password@localhost:3306/ceph_snapshot'
        )
        self._engine = None

    @property
    def engine(self):
        if self._engine is None:
            self._engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=5,
                pool_recycle=3600
            )
        return self._engine

    def add_key(self, zone_id: str, zone_name: str, ssh_user: str,
                private_key: str, public_key: str, fingerprint: str):
        """添加 Zone SSH 密钥"""
        with self.engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO zone_keys
                    (zone_id, zone_name, ssh_user, private_key, public_key, fingerprint)
                    VALUES (:zone_id, :zone_name, :ssh_user, :private_key, :public_key, :fingerprint)
                    ON DUPLICATE KEY UPDATE
                        zone_name = :zone_name,
                        ssh_user = :ssh_user,
                        private_key = :private_key,
                        public_key = :public_key,
                        fingerprint = :fingerprint
                """),
                {
                    "zone_id": zone_id,
                    "zone_name": zone_name,
                    "ssh_user": ssh_user,
                    "private_key": private_key,
                    "public_key": public_key,
                    "fingerprint": fingerprint
                }
            )
            conn.commit()

    def get_by_zone_id(self, zone_id: str) -> Optional[Dict]:
        """根据 Zone ID 获取密钥"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM zone_keys WHERE zone_id = :zone_id"),
                {"zone_id": zone_id}
            )
            row = result.fetchone()
            if not row:
                return None
            return {
                'id': row[0],
                'zone_id': row[1],
                'zone_name': row[2],
                'ssh_user': row[3],
                'private_key': row[4],
                'public_key': row[5],
                'fingerprint': row[6],
                'created_at': row[7],
                'updated_at': row[8]
            }

    def get_all(self) -> List[Dict]:
        """获取所有 Zone 密钥"""
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM zone_keys"))
            keys = []
            for row in result:
                keys.append({
                    'id': row[0],
                    'zone_id': row[1],
                    'zone_name': row[2],
                    'ssh_user': row[3],
                    'public_key': row[5],
                    'fingerprint': row[6],
                    'created_at': row[7],
                    'updated_at': row[8]
                })
            return keys

    def delete_by_zone_id(self, zone_id: str):
        """删除 Zone 密钥"""
        with self.engine.connect() as conn:
            conn.execute(
                text("DELETE FROM zone_keys WHERE zone_id = :zone_id"),
                {"zone_id": zone_id}
            )
            conn.commit()
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/unit/test_zone_key_model.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add ceph_snapshot_manager/models/zone_key.py tests/unit/test_zone_key_model.py
git commit -m "feat: add ZoneKey model for SSH key management"
```

---

### Task 9: 重构 audit 模型支持 MySQL

**Files:**
- Modify: `docker-enterprise/ceph_snapshot_manager/models/audit.py`
- Test: `docker-enterprise/tests/unit/test_audit_model.py`

- [ ] **Step 1: 查看现有实现并重构**

现有 audit.py 使用 SQLite，需要重构为 MySQL。

主要变更：
1. 构造函数接受 database_url 参数
2. 使用 SQLAlchemy 而非直接 sqlite3
3. 表结构不变（TINYINT(1) 替代 BOOLEAN）

- [ ] **Step 2: 提交**

```bash
git add ceph_snapshot_manager/models/audit.py
git commit -m "refactor: adapt AuditLogDB for MySQL"
```

---

## Phase 3: SSH Agent 服务

### Task 10: 创建 SSH Agent 通信服务

**Files:**
- Create: `docker-enterprise/ceph_snapshot_manager/services/ssh_agent_service.py`
- Test: `docker-enterprise/tests/unit/test_ssh_agent_service.py`

- [ ] **Step 1: 编写测试**

```python
import pytest
import os
from unittest.mock import Mock, patch

def test_add_key_to_agent():
    """测试添加密钥到 Agent"""
    with patch('socket.socket') as mock_socket:
        mock_conn = Mock()
        mock_socket.return_value.connect.return_value = None
        mock_conn.recv.return_value = b'{"success": true}'
        mock_conn.sendall.return_value = None

        service = SSHAgentService(socket_path='/tmp/test.sock')
        result = service.add_key('zone-1', 'private_key_content', 'public_key_content')
        assert result is True

def test_list_keys():
    """测试列出已加载密钥"""
    service = SSHAgentService(socket_path='/tmp/test.sock')
    with patch('socket.socket') as mock_socket:
        mock_conn = Mock()
        mock_socket.return_value.connect.return_value = None
        mock_conn.recv.return_value = b'{"success": true, "keys": [{"zone_id": "zone-1"}]}'

        result = service.list_keys()
        assert len(result) == 1
        assert result[0]['zone_id'] == 'zone-1'
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/unit/test_ssh_agent_service.py -v`
Expected: FAIL

- [ ] **Step 3: 实现服务**

```python
"""SSH Agent 通信服务 - 通过 UNIX Socket 与 ssh-key-agent 容器通信"""
import socket
import json
from typing import List, Dict, Optional

class SSHAgentService:
    """SSH Agent IPC 通信服务"""

    def __init__(self, socket_path: str = '/tmp/ceph-ssh-agent.sock'):
        self.socket_path = socket_path

    def _send_request(self, cmd: str, zone_id: str = None, payload: dict = None) -> dict:
        """发送请求到 SSH Agent"""
        request = {
            'cmd': cmd,
            'zone_id': zone_id,
            'payload': payload or {}
        }

        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.connect(self.socket_path)
                s.sendall(json.dumps(request).encode())
                s.settimeout(30)
                response = s.recv(4096)
                return json.loads(response.decode())
        except socket.timeout:
            return {'success': False, 'error': 'SSH Agent timeout'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def add_key(self, zone_id: str, private_key: str, public_key: str) -> bool:
        """添加密钥到 Agent"""
        response = self._send_request(
            'add_key',
            zone_id=zone_id,
            payload={'private_key': private_key, 'public_key': public_key}
        )
        return response.get('success', False)

    def remove_key(self, zone_id: str) -> bool:
        """从 Agent 移除密钥"""
        response = self._send_request('remove_key', zone_id=zone_id)
        return response.get('success', False)

    def list_keys(self) -> List[Dict]:
        """列出已加载的密钥"""
        response = self._send_request('list_keys')
        return response.get('keys', [])

    def ssh_exec(self, zone_id: str, host: str, command: str) -> Dict:
        """通过 Agent 执行 SSH 命令"""
        response = self._send_request(
            'ssh_exec',
            zone_id=zone_id,
            payload={'host': host, 'command': command}
        )
        return {
            'exit_status': response.get('exit_status', -1),
            'stdout': response.get('stdout', ''),
            'stderr': response.get('stderr', '')
        }
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/unit/test_ssh_agent_service.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add ceph_snapshot_manager/services/ssh_agent_service.py tests/unit/test_ssh_agent_service.py
git commit -m "feat: add SSH Agent IPC service"
```

---

### Task 11: 重构 CephService 使用 SSH Agent

**Files:**
- Modify: `docker-enterprise/ceph_snapshot_manager/services/ceph_service.py`

- [ ] **Step 1: 分析现有实现**

现有 CephService 直接使用 paramiko SSHClient 连接。需要重构为：
1. 通过 SSHAgentService 与 agent 通信
2. Zone 配置从数据库读取
3. SSH 连接由 agent 管理

主要变更：
- 删除 `_connect()`, `_disconnect()`, `_exec_command()` 方法
- 添加 `set_agent_service()` 方法注入 SSHAgentService
- Zone 配置存储在 MySQL 而非 config.ini

- [ ] **Step 2: 提交**

```bash
git add ceph_snapshot_manager/services/ceph_service.py
git commit -m "refactor: CephService uses SSH Agent for connections"
```

---

## Phase 4: 配置加载重构

### Task 12: 重构 settings.py 从数据库读取配置

**Files:**
- Modify: `docker-enterprise/ceph_snapshot_manager/config/settings.py`

- [ ] **Step 1: 分析现有实现**

现有 settings.py 从 config.ini 读取。需要重构为从 MySQL 读取。

主要变更：
1. 删除 `load_config()` 从文件读取的逻辑
2. 添加 `DatabaseConfigLoader` 类从 MySQL 读取配置
3. 兼容环境变量 `DATABASE_URL` 优先
4. 懒加载配置，首次访问时连接数据库

- [ ] **Step 2: 提交**

```bash
git add ceph_snapshot_manager/config/settings.py
git commit -m "refactor: settings.py loads config from MySQL"
```

---

## Phase 5: 管理 API

### Task 13: 创建密钥管理 API

**Files:**
- Create: `docker-enterprise/ceph_snapshot_manager/routes/admin/keys.py`
- Create: `docker-enterprise/tests/unit/test_admin_keys_api.py`

- [ ] **Step 1: 实现 API**

```python
"""SSH 密钥管理 API"""
from flask import Blueprint, request, jsonify
from flask_login import login_required
from ceph_snapshot_manager.models.zone_key import ZoneKeyModel
from ceph_snapshot_manager.services.ssh_agent_service import SSHAgentService
import paramiko
import hashlib

admin_keys_bp = Blueprint('admin_keys', __name__)

def get_zone_key_model():
    return ZoneKeyModel()

def get_ssh_agent():
    return SSHAgentService()

@admin_keys_bp.route('/api/admin/keys', methods=['GET'])
@login_required
def list_keys():
    """获取所有 Zone 密钥列表"""
    model = get_zone_key_model()
    keys = model.get_all()
    # 不返回私钥
    for key in keys:
        key.pop('private_key', None)
    return jsonify({'keys': keys})

@admin_keys_bp.route('/api/admin/keys/<zone_id>', methods=['GET'])
@login_required
def get_key(zone_id):
    """获取指定 Zone 的密钥信息"""
    model = get_zone_key_model()
    key = model.get_by_zone_id(zone_id)
    if not key:
        return jsonify({'error': 'Zone 密钥不存在'}), 404
    # 不返回私钥
    key.pop('private_key', None)
    return jsonify(key)

@admin_keys_bp.route('/api/admin/keys', methods=['POST'])
@login_required
def upload_key():
    """上传私钥并关联到 Zone"""
    data = request.get_json()
    zone_id = data.get('zone_id')
    zone_name = data.get('zone_name')
    ssh_user = data.get('ssh_user', 'root')
    private_key = data.get('private_key')

    if not all([zone_id, zone_name, private_key]):
        return jsonify({'error': '缺少必要参数'}), 400

    try:
        # 验证私钥格式
        key = paramiko.RSAKey.from_private_key(private_key)
        public_key = f"{key.get_name()} {key.get_base64()}"
        fingerprint = key.get_fingerprint().hex(':')

        # 保存到数据库
        model = get_zone_key_model()
        model.add_key(
            zone_id=zone_id,
            zone_name=zone_name,
            ssh_user=ssh_user,
            private_key=private_key,
            public_key=public_key,
            fingerprint=fingerprint
        )

        # 添加到 SSH Agent
        agent = get_ssh_agent()
        agent.add_key(zone_id, private_key, public_key)

        return jsonify({
            'success': True,
            'public_key': public_key,
            'fingerprint': fingerprint
        })
    except paramiko.ssh_exception.SSHException as e:
        return jsonify({'error': f'无效的私钥: {str(e)}'}), 400

@admin_keys_bp.route('/api/admin/keys/<zone_id>', methods=['PUT'])
@login_required
def update_key(zone_id):
    """更新 Zone 的密钥"""
    data = request.get_json()
    private_key = data.get('private_key')

    if not private_key:
        return jsonify({'error': '缺少私钥'}), 400

    try:
        key = paramiko.RSAKey.from_private_key(private_key)
        public_key = f"{key.get_name()} {key.get_base64()}"
        fingerprint = key.get_fingerprint().hex(':')

        model = get_zone_key_model()
        existing = model.get_by_zone_id(zone_id)
        if not existing:
            return jsonify({'error': 'Zone 密钥不存在'}), 404

        model.add_key(
            zone_id=zone_id,
            zone_name=existing['zone_name'],
            ssh_user=existing['ssh_user'],
            private_key=private_key,
            public_key=public_key,
            fingerprint=fingerprint
        )

        # 更新 Agent
        agent = get_ssh_agent()
        agent.remove_key(zone_id)
        agent.add_key(zone_id, private_key, public_key)

        return jsonify({'success': True})
    except paramiko.ssh_exception.SSHException as e:
        return jsonify({'error': f'无效的私钥: {str(e)}'}), 400

@admin_keys_bp.route('/api/admin/keys/<zone_id>', methods=['DELETE'])
@login_required
def delete_key(zone_id):
    """删除 Zone 的密钥"""
    model = get_zone_key_model()
    agent = get_ssh_agent()

    agent.remove_key(zone_id)
    model.delete_by_zone_id(zone_id)

    return jsonify({'success': True})
```

- [ ] **Step 2: 提交**

```bash
git add ceph_snapshot_manager/routes/admin/keys.py
git commit -m "feat: add SSH key management API"
```

---

### Task 14: 创建配置管理 API

**Files:**
- Create: `docker-enterprise/ceph_snapshot_manager/routes/admin/config.py`

- [ ] **Step 1: 实现 API**

```python
"""应用配置管理 API"""
from flask import Blueprint, request, jsonify
from flask_login import login_required
from ceph_snapshot_manager.models.app_config import AppConfigModel

admin_config_bp = Blueprint('admin_config', __name__)

def get_config_model():
    return AppConfigModel()

@admin_config_bp.route('/api/admin/config', methods=['GET'])
@login_required
def list_config():
    """获取所有配置"""
    model = get_config_model()
    configs = model.get_all()
    return jsonify({'configs': configs})

@admin_config_bp.route('/api/admin/config/<key>', methods=['GET'])
@login_required
def get_config(key):
    """获取单个配置值"""
    model = get_config_model()
    value = model.get(key)
    return jsonify({'key': key, 'value': value})

@admin_config_bp.route('/api/admin/config/<key>', methods=['PUT'])
@login_required
def update_config(key):
    """更新配置值"""
    data = request.get_json()
    value = data.get('value')

    if value is None:
        return jsonify({'error': '缺少 value 参数'}), 400

    model = get_config_model()
    model.set(key, value)

    return jsonify({'success': True})
```

- [ ] **Step 2: 提交**

```bash
git add ceph_snapshot_manager/routes/admin/config.py
git commit -m "feat: add config management API"
```

---

### Task 15: 创建 admin 路由包

**Files:**
- Create: `docker-enterprise/ceph_snapshot_manager/routes/admin/__init__.py`

- [ ] **Step 1: 实现路由注册**

```python
"""Admin 路由包"""
from flask import Flask

def register_admin_blueprints(app: Flask):
    """注册 admin 蓝图"""
    from ceph_snapshot_manager.routes.admin.keys import admin_keys_bp
    from ceph_snapshot_manager.routes.admin.config import admin_config_bp

    app.register_blueprint(admin_keys_bp)
    app.register_blueprint(admin_config_bp)
```

- [ ] **Step 2: 更新主路由注册**

Modify: `ceph_snapshot_manager/routes/__init__.py`
添加 `register_admin_blueprints(app)` 调用

- [ ] **Step 3: 提交**

```bash
git add ceph_snapshot_manager/routes/admin/__init__.py ceph_snapshot_manager/routes/__init__.py
git commit -m "feat: register admin blueprints"
```

---

## Phase 6: 前端页面

### Task 16: 创建密钥管理页面

**Files:**
- Create: `docker-enterprise/templates/admin/keys.html`

- [ ] **Step 1: 实现 HTML 页面**

页面包含：
- Zone 密钥列表表格（Zone Name, SSH User, Fingerprint, Created）
- 上传私钥按钮 → 模态框（选择 Zone, 上传私钥文件）
- 查看公钥按钮 → 模态框（显示公钥，复制按钮）
- 更换密钥按钮
- 删除密钥按钮

- [ ] **Step 2: 提交**

```bash
git add templates/admin/keys.html
git commit -m "feat: add SSH key management UI page"
```

---

### Task 17: 创建配置管理页面

**Files:**
- Create: `docker-enterprise/templates/admin/config.html`

- [ ] **Step 1: 实现 HTML 页面**

页面包含：
- 配置列表表格（Key, Value, Description, Secret）
- 编辑按钮 → 模态框（修改值）
- 敏感配置值显示为 ****
- 保存按钮

- [ ] **Step 2: 提交**

```bash
git add templates/admin/config.html
git commit -m "feat: add config management UI page"
```

---

## Phase 7: 数据迁移

### Task 18: 创建 SQLite 到 MySQL 迁移脚本

**Files:**
- Create: `docker-enterprise/tests/migration/sqlite_to_mysql.py`
- Modify: `docker-enterprise/scripts/init-mysql.sql` (添加迁移用户)

- [ ] **Step 1: 实现迁移脚本**

```python
"""SQLite 到 MySQL 数据迁移"""
import sqlite3
import pymysql
import sys

def migrate_users(sqlite_path: str, mysql_config: dict):
    """迁移用户数据"""
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_cursor = sqlite_conn.cursor()

    mysql_conn = pymysql.connect(**mysql_config)
    mysql_cursor = mysql_conn.cursor()

    # 读取 SQLite 用户
    sqlite_cursor.execute("SELECT id, username, password_hash, role FROM users")
    users = sqlite_cursor.fetchall()

    # 插入 MySQL
    for user in users:
        mysql_cursor.execute(
            "INSERT INTO users (id, username, password_hash, role) VALUES (%s, %s, %s, %s)",
            user
        )

    mysql_conn.commit()
    sqlite_conn.close()
    mysql_conn.close()
    print(f"Migrated {len(users)} users")

def migrate_audit_logs(sqlite_path: str, mysql_config: dict):
    """迁移审计日志"""
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_cursor = sqlite_conn.cursor()

    mysql_conn = pymysql.connect(**mysql_config)
    mysql_cursor = mysql_conn.cursor()

    # 读取 SQLite 审计日志
    sqlite_cursor.execute("SELECT * FROM audit_logs")
    logs = sqlite_cursor.fetchall()

    # 插入 MySQL
    for log in logs:
        mysql_cursor.execute(
            """INSERT INTO audit_logs
            (id, timestamp, username, action, zone_id, zone_name, volume_id,
             volume_name, snapshot_name, ceph_pool, full_snapshot_name,
             keep_count, dry_run, result, message, commands, client_ip)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            log
        )

    mysql_conn.commit()
    sqlite_conn.close()
    mysql_conn.close()
    print(f"Migrated {len(logs)} audit logs")

if __name__ == '__main__':
    sqlite_path = '../users.db'  # 源 SQLite 文件
    mysql_config = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'password',
        'database': 'ceph_snapshot'
    }

    migrate_users(sqlite_path, mysql_config)
    migrate_audit_logs('../audit.db', mysql_config)
    print("Migration complete!")
```

- [ ] **Step 2: 提交**

```bash
git add tests/migration/sqlite_to_mysql.py
git commit -m "feat: add SQLite to MySQL migration script"
```

---

## Phase 8: 集成测试

### Task 19: Docker Compose 启动验证

- [ ] **Step 1: 复制环境变量文件**

```bash
cp docker-enterprise/.env.example docker-enterprise/.env
```

- [ ] **Step 2: 启动服务**

```bash
cd docker-enterprise
docker-compose build
docker-compose up -d
```

- [ ] **Step 3: 验证容器运行**

```bash
docker-compose ps
docker-compose logs mysql
docker-compose logs ssh-key-agent
docker-compose logs web-app
```

- [ ] **Step 4: 验证数据库连接**

```bash
docker-compose exec web-app python -c "from ceph_snapshot_manager.models.app_config import AppConfigModel; print(AppConfigModel().get('cloudstack_url'))"
```

- [ ] **Step 5: 提交**

```bash
git add docker-enterprise/.env.example
git commit -m "chore: add .env.example"
```

---

### Task 20: 功能测试

- [ ] **Step 1: 登录测试**

访问 http://localhost:5000，使用 admin/admin123 登录

- [ ] **Step 2: 上传 SSH 密钥测试**

上传一个测试私钥，验证公钥生成和指纹显示

- [ ] **Step 3: 配置管理测试**

修改 cloudstack_url，验证保存后重新读取值正确

- [ ] **Step 4: 数据持久化测试**

```bash
docker-compose restart
# 验证数据未丢失
```

- [ ] **Step 5: 提交**

```bash
git commit -m "test: add integration test results"
```

---

## 实施检查清单

- [ ] Task 1: .env.example
- [ ] Task 2: init-mysql.sql
- [ ] Task 3: ssh-agent-entrypoint.sh
- [ ] Task 4: Dockerfile.ssh-agent
- [ ] Task 5: Dockerfile + requirements-docker.txt
- [ ] Task 6: docker-compose.yml
- [ ] Task 7: AppConfigModel
- [ ] Task 8: ZoneKeyModel
- [ ] Task 9: AuditLogDB MySQL 适配
- [ ] Task 10: SSHAgentService
- [ ] Task 11: CephService 重构
- [ ] Task 12: settings.py 重构
- [ ] Task 13: keys.py API
- [ ] Task 14: config.py API
- [ ] Task 15: admin 蓝图注册
- [ ] Task 16: keys.html
- [ ] Task 17: config.html
- [ ] Task 18: sqlite_to_mysql.py
- [ ] Task 19: Docker 启动验证
- [ ] Task 20: 功能测试

---

## 执行顺序建议

**Phase 1-3（基础设施+模型）** → **Phase 4（配置加载）** → **Phase 5（API）** → **Phase 6（前端）** → **Phase 7-8（迁移+测试）**
