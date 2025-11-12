from http.server import BaseHTTPRequestHandler
import json
import logging
from graphql import graphql_sync
from schemas import schema

logger = logging.getLogger("CartAPI")

class GraphQLHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = """
            <h1 style="color:#1a73e8">Cart Service — ISHLAYAPTI! (8451)</h1>
            <p><strong>Port:</strong> <code>8451</code></p>
            <p><strong>GraphQL:</strong> <code>POST /graphql</code></p>
            <hr>
            <h3>Test: Savat yaratish</h3>
            <pre style="background:#f4f4f4;padding:12px;border-radius:8px;">
curl -k -X POST https://localhost:8451/graphql \\
  -H "Content-Type: application/json" \\
  -d '{"query": "mutation { addToCart(sessionId: \\"guest-123\\", input: {productId: 1, quantity: 2}) { cartId summary { totalPrice } } }"}'
            </pre>
            """
            self.wfile.write(html.encode())
        else:
            self._error(404, "Sahifa topilmadi")

    def do_POST(self):
        if self.path != '/graphql':
            self._error(404, "Endpoint topilmadi")
            return

        try:
            length = int(self.headers.get('Content-Length', 0))
            if length <= 0:
                self._error(400, "Bo‘sh so‘rov")
                return

            body = self.rfile.read(length).decode()
            request_data = json.loads(body)
            query = request_data.get('query')
            variables = request_data.get('variables', {})

            if not query:
                self._error(400, "GraphQL query yo‘q")
                return

            logger.info(f"GraphQL So‘rov: {query[:100]}")

            result = graphql_sync(schema, query, variable_values=variables)
            response_data = result.formatted

            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False, indent=2).encode('utf-8'))

        except Exception as e:
            logger.error(f"Xato: {e}")
            self._error(500, "Ichki xato")

    def _error(self, code, msg):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"errors": [{"message": msg}]}).encode())