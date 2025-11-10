from  http.server import  BaseHTTPRequestHandler
import json 
from graphql import graphql_sync
from users_service.schema import schema

class GraphQLHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Users Service GraphQL API</h1></body></html>")
        else:
            self.send_response(404)
            self.end_headers()
    def do_POST(self):
        if self.path == "/graphql":
            length = int(self.headers.get("Content-Length"))
            body = json.loads(self.rfile.read(length))
            result = graphql_sync(schema, body.get("query"), variable_values=body.get("variables"))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result.to_dict()).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()