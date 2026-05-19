"""User model and database operations - MySQL version."""
from typing import Optional, List
import bcrypt
from flask_login import UserMixin
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool


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

    def can_manage_config(self) -> bool:
        """Check if user can manage application config."""
        return self.role == 'admin'

    def can_manage_keys(self) -> bool:
        """Check if user can manage SSH keys."""
        return self.role == 'admin'


class UserDB:
    """User persistence layer using MySQL."""

    def __init__(self, database_url: str = None):
        import os
        self.database_url = database_url or os.environ.get(
            'DATABASE_URL',
            'mysql+pymysql://root:password@localhost:3306/ceph_snapshot'
        )
        self._engine = None

    @property
    def engine(self):
        if self._engine is None:
            self._engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=5,
                pool_recycle=3600
            )
        return self._engine

    def get_user(self, username: str) -> Optional[User]:
        """Get user by username."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT id, username, password_hash, role FROM users WHERE username = :username"),
                {"username": username}
            )
            row = result.fetchone()
            if row:
                return User(row[0], row[1], row[2], row[3])
        return None

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT id, username, password_hash, role FROM users WHERE id = :id"),
                {"id": user_id}
            )
            row = result.fetchone()
            if row:
                return User(row[0], row[1], row[2], row[3])
        return None

    def create_user(self, username: str, password: str, role: str = 'viewer') -> None:
        """Create a new user."""
        password_hash = User.hash_password(password)
        with self.engine.connect() as conn:
            conn.execute(
                text("INSERT INTO users (username, password_hash, role) VALUES (:username, :hash, :role)"),
                {"username": username, "hash": password_hash, "role": role}
            )
            conn.commit()

    def update_user(self, user_id: int, password: str = None, role: str = None) -> None:
        """Update user password and/or role."""
        with self.engine.connect() as conn:
            if password and role:
                password_hash = User.hash_password(password)
                conn.execute(
                    text("UPDATE users SET password_hash = :hash, role = :role WHERE id = :id"),
                    {"hash": password_hash, "role": role, "id": user_id}
                )
            elif password:
                password_hash = User.hash_password(password)
                conn.execute(
                    text("UPDATE users SET password_hash = :hash WHERE id = :id"),
                    {"hash": password_hash, "id": user_id}
                )
            elif role:
                conn.execute(
                    text("UPDATE users SET role = :role WHERE id = :id"),
                    {"role": role, "id": user_id}
                )
            conn.commit()

    def delete_user(self, user_id: int) -> None:
        """Delete a user by ID."""
        with self.engine.connect() as conn:
            conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
            conn.commit()

    def list_users(self) -> List[dict]:
        """List all users (without password hashes)."""
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT id, username, role, created_at FROM users"))
            return [
                {'id': row[0], 'username': row[1], 'role': row[2], 'created_at': str(row[3])}
                for row in result.fetchall()
            ]
