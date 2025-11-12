from http.server import BaseHTTPRequestHandler
import json
import traceback
from graphql import graphql_sync
from schemas import schema

class GraphQLHandler(BaseHTTPRequestHandler):
    ...

    def do_POST(self):
        if self.path == '/graphql':
            try:
                # Read and parse request body
                length = int(self.headers.get('Content-Length', 0))
                body = json.loads(self.rfile.read(length).decode('utf-8'))
                query = body.get('query')
                variables = body.get('variables', {})

                print("\n=== GraphQL Request ===")
                print("Query:", query)
                print("Variables:", variables)

                # Example context
                context = {'user': {'id': 1, 'role': 'admin'}}

                # Execute the query
                result = graphql_sync(
                    schema,
                    query,
                    variable_values=variables,
                    context_value=context
                )

                print("Result data:", result.data)
                print("Result errors:", result.errors)

                # ✅ Correct formatting for graphql-core 3.2+
                response_data = result.formatted

                # Send response
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(response_data, ensure_ascii=False, indent=2).encode('utf-8'))

            except json.JSONDecodeError:
                self.send_error(400, "Invalid JSON")
            except Exception as e:
                print("ERROR:", str(e))
                traceback.print_exc()
                self.send_error(500, str(e))
