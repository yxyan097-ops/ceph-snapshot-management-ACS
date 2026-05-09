"""Audit log routes."""
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user

from ceph_snapshot_manager.utils.decorators import require_admin_permission

audit_bp = Blueprint('audit', __name__)

# Module-level service placeholder
_audit_db = None


def init_audit(app):
    """Initialize audit routes with app context."""
    global _audit_db
    _audit_db = app.audit_db


def get_audit_db():
    """Get the audit database instance."""
    return _audit_db


@audit_bp.route('/api/audit/logs', methods=['GET'])
@login_required
def get_audit_logs():
    """Get audit logs with pagination."""
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    try:
        logs = get_audit_db().get_logs(limit=limit, offset=offset)
        total = get_audit_db().count_logs()
        return jsonify({'logs': logs, 'total': total})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@audit_bp.route('/api/audit/logs', methods=['POST'])
@login_required
def add_audit_log():
    """Add a new audit log entry."""
    data = request.get_json()
    action = data.get('action', '')
    zone_id = data.get('zone_id')
    volume_id = data.get('volume_id')
    volume_name = data.get('volume_name')
    snapshot_name = data.get('snapshot_name')
    keep_count = data.get('keep_count')
    dry_run = data.get('dry_run')
    result = data.get('result', 'success')
    message = data.get('message', '')

    try:
        get_audit_db().add_log(
            username=current_user.username,
            action=action,
            zone_id=zone_id,
            volume_id=volume_id,
            volume_name=volume_name,
            snapshot_name=snapshot_name,
            keep_count=keep_count,
            dry_run=dry_run,
            result=result,
            message=message
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@audit_bp.route('/api/audit/clear', methods=['POST'])
@login_required
@require_admin_permission
def clear_audit_logs():
    """Clear all audit logs (admin only)."""
    try:
        get_audit_db().clear_logs()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@audit_bp.route('/audit')
@login_required
def audit_page():
    """Render the audit page."""
    return render_template('audit.html')
