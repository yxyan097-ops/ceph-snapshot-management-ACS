"""Flask-Login extension setup."""
from flask_login import LoginManager


def init_login_manager(app):
    """Initialize Flask-Login manager."""
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    app.login_manager = login_manager
    return login_manager
