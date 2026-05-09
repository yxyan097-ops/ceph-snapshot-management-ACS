"""Audit log model and database operations."""
import sqlite3
from datetime import datetime
from typing import List, Optional


class AuditLogDB:
    """Audit log persistence layer."""

    def __init__(self, db_path: str = 'audit.db'):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the audit_logs table."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    username TEXT NOT NULL,
                    action TEXT NOT NULL,
                    zone_id TEXT,
                    zone_name TEXT,
                    volume_id TEXT,
                    volume_name TEXT,
                    snapshot_name TEXT,
                    ceph_pool TEXT,
                    full_snapshot_name TEXT,
                    keep_count INTEGER,
                    dry_run INTEGER,
                    result TEXT,
                    message TEXT,
                    commands TEXT,
                    client_ip TEXT
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_logs(timestamp DESC)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_action ON audit_logs(action)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_username ON audit_logs(username)')

    def add_log(
        self,
        username: str,
        action: str,
        zone_id: Optional[str] = None,
        zone_name: Optional[str] = None,
        volume_id: Optional[str] = None,
        volume_name: Optional[str] = None,
        snapshot_name: Optional[str] = None,
        ceph_pool: Optional[str] = None,
        full_snapshot_name: Optional[str] = None,
        keep_count: Optional[int] = None,
        dry_run: Optional[bool] = None,
        result: str = 'success',
        message: str = '',
        commands: Optional[str] = None,
        client_ip: Optional[str] = None
    ) -> None:
        """Add a new audit log entry."""
        timestamp = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO audit_logs (timestamp, username, action, zone_id, zone_name, volume_id, volume_name,
                    snapshot_name, ceph_pool, full_snapshot_name, keep_count, dry_run, result, message, commands, client_ip)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp, username, action, zone_id, zone_name, volume_id, volume_name,
                snapshot_name, ceph_pool, full_snapshot_name, keep_count,
                1 if dry_run else 0 if dry_run is not None else None,
                result, message, commands, client_ip
            ))
            conn.commit()

    def get_logs(self, limit: int = 100, offset: int = 0) -> List[dict]:
        """Get paginated audit logs ordered by timestamp descending."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ? OFFSET ?
            ''', (limit, offset))
            return [dict(row) for row in cursor.fetchall()]

    def count_logs(self) -> int:
        """Get total count of audit logs."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM audit_logs')
            return cursor.fetchone()[0]

    def clear_logs(self) -> None:
        """Delete all audit logs."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM audit_logs')
            conn.commit()
