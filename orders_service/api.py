# orders_service/api.py
from http.server import BaseHTTPRequestHandler
import json
import traceback
import logging
from graphql import graphql_sync
from schemas import schema

# Logging sozlash
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GraphQLHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Test sahifasi — browserda ko'rish uchun"""
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = f"""
            <h1>Orders Service — ISHLAYAPTI!</h1>
            <p><strong>Port:</strong> <code>8445</code></p>
            <p><strong>GraphQL Endpoint:</strong> <code>POST /graphql</code></p>
            <hr>
            <h3>Test: Buyurtma yaratish</h3>
            <pre>
curl -k -X POST https://localhost:8445/graphql \\
  -H "Content-Type: application/json" \\
  -d '{{
    "query": "mutation {{ createOrder(input: {{ userId: 1, items: [{{productId: 1, quantity: 2}}], shippingAddress: \\"Toshkent\\", paymentMethod: \\"card\\" }}) }}"
  }}'
            </pre>
            <hr>
            <p><strong>Status:</strong> <span style="color:green">ACTIVE</span></p>
            """
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

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

            # DEBUG: Terminalga chiqarish
            logger.info("\n=== GraphQL So'rov ===")
            logger.info("Client IP: %s", self.client_address[0])
            logger.info("Query: %s", query.strip()[:200])
            if variables:
                logger.info("Variables: %s", json.dumps(variables, ensure_ascii=False))

            # Mock context (keyin JWT bilan)
            context = {
                'user': {'id': 1, 'role': 'user'},  # test uchun
                'request': self
            }

            # GraphQL ishga tushirish
            result = graphql_sync(
                schema,
                query,
                variable_values=variables,
                context_value=context
            )

            # TO'G'RI USUL: result.formatted
            response_data = result.formatted

            # DEBUG: Natija
            logger.info("Muvaffaqiyatli javob: %s", 
                        json.dumps(response_data.get('data'), ensure_ascii=False, indent=2)[:500])
            if response_data.get('errors'):
                logger.warning("Xatolar: %s", response_data['errors'])

            # Javob yuborish
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
            logger.error("Kutilmagan xato: %s\n%s", str(e), traceback.format_exc())
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