# promotions_service/db.py
import sqlite3
from contextlib import contextmanager
from typing import Optional, List, Dict
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PromoDB")

class PromotionsDatabase:
    def __init__(self, db_path: str = 'promotions.db'):
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
            # 1. promo_codes
            conn.execute("""
                CREATE TABLE IF NOT EXISTS promo_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    discount_type TEXT NOT NULL CHECK(discount_type IN ('percent', 'fixed')),
                    discount_value DECIMAL(10,2) NOT NULL,
                    min_amount DECIMAL(12,2) DEFAULT 0,
                    max_uses INTEGER,
                    used_count INTEGER DEFAULT 0,
                    applies_to TEXT CHECK(applies_to IN ('all', 'products', 'categories', 'users')),
                    applies_to_ids TEXT, -- JSON: [1,2,3]
                    start_date DATETIME,
                    end_date DATETIME,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. flash_sales
            conn.execute("""
                CREATE TABLE IF NOT EXISTS flash_sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    discount_percent DECIMAL(5,2) NOT NULL,
                    product_ids TEXT NOT NULL, -- JSON
                    start_time DATETIME NOT NULL,
                    end_time DATETIME NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. loyalty_tiers
            conn.execute("""
                CREATE TABLE IF NOT EXISTS loyalty_tiers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    min_points INTEGER NOT NULL,
                    multiplier DECIMAL(3,2) DEFAULT 1.0,
                    benefits TEXT -- JSON
                )
            """)

            # 4. user_points
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_points (
                    user_id INTEGER PRIMARY KEY,
                    points INTEGER DEFAULT 0,
                    tier_id INTEGER,
                    total_spent DECIMAL(15,2) DEFAULT 0,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tier_id) REFERENCES loyalty_tiers(id)
                )
            """)

            # 5. gift_cards
            conn.execute("""
                CREATE TABLE IF NOT EXISTS gift_cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    balance DECIMAL(12,2) NOT NULL,
                    initial_amount DECIMAL(12,2) NOT NULL,
                    user_id INTEGER,
                    expires_at DATETIME,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            # 6. promo_usage_log
            conn.execute("""
                CREATE TABLE IF NOT EXISTS promo_usage_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    promo_code_id INTEGER,
                    user_id INTEGER,
                    order_id INTEGER,
                    discount_applied DECIMAL(12,2),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (promo_code_id) REFERENCES promo_codes(id)
                )
            """)

            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_promo_code ON promo_codes(code)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_promo_active ON promo_codes(is_active)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_flash_active ON flash_sales(is_active)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_points ON user_points(user_id)")

            # Default loyalty tiers
            conn.executemany("""
                INSERT OR IGNORE INTO loyalty_tiers (name, min_points, multiplier)
                VALUES (?, ?, ?)
            """, [
                ('Bronze', 0, 1.0),
                ('Silver', 1000, 1.1),
                ('Gold', 5000, 1.2),
                ('Platinum', 20000, 1.5)
            ])