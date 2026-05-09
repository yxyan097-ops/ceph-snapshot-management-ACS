"""Ceph Snapshot Manager - Flask Application Factory."""
import os
from flask import Flask, render_template

from ceph_snapshot_manager.config.settings import load_config
from ceph_snapshot_manager.extensions.login import init_login_manager
from ceph_snapshot_manager.models import UserDB, AuditLogDB
from ceph_snapshot_manager.services import CephService, CloudStackService, SnapshotService
from ceph_snapshot_manager.routes import register_blueprints


def create_app(config_path: str = 'config.ini') -> Flask:
    """Create and configure the Flask application.

    Args:
        config_path: Path to the configuration file

    Returns:
        Configured Flask application instance
    """
    # Get the directory containing this file (ceph_snapshot_manager package)
    package_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to find the project root where templates/ and static/ are
    project_root = os.path.dirname(package_dir)

    app = Flask(__name__,
                template_folder=os.path.join(project_root, 'templates'),
                static_folder=os.path.join(project_root, 'static'))

    # Load configuration
    config = load_config(config_path)

    # Flask configuration
    app.secret_key = config.app.secret_key
    app.config['PROVIDE_AUTOMATIC_OPTIONS'] = True

    # Initialize Flask-Login
    init_login_manager(app)

    # Initialize database models
    user_db = UserDB()
    audit_db = AuditLogDB()

    # Initialize services
    ceph_service = None
    ceph_service_per_zone = {}

    # Create per-zone CephService instances
    if config.ceph_configs:
        for zone_id, ceph_config in config.ceph_configs.items():
            ceph_service_per_zone[zone_id] = CephService(ceph_config)
        # Use first zone's service as default
        ceph_service = next(iter(ceph_service_per_zone.values()))
    elif config.ceph_default:
        ceph_service = CephService(config.ceph_default)

    cloudstack_service = CloudStackService(config.cloudstack)
    snapshot_service = SnapshotService(
        ceph_service=ceph_service,
        cloudstack_service=cloudstack_service,
        audit_db=audit_db
    )

    # Attach services and models to app for access by routes
    app.user_db = user_db
    app.audit_db = audit_db
    app.ceph_service = ceph_service
    app.ceph_service_per_zone = ceph_service_per_zone
    app.cloudstack_service = cloudstack_service
    app.snapshot_service = snapshot_service
    app.config['ceph_configs'] = config.ceph_configs
    app.config['ceph_default'] = config.ceph_default

    # Register blueprints
    register_blueprints(app)

    # Register user loader
    @app.login_manager.user_loader
    def load_user(user_id):
        return user_db.get_user_by_id(int(user_id))

    # Core routes
    @app.route('/')
    def index():
        from flask_login import current_user
        if current_user.is_authenticated:
            return render_template('index.html')
        return render_template('login.html')

    # Template filters
    @app.template_filter('size_format')
    def size_format(value):
        if value is None or value == 0:
            return '0 B'
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(value)
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        return f'{size:.2f} {units[unit_index]}'

    return app
