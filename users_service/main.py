from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from api import schema

class GraphQLHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')

        try:
            request_json = json.loads(post_data)
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Invalid JSON format'}).encode('utf-8'))
            return

        query = request_json.get('query')
        variables = request_json.get('variables')

        if not query:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Missing query field'}).encode('utf-8'))
            return

        result = schema.execute(query, variables=variables)

        response = {}
        if result.errors:
            response['errors'] = [str(error) for error in result.errors]
        if result.data:
            response['data'] = result.data

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))

def run(server_class=HTTPServer, handler_class=GraphQLHandler, port=8001):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'🚀 GraphQL server running on port {port}')
    httpd.serve_forever()

if __name__ == "__main__":
    run()
