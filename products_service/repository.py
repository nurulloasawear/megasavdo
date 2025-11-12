# products_service/repository.py
from db import ProductDatabase
from typing import List, Dict, Optional, Any
import logging

# Logging sozlash
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global DB instance
db = ProductDatabase()

# ========================
# CATEGORY OPERATIONS
# ========================
def create_category(name: str, slug: str, parent_id: Optional[int] = None, description: str = "") -> int:
    """
    Yangi kategoriya yaratadi
    """
    try:
        return db.create_category(name, slug, parent_id, description)
    except Exception as e:
        logger.error(f"Kategoriya yaratishda xato: {e}")
        raise ValueError("Kategoriya yaratib bo'lmadi")

def get_category(category_id: int) -> Optional[Dict]:
    return db.get_category_by_id(category_id)

def get_categories() -> List[Dict]:
    return db.get_all_categories()

# ========================
# PRODUCT OPERATIONS
# ========================
def create_product(
    name: str,
    slug: str,
    price: float,
    category_id: Optional[int] = None,
    description: str = "",
    short_description: str = "",
    old_price: Optional[float] = None,
    sku: Optional[str] = None,
    brand: Optional[str] = None,
    stock_quantity: int = 0,
    weight_kg: Optional[float] = None,
    dimensions: Optional[str] = None,
    warranty_months: int = 0
) -> int:
    """
    Yangi mahsulot yaratadi + inventory avto yaratadi
    """
    if price < 0:
        raise ValueError("Narx manfiy bo'lishi mumkin emas")
    if stock_quantity < 0:
        raise ValueError("Stock miqdori manfiy bo'lishi mumkin emas")

    try:
        return db.create_product(
            name=name,
            slug=slug,
            price=price,
            category_id=category_id,
            description=description,
            short_description=short_description,
            old_price=old_price,
            sku=sku,
            brand=brand,
            stock_quantity=stock_quantity,
            weight_kg=weight_kg,
            dimensions=dimensions,
            warranty_months=warranty_months
        )
    except Exception as e:
        logger.error(f"Mahsulot yaratishda xato: {e}")
        raise ValueError("Mahsulot yaratib bo'lmadi")

def get_product(product_id: int) -> Optional[Dict]:
    """
    To'liq mahsulot ma'lumoti: atributlar, rasmlar, stock
    """
    return db.get_product_by_id(product_id)

def get_products_by_ids(product_ids: List[int]) -> List[Dict]:
    """
    Bir nechta mahsulotni ID bo'yicha olish
    """
    if not product_ids:
        return []
    return db.get_products_by_ids(product_ids)  # db.py ga qo'shiladi

# ========================
# ATTRIBUTE & IMAGE
# ========================
def add_product_attribute(product_id: int, name: str, value: str) -> bool:
    """
    Mahsulotga atribut qo'shish
    """
    if not name or not value:
        raise ValueError("Atribut nomi va qiymati bo'sh bo'lmasligi kerak")
    return db.add_attribute(product_id, name, value)

def add_product_image(
    product_id: int,
    image_url: str,
    alt_text: str = "",
    is_main: bool = False,
    sort_order: int = 0
) -> bool:
    """
    Mahsulotga rasm qo'shish
    """
    if not image_url:
        raise ValueError("Rasm URL bo'sh bo'lmasligi kerak")
    return db.add_image(product_id, image_url, alt_text, is_main, sort_order)

# ========================
# STOCK OPERATIONS (XAVFSIZ, TRANSACTION)
# ========================
def check_stock(items: List[Dict]) -> List[Dict]:
    """
    Stockni tekshirish (free_stock = quantity - reserved)
    """
    results = []
    with db.get_connection() as conn:
        cursor = conn.cursor()
        for item in items:
            pid = item['product_id']
            qty = item['quantity']
            if qty <= 0:
                results.append({
                    'product_id': pid,
                    'available': 0,
                    'reserved': 0,
                    'free_stock': 0,
                    'requested': qty,
                    'in_stock': False,
                    'message': "Miqdor nol yoki manfiy"
                })
                continue

            cursor.execute("""
                SELECT quantity, COALESCE(reserved_quantity, 0) as reserved 
                FROM inventory WHERE product_id = ?
            """, (pid,))
            row = cursor.fetchone()
            available = row['quantity'] if row else 0
            reserved = row['reserved'] if row else 0
            free_stock = available - reserved
            in_stock = free_stock >= qty

            results.append({
                'product_id': pid,
                'available': available,
                'reserved': reserved,
                'free_stock': free_stock,
                'requested': qty,
                'in_stock': in_stock,
                'message': f"{free_stock} dona mavjud" if not in_stock else "Yeterli"
            })
    return results

