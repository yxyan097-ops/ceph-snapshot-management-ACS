"""Utility decorators for routes."""
from functools import wraps
from flask import jsonify
from flask_login import current_user


def require_cleanup_permission(f):
    """Decorator to require cleanup permission."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': '需要登录'}), 401
        if not current_user.can_cleanup():
            return jsonify({'error': '权限不足'}), 403
        return f(*args, **kwargs)
    return decorated_function


def require_admin_permission(f):
    """Decorator to require admin permission."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': '需要登录'}), 401
        if not current_user.can_manage_users():
            return jsonify({'error': '权限不足'}), 403
        return f(*args, **kwargs)
    return decorated_function
