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
