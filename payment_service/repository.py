# payments_service/repository.py
from db import PaymentDatabase
from typing import List, Dict, Optional, Any
import requests
import hashlib
import hmac
import time
import json
import logging

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global DB
db = PaymentDatabase()

# Test config (realda config.py dan oling)
CLICK_CONFIG = {
    'merchant_id': 12345,  # Test ID
    'service_id': 67,      # Test service
    'secret_key': 'test_secret_key',  # Test key
    'base_url': 'https://api.click.uz/v2/merchant/'
}

PAYME_CONFIG = {
    'merchant_id': '1234567890',  # Test ID
    'key': 'test_key_123',        # Test key
    'base_url': 'https://checkout.paycom.uz/api/'
}

# ========================
# CLICK INTEGRATSIYASI
# ========================
class ClickPayment:
    def __init__(self):
        self.base_url = CLICK_CONFIG['base_url']
        self.merchant_id = CLICK_CONFIG['merchant_id']
        self.service_id = CLICK_CONFIG['service_id']
        self.secret_key = CLICK_CONFIG['secret_key']

    def _generate_auth(self, merchant_trans_id: str) -> str:
        """Auth: merchant_trans_id:digest:timestamp"""
        timestamp = str(int(time.time()))
        digest = hashlib.sha1((timestamp + self.secret_key).encode()).hexdigest()
        return f"{merchant_trans_id}:{digest}:{timestamp}"

    def create_payment(self, order_id: int, amount: float, return_url: str) -> Dict:
        """Click ga to'lov yaratish"""
        merchant_trans_id = f"ORD{order_id}_{int(time.time())}"
        params = {
            'merchant_id': self.merchant_id,
            'service_id': self.service_id,
            'amount': int(amount * 100),  # Tiyin
            'currency': '860',  # UZS
            'order_id': merchant_trans_id,
            'action': 'pay',
            'return_url': return_url,
            'language': 'uz'
        }

        headers = {
            'Content-Type': 'application/json',
            'Authorization': self._generate_auth(merchant_trans_id)
        }

        try:
            resp = requests.post(
                f"{self.base_url}pay",
                json=params,
                headers=headers,
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get('error'):
                raise ValueError(f"Click xato: {data['error']}")
            logger.info(f"Click to'lov yaratildi: {data['token']}")
            return {
                'token': data['token'],
                'payment_url': data['checkout_url'],
                'transaction_id': merchant_trans_id
            }
        except Exception as e:
            logger.error(f"Click yaratish xatosi: {e}")
            raise

    def verify_payment(self, token: str) -> Dict:
        """Click to'lovni tekshirish"""
        headers = {'Content-Type': 'application/json'}
        try:
            resp = requests.post(
                f"{self.base_url}check",
                json={'token': token},
                headers=headers,
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get('error'):
                raise ValueError(f"Click tekshirish xatosi: {data['error']}")
            logger.info(f"Click tekshirildi: {data['status']}")
            return {
                'status': data['status'],  # 'paid', 'failed'
                'amount': data['amount'] / 100,
                'transaction_id': data['merchant_trans_id']
            }
        except Exception as e:
            logger.error(f"Click tekshirish xatosi: {e}")
            raise

# ========================
# PAYME INTEGRATSIYASI
# ========================
class PaymePayment:
    def __init__(self):
        self.merchant_id = PAYME_CONFIG['merchant_id']
        self.key = PAYME_CONFIG['key']
        self.base_url = PAYME_CONFIG['base_url']

    def _hmac_signature(self, data: Dict) -> str:
        """HMAC-SHA1 signature"""
        json_str = json.dumps(data, separators=(',', ':'), sort_keys=True)
        return hmac.new(
            self.key.encode(),
            json_str.encode(),
            hashlib.sha1
        ).hexdigest()

    def create_payment(self, order_id: int, amount: float, account: str) -> Dict:
        """Payme ga to'lov yaratish"""
        merchant_trans_id = f"PAY{order_id}_{int(time.time())}"
        params = {
            'method': 'create',
            'params': {
                'merchant_id': self.merchant_id,
                'account': account,  # User ID
                'amount': int(amount * 100),  # Tiyin
                'transaction': merchant_trans_id,
                'description': f"Buyurtma #{order_id}"
            }
        }
        params['json_params'] = json.dumps(params['params'])
        params['sign'] = self._hmac_signature(params['params'])

        try:
            resp = requests.post(
                f"{self.base_url}payments",
                json=params,
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get('error'):
                raise ValueError(f"Payme xato: {data['error']}")
            logger.info(f"Payme to'lov yaratildi: {data['result']['token']}")
            return {
                'token': data['result']['token'],
                'payment_url': f"https://checkout.paycom.uz/{data['result']['token']}",
                'transaction_id': merchant_trans_id
            }
        except Exception as e:
            logger.error(f"Payme yaratish xatosi: {e}")
            raise

    def verify_payment(self, token: str) -> Dict:
        """Payme to'lovni tekshirish"""
        params = {
            'method': 'check',
            'params': {'token': token}
        }
        params['json_params'] = json.dumps(params['params'])
        params['sign'] = self._hmac_signature(params['params'])

        try:
            resp = requests.post(
                f"{self.base_url}payments",
                json=params,
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get('error'):
                raise ValueError(f"Payme tekshirish xatosi: {data['error']}")
            result = data['result']
            logger.info(f"Payme tekshirildi: {result['status']}")
            return {
                'status': result['status'],  # 'paid', 'failed'
                'amount': result['amount'] / 100,
                'transaction_id': result['transaction']
            }
        except Exception as e:
            logger.error(f"Payme tekshirish xatosi: {e}")
            raise

# ========================
# MAIN FUNCTIONS
# ========================
def create_payment(order_id: int, method_name: str, amount: float, payer_info: Dict = None) -> Dict:
    """
    To'lov yaratish (Click yoki Payme)
    """
    # Method topish
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM payment_methods WHERE name = ? AND is_active = 1", (method_name,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"To'lov usuli topilmadi: {method_name}")

    method_id = row['id']

    # DB ga yozish
    payment_id = db.create_payment(order_id, method_id, amount, payer_info)

    # Gateway ga yuborish
    if method_name == 'click':
        click = ClickPayment()
        gateway_data = click.create_payment(order_id, amount, f"https://your-site.com/return")
    elif method_name == 'payme':
        payme = PaymePayment()
        gateway_data = payme.create_payment(order_id, amount, str(order_id))  # account = order_id
    else:
        raise ValueError("Faqat 'click' yoki 'payme' qo'llab-quvvatlanadi")

    # Gateway ma'lumotlarini saqlash
    db.update_payment_status(
        payment_id,
        'pending',
        gateway_data['transaction_id'],
        {'token': gateway_data['token']}
    )

    return {
        'payment_id': payment_id,
        'payment_url': gateway_data['payment_url'],
        'transaction_id': gateway_data['transaction_id']
    }
# ========================
# PAYMENT READ
# ========================
def get_payment(payment_id: int) -> Optional[Dict]:
    """
    To'lov ma'lumotlarini olish (logs + refunds bilan)
    """
    payment = db.get_payment(payment_id)
    if not payment:
        return None
    # payer_info JSON string → dict
    try:
        payment['payer_info'] = json.loads(payment['payer_info']) if payment['payer_info'] else {}
    except:
        payment['payer_info'] = {}
    return payment

# ========================
# UTILS
# ========================
def get_payment_methods() -> List[Dict]:
    return db.get_active_methods()

def get_payment_stats() -> Dict:
    return db.get_payment_stats()

def verify_payment(payment_id: int, token: str) -> Dict:
    """
    To'lovni tekshirish va status yangilash
    """
    payment = db.get_payment(payment_id)
    if not payment:
        raise ValueError("To'lov topilmadi")

    if payment['status'] != 'pending':
        raise ValueError("To'lov allaqachon hal qilingan")

    method_name = payment['method_name']

    if method_name == 'click':
        click = ClickPayment()
        gateway_data = click.verify_payment(token)
    elif method_name == 'payme':
        payme = PaymePayment()
        gateway_data = payme.verify_payment(token)
    else:
        raise ValueError("Noto'g'ri usul")

    # Status yangilash
    new_status = 'paid' if gateway_data['status'] == 'paid' else 'failed'
    error_msg = gateway_data.get('error_message') if new_status == 'failed' else None

    success = db.update_payment_status(
        payment_id,
        new_status,
        gateway_data['transaction_id'],
        {'gateway_status': gateway_data['status']},
        error_msg
    )

    if success and new_status == 'paid':
        logger.info(f"To'lov muvaffaqiyatli: payment_id={payment_id}")

    return {
        'status': new_status,
        'amount': gateway_data['amount'],
        'success': success
    }

# ========================
# REFUND
# ========================
def request_refund(payment_id: int, amount: float, reason: str) -> int:
    return db.request_refund(payment_id, amount, reason)

def process_refund(refund_id: int, status: str, gateway_refund_id: str = None) -> bool:
    return db.process_refund(refund_id, status, gateway_refund_id)

# ========================
# UTILS
# ========================
def get_payment_methods() -> List[Dict]:
    return db.get_active_methods()

def get_payment_stats() -> Dict:
    return db.get_payment_stats()
# ... (oldingi kodlar saqlanadi)

