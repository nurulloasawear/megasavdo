# delivery_service/repository.py
from db import DeliveryDatabase
from typing import List, Dict, Optional
import requests
import logging

logger = logging.getLogger(__name__)
db = DeliveryDatabase()

ORDERS_URL = "https://localhost:8445/graphql"

def _call_orders(query: str, variables: Dict = None) -> Dict:
    try:
        resp = requests.post(ORDERS_URL, json={"query": query, "variables": variables or {}}, verify=False, timeout=5)
        resp.raise_for_status()
        return resp.json().get('data', {})
    except Exception as e:
        logger.error(f"Orders xizmati xatosi: {e}")
        raise ValueError("Buyurtma xizmati ishlamayapti")

# ========================
# DELIVERY METHODS
# ========================
def get_delivery_methods() -> List[Dict]:
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, display_name, price, estimated_days FROM delivery_methods WHERE is_active = 1")
        return [dict(row) for row in cursor.fetchall()]

# ========================
# ADDRESSES
# ========================
def save_address(user_id: int, data: Dict) -> int:
    with db.get_connection() as conn:
        cursor = conn.cursor()
        if data.get('is_default'):
            conn.execute("UPDATE addresses SET is_default = 0 WHERE user_id = ?", (user_id,))
        cursor.execute("""
            INSERT INTO addresses (user_id, full_name, phone, region, city, address_line, postal_code, is_default)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, data['full_name'], data['phone'], data['region'],
            data['city'], data['address_line'], data.get('postal_code'), data.get('is_default', 0)
        ))
        return cursor.lastrowid

def get_user_addresses(user_id: int) -> List[Dict]:
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM addresses WHERE user_id = ? ORDER BY is_default DESC", (user_id,))
        return [dict(row) for row in cursor.fetchall()]

# ========================
# ORDER DELIVERY
# ========================
def create_delivery(order_id: int, method_id: int, address_id: int, notes: str = "") -> int:
    # Buyurtma mavjudligini tekshirish
    query = """query($id: Int!) { order(id: $id) { id status } }"""
    data = _call_orders(query, {"id": order_id})
    if not data.get('order'):
        raise ValueError("Buyurtma topilmadi")
    if data['order']['status'] not in ['created', 'confirmed']:
        raise ValueError("Yetkazib berish faqat yaratilgan yoki tasdiqlangan buyurtma uchun")

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO order_deliveries (order_id, method_id, address_id, notes)
            VALUES (?, ?, ?, ?)
        """, (order_id, method_id, address_id, notes))
        return cursor.lastrowid

def update_delivery_status(delivery_id: int, status: str, tracking_code: str = None) -> bool:
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE order_deliveries 
            SET status = ?, tracking_code = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, tracking_code, delivery_id))
        return cursor.rowcount > 0

def get_delivery(delivery_id: int) -> Optional[Dict]:
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT d.*, m.display_name, a.*
            FROM order_deliveries d
            JOIN delivery_methods m ON d.method_id = m.id
            JOIN addresses a ON d.address_id = a.id
            WHERE d.id = ?
        """, (delivery_id,))
        row = cursor.fetchone()
        return dict(row) if row else None