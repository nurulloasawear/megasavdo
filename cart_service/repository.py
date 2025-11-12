# cart_service/repository.py
from db import CartDatabase
from typing import Dict, Optional, List
import requests
import logging
import json
import uuid
from datetime import datetime

# ========================
# LOGGING
# ========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("CartRepo")

# ========================
# XIZMATLAR URLlari (API Gateway orqali)
# ========================
SERVICES = {
    "products": "https://localhost:8447/graphql",   # API Gateway
    "promotions": "https://localhost:8447/graphql",
    "inventory": "https://localhost:8447/graphql",
    "users": "https://localhost:8447/graphql",
}

# ========================
# DB
# ========================
db = CartDatabase()

# ========================
# HELPER: API Gateway orqali so'rov
# ========================
def _call_gateway(query: str, variables: Dict = None) -> Dict:
    try:
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        resp = requests.post(
            SERVICES["products"],  # bitta endpoint
            json=payload,
            verify=False,
            timeout=5
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("errors"):
            logger.warning(f"Gateway xato: {data['errors']}")
            return {}
        return data.get("data", {})
    except Exception as e:
        logger.error(f"Gateway aloqa xatosi: {e}")
        raise ValueError("Xizmatlar bilan aloqa uzildi")

# ========================
# CART OPERATSIYALARI
# ========================
def create_or_get_cart(user_id: Optional[int], session_id: str) -> Dict:
    """
    Savat yaratish yoki mavjudini olish
    """
    if user_id:
        cart = db.get_cart_by_user(user_id)
        if cart:
            return cart
        # Yangi user savati
        cart_id = db.create_cart(user_id, session_id)
    else:
        cart = db.get_cart_by_session(session_id)
        if cart:
            return cart
        # Yangi guest savati
        cart_id = db.create_cart(None, session_id)

    return db.get_cart_by_session(session_id) or db.get_cart_by_user(user_id)

def merge_guest_cart(guest_session_id: str, user_id: int) -> Dict:
    """
    Login bo‘lganda guest savatni user savatiga birlashtirish
    """
    new_cart_id = db.merge_carts(guest_session_id, user_id)
    return db.get_cart_by_user(user_id) if new_cart_id else {}

# ========================
# MAHSULOT NARXI & STOCK
# ========================
def get_product_price_and_stock(product_id: int, variant_id: Optional[int] = None) -> Dict:
    """
    products_service dan real-time narx va stock
    """
    query = """
    query($id: Int!, $variant: Int) {
      product(id: $id) {
        id
        name
        price
        discount_price
        stock
        variants(variant_id: $variant) {
          id
          price
          discount_price
          stock
        }
      }
    }
    """
    data = _call_gateway(query, {"id": product_id, "variant": variant_id})
    product = data.get("product", {})
    
    if not product:
        raise ValueError("Mahsulot topilmadi")

    # Variant bo‘lsa
    if variant_id and product.get("variants"):
        variant = product["variants"][0]
        return {
            "name": product["name"],
            "price": variant["price"],
            "discount_price": variant["discount_price"],
            "stock": variant["stock"]
        }
    
    return {
        "name": product["name"],
        "price": product["price"],
        "discount_price": product["discount_price"],
        "stock": product["stock"]
    }

# ========================
# CHEGIRMA (promotions_service)
# ========================
def apply_promo_code(cart_id: int, promo_code: str) -> Dict:
    """
    Promo kod tekshirish va chegirma qo‘llash
    """
    # 1. Promo kod mavjudligi
    query = """
    query($code: String!) {
      promotion(code: $code) {
        id
        discount_type
        discount_value
        min_amount
        applies_to
      }
    }
    """
    data = _call_gateway(query, {"code": promo_code})
    promo = data.get("promotion")
    if not promo:
        raise ValueError("Noto‘g‘ri promo kod")

    # 2. Savat summasi
    summary = db.get_cart_summary(cart_id)
    if summary["total_price"] < promo["min_amount"]:
        raise ValueError(f"Minimal {promo['min_amount']} so‘m kerak")

    # 3. Chegirma hisoblash
    discount = 0
    if promo["discount_type"] == "percent":
        discount = summary["total_price"] * promo["discount_value"] / 100
    else:
        discount = promo["discount_value"]

    # 4. Yangi total
    new_total = max(0, summary["total_price"] - discount)

    return {
        "promo_id": promo["id"],
        "discount": discount,
        "new_total": new_total,
        "message": f"{promo['discount_value']}% chegirma qo‘llandi"
    }

# ========================
# ADD TO CART
# ========================
def add_to_cart(
    user_id: Optional[int],
    session_id: str,
    product_id: int,
    variant_id: Optional[int],
    quantity: int = 1
) -> Dict:
    """
    Savatga mahsulot qo‘shish
    """
    # 1. Mahsulot ma'lumotlari
    product = get_product_price_and_stock(product_id, variant_id)
    if product["stock"] < quantity:
        raise ValueError(f"Yetarli qoldiq yo‘q: {product['stock']} dona bor")

    # 2. Savatni olish/yaratish
    cart = create_or_get_cart(user_id, session_id)

    # 3. Narx snapshot
    price = product["discount_price"] or product["price"]

    # 4. DB ga yozish
    item_id = db.add_item(
        cart_id=cart["id"],
        product_id=product_id,
        variant_id=variant_id,
        quantity=quantity,
        price=price,
        discount_price=product["discount_price"]
    )

    # 5. Summary
    summary = db.get_cart_summary(cart["id"])

    logger.info(f"Savatga qo‘shildi: product_id={product_id}, quantity={quantity}, cart_id={cart['id']}")

    return {
        "cart_id": cart["id"],
        "item_id": item_id,
        "product_name": product["name"],
        "quantity": quantity,
        "price": price,
        "total_items": summary["items_count"],
        "total_price": summary["total_price"]
    }

# ========================
# UPDATE / REMOVE
# ========================
def update_cart_item(item_id: int, quantity: int) -> Dict:
    if quantity <= 0:
        return remove_from_cart(item_id)
    
    success = db.update_quantity(item_id, quantity)
    if not success:
        raise ValueError("Element topilmadi")

    # Summary qaytarish
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT cart_id FROM cart_items WHERE id = ?", (item_id,))
        cart_id = cursor.fetchone()["cart_id"]
    summary = db.get_cart_summary(cart_id)

    return {
        "success": True,
        "quantity": quantity,
        "total_price": summary["total_price"]
    }

def remove_from_cart(item_id: int) -> Dict:
    success = db.remove_item(item_id)
    if not success:
        raise ValueError("Element topilmadi")

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT cart_id FROM cart_items WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        cart_id = row["cart_id"] if row else None

    summary = db.get_cart_summary(cart_id) if cart_id else {"total_price": 0}

    return {
        "success": True,
        "removed": True,
        "total_price": summary["total_price"]
    }

# ========================
# GET CART
# ========================
def get_cart(user_id: Optional[int], session_id: str) -> Dict:
    cart = create_or_get_cart(user_id, session_id)
    summary = db.get_cart_summary(cart["id"])

    return {
        "cart_id": cart["id"],
        "items": cart["items"],
        "summary": summary,
        "is_guest": user_id is None
    }

# ========================
# CHECKOUT PREPARE
# ========================
def prepare_checkout(cart_id: int) -> Dict:
    """
    Checkout oldidan tekshirish
    """
    items = db.get_cart_items(cart_id)
    if not items:
        raise ValueError("Savat bo‘sh")

    # Har bir mahsulotni real-time tekshirish
    total = 0
    invalid_items = []

    for item in items:
        try:
            current = get_product_price_and_stock(item["product_id"], item.get("variant_id"))
            if current["stock"] < item["quantity"]:
                invalid_items.append({
                    "product_id": item["product_id"],
                    "requested": item["quantity"],
                    "available": current["stock"]
                })
            price = current["discount_price"] or current["price"]
            total += price * item["quantity"]
        except:
            invalid_items.append({"product_id": item["product_id"], "error": "Topilmadi"})

    if invalid_items:
        raise ValueError(f"Qoldiq yetarli emas: {invalid_items}")

    # Savatni checkout holatiga o‘tkazish
    db.clear_cart(cart_id)

    return {
        "cart_id": cart_id,
        "items": items,
        "total_amount": total,
        "currency": "UZS",
        "status": "ready_for_checkout"
    }

# ========================
# UTILS
# ========================
def generate_session_id() -> str:
    return str(uuid.uuid4())

def cleanup_expired():
    """Cron job uchun"""
    db.cleanup_expired_carts()
    logger.info("Eski guest savatlari tozalandi")