def reserve_stock(items: List[Dict]) -> bool:
    """
    Buyurtma uchun stockni bron qilish (transaction bilan)
    """
    with db.get_connection() as conn:
        cursor = conn.cursor()
        try:
            for item in items:
                pid = item['product_id']
                qty = item['quantity']
                cursor.execute("""
                    UPDATE inventory 
                    SET reserved_quantity = reserved_quantity + ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE product_id = ? 
                      AND (quantity - reserved_quantity) >= ?
                """, (qty, pid, qty))
                if cursor.rowcount == 0:
                    raise ValueError(f"Stock yetarli emas: product_id={pid}")
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Stock bron qilishda xato: {e}")
            raise

def release_stock(items: List[Dict]) -> bool:
    """
    Bronni bekor qilish
    """
    with db.get_connection() as conn:
        cursor = conn.cursor()
        try:
            for item in items:
                pid = item['product_id']
                qty = item['quantity']
                cursor.execute("""
                    UPDATE inventory 
                    SET reserved_quantity = GREATEST(reserved_quantity - ?, 0),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE product_id = ?
                """, (qty, pid))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Stock bekor qilishda xato: {e}")
            raise

def update_stock_admin(product_id: int, new_quantity: int) -> bool:
    """
    Admin tomonidan stockni o'zgartirish
    """
    if new_quantity < 0:
        raise ValueError("Stock miqdori manfiy bo'lishi mumkin emas")
    return db.update_stock(product_id, new_quantity)

# ========================
# SEARCH & UTILS
# ========================
def get_low_stock_products(threshold: int = 10) -> List[Dict]:
    """
    Qoldig'i kam mahsulotlar
    """
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id, p.name, p.sku, i.quantity, COALESCE(i.reserved_quantity, 0) as reserved
            FROM products p
            JOIN inventory i ON p.id = i.product_id
            WHERE (i.quantity - COALESCE(i.reserved_quantity, 0)) <= ? AND p.is_active = 1
            ORDER BY (i.quantity - COALESCE(i.reserved_quantity, 0))
        """, (threshold,))
        return [dict(row) for row in cursor.fetchall()]

def search_products(
    query: Optional[str] = None,
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock_only: bool = False,
    limit: int = 20,
    offset: int = 0
) -> List[Dict]:
    """
    Qidiruv + filter
    """
    sql = """
        SELECT p.*, c.name as category_name, 
               i.quantity, COALESCE(i.reserved_quantity, 0) as reserved_quantity
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN inventory i ON p.id = i.product_id
        WHERE p.is_active = 1
    """
    params = []
    conditions = []

    if query:
        conditions.append("(p.name LIKE ? OR p.description LIKE ? OR p.sku LIKE ?)")
        params.extend([f"%{query}%"] * 3)
    if category_id:
        conditions.append("p.category_id = ?")
        params.append(category_id)
    if min_price is not None:
        conditions.append("p.price >= ?")
        params.append(min_price)
    if max_price is not None:
        conditions.append("p.price <= ?")
        params.append(max_price)
    if in_stock_only:
        conditions.append("(i.quantity - COALESCE(i.reserved_quantity, 0)) > 0")

    if conditions:
        sql += " AND " + " AND ".join(conditions)

    sql += " ORDER BY p.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        products = []
        for row in rows:
            p = dict(row)
            pid = p['id']
            cursor.execute("SELECT attribute_name, attribute_value FROM product_attributes WHERE product_id = ?", (pid,))
            p['attributes'] = [dict(r) for r in cursor.fetchall()]
            products.append(p)
        return products