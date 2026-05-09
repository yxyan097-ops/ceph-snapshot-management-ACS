"""Snapshot operation routes."""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from ceph_snapshot_manager.utils.decorators import require_cleanup_permission

snapshots_bp = Blueprint('snapshots', __name__)

# Module-level service placeholders
_snapshot_service = None


def init_snapshots(app):
    """Initialize snapshots routes with app context."""
    global _snapshot_service
    _snapshot_service = app.snapshot_service


def get_snapshot_service():
    """Get the snapshot service instance."""
    return _snapshot_service


def _get_client_ip():
    """Extract client IP from request."""
    return request.remote_addr or 'unknown'


@snapshots_bp.route('/api/snapshots/delete', methods=['POST'])
@login_required
@require_cleanup_permission
def delete_snapshot():
    """Delete a Ceph snapshot."""
    data = request.get_json()
    volume_id = data.get('volume_id')
    snapshot_name = data.get('snapshot_name')
    dry_run = data.get('dry_run', True)
    zone_id = data.get('zone_id')
    zone_name = data.get('zone_name')

    if not volume_id or not snapshot_name:
        return jsonify({'error': 'volume_id 和 snapshot_name 不能为空'}), 400

    try:
        result = get_snapshot_service().delete_snapshot(
            volume_id=volume_id,
            snapshot_name=snapshot_name,
            dry_run=dry_run,
            username=current_user.username,
            zone_id=zone_id,
            zone_name=zone_name,
            client_ip=_get_client_ip()
        )

        # For dry run, add the command info
        if dry_run:
            result['dry_run'] = True
            result['message'] = result.get('output', '')
            result['command'] = f"rbd snap rm {volume_id}@{snapshot_name}"

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@snapshots_bp.route('/api/snapshots/create', methods=['POST'])
@login_required
@require_cleanup_permission
def create_snapshot():
    """Create a new Ceph snapshot."""
    data = request.get_json()
    volume_id = data.get('volume_id')
    snapshot_name = data.get('snapshot_name')
    zone_id = data.get('zone_id')
    zone_name = data.get('zone_name')

    if not volume_id or not snapshot_name:
        return jsonify({'error': 'volume_id 和 snapshot_name 不能为空'}), 400

    try:
        result = get_snapshot_service().create_snapshot(
            volume_id=volume_id,
            snapshot_name=snapshot_name,
            username=current_user.username,
            zone_id=zone_id,
            zone_name=zone_name,
            client_ip=_get_client_ip()
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@snapshots_bp.route('/api/snapshots/protect', methods=['POST'])
@login_required
@require_cleanup_permission
def protect_snapshot():
    """Protect a Ceph snapshot."""
    data = request.get_json()
    volume_id = data.get('volume_id')
    snapshot_name = data.get('snapshot_name')
    zone_id = data.get('zone_id')
    zone_name = data.get('zone_name')

    if not volume_id or not snapshot_name:
        return jsonify({'error': 'volume_id 和 snapshot_name 不能为空'}), 400

    try:
        result = get_snapshot_service().protect_snapshot(
            volume_id=volume_id,
            snapshot_name=snapshot_name,
            username=current_user.username,
            zone_id=zone_id,
            zone_name=zone_name,
            client_ip=_get_client_ip()
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@snapshots_bp.route('/api/snapshots/unprotect', methods=['POST'])
@login_required
@require_cleanup_permission
def unprotect_snapshot():
    """Unprotect a Ceph snapshot."""
    data = request.get_json()
    volume_id = data.get('volume_id')
    snapshot_name = data.get('snapshot_name')
    zone_id = data.get('zone_id')
    zone_name = data.get('zone_name')

    if not volume_id or not snapshot_name:
        return jsonify({'error': 'volume_id 和 snapshot_name 不能为空'}), 400

    try:
        result = get_snapshot_service().unprotect_snapshot(
            volume_id=volume_id,
            snapshot_name=snapshot_name,
            username=current_user.username,
            zone_id=zone_id,
            zone_name=zone_name,
            client_ip=_get_client_ip()
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
