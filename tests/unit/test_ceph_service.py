"""Unit tests for Ceph service result types."""
import pytest
from ceph_snapshot_manager.services.ceph_service import (
    OperationResult, CleanupResult, HealthStatus
)


class TestOperationResult:
    """Tests for OperationResult."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = OperationResult(
            success=True,
            output='test output',
            error='',
            commands=['cmd1', 'cmd2']
        )
        d = result.to_dict()
        assert d['success'] is True
        assert d['output'] == 'test output'
        assert d['error'] == ''
        assert d['commands'] == ['cmd1', 'cmd2']

    def test_default_commands(self):
        """Test default commands is empty list."""
        result = OperationResult(success=True)
        assert result.commands == []
        assert result.to_dict()['commands'] == []


class TestCleanupResult:
    """Tests for CleanupResult."""

    def test_to_dict_includes_dry_run(self):
        """Test that to_dict includes dry_run field."""
        result = CleanupResult(
            success=True,
            output='cleaned',
            commands=['rm cmd'],
            dry_run=True
        )
        d = result.to_dict()
        assert d['dry_run'] is True
        assert d['success'] is True

    def test_dry_run_false(self):
        """Test dry_run when False."""
        result = CleanupResult(
            success=True,
            dry_run=False
        )
        assert result.to_dict()['dry_run'] is False


class TestHealthStatus:
    """Tests for HealthStatus."""

    def test_healthy_to_dict(self):
        """Test healthy status to dict."""
        status = HealthStatus(
            healthy=True,
            status={'pg_state': 'active+clean'},
            error=None
        )
        d = status.to_dict()
        assert d['healthy'] is True
        assert d['status'] == {'pg_state': 'active+clean'}
        assert d['error'] is None

    def test_unhealthy_to_dict(self):
        """Test unhealthy status to dict."""
        status = HealthStatus(
            healthy=False,
            status=None,
            error='connection failed'
        )
        d = status.to_dict()
        assert d['healthy'] is False
        assert d['error'] == 'connection failed'
