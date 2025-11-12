# analytics_service/repository.py
from db import AnalyticsDatabase
from typing import Dict, List
import requests
import logging
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)
db = AnalyticsDatabase()

# Xizmatlar URLlari
SERVICES = {
    "orders": "https://localhost:8445/graphql",
    "payments": "https://localhost:8446/graphql",
    "users": "https://localhost:8443/graphql",
    "products": "https://localhost:8444/graphql",
}

def _call(service: str, query: str, variables: Dict = None) -> Dict:
    try:
        resp = requests.post(SERVICES[service], json={"query": query, "variables": variables or {}}, verify=False, timeout=5)
        resp.raise_for_status()
        return resp.json().get('data', {})
    except Exception as e:
        logger.error(f"{service} xizmati xatosi: {e}")
        return {}

# ========================
# DAILY STATS
# ========================
def update_daily_stats():
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 1. Orders bugun
    orders_data = _call("orders", """
        query { orderStats { created confirmed preparing shipped delivered cancelled refunded } }
    """)
    stats = orders_data.get('orderStats', {})
    total_orders = sum(stats.values())

    # 2. Revenue (paid payments)
    payments_data = _call("payments", """
        query { paymentStats { paid } }
    """)
    revenue = payments_data.get('paymentStats', {}).get('paid', 0) * 100000  # misol

    # 3. New users
    users_data = _call("users", """
        query { userStats { total } }
    """)
    new_users = users_data.get('userStats', {}).get('total', 0)  # keyin to'g'rilanadi

    # 4. Top product
    top_product = _call("products", """
        query { searchProducts(limit: 1) { id name } }
    """).get('searchProducts', [{}])[0]

    # DB ga yozish
    with db.get_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO daily_stats 
            (date, total_orders, total_revenue, new_users, top_product_id, top_product_name, top_product_sales)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (today, total_orders, revenue, new_users, top_product.get('id'), top_product.get('name'), 0))

# ========================
# DASHBOARD DATA
# ========================
def get_dashboard_stats() -> Dict:
    update_daily_stats()
    today = datetime.now().strftime("%Y-%m-%d")
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM daily_stats WHERE date = ?", (today,))
        row = cursor.fetchone()
        if not row:
            return {"error": "Ma'lumot yo'q"}
        return dict(row)

def get_top_products(limit: int = 10) -> List[Dict]:
    data = _call("orders", """
        query { userOrders(userId: 1) { items { productName totalPrice } } }
    """)
    # Keyin real hisoblash
    return [{"name": "iPhone 15", "sales": 15000000}, {"name": "MacBook", "sales": 12000000}][:limit]

def get_revenue_trend(days: int = 7) -> List[Dict]:
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT date, total_revenue FROM daily_stats 
            WHERE date >= date('now', ? || ' days') 
            ORDER BY date
        """, (f"-{days}",))
        return [dict(row) for row in cursor.fetchall()]