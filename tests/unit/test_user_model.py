"""Unit tests for user model."""
import pytest
from ceph_snapshot_manager.models.user import User, UserDB


class TestUser:
    """Tests for User model."""

    def test_user_role_admin(self):
        """Test admin user has correct permissions."""
        user = User(1, 'admin', 'hash', 'admin')
        assert user.can_cleanup() is True
        assert user.can_manage_users() is True

    def test_user_role_operator(self):
        """Test operator user has correct permissions."""
        user = User(2, 'operator', 'hash', 'operator')
        assert user.can_cleanup() is True
        assert user.can_manage_users() is False

    def test_user_role_viewer(self):
        """Test viewer user has correct permissions."""
        user = User(3, 'viewer', 'hash', 'viewer')
        assert user.can_cleanup() is False
        assert user.can_manage_users() is False

    def test_user_is_authenticated(self):
        """Test user authentication status."""
        user = User(1, 'test', 'hash', 'viewer')
        assert user.is_authenticated is True
        assert user.is_active is True
        assert user.is_anonymous is False

    def test_user_get_id(self):
        """Test user ID retrieval."""
        user = User(42, 'test', 'hash', 'viewer')
        assert user.get_id() == '42'
