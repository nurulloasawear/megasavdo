# orders_service/db.py
import sqlite3
from contextlib import contextmanager
from typing import Optional, List, Dict
import os
import logging

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrderDatabase:
    def __init__(self, db_path: str = 'orders.db'):
        self.db_path = os.path.join(os.path.dirname(__file__), db_path)
        self.init_db()

    @contextmanager
    def get_connection(self):
        """
        Xavfsiz tranzaksiya: commit yoki rollback
        """
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"DB tranzaksiya xatosi: {e}")
            raise
        finally:
            conn.close()

    def init_db(self):
        with self.get_connection() as conn:
            # 1. orders
            conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'created' 
                        CHECK(status IN ('created', 'confirmed', 'preparing', 'shipped', 'delivered', 'cancelled', 'refunded')),
                    total_amount DECIMAL(12,2) NOT NULL,
                    currency TEXT DEFAULT 'UZS',
                    shipping_address TEXT NOT NULL,
                    billing_address TEXT,
                    payment_method TEXT NOT NULL,
                    payment_status TEXT DEFAULT 'pending' 
                        CHECK(payment_status IN ('pending', 'paid', 'failed', 'refunded')),
                    tracking_code TEXT,
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
                )
            """)

            # 2. order_items
            conn.execute("""
                CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    product_name TEXT NOT NULL,
                    product_sku TEXT,
                    quantity INTEGER NOT NULL CHECK(quantity > 0),
                    unit_price DECIMAL(12,2) NOT NULL CHECK(unit_price >= 0),
                    total_price DECIMAL(12,2) NOT NULL CHECK(total_price >= 0),
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
                )
            """)

            # 3. order_status_history
            conn.execute("""
                CREATE TABLE IF NOT EXISTS order_status_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    changed_by INTEGER,
                    notes TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
                )
            """)

            # 4. refunds
            conn.execute("""
                CREATE TABLE IF NOT EXISTS refunds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    amount DECIMAL(12,2) NOT NULL CHECK(amount > 0),
                    reason TEXT NOT NULL,
                    status TEXT DEFAULT 'requested' 
                        CHECK(status IN ('requested', 'approved', 'rejected', 'processed')),
                    requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    processed_at DATETIME,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
                )
            """)

            # 5. indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_refunds_order ON refunds(order_id)")

            # 6. triggers
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS update_order_ts
                AFTER UPDATE ON orders FOR EACH ROW
                BEGIN
                    UPDATE orders SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
                END;
            """)

    # ========================
    # ORDER CRUD
    # ========================
    def create_order(
        self,
        user_id: int,
        items: List[Dict],
        shipping_address: str,
        billing_address: str,
        payment_method: str,
        notes: str = ""
    ) -> int:
        """
        Buyurtma yaratish (transaction ichida)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            total = sum(item['total_price'] for item in items)
            cursor.execute("""
                INSERT INTO orders 
                (user_id, total_amount, shipping_address, billing_address, payment_method, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, total, shipping_address, billing_address, payment_method, notes))
            order_id = cursor.lastrowid

            # order_items
            for item in items:
                cursor.execute("""
                    INSERT INTO order_items 
                    (order_id, product_id, product_name, product_sku, quantity, unit_price, total_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    order_id,
                    item['product_id'],
                    item['product_name'],
                    item.get('product_sku'),
                    item['quantity'],
                    item['unit_price'],
                    item['total_price']
                ))

            # status history
            cursor.execute("""
                INSERT INTO order_status_history (order_id, status, changed_by)
                VALUES (?, 'created', NULL)
            """, (order_id,))

            return order_id

    def get_order(self, order_id: int) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT o.*, u.username, u.email
                FROM orders o
                LEFT JOIN users u ON o.user_id = u.id
                WHERE o.id = ?
            """, (order_id,))
            row = cursor.fetchone()
            if not row:
                return None
            order = dict(row)

            # items
            cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
            order['items'] = [dict(r) for r in cursor.fetchall()]

            # status history
            cursor.execute("""
                SELECT * FROM order_status_history 
                WHERE order_id = ? ORDER BY timestamp
            """, (order_id,))
            order['status_history'] = [dict(r) for r in cursor.fetchall()]

            # refunds
            cursor.execute("SELECT * FROM refunds WHERE order_id = ? ORDER BY requested_at DESC", (order_id,))
            order['refunds'] = [dict(r) for r in cursor.fetchall()]

            return order

    def get_user_orders(self, user_id: int) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, status, total_amount, created_at, tracking_code, payment_status
                FROM orders WHERE user_id = ? ORDER BY created_at DESC
            """, (user_id,))
            return [dict(row) for row in cursor.fetchall()]

    def update_order_status(self, order_id: int, new_status: str, changed_by: int = None, notes: str = None) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
            if cursor.rowcount == 0:
                return False
            conn.execute("""
                INSERT INTO order_status_history (order_id, status, changed_by, notes)
                VALUES (?, ?, ?, ?)
            """, (order_id, new_status, changed_by, notes))
            return True

    def cancel_order(self, order_id: int, reason: str) -> bool:
        """
        Buyurtmani bekor qilish (status + history)
        """
        return self.update_order_status(order_id, 'cancelled', notes=reason)

    # ========================
    # REFUND
    # ========================
    def request_refund(self, order_id: int, amount: float, reason: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO refunds (order_id, amount, reason)
                VALUES (?, ?, ?)
            """, (order_id, amount, reason))
            return cursor.lastrowid

    def get_refunds(self, order_id: int) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM refunds WHERE order_id = ? ORDER BY requested_at DESC
            """, (order_id,))
            return [dict(row) for row in cursor.fetchall()]

    def approve_refund(self, refund_id: int, admin_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE refunds SET status = 'approved', processed_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'requested'
            """, (refund_id,))
            if cursor.rowcount == 0:
                return False
            # Order status → refunded
            cursor.execute("SELECT order_id FROM refunds WHERE id = ?", (refund_id,))
            order_id = cursor.fetchone()['order_id']
            self.update_order_status(order_id, 'refunded', admin_id, f"Refund #{refund_id} tasdiqlandi")
            return True

    # ========================
    # UTILS
    # ========================
    def get_order_stats(self) -> Dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status, COUNT(*) as count FROM orders GROUP BY status
            """)
            rows = cursor.fetchall()
            stats = {row['status']: row['count'] for row in rows}
            return {
                'created': stats.get('created', 0),
                'confirmed': stats.get('confirmed', 0),
                'preparing': stats.get('preparing', 0),
                'shipped': stats.get('shipped', 0),
                'delivered': stats.get('delivered', 0),
                'cancelled': stats.get('cancelled', 0),
                'refunded': stats.get('refunded', 0),
            }