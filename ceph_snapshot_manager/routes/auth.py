"""Authentication routes."""
from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user

auth_bp = Blueprint('auth', __name__)

# Module-level service placeholders (set during app initialization)
_user_db = None


def init_auth(app):
    """Initialize auth routes with app context."""
    global _user_db
    _user_db = app.user_db

    @auth_bp.record
    def on_register(state):
        """Load user loader after registration."""
        from flask_login import login_manager
        login_manager = state.app.login_manager

        @login_manager.user_loader
        def load_user(user_id):
            return _user_db.get_user_by_id(int(user_id))


def get_user_db():
    """Get the user database instance."""
    return _user_db


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """Login endpoint."""
    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'success': False, 'error': '用户名和密码不能为空'}), 400

    user = get_user_db().get_user(username)
    if user and user.check_password(password):
        login_user(user)
        return jsonify({
            'success': True,
            'user': {'username': user.username, 'role': user.role}
        })

    return jsonify({'success': False, 'error': '用户名或密码错误'}), 401


@auth_bp.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    """Logout endpoint."""
    logout_user()
    return jsonify({'success': True})


@auth_bp.route('/api/auth/current_user', methods=['GET'])
def get_current_user():
    """Get current user info."""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': {'username': current_user.username, 'role': current_user.role}
        })
    return jsonify({'authenticated': False})


@auth_bp.route('/api/auth/users', methods=['GET'])
@login_required
def list_users():
    """List all users (admin only)."""
    if not current_user.can_manage_users():
        return jsonify({'error': '权限不足'}), 403
    return jsonify({'users': get_user_db().list_users()})


@auth_bp.route('/api/auth/users', methods=['POST'])
@login_required
def create_user():
    """Create a new user (admin only)."""
    if not current_user.can_manage_users():
        return jsonify({'error': '权限不足'}), 403

    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')
    role = data.get('role', 'viewer')

    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400

    try:
        get_user_db().create_user(username, password, role)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': f'创建用户失败: {str(e)}'}), 400


@auth_bp.route('/api/auth/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    """Delete a user (admin only)."""
    if not current_user.can_manage_users():
        return jsonify({'error': '权限不足'}), 403

    if user_id == current_user.id:
        return jsonify({'error': '不能删除当前登录用户'}), 400

    get_user_db().delete_user(user_id)
    return jsonify({'success': True})
