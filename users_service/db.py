# db.py
import sqlite3
from contextlib import contextmanager
import bcrypt
from typing import Optional, List, Dict, Any

class Database:
    def __init__(self, db_path: str = 'users.db'):
        self.db_path = db_path
        self.init_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row 
        try:
            yield conn 
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def init_db(self):
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    phone_number TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

   
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS update_user_timestamp
                AFTER UPDATE ON users
                FOR EACH ROW
                BEGIN
                    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
                END;
            """)

    def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    def add_user(self, username: str, name: str, role: str, phone_number: str, password: str, email: str) -> int:
        hashed = self.hash_password(password)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, name, role, phone_number, password_hash, email)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (username, name, role, phone_number, hashed, email))
            return cursor.lastrowid

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_users(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def update_user(self, user_id: int, **kwargs) -> bool:
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        # Admin bo'lsa — hamma maydonni o'zgartirishi mumkin
        # Oddiy user — faqat o'zini
        is_admin = user['role'] == 'admin'
        allowed = {'username', 'name', 'phone_number', 'email', 'status', 'role'} if is_admin else {'username', 'name', 'phone_number', 'email'}

        updates = {}
        for k, v in kwargs.items():
            if k in allowed:
                updates[k] = v
            if k == 'password':
                updates['password_hash'] = self.hash_password(v)

        if not updates:
            return False

        fields = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [user_id]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE users SET {fields} WHERE id = ?", values)
            return cursor.rowcount > 0

    def deactivate_user(self, user_id: int) -> bool:
        return self.update_user(user_id, status='inactive')

    def delete_user(self, user_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            return cursor.rowcount > 0