"""Unit tests for audit model."""
import pytest
import tempfile
import os
import gc

from ceph_snapshot_manager.models.audit import AuditLogDB


class TestAuditLogDB:
    """Tests for AuditLogDB model."""

    @pytest.fixture
    def audit_db(self):
        """Create a test audit database."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, 'test_audit.db')
        db = AuditLogDB(db_path=db_path)
        yield db
        # Cleanup - force garbage collection first
        del db
        gc.collect()
        # On Windows, may need multiple attempts
        for _ in range(3):
            try:
                if os.path.exists(db_path):
                    os.remove(db_path)
                break
            except PermissionError:
                gc.collect()

    def test_add_log(self, audit_db):
        """Test adding an audit log entry."""
        audit_db.add_log(
            username='testuser',
            action='test_action',
            zone_id='zone-1',
            volume_id='vol-1',
            volume_name='test-volume',
            snapshot_name='snap-1',
            result='success',
            message='Test message'
        )

        logs = audit_db.get_logs(limit=10)
        assert len(logs) == 1
        assert logs[0]['username'] == 'testuser'
        assert logs[0]['action'] == 'test_action'
        assert logs[0]['zone_id'] == 'zone-1'

    def test_get_logs_pagination(self, audit_db):
        """Test log pagination."""
        for i in range(5):
            audit_db.add_log(
                username=f'user{i}',
                action='test_action',
                result='success'
            )

        logs = audit_db.get_logs(limit=2, offset=0)
        assert len(logs) == 2

        logs_page2 = audit_db.get_logs(limit=2, offset=2)
        assert len(logs_page2) == 2

    def test_count_logs(self, audit_db):
        """Test log counting."""
        assert audit_db.count_logs() == 0

        audit_db.add_log(username='user1', action='test', result='success')
        assert audit_db.count_logs() == 1

        audit_db.add_log(username='user2', action='test', result='success')
        assert audit_db.count_logs() == 2

    def test_clear_logs(self, audit_db):
        """Test clearing logs."""
        audit_db.add_log(username='user1', action='test', result='success')
        audit_db.add_log(username='user2', action='test', result='success')
        assert audit_db.count_logs() == 2

        audit_db.clear_logs()
        assert audit_db.count_logs() == 0
