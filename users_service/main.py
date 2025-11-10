import ssl
from http.server import HTTPServer
from api import GraphQLHandler

if __name__ == '__main__':
    # Sertifikat yarat (bir marta)
    import os
    if not os.path.exists('cert.pem'):
        os.system('openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=localhost"')

    server = HTTPServer(('localhost', 8443), GraphQLHandler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain('cert.pem', 'key.pem')
    server.socket = ctx.wrap_socket(server.socket, server_side=True)

    print("Users Service: https://localhost:8443/graphql")
    server.serve_forever()