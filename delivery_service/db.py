# delivery_service/db.py
import sqlite3
from contextlib import contextmanager
from typing import Optional, List, Dict
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DeliveryDB")

class DeliveryDatabase:
    def __init__(self, db_path: str = 'delivery.db'):
        self.db_path = os.path.join(os.path.dirname(__file__), db_path)
        self.init_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"DB xato: {e}")
            raise
        finally:
            conn.close()

    def init_db(self):
        with self.get_connection() as conn:
            # 1. delivery_methods
            conn.execute("""
                CREATE TABLE IF NOT EXISTS delivery_methods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    price DECIMAL(10,2) DEFAULT 0,
                    estimated_days TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. addresses
            conn.execute("""
                CREATE TABLE IF NOT EXISTS addresses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    full_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    region TEXT NOT NULL,
                    city TEXT NOT NULL,
                    address_line TEXT NOT NULL,
                    postal_code TEXT,
                    is_default BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            # 3. order_deliveries
            conn.execute("""
                CREATE TABLE IF NOT EXISTS order_deliveries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL UNIQUE,
                    method_id INTEGER NOT NULL,
                    address_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending', 'confirmed', 'in_transit', 'delivered', 'failed', 'returned')),
                    tracking_code TEXT,
                    estimated_delivery TEXT,
                    delivered_at DATETIME,
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                    FOREIGN KEY (method_id) REFERENCES delivery_methods(id),
                    FOREIGN KEY (address_id) REFERENCES addresses(id)
                )
            """)

            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_addresses_user ON addresses(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_deliveries_order ON order_deliveries(order_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_deliveries_status ON order_deliveries(status)")

            # Default methods
            defaults = [
                ('courier', 'Kuryer orqali', 25000, '1-3 kun', 1),
                ('pickup', 'O‘zim olib ketaman', 0, 'Bugun', 1),
                ('post', 'Pochta orqali', 15000, '3-7 kun', 1),
            ]
            conn.executemany("""
                INSERT OR IGNORE INTO delivery_methods (name, display_name, price, estimated_days, is_active)
                VALUES (?, ?, ?, ?, ?)
            """, defaults)