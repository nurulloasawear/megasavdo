# payments_service/db.py
import sqlite3
from contextlib import contextmanager
from typing import Optional, List, Dict
import os
import logging
import json
# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PaymentsDB")

class PaymentDatabase:
    def __init__(self, db_path: str = 'payments.db'):
        self.db_path = os.path.join(os.path.dirname(__file__), db_path)
        self.init_db()

    @contextmanager
    def get_connection(self):
        """
        Xavfsiz tranzaksiya: commit yoki rollback
        """
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
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
            # 1. payment_methods
            conn.execute("""
                CREATE TABLE IF NOT EXISTS payment_methods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE CHECK(name IN ('card', 'cash', 'click', 'payme', 'uzum')),
                    display_name TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    config TEXT,  -- JSON: {"api_key": "..."}
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. payments
            conn.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    method_id INTEGER NOT NULL,
                    amount DECIMAL(12,2) NOT NULL CHECK(amount > 0),
                    currency TEXT DEFAULT 'UZS',
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending', 'paid', 'failed', 'refunded', 'cancelled')),
                    gateway_transaction_id TEXT,
                    gateway_response TEXT,  -- JSON
                    payer_info TEXT,        -- JSON: email, phone
                    error_message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE RESTRICT,
                    FOREIGN KEY (method_id) REFERENCES payment_methods(id)
                )
            """)

            # 3. payment_logs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS payment_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payment_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT,
                    metadata TEXT,  -- JSON
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE CASCADE
                )
            """)

            # 4. refunds
            conn.execute("""
                CREATE TABLE IF NOT EXISTS refunds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payment_id INTEGER NOT NULL,
                    amount DECIMAL(12,2) NOT NULL CHECK(amount > 0),
                    reason TEXT,
                    status TEXT DEFAULT 'requested'
                        CHECK(status IN ('requested', 'approved', 'rejected', 'processed')),
                    gateway_refund_id TEXT,
                    requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    processed_at DATETIME,
                    FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE CASCADE
                )
            """)

            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_order ON payments(order_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_method ON payments(method_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_refunds_payment ON refunds(payment_id)")

            # Trigger: updated_at
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS update_payment_ts
                AFTER UPDATE ON payments FOR EACH ROW
                BEGIN
                    UPDATE payments SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
                END;
            """)

            # Default payment methods
            default_methods = [
                ('card', 'Karta orqali', 1, '{}'),
                ('cash', 'Naqd pul', 1, '{}'),
                ('click', 'Click', 1, '{"api_url": "https://api.click.uz"}'),
                ('payme', 'Payme', 1, '{"merchant_id": "12345"}'),
                ('uzum', 'Uzum Bank', 1, '{}'),
            ]
            conn.executemany("""
                INSERT OR IGNORE INTO payment_methods (name, display_name, is_active, config)
                VALUES (?, ?, ?, ?)
            """, default_methods)

    # ========================
    # PAYMENT CRUD
    # ========================
    def create_payment(
        self,
        order_id: int,
        method_id: int,
        amount: float,
        payer_info: Dict = None
    ) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO payments (order_id, method_id, amount, payer_info)
                VALUES (?, ?, ?, ?)
            """, (order_id, method_id, amount, json.dumps(payer_info or {})))
            payment_id = cursor.lastrowid

            # Log
            conn.execute("""
                INSERT INTO payment_logs (payment_id, status, message)
                VALUES (?, 'pending', 'To\'lov yaratildi')
            """, (payment_id,))

            return payment_id

    def get_payment(self, payment_id: int) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.*, m.name as method_name, m.display_name
                FROM payments p
                JOIN payment_methods m ON p.method_id = m.id
                WHERE p.id = ?
            """, (payment_id,))
            row = cursor.fetchone()
            if not row:
                return None
            payment = dict(row)
            payment['payer_info'] = json.loads(payment['payer_info']) if payment['payer_info'] else {}

            # Logs
            cursor.execute("SELECT * FROM payment_logs WHERE payment_id = ? ORDER BY timestamp", (payment_id,))
            payment['logs'] = [dict(r) for r in cursor.fetchall()]

            # Refunds
            cursor.execute("SELECT * FROM refunds WHERE payment_id = ? ORDER BY requested_at DESC", (payment_id,))
            payment['refunds'] = [dict(r) for r in cursor.fetchall()]

            return payment

    def update_payment_status(
        self,
        payment_id: int,
        new_status: str,
        gateway_transaction_id: str = None,
        gateway_response: Dict = None,
        error_message: str = None
    ) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE payments 
                SET status = ?, 
                    gateway_transaction_id = ?, 
                    gateway_response = ?, 
                    error_message = ?
                WHERE id = ?
            """, (
                new_status,
                gateway_transaction_id,
                json.dumps(gateway_response) if gateway_response else None,
                error_message,
                payment_id
            ))
            if cursor.rowcount == 0:
                return False

            # Log
            message = f"Status: {new_status}"
            if error_message:
                message += f" | Xato: {error_message}"
            conn.execute("""
                INSERT INTO payment_logs (payment_id, status, message, metadata)
                VALUES (?, ?, ?, ?)
            """, (
                payment_id,
                new_status,
                message,
                json.dumps(gateway_response) if gateway_response else None
            ))
            return True

    def get_payments_by_order(self, order_id: int) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.id, p.status, p.amount, p.created_at, m.display_name
                FROM payments p
                JOIN payment_methods m ON p.method_id = m.id
                WHERE p.order_id = ? ORDER BY p.created_at DESC
            """, (order_id,))
            return [dict(row) for row in cursor.fetchall()]

    # ========================
    # REFUND
    # ========================
    def request_refund(self, payment_id: int, amount: float, reason: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO refunds (payment_id, amount, reason)
                VALUES (?, ?, ?)
            """, (payment_id, amount, reason))
            return cursor.lastrowid

    def process_refund(self, refund_id: int, status: str, gateway_refund_id: str = None) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE refunds 
                SET status = ?, gateway_refund_id = ?, processed_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'requested'
            """, (status, gateway_refund_id, refund_id))
            return cursor.rowcount > 0

    # ========================
    # UTILS
    # ========================
    def get_active_methods(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, display_name FROM payment_methods WHERE is_active = 1")
            return [dict(row) for row in cursor.fetchall()]

    def get_payment_stats(self) -> Dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, COUNT(*) FROM payments GROUP BY status")
            rows = cursor.fetchall()
            stats = {r['status']: r['COUNT(*)'] for r in rows}
            return {
                'pending': stats.get('pending', 0),
                'paid': stats.get('paid', 0),
                'failed': stats.get('failed', 0),
                'refunded': stats.get('refunded', 0),
            }