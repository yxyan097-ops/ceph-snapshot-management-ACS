"""Pytest configuration and fixtures."""
import pytest
import tempfile
import os

from ceph_snapshot_manager.config.settings import CephConfig, CloudStackConfig, AppConfig, DatabaseConfig, Config


@pytest.fixture
def ceph_config():
    """Create a test Ceph configuration."""
    return CephConfig(
        ssh_host='localhost',
        ssh_user='testuser',
        ssh_password='testpass',
        ssh_key_path=None,
        snap_trim_script='/tmp/test-snap-trim.sh',
        default_keep=3
    )


@pytest.fixture
def cloudstack_config():
    """Create a test CloudStack configuration."""
    return CloudStackConfig(
        url='https://test.example.com/api',
        api_key='test_api_key',
        secret_key='test_secret_key'
    )


@pytest.fixture
def app_config():
    """Create a test application configuration."""
    return AppConfig(
        secret_key='test-secret-key',
        host='127.0.0.1',
        port=5000,
        debug=True
    )


@pytest.fixture
def database_config():
    """Create a test database configuration with temp files."""
    temp_dir = tempfile.mkdtemp()
    return DatabaseConfig(
        users_db=os.path.join(temp_dir, 'test_users.db'),
        audit_db=os.path.join(temp_dir, 'test_audit.db')
    )


@pytest.fixture
def full_config(ceph_config, cloudstack_config, app_config, database_config):
    """Create a full test configuration."""
    return Config(
        cloudstack=cloudstack_config,
        ceph=ceph_config,
        app=app_config,
        database=database_config
    )
