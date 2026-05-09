"""Configuration management for Ceph Snapshot Manager."""
import configparser
from dataclasses import dataclass, field
from typing import Optional, Dict


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
    ssh_password: Optional[str] = None
    ssh_key_path: Optional[str] = None
    snap_trim_script: str = '/tmp/snap-trim.sh'
    default_keep: int = 3


@dataclass
class AppConfig:
    """Application configuration."""
    secret_key: str = 'dev-secret-key'
    host: str = '0.0.0.0'
    port: int = 5000
    debug: bool = False


@dataclass
class DatabaseConfig:
    """Database configuration."""
    users_db: str = 'users.db'
    audit_db: str = 'audit.db'


@dataclass
class Config:
    """Main configuration container."""
    cloudstack: CloudStackConfig
    ceph_configs: Dict[str, CephConfig] = field(default_factory=dict)
    ceph_default: Optional[CephConfig] = None
    app: AppConfig = None
    database: DatabaseConfig = None


def load_config(config_path: str = 'config.ini') -> Config:
    """Load and validate configuration from ini file.

    Args:
        config_path: Path to the config.ini file

    Returns:
        Config object with all settings

    Raises:
        ValueError: If required configuration is missing
    """
    config = configparser.ConfigParser()
    config.read(config_path)

    # CloudStack config
    if 'cloudstack' not in config:
        raise ValueError("Missing [cloudstack] section in config")

    cloudstack_config = CloudStackConfig(
        url=config.get('cloudstack', 'url'),
        api_key=config.get('cloudstack', 'api_key'),
        secret_key=config.get('cloudstack', 'secret_key')
    )

    # Ceph config - support multiple zones
    ceph_configs: Dict[str, CephConfig] = {}
    ceph_default = None

    # Get default Ceph settings
    default_snap_trim_script = config.get('ceph', 'snap_trim_script', fallback='/tmp/snap-trim.sh')
    default_keep = config.getint('ceph', 'default_keep', fallback=3)

    # Parse ceph:zonename sections
    for section in config.sections():
        if section.startswith('ceph:'):
            zone_id = section[5:]  # Extract zone name after 'ceph:'
            ceph_configs[zone_id] = CephConfig(
                ssh_host=config.get(section, 'ssh_host'),
                ssh_user=config.get(section, 'ssh_user'),
                ssh_password=config.get(section, 'ssh_password', fallback=None),
                ssh_key_path=config.get(section, 'ssh_key_path', fallback=None),
                snap_trim_script=config.get(section, 'snap_trim_script', fallback=default_snap_trim_script),
                default_keep=config.getint(section, 'default_keep', fallback=default_keep)
            )

    # If no zone-specific configs, try legacy [ceph] section
    if not ceph_configs and 'ceph' in config:
        if config.has_option('ceph', 'ssh_host'):
            ceph_default = CephConfig(
                ssh_host=config.get('ceph', 'ssh_host'),
                ssh_user=config.get('ceph', 'ssh_user'),
                ssh_password=config.get('ceph', 'ssh_password', fallback=None),
                ssh_key_path=config.get('ceph', 'ssh_key_path', fallback=None),
                snap_trim_script=config.get('ceph', 'snap_trim_script', fallback='/tmp/snap-trim.sh'),
                default_keep=config.getint('ceph', 'default_keep', fallback=3)
            )

    # App config
    if 'app' not in config:
        raise ValueError("Missing [app] section in config")

    app_config = AppConfig(
        secret_key=config.get('app', 'secret_key', fallback='dev-secret-key'),
        host=config.get('app', 'host', fallback='0.0.0.0'),
        port=config.getint('app', 'port', fallback=5000),
        debug=config.getboolean('app', 'debug', fallback=False)
    )

    # Database config
    database_config = DatabaseConfig(
        users_db=config.get('database', 'users_db', fallback='users.db') if 'database' in config else 'users.db',
        audit_db=config.get('database', 'audit_db', fallback='audit.db') if 'database' in config else 'audit.db'
    )

    return Config(
        cloudstack=cloudstack_config,
        ceph_configs=ceph_configs,
        ceph_default=ceph_default,
        app=app_config,
        database=database_config
    )
