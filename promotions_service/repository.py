# promotions_service/repository.py
from db import PromotionsDatabase
from typing import Dict, Optional, List
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
db = PromotionsDatabase()

# ========================
# PROMO CODE
# ========================
def validate_promo_code(code: str, cart_items: List[Dict], user_id: Optional[int] = None) -> Dict:
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM promo_codes 
            WHERE code = ? AND is_active = 1 
            AND (start_date IS NULL OR start_date <= CURRENT_TIMESTAMP)
            AND (end_date IS NULL OR end_date >= CURRENT_TIMESTAMP)
        """, (code,))
        row = cursor.fetchone()
        if not row:
            raise ValueError("Promo kod topilmadi yoki faol emas")
        
        promo = dict(row)
        if promo['max_uses'] and promo['used_count'] >= promo['max_uses']:
            raise ValueError("Promo kod chegarasiga yetdi")

        total = sum(item['price'] * item['quantity'] for item in cart_items)
        if total < promo['min_amount']:
            raise ValueError(f"Minimal {promo['min_amount']} so‘m kerak")

        # applies_to tekshirish
        if promo['applies_to'] != 'all':
            ids = json.loads(promo['applies_to_ids'] or '[]')
            valid = False
            if promo['applies_to'] == 'products':
                valid = any(item['product_id'] in ids for item in cart_items)
            elif promo['applies_to'] == 'categories':
                # keyin products_service dan
                valid = True
            elif promo['applies_to'] == 'users' and user_id in ids:
                valid = True
            if not valid:
                raise ValueError("Bu promo kod sizga mos emas")

        # Chegirma
        discount = 0
        if promo['discount_type'] == 'percent':
            discount = total * promo['discount_value'] / 100
        else:
            discount = min(promo['discount_value'], total)

        return {
            "promo_id": promo['id'],
            "code": promo['code'],
            "discount": discount,
            "new_total": total - discount
        }

def apply_promo_to_order(promo_id: int, order_id: int, user_id: int, discount: float):
    with db.get_connection() as conn:
        conn.execute("""
            INSERT INTO promo_usage_log (promo_code_id, user_id, order_id, discount_applied)
            VALUES (?, ?, ?, ?)
        """, (promo_id, user_id, order_id, discount))
        conn.execute("UPDATE promo_codes SET used_count = used_count + 1 WHERE id = ?", (promo_id,))

# ========================
# FLASH SALE
# ========================
def get_flash_sale_discount(product_id: int) -> Optional[float]:
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT discount_percent FROM flash_sales 
            WHERE is_active = 1 
            AND start_time <= CURRENT_TIMESTAMP 
            AND end_time >= CURRENT_TIMESTAMP
        """)
        rows = cursor.fetchall()
        for row in rows:
            sale = dict(row)
            product_ids = json.loads(sale.get('product_ids', '[]'))
            if product_id in product_ids:
                return sale['discount_percent']
        return None

# ========================
# LOYALTY
# ========================
def add_points(user_id: int, order_total: float):
    points = int(order_total / 1000)  # 1000 so‘m = 1 ball
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_points (user_id, points, total_spent) 
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                points = points + excluded.points,
                total_spent = total_spent + excluded.total_spent,
                last_updated = CURRENT_TIMESTAMP
        """, (user_id, points, order_total))
        
        # Tier yangilash
        cursor.execute("""
            SELECT id FROM loyalty_tiers 
            WHERE min_points <= (SELECT points FROM user_points WHERE user_id = ?)
            ORDER BY min_points DESC LIMIT 1
        """, (user_id,))
        tier_row = cursor.fetchone()
        tier_id = tier_row['id'] if tier_row else 1
        conn.execute("UPDATE user_points SET tier_id = ? WHERE user_id = ?", (tier_id, user_id))

# ========================
# GIFT CARD
# ========================
def validate_gift_card(code: str, amount: float) -> Dict:
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM gift_cards 
            WHERE code = ? AND is_active = 1 
            AND (expires_at IS NULL OR expires_at >= CURRENT_TIMESTAMP)
        """, (code,))
        row = cursor.fetchone()
        if not row:
            raise ValueError("Gift card topilmadi")
        card = dict(row)
        if card['balance'] < amount:
            raise ValueError(f"Yetarli balans yo‘q: {card['balance']} so‘m")
        return {
            "card_id": card['id'],
            "balance": card['balance'],
            "use_amount": min(amount, card['balance'])
        }

def deduct_gift_card(card_id: int, amount: float):
    with db.get_connection() as conn:
        conn.execute("""
            UPDATE gift_cards SET balance = balance - ? WHERE id = ?
        """, (amount, card_id))