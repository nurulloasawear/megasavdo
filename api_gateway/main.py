# api_gateway/api.py
from http.server import BaseHTTPRequestHandler
import json
import requests
import logging

logger = logging.getLogger("APIGateway")

SERVICES = {
    "users": "https://localhost:8443/graphql",
    "products": "https://localhost:8444/graphql",
    "orders": "https://localhost:8445/graphql",
    "payments": "https://localhost:8446/graphql",
}

class GraphQLHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = """
            <h1>API GATEWAY — ISHLAYAPTI!</h1>
            <p><strong>Port:</strong> <code>8447</code></p>
            <p><strong>GraphQL:</strong> <code>POST /graphql</code></p>
            <hr>
            <h3>Test: Buyurtma yaratish</h3>
            <pre>
curl -k -X POST https://localhost:8447/graphql \\
  -d '{"query": "mutation { orders { createOrder(input: {userId:1, items:[{productId:1,quantity:1}], shippingAddress:\\"Toshkent\\", paymentMethod:\\"card\\"}) } }"}'
            </pre>
            """
            self.wfile.write(html.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path != '/graphql':
            self._error(404, "Endpoint topilmadi")
            return

        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode()
            data = json.loads(body)
            query = data.get('query', '')
            variables = data.get('variables', {})

            # Service aniqlash
            service = None
            if 'users' in query.lower():
                service = "users"
            elif 'products' in query.lower() or 'checkStock' in query:
                service = "products"
            elif 'orders' in query.lower() or 'createOrder' in query:
                service = "orders"
            elif 'payments' in query.lower() or 'createPayment' in query:
                service = "payments"

            if not service:
                self._error(400, "Xizmat aniqlanmadi")
                return

            url = SERVICES[service]
            logger.info(f"Forward → {service.upper()} ({url})")

            # Forward
            resp = requests.post(
                url,
                json={"query": query, "variables": variables},
                verify=False,
                timeout=10
            )
            resp.raise_for_status()
            result = resp.json()

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False, indent=2).encode())

        except Exception as e:
            logger.error(f"Xato: {e}")
            self._error(500, "Ichki xato")

    def _error(self, code, msg):
        self.send_response(code)
        self.send_header('.Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"errors": [{"message": msg}]}).encode())
        