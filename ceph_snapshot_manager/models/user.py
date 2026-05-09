"""User model and database operations."""
import sqlite3
import bcrypt
from flask_login import UserMixin
from typing import Optional, List


class User(UserMixin):
    """User domain model with role-based permissions."""

    def __init__(self, user_id: int, username: str, password_hash: str, role: str = 'viewer'):
        self.id = user_id
        self.username = username
        self.password_hash = password_hash
        self.role = role

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def check_password(self, password: str) -> bool:
        """Verify a password against the stored hash."""
        return bcrypt.checkpw(password.encode(), self.password_hash.encode())

    def can_cleanup(self) -> bool:
        """Check if user can perform cleanup operations."""
        return self.role in ('admin', 'operator')

    def can_view(self) -> bool:
        """Check if user can view resources."""
        return True

    def can_manage_users(self) -> bool:
        """Check if user can manage other users."""
        return self.role == 'admin'


class UserDB:
    """User persistence layer using SQLite."""

    def __init__(self, db_path: str = 'users.db'):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the users table."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'viewer'
                )
            ''')

    def get_user(self, username: str) -> Optional[User]:
        """Get user by username."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT id, username, password_hash, role FROM users WHERE username = ?',
                (username,)
            )
            row = cursor.fetchone()
            if row:
                return User(row[0], row[1], row[2], row[3])
        return None

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT id, username, password_hash, role FROM users WHERE id = ?',
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                return User(row[0], row[1], row[2], row[3])
        return None

    def create_user(self, username: str, password: str, role: str = 'viewer') -> None:
        """Create a new user."""
        password_hash = User.hash_password(password)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                (username, password_hash, role)
            )
            conn.commit()

    def delete_user(self, user_id: int) -> None:
        """Delete a user by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.commit()

    def list_users(self) -> List[dict]:
        """List all users (without password hashes)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT id, username, role FROM users')
            return [{'id': r[0], 'username': r[1], 'role': r[2]} for r in cursor.fetchall()]
