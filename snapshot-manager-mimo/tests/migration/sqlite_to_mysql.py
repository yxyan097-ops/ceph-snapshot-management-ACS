"""SQLite 到 MySQL 数据迁移"""
import sqlite3
import pymysql
import sys
import os

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
    # 默认路径（相对于项目根目录）
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sqlite_users = os.path.join(project_root, 'users.db')
    sqlite_audit = os.path.join(project_root, 'audit.db')

    mysql_config = {
        'host': os.environ.get('MYSQL_HOST', 'localhost'),
        'port': int(os.environ.get('MYSQL_PORT', 3306)),
        'user': os.environ.get('MYSQL_USER', 'root'),
        'password': os.environ.get('MYSQL_PASSWORD', ''),
        'database': os.environ.get('MYSQL_DATABASE', 'ceph_snapshot'),
        'charset': 'utf8mb4'
    }

    print("Starting migration from SQLite to MySQL...")
    print(f"MySQL config: {mysql_config['host']}:{mysql_config['port']}/{mysql_config['database']}")

    # 迁移用户
    if os.path.exists(sqlite_users):
        migrate_users(sqlite_users, mysql_config)
    else:
        print(f"Warning: {sqlite_users} not found, skipping users migration")

    # 迁移审计日志
    if os.path.exists(sqlite_audit):
        migrate_audit_logs(sqlite_audit, mysql_config)
    else:
        print(f"Warning: {sqlite_audit} not found, skipping audit logs migration")

    print("Migration complete!")