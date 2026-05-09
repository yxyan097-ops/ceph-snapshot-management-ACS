"""Ceph operations routes."""
from flask import Blueprint, jsonify
from flask_login import login_required

cleanup_bp = Blueprint('ceph', __name__)

# Module-level service placeholder
_ceph_service = None
_ceph_service_per_zone = {}
_app_config = None


def init_ceph(app):
    """Initialize ceph routes with app context."""
    global _ceph_service, _app_config
    _ceph_service = app.ceph_service
    _app_config = app.config


def get_ceph_service(zone_id: str = None):
    """Get the ceph service instance for a zone.

    Args:
        zone_id: The zone ID. If None, returns default service.

    Returns:
        CephService instance for the zone, or default service.
    """
    if zone_id and zone_id in _ceph_service_per_zone:
        return _ceph_service_per_zone[zone_id]
    return _ceph_service


def register_zone_ceph_service(zone_id: str, ceph_service):
    """Register a CephService instance for a zone.

    Args:
        zone_id: The zone ID
        ceph_service: The CephService instance
    """
    _ceph_service_per_zone[zone_id] = ceph_service


def get_zone_ceph_configs():
    """Get the ceph configurations per zone from app config.

    Returns:
        Dict of zone_id -> CephConfig
    """
    if _app_config:
        return _app_config.get('ceph_configs', {})
    return {}


@cleanup_bp.route('/api/ceph/volumes', methods=['GET'])
@login_required
def get_ceph_volumes():
    """Get all Ceph RBD volumes across pools."""
    ceph_service = get_ceph_service()
    if ceph_service is None:
        return jsonify({'error': 'Ceph 管理器未初始化'}), 500

    try:
        pools = ceph_service.list_pools()
        all_volumes = {}
        for pool in pools:
            volumes = ceph_service.list_volumes(pool)
            for vol in volumes:
                all_volumes[vol] = {'name': vol, 'pool': pool}
        return jsonify({'volumes': all_volumes})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
