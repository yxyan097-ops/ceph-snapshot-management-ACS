"""Volume and zone routes."""
from flask import Blueprint, jsonify
from flask_login import login_required, current_user

volumes_bp = Blueprint('volumes', __name__)

# Module-level service placeholders
_snapshot_service = None


def init_volumes(app):
    """Initialize volumes routes with app context."""
    global _snapshot_service
    _snapshot_service = app.snapshot_service


def get_snapshot_service():
    """Get the snapshot service instance."""
    return _snapshot_service


@volumes_bp.route('/api/zones', methods=['GET'])
@login_required
def get_zones():
    """Get all CloudStack zones."""
    try:
        zones = get_snapshot_service().get_zones()
        return jsonify({'zones': zones})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@volumes_bp.route('/api/zones/<zone_id>/volumes', methods=['GET'])
@login_required
def get_zone_volumes(zone_id):
    """Get volumes in a zone with snapshot counts."""
    try:
        volumes = get_snapshot_service().get_volumes_with_snapshot_counts(zone_id)
        # Filter for DATADISK or ROOT types
        volumes = [v for v in volumes if v.get('type') in ('DATADISK', 'ROOT')]
        return jsonify({'volumes': volumes})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@volumes_bp.route('/api/volumes/<volume_id>/snapshots', methods=['GET'])
@login_required
def get_volume_snapshots(volume_id):
    """Get CloudStack snapshots for a volume."""
    try:
        snapshots = get_snapshot_service().get_cloudstack_snapshots(volume_id)
        return jsonify({'snapshots': snapshots})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@volumes_bp.route('/api/volumes/<volume_id>/ceph_snapshots', methods=['GET'])
@login_required
def get_ceph_snapshots(volume_id):
    """Get Ceph RBD snapshots for a volume."""
    try:
        snapshots = get_snapshot_service().get_volume_snapshots(volume_id)
        return jsonify({'snapshots': snapshots})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
