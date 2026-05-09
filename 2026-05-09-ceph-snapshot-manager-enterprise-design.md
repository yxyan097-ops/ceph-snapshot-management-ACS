# Ceph 快照管理系统 - 企业级架构设计方案

**日期:** 2026-05-09
**版本:** v2.0

---

## 1. 概述

### 1.1 项目背景

现有 Ceph 快照管理系统使用 SQLite 数据库和 SSH 密码认证，已无法满足企业级运维需求。本方案将系统迁移至企业级架构。

### 1.2 升级目标

| 维度 | 现状 | 目标 |
|------|------|------|
| 数据库 | SQLite | MySQL 8.0 |
| SSH 认证 | 用户名+密码 | SSH Key |
| 部署方式 | 传统部署 | Docker Compose |
| 密钥管理 | 配置文件中 | Web UI 管理 |
| 配置管理 | config.ini | 数据库存储 + Web UI |
| 数据持久化 | 无统一管理 | Docker Volume |

---

## 2. Docker Compose 架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Network                          │
│                    (ceph-snapshot-net)                     │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ MySQL        │  │ ssh-key-agent│  │   web-app   │     │
│  │ Container    │◄─┤ Container   │◄─┤  Container   │     │
│  │              │  │             │  │             │     │
│  │ • Volume     │  │ • Volume    │  │ • Volume    │     │
│  │   /app/mysql │  │   /app/keys │  │   /app/data │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  CloudStack API  │
                    │  (外部服务)       │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Ceph Clusters   │
                    │  (多 Zone)       │
                    └──────────────────┘
```

### 2.2 容器说明

| 容器 | 镜像 | 说明 |
|------|------|------|
| `mysql` | mysql:8.0 | 持久化 MySQL 8.0 |
| `ssh-key-agent` | 自定义镜像 | SSH 密钥管理 + Agent |
| `web-app` | 自定义镜像 | Flask 应用 |

### 2.3 数据卷设计

所有数据卷统一挂载至 `/app` 目录下，便于集中管理和备份。

| 卷名 | 容器内路径 | 说明 |
|------|-----------|------|
| `mysql_data` | `/app/mysql/data` | MySQL 数据文件 |
| `ssh_keys` | `/app/keys` | Zone SSH 密钥 |
| `app_data` | `/app/data` | 应用运行时数据 |

---

## 3. 目录结构设计

```
ceph-snapshot-manager/
├── docker-compose.yml           # Docker Compose 配置
├── Dockerfile                  # Web 应用镜像构建
├── Dockerfile.ssh-agent        # SSH Agent 镜像构建
├── .env.example               # 环境变量模板
│
├── scripts/
│   ├── init-mysql.sql         # MySQL 初始化脚本
│   └── ssh-agent-entrypoint.sh # SSH Agent 启动脚本
│
├── ceph_snapshot_manager/      # 应用包
│   ├── __init__.py
│   ├── config/
│   │   └── settings.py        # 从数据库读取配置
│   ├── models/
│   │   ├── user.py            # 用户模型
│   │   ├── audit.py           # 审计日志模型
│   │   ├── zone_key.py        # Zone SSH 密钥模型 [新增]
│   │   └── app_config.py      # 应用配置模型 [新增]
│   ├── services/
│   │   ├── ceph_service.py    # Ceph SSH 操作
│   │   ├── cloudstack_service.py
│   │   ├── snapshot_service.py
│   │   └── ssh_agent_service.py # SSH Agent 通信 [新增]
│   ├── routes/
│   │   ├── auth.py
│   │   ├── volumes.py
│   │   ├── snapshots.py
│   │   ├── cleanup.py
│   │   ├── ceph.py
│   │   ├── audit.py
│   │   └── admin/             # [新增] 管理路由
│   │       ├── keys.py        # 密钥管理 API
│   │       └── config.py      # 配置管理 API
│   └── utils/
│       ├── decorators.py
│       └── responses.py
│
├── templates/                  # HTML 模板
│   ├── index.html
│   ├── login.html
│   ├── audit.html
│   └── admin/                  # [新增] 管理页面
│       ├── keys.html
│       └── config.html
├── static/
│   └── style.css
└── tests/
```

---

## 4. 数据库 Schema（MySQL）

### 4.1 用户表

```sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'operator', 'viewer') DEFAULT 'viewer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 Zone SSH 密钥表

