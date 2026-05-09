"""Routes package - registers all blueprints."""
from flask import Flask

from ceph_snapshot_manager.routes.auth import auth_bp
from ceph_snapshot_manager.routes.volumes import volumes_bp
from ceph_snapshot_manager.routes.snapshots import snapshots_bp
from ceph_snapshot_manager.routes.cleanup import cleanup_bp
from ceph_snapshot_manager.routes.ceph import cleanup_bp as ceph_bp
from ceph_snapshot_manager.routes.audit import audit_bp


def register_blueprints(app: Flask) -> None:
    """Register all blueprints with the Flask app.

    Args:
        app: Flask application instance
    """
    # Initialize modules with app context
    from ceph_snapshot_manager.routes.auth import init_auth
    from ceph_snapshot_manager.routes.volumes import init_volumes
    from ceph_snapshot_manager.routes.snapshots import init_snapshots
    from ceph_snapshot_manager.routes.cleanup import init_cleanup
    from ceph_snapshot_manager.routes.ceph import init_ceph
    from ceph_snapshot_manager.routes.audit import init_audit

    init_auth(app)
    init_volumes(app)
    init_snapshots(app)
    init_cleanup(app)
    init_ceph(app)
    init_audit(app)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(volumes_bp)
    app.register_blueprint(snapshots_bp)
    app.register_blueprint(cleanup_bp)
    app.register_blueprint(ceph_bp)
    app.register_blueprint(audit_bp)
