# cart_service/db.py
import sqlite3
from contextlib import contextmanager
from typing import Optional, List, Dict
import os
import logging
import json

# ========================
# LOGGING
# ========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("CartDB")

class CartDatabase:
    def __init__(self, db_path: str = 'cart.db'):
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
        conn.execute("PRAGMA synchronous = NORMAL;")
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
            # 1. carts (user_id NULL → guest, session_id bor)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS carts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,                     -- NULL = guest
                    session_id TEXT NOT NULL,            -- UUID yoki random
                    status TEXT DEFAULT 'active'         -- active, checkout, abandoned
                        CHECK(status IN ('active', 'checkout', 'abandoned', 'merged')),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME,                 -- guest uchun
                    UNIQUE(session_id),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # 2. cart_items
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cart_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cart_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    variant_id INTEGER,                  -- rang, razmer
                    quantity INTEGER NOT NULL CHECK(quantity > 0),
                    price DECIMAL(12,2) NOT NULL,        -- saqlangan narx (snapshot)
                    discount_price DECIMAL(12,2),        -- chegirma narxi
                    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cart_id) REFERENCES carts(id) ON DELETE CASCADE,
                    FOREIGN KEY (product_id) REFERENCES products(id),
                    UNIQUE(cart_id, product_id, variant_id)
                )
            """)

            # 3. cart_activity_log
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cart_activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cart_id INTEGER NOT NULL,
                    action TEXT NOT NULL,                -- add, remove, update, view
                    product_id INTEGER,
                    quantity INTEGER,
                    metadata TEXT,                       -- JSON: old_price, source
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cart_id) REFERENCES carts(id) ON DELETE CASCADE
                )
            """)

            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_carts_user ON carts(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_carts_session ON carts(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_carts_status ON carts(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cart_items_cart ON cart_items(cart_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cart_items_product ON cart_items(product_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_cart ON cart_activity_log(cart_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_action ON cart_activity_log(action)")

            # Trigger: updated_at
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS update_cart_ts
                AFTER UPDATE ON carts FOR EACH ROW
                BEGIN
                    UPDATE carts SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
                END;
            """)

            # Trigger: expires_at for guest (1 soat)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS set_cart_expiry
                AFTER INSERT ON carts WHEN NEW.user_id IS NULL
                BEGIN
                    UPDATE carts SET expires_at = datetime('now', '+1 hour') WHERE id = NEW.id;
                END;
            """)

    # ========================
    # CART CRUD
    # ========================
    def create_cart(self, user_id: Optional[int], session_id: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO carts (user_id, session_id)
                VALUES (?, ?)
            """, (user_id, session_id))
            return cursor.lastrowid

    def get_cart_by_session(self, session_id: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM carts WHERE session_id = ? AND status = 'active'
            """, (session_id,))
            row = cursor.fetchone()
            if not row:
                return None
            cart = dict(row)
            cart['items'] = self.get_cart_items(cart['id'])
            return cart

    def get_cart_by_user(self, user_id: int) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM carts WHERE user_id = ? AND status = 'active'
            """, (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            cart = dict(row)
            cart['items'] = self.get_cart_items(cart['id'])
            return cart

    def merge_carts(self, guest_session_id: str, user_id: int) -> int:
        """Login bo‘lganda guest savatni user savatiga birlashtirish"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Guest cart
            cursor.execute("SELECT id FROM carts WHERE session_id = ? AND status = 'active'", (guest_session_id,))
            guest_row = cursor.fetchone()
            if not guest_row:
                return 0
            guest_cart_id = guest_row['id']

            # User cart
            cursor.execute("SELECT id FROM carts WHERE user_id = ? AND status = 'active'", (user_id,))
            user_row = cursor.fetchone()
            if not user_row:
                # User cart yaratish
                cursor.execute("INSERT INTO carts (user_id, session_id) VALUES (?, ?)", (user_id, guest_session_id))
                user_cart_id = cursor.lastrowid
            else:
                user_cart_id = user_row['id']

            # Guest items → user cart
            cursor.execute("""
                INSERT OR REPLACE INTO cart_items (cart_id, product_id, variant_id, quantity, price, discount_price)
                SELECT ?, product_id, variant_id, quantity, price, discount_price
                FROM cart_items WHERE cart_id = ?
            """, (user_cart_id, guest_cart_id))

            # Guest cartni yopish
            conn.execute("UPDATE carts SET status = 'merged' WHERE id = ?", (guest_cart_id,))
            return user_cart_id

    # ========================
    # CART ITEMS
    # ========================
    def get_cart_items(self, cart_id: int) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ci.*, p.name as product_name, p.image_url
                FROM cart_items ci
                JOIN products p ON ci.product_id = p.id
                WHERE ci.cart_id = ?
            """, (cart_id,))
            return [dict(row) for row in cursor.fetchall()]

    def add_item(self, cart_id: int, product_id: int, variant_id: Optional[int], quantity: int, price: float, discount_price: Optional[float] = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cart_items (cart_id, product_id, variant_id, quantity, price, discount_price)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(cart_id, product_id, variant_id) DO UPDATE SET
                    quantity = quantity + excluded.quantity
            """, (cart_id, product_id, variant_id, quantity, price, discount_price or price))
            item_id = cursor.lastrowid or cursor.execute("""
                SELECT id FROM cart_items WHERE cart_id = ? AND product_id = ? AND variant_id = ?
            """, (cart_id, product_id, variant_id)).fetchone()['id']

            # Log
            conn.execute("""
                INSERT INTO cart_activity_log (cart_id, action, product_id, quantity, metadata)
                VALUES (?, 'add', ?, ?, ?)
            """, (cart_id, product_id, quantity, json.dumps({"price": price, "discount": discount_price})))
            return item_id

    def update_quantity(self, item_id: int, quantity: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT cart_id, product_id FROM cart_items WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            if not row:
                return False
            cursor.execute("""
                UPDATE cart_items SET quantity = ? WHERE id = ?
            """, (quantity, item_id))
            conn.execute("""
                INSERT INTO cart_activity_log (cart_id, action, product_id, quantity)
                VALUES (?, 'update', ?, ?)
            """, (row['cart_id'], row['product_id'], quantity))
            return True

    def remove_item(self, item_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT cart_id, product_id FROM cart_items WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            if not row:
                return False
            cursor.execute("DELETE FROM cart_items WHERE id = ?", (item_id,))
            conn.execute("""
                INSERT INTO cart_activity_log (cart_id, action, product_id)
                VALUES (?, 'remove', ?)
            """, (row['cart_id'], row['product_id']))
            return True

    def clear_cart(self, cart_id: int) -> bool:
        with self.get_connection() as conn:
            conn.execute("DELETE FROM cart_items WHERE cart_id = ?", (cart_id,))
            conn.execute("UPDATE carts SET status = 'checkout' WHERE id = ?", (cart_id,))
            return True

    # ========================
    # UTILS
    # ========================
    def get_cart_summary(self, cart_id: int) -> Dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as items_count,
                    SUM(quantity) as total_quantity,
                    SUM(CASE WHEN discount_price IS NOT NULL THEN discount_price * quantity ELSE price * quantity END) as total_price
                FROM cart_items WHERE cart_id = ?
            """, (cart_id,))
            row = cursor.fetchone()
            return dict(row) if row else {"items_count": 0, "total_quantity": 0, "total_price": 0}

    def cleanup_expired_carts(self):
        """Har 10 daqiqada ishlaydi"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE carts SET status = 'abandoned'
                WHERE user_id IS NULL AND expires_at < CURRENT_TIMESTAMP AND status = 'active'
            """)