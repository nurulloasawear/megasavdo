# payments_service/api.py
from http.server import BaseHTTPRequestHandler
import json
import traceback
import logging
from graphql import graphql_sync
from schemas import schema

# ========================
# LOGGING
# ========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("PaymentsAPI")

class GraphQLHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Test sahifasi — browserda ko'rish uchun"""
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = f"""
            <h1 style="color: #1a73e8;">Payments Service — ISHLAYAPTI!</h1>
            <p><strong>Port:</strong> <code>8446</code></p>
            <p><strong>GraphQL Endpoint:</strong> <code>POST /graphql</code></p>
            <hr>
            <h3>Test: To'lov yaratish (Click)</h3>
            <pre style="background:#f4f4f4;padding:12px;border-radius:8px;">
curl -k -X POST https://localhost:8446/graphql \\
  -H "Content-Type: application/json" \\
  -d '{{
    "query": "mutation {{ createPayment(input: {{ orderId: 1, method: \\"click\\", amount: 50000, payerInfo: {{email: \\"test@example.com\\"}} }}) {{ paymentId paymentUrl transactionId }} }}"
  }}'
            </pre>
            <hr>
            <p><strong>Status:</strong> <span style="color:green;font-weight:bold;">ACTIVE</span></p>
            <p><em>Click, Payme, Card — hammasi ishlaydi!</em></p>
            """
            self.wfile.write(html.encode('utf-8'))
        else:
            self._send_error(404, "Sahifa topilmadi")

    def do_POST(self):
        if self.path != '/graphql':
            self._send_error(404, "Endpoint topilmadi")
            return

        try:
            # Request body o'qish
            length = int(self.headers.get('Content-Length', 0))
            if length <= 0:
                self._send_error(400, "Bo'sh so'rov")
                return

            body = self.rfile.read(length).decode('utf-8')
            request_data = json.loads(body)

            query = request_data.get('query')
            variables = request_data.get('variables', {})

            if not query:
                self._send_error(400, "GraphQL query bo'sh")
                return

            # ========================
            # DEBUG LOG
            # ========================
            logger.info("\n" + "="*60)
            logger.info("GraphQL So'rov")
            logger.info("Client IP: %s", self.client_address[0])
            logger.info("Query: %s", query.strip()[:300])
            if variables:
                logger.info("Variables: %s", json.dumps(variables, ensure_ascii=False, indent=2))

            # Mock context (keyin JWT bilan)
            context = {
                'user': {'id': 1, 'role': 'user'},
                'request': self
            }

            # ========================
            # GraphQL ISHGA TUSHIRISH
            # ========================
            result = graphql_sync(
                schema,
                query,
                variable_values=variables,
                context_value=context
            )

            # TO'G'RI USUL: result.formatted
            response_data = result.formatted

            # ========================
            # DEBUG NATIJA
            # ========================
            data_part = response_data.get('data')
            errors_part = response_data.get('errors')

            if data_part:
                logger.info("Muvaffaqiyatli javob:")
                logger.info(json.dumps(data_part, ensure_ascii=False, indent=2))
            if errors_part:
                logger.warning("Xatolar:")
                for err in errors_part:
                    logger.warning("  - %s", err.get('message', 'Noma\'lum xato'))

            # ========================
            # JAVOB YUBORISH
            # ========================
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')  # keyin o'chiriladi
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False, indent=2).encode('utf-8'))

        except json.JSONDecodeError as e:
            logger.error("JSON xatosi: %s", e)
            self._send_error(400, "Noto'g'ri JSON format")
        except ValueError as e:
            logger.warning("Business logic xatosi: %s", str(e))
            self._send_error(400, str(e))
        except Exception as e:
            logger.error("Kutilmagan xato:\n%s", traceback.format_exc())
            self._send_error(500, "Ichki server xatosi")

    def _send_error(self, code: int, message: str):
        """Xatolik javobini yuborish"""
        self.send_response(code)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        error_response = {
            "data": None,
            "errors": [{"message": message}]
        }
        self.wfile.write(json.dumps(error_response, ensure_ascii=False).encode('utf-8'))