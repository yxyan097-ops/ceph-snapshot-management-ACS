"""Configuration management for Ceph Snapshot Manager - MySQL version."""
import os
from dataclasses import dataclass, field
from typing import Optional, Dict

from ceph_snapshot_manager.models.app_config import AppConfigModel


@dataclass
class CloudStackConfig:
    """CloudStack API configuration."""
    url: str
    api_key: str
    secret_key: str


@dataclass
class CephConfig:
    """Ceph configuration."""
    ssh_host: str
    ssh_user: str
    ssh_key_path: Optional[str] = None
    ssh_private_key: Optional[str] = None
    ssh_password: Optional[str] = None
    snap_trim_script: str = '/scripts/snap-trim.sh'
    default_keep: int = 3


@dataclass
class AppConfig:
    """Application configuration."""
    secret_key: str = 'dev-secret-key'
    host: str = '0.0.0.0'
    port: int = 5000
    debug: bool = False


class Config:
    """Main configuration container loaded from database."""

    def __init__(self):
        self.cloudstack: CloudStackConfig = None
        self.ceph_configs: Dict[str, CephConfig] = {}
        self.ceph_default: CephConfig = None
        self.app: AppConfig = None

    @classmethod
    def load_from_database(cls, database_url: str = None) -> 'Config':
        """Load configuration from MySQL database."""
        config = cls()
        db_url = database_url or get_database_url()
        model = AppConfigModel(db_url)

        # Load CloudStack config
        config.cloudstack = CloudStackConfig(
            url=model.get('cloudstack_url') or '',
            api_key=model.get_secret('cloudstack_api_key') or '',
            secret_key=model.get_secret('cloudstack_secret_key') or ''
        )

        # Load Ceph configs from zone_keys
        from ceph_snapshot_manager.models.zone_key import ZoneKeyModel
        zone_model = ZoneKeyModel(db_url)
        for zone_key in zone_model.get_all():
            # Get full key details including private_key
            key_detail = zone_model.get_by_zone_id(zone_key['zone_id'])
            config.ceph_configs[zone_key['zone_id']] = CephConfig(
                ssh_host=zone_key['zone_name'],  # zone_name as ssh_host
                ssh_user=zone_key['ssh_user'],
                ssh_private_key=key_detail.get('private_key') if key_detail else None
            )

        # Load App config
        config.app = AppConfig(
            secret_key=model.get_secret('app_secret_key') or 'dev-secret-key'
        )

        return config


def get_database_url() -> str:
    """Get database URL from environment."""
    return os.environ.get(
        'DATABASE_URL',
        'mysql+pymysql://root:password@localhost:3306/ceph_snapshot'
    )


def load_config() -> Config:
    """Load configuration from database."""
    return Config.load_from_database(get_database_url())