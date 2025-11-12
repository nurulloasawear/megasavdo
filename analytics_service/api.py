# analytics_service/api.py
from http.server import BaseHTTPRequestHandler
import json
import logging
from graphql import graphql_sync
from schemas import schema

logger = logging.getLogger("AnalyticsAPI")

class GraphQLHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write("<h1>Analytics Service — ISHLAYAPTI! (8449)</h1><p>Dashboard: <code>POST /graphql</code></p>")
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
            result = graphql_sync(schema, data.get('query', ''), variable_values=data.get('variables', {}))
            response = result.formatted

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response, ensure_ascii=False, indent=2).encode())
        except Exception as e:
            logger.error(f"Xato: {e}")
            self._error(500, "Ichki xato")

    def _error(self, code, msg):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"errors": [{"message": msg}]}).encode())