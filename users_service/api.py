# users_service/api.py
from http.server import BaseHTTPRequestHandler
import json
from graphql import graphql_sync,FormattedExecutionResult as format_execution_result
from schemas import schema
import traceback
class GraphQLHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/graphql':
            try:
                length = int(self.headers['Content-Length'])
                body = json.loads(self.rfile.read(length))
                print(body)
                query = body.get('query')
                variables = body.get('variables', {})

                context = {'user': {'id': 1, 'role': 'customer'}}

                result = graphql_sync(schema, query, variable_values=variables, context_value=context)

                # ✅ To‘g‘ri formatlash
                response_data = result.formatted  # yoki result.to_dict()

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))

            except Exception as e:
                print("Error:", e)
                traceback.print_exc()
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"errors": [str(e)]}, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

            if self.path == '/graphql':
                try:
                    length = int(self.headers['Content-Length'])
                    # print(length)
                    # print(self.rfile.read(length))
                    body = json.loads(self.rfile.read(length))
                    print(body)
                    query = body.get('query')
                    variables = body.get('variables', {})

                    # Mock user (keyin JWT bilan)
                    context = {'user': {'id': 1, 'role': 'customer'}}

                    result = graphql_sync(schema, query, variable_values=variables, context_value=context)
                    
                    # TO'G'RI USUL: format_execution_result
                    response_data = format_execution_result(result)

                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
                except Exception as e:
                    print("Error:", e)
                    traceback.print_exc()
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"errors": [str(e)]}, ensure_ascii=False).encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()