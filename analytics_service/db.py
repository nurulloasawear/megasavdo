# analytics_service/db.py
import sqlite3
from contextlib import contextmanager
from typing import List, Dict
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AnalyticsDB")

class AnalyticsDatabase:
    def __init__(self, db_path: str = 'analytics.db'):
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
            # 1. daily_stats
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY,
                    total_orders INTEGER DEFAULT 0,
                    total_revenue DECIMAL(15,2) DEFAULT 0,
                    new_users INTEGER DEFAULT 0,
                    active_users INTEGER DEFAULT 0,
                    top_product_id INTEGER,
                    top_product_name TEXT,
                    top_product_sales INTEGER
                )
            """)

            # 2. product_views (keyin frontenddan)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS product_views (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    user_id INTEGER,
                    viewed_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. cache for fast queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_views_product ON product_views(product_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_views_date ON product_views(viewed_at)")