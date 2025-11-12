# orders_service/repository.py
from db import OrderDatabase
from typing import List, Dict, Optional, Any
import requests
import logging

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global DB
db = OrderDatabase()

# Microservices URL
PRODUCTS_URL = "https://localhost:8444/graphql"
USERS_URL = "https://localhost:8443/graphql"

# ========================
# HELPER: API CALL
# ========================
def _graphql_request(url: str, query: str, variables: Dict = None) -> Dict:
    """
    Xavfsiz GraphQL so'rov
    """
    try:
        resp = requests.post(
            url,
            json={"query": query, "variables": variables or {}},
            verify=False,
            timeout=5
        )
        resp.raise_for_status()
        data = resp.json()
        if 'errors' in data:
            raise ValueError(f"API xato: {data['errors']}")
        return data['data']
    except Exception as e:
        logger.error(f"API so'rov xatosi ({url}): {e}")
        raise ValueError(f"Xizmat bilan bog'lanib bo'lmadi: {url.split('/')[-2]}")

# ========================
# USER VALIDATION
# ========================
def _validate_user(user_id: int) -> Dict:
    """
    users_service dan user ma'lumotlarini olish
    """
    query = """
    query ($id: Int!) {
        user(id: $id) {
            id username email
        }
    }
    """
    data = _graphql_request(USERS_URL, query, {"id": user_id})
    user = data.get('user')
    if not user:
        raise ValueError("Foydalanuvchi topilmadi")
    return user

# ========================
# PRODUCT & STOCK VALIDATION
# ========================
def _validate_and_enrich_items(items: List[Dict]) -> tuple[List[Dict], float]:
    """
    products_service dan:
    - Mahsulot mavjudligi
    - Narx
    - Stock yetarliligi
    - Ma'lumotlar bilan boyitish
    """
    product_ids = [item['product_id'] for item in items]
    if not product_ids:
        raise ValueError("Buyurtma bo'sh")

    # 1. Mahsulotlarni olish
    ids_str = ",".join(map(str, product_ids))
    query = f"""
    query {{
        productsByIds(ids: [{ids_str}]) {{
            id name price sku stockAvailable reservedQuantity
        }}
    }}
    """
    data = _graphql_request(PRODUCTS_URL, query)
    products = {p['id']: p for p in data['productsByIds']}
    
    if len(products) != len(product_ids):
        missing = set(product_ids) - set(products.keys())
        raise ValueError(f"Mahsulot topilmadi: {missing}")

    # 2. Stock tekshirish
    stock_items = [{"product_id": i['product_id'], "quantity": i['quantity']} for i in items]
    stock_query = """
    query ($items: [StockItemInput!]!) {
        checkStock(items: $items) {
            product_id free_stock in_stock message
        }
    }
    """
    stock_data = _graphql_request(PRODUCTS_URL, stock_query, {"items": stock_items})
    stock_results = {r['product_id']: r for r in stock_data['checkStock']}

    enriched_items = []
    total = 0.0
    for item in items:
        pid = item['product_id']
        qty = item['quantity']
        if qty <= 0:
            raise ValueError(f"Mahsulot miqdori nol yoki manfiy: {pid}")

        prod = products[pid]
        stock = stock_results[pid]
        if not stock['in_stock']:
            raise ValueError(f"Stock yetarli emas: {prod['name']} — {stock['message']}")

        enriched_items.append({
            'product_id': pid,
            'product_name': prod['name'],
            'product_sku': prod.get('sku'),
            'quantity': qty,
            'unit_price': prod['price'],
            'total_price': prod['price'] * qty
        })
        total += prod['price'] * qty

    return enriched_items, total

# ========================
# ORDER CREATION
# ========================
def create_order(
    user_id: int,
    items: List[Dict],
    shipping_address: str,
    payment_method: str,
    billing_address: str = "",
    notes: str = ""
) -> int:
    """
    To'liq buyurtma yaratish:
    1. User tekshirish
    2. Mahsulot + stock tekshirish
    3. Narx hisoblash
    4. DB ga yozish
    5. Stockni bron qilish
    """
    if not shipping_address:
        raise ValueError("Yetkazib berish manzili bo'sh")
    if payment_method not in ['card', 'cash', 'click', 'payme']:
        raise ValueError("Noto'g'ri to'lov usuli")

    # 1. User
    user = _validate_user(user_id)

    # 2. Mahsulotlar + stock
    enriched_items, total = _validate_and_enrich_items(items)

    # 3. DB ga yozish
    order_id = db.create_order(
        user_id=user_id,
        items=enriched_items,
        shipping_address=shipping_address,
        billing_address=billing_address,
        payment_method=payment_method,
        notes=notes
    )

    # 4. Stockni bron qilish
    try:
        reserve_query = """
        mutation ($items: [StockItemInput!]!) {
            reserveStock(items: $items)
        }
        """
        reserve_items = [{"product_id": i['product_id'], "quantity": i['quantity']} for i in items]
        reserve_resp = _graphql_request(PRODUCTS_URL, reserve_query, {"items": reserve_items})
        if not reserve_resp['reserveStock']:
            raise ValueError("Stock bron qilib bo'lmadi")
    except Exception as e:
        # Rollback: buyurtmani o'chirish
        db.cancel_order(order_id, f"Stock bron xatosi: {e}")
        raise ValueError(f"Buyurtma qayta ishlandi: {e}")

    logger.info(f"Buyurtma #{order_id} muvaffaqiyatli yaratildi (user_id={user_id})")
    return order_id

# ========================
# ORDER STATUS
# ========================
def update_order_status(
    order_id: int,
    new_status: str,
    changed_by: Optional[int] = None,
    notes: Optional[str] = None
) -> bool:
    valid_transitions = {
        'created': ['confirmed', 'cancelled'],
        'confirmed': ['preparing', 'cancelled'],
        'preparing': ['shipped'],
        'shipped': ['delivered'],
        'delivered': ['refunded'],
    }
    order = db.get_order(order_id)
    if not order:
        raise ValueError("Buyurtma topilmadi")
    
    current = order['status']
    if new_status not in valid_transitions.get(current, []):
        raise ValueError(f"{current} → {new_status} o'tish mumkin emas")

    # Agar cancelled bo'lsa → stockni qaytarish
    if new_status == 'cancelled':
        items = [{"product_id": i['product_id'], "quantity": i['quantity']} for i in order['items']]
        try:
            release_query = """
            mutation ($items: [StockItemInput!]!) {
                releaseStock(items: $items)
            }
            """
            _graphql_request(PRODUCTS_URL, release_query, {"items": items})
        except:
            logger.warning(f"Stock qaytarishda xato: order_id={order_id}")

    return db.update_order_status(order_id, new_status, changed_by, notes)

# ========================
# REFUND
# ========================
def request_refund(order_id: int, amount: float, reason: str) -> int:
    order = db.get_order(order_id)
    if not order:
        raise ValueError("Buyurtma topilmadi")
    if order['status'] != 'delivered':
        raise ValueError("Faqat yetkazilgan buyurtma uchun qaytarish mumkin")
    if amount > order['total_amount']:
        raise ValueError("Qaytarish summasi buyurtma summasidan oshmasligi kerak")
    return db.request_refund(order_id, amount, reason)

# ========================
# UTILS
# ========================
def get_order(order_id: int) -> Optional[Dict]:
    return db.get_order(order_id)

def get_user_orders(user_id: int) -> List[Dict]:
    return db.get_user_orders(user_id)

def get_order_stats() -> Dict:
    return db.get_order_stats()