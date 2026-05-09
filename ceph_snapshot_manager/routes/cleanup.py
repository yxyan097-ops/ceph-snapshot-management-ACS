"""Cleanup operation routes."""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from ceph_snapshot_manager.utils.decorators import require_cleanup_permission

cleanup_bp = Blueprint('cleanup', __name__)

# Module-level service placeholder
_ceph_service = None
_ceph_service_per_zone = {}


def init_cleanup(app):
    """Initialize cleanup routes with app context."""
    global _ceph_service, _ceph_service_per_zone
    _ceph_service = app.ceph_service
    _ceph_service_per_zone = getattr(app, 'ceph_service_per_zone', {})


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


@cleanup_bp.route('/api/cleanup', methods=['POST'])
@login_required
@require_cleanup_permission
def cleanup():
    """Cleanup snapshots for a volume."""
    data = request.get_json()
    zone_id = data.get('zone_id')
    zone_name = data.get('zone_name')
    disk_id = data.get('disk_id')
    keep_count = data.get('keep_count', 3)
    dry_run = data.get('dry_run', True)

    if not disk_id:
        return jsonify({'error': 'disk_id 不能为空'}), 400

    ceph_service = get_ceph_service(zone_name)
    if ceph_service is None:
        return jsonify({'error': 'Ceph 管理器未初始化'}), 500

    try:
        # Get snapshot service for audit logging
        snapshot_service = get_snapshot_service()
        result = snapshot_service.cleanup_snapshots(
            disk_id=disk_id,
            keep_count=keep_count,
            dry_run=dry_run,
            zone_id=zone_id,
            zone_name=zone_name,
            username=current_user.username,
            client_ip=request.remote_addr
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def get_snapshot_service():
    """Get the snapshot service instance."""
    from ceph_snapshot_manager.routes.volumes import get_snapshot_service as _get
    return _get()


@cleanup_bp.route('/api/health', methods=['GET'])
@login_required
def health():
    """Check Ceph cluster health and operation readiness.

    Query params:
        zone_name: Optional zone name to check specific cluster health
    """
    zone_name = request.args.get('zone_name')
    ceph_service = get_ceph_service(zone_name)

    if ceph_service is None:
        return jsonify({'healthy': False, 'can_proceed': False, 'error': 'Ceph 管理器未初始化'})

    try:
        health_result = ceph_service.check_health()
        can_proceed, proceed_msg = ceph_service.check_can_proceed()

        response = health_result.to_dict()
        response['can_proceed'] = can_proceed
        response['proceed_message'] = proceed_msg
        return jsonify(response)
    except Exception as e:
        return jsonify({'healthy': False, 'can_proceed': False, 'error': str(e)}), 500
