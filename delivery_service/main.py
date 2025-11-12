# delivery_service/main.py
import ssl, os, subprocess, logging
from http.server import HTTPServer
from api import GraphQLHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(name)s | %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("DeliveryService")

def run():
    PORT = 8448
    cert, key = 'cert.pem', 'key.pem'
    if not os.path.exists(cert):
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:4096', '-keyout', key, '-out', cert, '-days', '365', '-nodes', '-batch', '-subj', '/CN=localhost'], check=True)
    server = HTTPServer(('localhost', PORT), GraphQLHandler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert, key)
    server.socket = ctx.wrap_socket(server.socket, server_side=True)
    logger.info(f"Delivery Service → https://localhost:{PORT}")
    server.serve_forever()

if __name__ == '__main__':
    run()