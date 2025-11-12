# products_service/db.py
import sqlite3
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
import os

class ProductDatabase:
    def __init__(self, db_path: str = 'products.db'):
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
            # 1. categories
            conn.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    slug TEXT UNIQUE NOT NULL,
                    parent_id INTEGER,
                    description TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL
                )
            """)

            # 2. products
            conn.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    slug TEXT UNIQUE NOT NULL,
                    description TEXT,
                    short_description TEXT,
                    price DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                    old_price DECIMAL(12,2),
                    sku TEXT UNIQUE,
                    category_id INTEGER,
                    brand TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    in_stock BOOLEAN DEFAULT 1,
                    stock_quantity INTEGER DEFAULT 0,
                    weight_kg DECIMAL(8,3),
                    dimensions TEXT, -- '10x20x30'
                    warranty_months INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
                )
            """)

            # 3. product_attributes (rang, o'lcham, RAM, etc.)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS product_attributes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    attribute_name TEXT NOT NULL, -- 'color', 'size', 'RAM'
                    attribute_value TEXT NOT NULL, -- 'qizil', 'XL', '8GB'
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
                )
            """)

            # 4. inventory (ombor joylashuvi)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    warehouse_location TEXT, -- 'A-12', 'Toshkent-1'
                    quantity INTEGER DEFAULT 0,
                    reserved_quantity INTEGER DEFAULT 0,
                    last_restocked DATETIME,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
                )
            """)

            # 5. seo_meta
            conn.execute("""
                CREATE TABLE IF NOT EXISTS seo_meta (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER UNIQUE NOT NULL,
                    meta_title TEXT,
                    meta_description TEXT,
                    meta_keywords TEXT,
                    og_image TEXT,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
                )
            """)

            # 6. product_images
            conn.execute("""
                CREATE TABLE IF NOT EXISTS product_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    image_url TEXT NOT NULL,
                    alt_text TEXT,
                    is_main BOOLEAN DEFAULT 0,
                    sort_order INTEGER DEFAULT 0,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
                )
            """)

            # Trigger: updated_at
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS update_product_ts
                AFTER UPDATE ON products FOR EACH ROW
                BEGIN
                    UPDATE products SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
                END;
            """)

            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS update_category_ts
                AFTER UPDATE ON categories FOR EACH ROW
                BEGIN
                    UPDATE categories SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
                END;
            """)

    # ========================
    # CATEGORY CRUD
    # ========================
    def create_category(self, name: str, slug: str, parent_id: Optional[int] = None, description: str = "") -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO categories (name, slug, parent_id, description)
                VALUES (?, ?, ?, ?)
            """, (name, slug, parent_id, description))
            return cursor.lastrowid

    def get_category_by_id(self, category_id: int) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_categories(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM categories WHERE is_active = 1 ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]

    # ========================
    # PRODUCT CRUD
    # ========================
    def create_product(self, name: str, slug: str, price: float, category_id: Optional[int] = None, **kwargs) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            fields = ['name', 'slug', 'price', 'category_id']
            values = [name, slug, price, category_id]
            placeholders = ['?', '?', '?', '?']

            optional_fields = {
                'description': kwargs.get('description'),
                'short_description': kwargs.get('short_description'),
                'old_price': kwargs.get('old_price'),
                'sku': kwargs.get('sku'),
                'brand': kwargs.get('brand'),
                'stock_quantity': kwargs.get('stock_quantity', 0),
                'weight_kg': kwargs.get('weight_kg'),
                'dimensions': kwargs.get('dimensions'),
                'warranty_months': kwargs.get('warranty_months', 0)
            }

            for field, value in optional_fields.items():
                if value is not None:
                    fields.append(field)
                    values.append(value)
                    placeholders.append('?')

            sql = f"INSERT INTO products ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
            cursor.execute(sql, values)
            product_id = cursor.lastrowid

            # Avto inventory yaratish
            conn.execute("""
                INSERT INTO inventory (product_id, quantity) VALUES (?, ?)
            """, (product_id, kwargs.get('stock_quantity', 0)))

            return product_id

    def get_product_by_id(self, product_id: int) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.*, c.name as category_name, i.quantity as stock_available
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                LEFT JOIN inventory i ON p.id = i.product_id
                WHERE p.id = ? AND p.is_active = 1
            """, (product_id,))
            row = cursor.fetchone()
            if not row:
                return None
            product = dict(row)

            # Atributlar
            cursor.execute("SELECT attribute_name, attribute_value FROM product_attributes WHERE product_id = ?", (product_id,))
            product['attributes'] = [dict(r) for r in cursor.fetchall()]

            # Rasmlar
            cursor.execute("SELECT image_url, alt_text, is_main FROM product_images WHERE product_id = ? ORDER BY sort_order", (product_id,))
            product['images'] = [dict(r) for r in cursor.fetchall()]

            return product

    def get_all_products(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.*, c.name as category_name, i.quantity as stock_available
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                LEFT JOIN inventory i ON p.id = i.product_id
                WHERE p.is_active = 1
                ORDER BY p.created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            rows = cursor.fetchall()
            products = []
            for row in rows:
                product = dict(row)
                pid = product['id']
                cursor.execute("SELECT attribute_name, attribute_value FROM product_attributes WHERE product_id = ?", (pid,))
                product['attributes'] = [dict(r) for r in cursor.fetchall()]
                products.append(product)
            return products

    def search_products(self, query: str, category_id: Optional[int] = None, min_price: Optional[float] = None, max_price: Optional[float] = None) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            sql = """
                SELECT p.*, c.name as category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.is_active = 1
                AND (p.name LIKE ? OR p.description LIKE ? OR p.sku LIKE ?)
            """
            params = [f"%{query}%", f"%{query}%", f"%{query}%"]

            if category_id:
                sql += " AND p.category_id = ?"
                params.append(category_id)
            if min_price is not None:
                sql += " AND p.price >= ?"
                params.append(min_price)
            if max_price is not None:
                sql += " AND p.price <= ?"
                params.append(max_price)

            sql += " ORDER BY p.name LIMIT 20"

            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    # ========================
    # ATTRIBUTE & IMAGE
    # ========================
    def add_attribute(self, product_id: int, name: str, value: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO product_attributes (product_id, attribute_name, attribute_value)
                VALUES (?, ?, ?)
            """, (product_id, name, value))
            return cursor.rowcount > 0

    def add_image(self, product_id: int, image_url: str, alt_text: str = "", is_main: bool = False, sort_order: int = 0) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO product_images (product_id, image_url, alt_text, is_main, sort_order)
                VALUES (?, ?, ?, ?, ?)
            """, (product_id, image_url, alt_text, 1 if is_main else 0, sort_order))
            return cursor.rowcount > 0

    # ========================
    # INVENTORY
    # ========================
    def update_stock(self, product_id: int, quantity: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE inventory SET quantity = ?, updated_at = CURRENT_TIMESTAMP
                WHERE product_id = ?
            """, (quantity, product_id))
            return cursor.rowcount > 0