```sql
CREATE TABLE zone_keys (
    id INT AUTO_INCREMENT PRIMARY KEY,
    zone_id VARCHAR(255) NOT NULL,           -- CloudStack Zone ID
    zone_name VARCHAR(255) NOT NULL,          -- CloudStack Zone Name
    ssh_user VARCHAR(255) NOT NULL DEFAULT 'root',
    private_key TEXT NOT NULL,                -- 私钥内容
    public_key TEXT,                          -- 自动生成的公钥
    fingerprint VARCHAR(255),                  -- 密钥指纹
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_zone_id (zone_id)
);
```

### 4.3 应用配置表

```sql
CREATE TABLE app_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(255) UNIQUE NOT NULL,
    config_value TEXT,
    description VARCHAR(512),
    is_secret BOOLEAN DEFAULT FALSE,           -- 是否敏感配置
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 4.4 审计日志表

```sql
CREATE TABLE audit_logs (
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
```

### 4.5 索引

```sql
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_username ON audit_logs(username);
CREATE INDEX idx_zone_keys_zone_id ON zone_keys(zone_id);
```

### 4.6 初始配置数据

```sql
INSERT INTO app_config (config_key, config_value, description, is_secret) VALUES
('cloudstack_url', 'http://172.16.100.9:8080/client/api', 'CloudStack API URL', FALSE),
('cloudstack_api_key', '', 'CloudStack API Key', TRUE),
('cloudstack_secret_key', '', 'CloudStack Secret Key', TRUE),
('snap_trim_script', '/scripts/snap-trim.sh', 'Snapshot trim script path', FALSE),
('default_keep', '3', 'Default snapshot retention count', FALSE),
('app_secret_key', 'change-me-in-production', 'Flask secret key', TRUE);
```

---

## 5. 核心模块设计

### 5.1 SSH Agent 服务

#### 5.1.1 架构

```
┌─────────────────────────────────────────────────┐
│              ssh-key-agent container            │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │  SSH Agent Manager                      │   │
│  │  • 监听 /tmp/ceph-ssh-agent.sock       │   │
│  │  • 管理所有 Zone 的密钥                 │   │
│  │  • 提供 SSH 连接池                     │   │
│  └─────────────────────────────────────────┘   │
│                    ▲                            │
│                    │ UNIX Socket               │
│         ┌─────────┴─────────┐                 │
│         │                   │                 │
│  ┌──────┴──────┐    ┌──────┴──────┐         │
│  │ Zone1 Key   │    │ Zone2 Key   │  ...    │
│  │ rsa 2048   │    │ rsa 4096   │         │
│  └─────────────┘    └─────────────┘         │
│                                                 │
│  Volume: /app/keys (持久化私钥)               │
└─────────────────────────────────────────────────┘
```

#### 5.1.2 Agent 协议

请求/响应通过 JSON over UNIX Socket 通信：

```python
# 请求格式
{
    "cmd": "add_key",       # add_key | remove_key | list_keys | ssh_exec
    "zone_id": "zone-uuid",
    "payload": {...}
}

# 响应格式
{
    "success": true,
    "result": {...}
}
```

#### 5.1.3 密钥管理流程

```
管理员上传私钥
    │
    ▼
Web-App 验证私钥格式
    │
    ▼
生成公钥和指纹
    │
    ▼
通过 Socket 发送给 SSH Agent
    │
    ▼
Agent 添加到 SSH Agent
    │
    ▼
私钥持久化到 Volume /app/keys/{zone_id}/
    │
    ▼
Zone 配置关联完成
```

### 5.2 配置加载流程

```
应用启动
    │
    ▼
┌──────────────────┐
│ 读取环境变量     │  ← DATABASE_URL 等
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 连接 MySQL       │
│ 读取 app_config  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 连接 SSH Agent   │
│ 加载 Zone 密钥   │
└────────┬─────────┘
         │
         ▼
    应用就绪
```

---

## 6. Web UI 管理功能

### 6.1 SSH 密钥管理

| 功能 | 说明 |
|------|------|
| 密钥列表 | 显示所有 Zone 及其关联密钥（指纹、创建时间） |
| 上传私钥 | 上传私钥文件，自动生成公钥，关联到 Zone |
| 查看公钥 | 显示公钥内容，便于复制到 Ceph 节点 |
| 更换密钥 | 密钥轮换，新密钥自动生效 |
| 删除密钥 | 解除 Zone 与密钥的关联 |

### 6.2 应用配置管理

| 功能 | 说明 |
|------|------|
| 配置列表 | 显示所有配置项 |
| 编辑配置 | 修改配置值 |
| 敏感信息 | 密码类配置加密显示 |

### 6.3 Zone 自动发现

- Zone 信息从 CloudStack API 自动获取
- 无需手动添加/删除 Zone
- 首次访问时若无密钥关联，提示管理员上传

---

## 7. Docker Compose 配置

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
      - /tmp/ceph-ssh-agent.sock:/tmp/ceph-ssh-agent.sock
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
      - ./scripts/snap-trim.sh:/scripts/snap-trim.sh
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

---

## 8. 迁移步骤

### Phase 1: 基础设施准备

1. 编写 Dockerfile（Web 应用）
2. 编写 Dockerfile.ssh-agent（SSH Agent）
3. 编写 docker-compose.yml
4. 创建 .env.example
5. 创建 MySQL 初始化脚本 init-mysql.sql
6. 创建 SSH Agent 入口脚本 ssh-agent-entrypoint.sh

### Phase 2: 数据库迁移

1. 创建 MySQL Schema（init-mysql.sql）
2. 编写数据迁移脚本（SQLite → MySQL）
3. 迁移用户数据
4. 迁移审计日志数据

### Phase 3: 应用适配

1. 重构 `config/settings.py` 从数据库读取配置
2. 实现 SSH Agent 通信模块 `ssh_agent_service.py`
3. 实现 Zone 密钥管理模型 `zone_key.py`
4. 实现配置管理模型 `app_config.py`
5. 实现密钥管理 API 路由
6. 实现配置管理 API 路由
7. 重构 CephService 使用 SSH Agent 通信

### Phase 4: 前端适配

1. 新增 SSH 密钥管理页面
2. 新增配置管理页面
3. 集成新 API

### Phase 5: 测试验证

1. Docker Compose 本地启动
2. 验证所有功能
3. 数据持久化测试（重启容器数据不丢失）
4. 多 Zone SSH 连接测试

---

## 9. 备份策略

所有持久化数据集中在 `/app` 目录：

```bash
# 备份所有数据
docker run --rm \
  -v ceph-snapshot-mysql_data:/app/mysql/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/ceph-snapshot-$(date +%Y%m%d).tar.gz /app

# 备份 MySQL（在线）
mysqldump -h 127.0.0.1 -u root -p ceph_snapshot > backup.sql
```

---

## 10. 版本迭代说明

### 升级应用版本

```bash
# 1. 拉取新镜像或重新构建
docker build -t ceph-snapshot-manager:v2 .

# 2. 更新 docker-compose.yml 中的镜像版本
# image: ceph-snapshot-manager:v2

# 3. 重新启动（数据卷不丢失）
docker-compose up -d
```

### 数据迁移注意事项

- MySQL 数据存储在 Docker Volume，升级镜像不影响数据
- SSH 密钥存储在 Volume，升级镜像不影响数据
- 应用配置存储在 MySQL，升级镜像不影响数据
