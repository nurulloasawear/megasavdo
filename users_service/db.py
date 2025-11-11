# users_service/db.py
import sqlite3
from contextlib import contextmanager
import bcrypt
from typing import Optional, List, Dict, Any
import os

class UserDatabase:
    def __init__(self, db_path: str = 'users.db'):
        self.db_path = os.path.join(os.path.dirname(__file__), db_path)
        self.init_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self):
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    phone_number TEXT UNIQUE NOT NULL,
                    role TEXT NOT NULL DEFAULT 'customer' CHECK(role IN ('customer', 'admin', 'courier', 'warehouse')),
                    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'inactive', 'banned')),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    action TEXT NOT NULL CHECK(action IN (
                        'view', 'wishlist_add', 'wishlist_remove',
                        'compare_add', 'compare_remove', 'cart_add', 'cart_remove'
                    )),
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS loyalty (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    points INTEGER DEFAULT 0 CHECK(points >= 0),
                    tier TEXT DEFAULT 'bronze' CHECK(tier IN ('bronze', 'silver', 'gold', 'platinum')),
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    entity TEXT NOT NULL,
                    entity_id INTEGER,
                    details TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS update_user_ts
                AFTER UPDATE ON users FOR EACH ROW
                BEGIN
                    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
                END;
            """)

    # ========================
    # HASHING
    # ========================
    def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def verify_password(self, password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    # ========================
    # USER CRUD
    # ========================
    def create_user(self, username: str, name: str, email: str, phone_number: str, password: str, role: str = 'customer') -> int:
        hashed = self.hash_password(password)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, name, email, phone_number, password_hash, role)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (username, name, email, phone_number, hashed, role))
            user_id = cursor.lastrowid

            # Avto loyalty yaratish
            conn.execute("INSERT INTO loyalty (user_id, points, tier) VALUES (?, 0, 'bronze')", (user_id,))
            return user_id

    # def get_user_by_id(self, user_id: int) -> Optional[Dict]:
    #     with self.get_connection() as conn:
    #         cursor = conn.cursor()
    #         cursor.execute("""
    #             SELECT u.*, l.points, l.tier 
    #             FROM users u 
    #             LEFT JOIN loyalty l ON u.id = l.user_id 
    #             WHERE u.id = ?
    #         """, (user_id,))
    #         row = cursor.fetchone()
    #         return dict(row) if row else None
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            if row:
                return {k: row[k] for k in row.keys()}
            return None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.*, l.points, l.tier 
                FROM users u 
                LEFT JOIN loyalty l ON u.id = l.user_id 
                WHERE u.id = ?
            """, (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None  # <--- dict(row)

    def get_all_users(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.*, l.points, l.tier 
                FROM users u 
                LEFT JOIN loyalty l ON u.id = l.user_id 
                ORDER BY u.created_at DESC
            """)
            rows = cursor.fetchall()
            print([dict(row) for row in rows])
            return [dict(row) for row in rows]

    def update_user(self, user_id: int, **kwargs) -> bool:
        user = self.get_user_by_id(user_id)
        if not user: return False

        allowed = {'username', 'name', 'email', 'phone_number', 'status'}
        if user['role'] == 'admin':
            allowed.update({'role'})

        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if 'password' in kwargs:
            updates['password_hash'] = self.hash_password(kwargs['password'])

        if not updates: return False

        fields = ', '.join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [user_id]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE users SET {fields} WHERE id = ?", values)
            return cursor.rowcount > 0

    def deactivate_user(self, user_id: int) -> bool:
        return self.update_user(user_id, status='inactive')

    def ban_user(self, user_id: int) -> bool:
        return self.update_user(user_id, status='banned')

    # ========================
    # USER ACTIVITY
    # ========================
    def add_user_activity(self, user_id: int, product_id: int, action: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_activity (user_id, product_id, action)
                VALUES (?, ?, ?)
            """, (user_id, product_id, action))
            return cursor.rowcount > 0

    def get_wishlist(self, user_id: int) -> List[int]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT product_id FROM user_activity 
                WHERE user_id = ? AND action = 'wishlist_add'
            """, (user_id,))
            return [row['product_id'] for row in cursor.fetchall()]

    # ========================
    # LOYALTY
    # ========================
    def add_points(self, user_id: int, points: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE loyalty SET points = points + ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (points, user_id))
            return cursor.rowcount > 0

    # ========================
    # AUDIT LOG
    # ========================
    def log_action(self, user_id: int, action: str, entity: str, entity_id: int = None, details: str = None):
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO audit_log (user_id, action, entity, entity_id, details)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, action, entity, entity_id, details))