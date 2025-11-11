# users_service/main.py
import ssl
import os
from http.server import HTTPServer
from api import GraphQLHandler

if __name__ == '__main__':
    # Sertifikat yarat (bir marta)
    cert_path = 'cert.pem'
    key_path = 'key.pem'
    if not os.path.exists(cert_path):
        os.system(f'openssl req -x509 -newkey rsa:4096 -keyout {key_path} -out {cert_path} -days 365 -nodes -subj "/CN=localhost"')

    server = HTTPServer(('localhost', 8443), GraphQLHandler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert_path, key_path)
    server.socket = ctx.wrap_socket(server.socket, server_side=True)

    print("Users Service: https://localhost:8443/graphql")
    server.serve_forever()