# cart_service/main.py
import ssl
import os
import subprocess
import logging
from http.server import HTTPServer
from api import GraphQLHandler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("CartService")

def generate_ssl_cert():
    cert_path = 'cert.pem'
    key_path = 'key.pem'
    if os.path.exists(cert_path) and os.path.exists(key_path):
        logger.info("Sertifikatlar topildi")
        return cert_path, key_path

    logger.info("Sertifikat yaratilmoqda...")
    cmd = [
        'openssl', 'req', '-x509', '-newkey', 'rsa:4096',
        '-keyout', key_path, '-out', cert_path,
        '-days', '365', '-nodes', '-batch',
        '-subj', '/CN=localhost/O=CartService/C=UZ'
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info("Sertifikatlar yaratildi")
    except Exception as e:
        logger.error(f"Sertifikat xatosi: {e}")
        exit(1)
    return cert_path, key_path

def run():
    HOST = 'localhost'
    PORT = 8452
    cert_file, key_file = generate_ssl_cert()

    server = HTTPServer((HOST, PORT), GraphQLHandler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=cert_file, keyfile=key_file)
    server.socket = context.wrap_socket(server.socket, server_side=True)

    banner = f"""
╔══════════════════════════════════════════════════════════╗
║              CART SERVICE — MUVOFFAQIYATLI ISHLADI!      ║
╚══════════════════════════════════════════════════════════╝
   HTTPS: https://{HOST}:{PORT}
   GraphQL: POST /graphql
   Test: curl -k https://localhost:{PORT}/graphql
   API Gateway orqali: 8447
"""
    logger.info(banner)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nXizmat to‘xtatildi")
    finally:
        server.server_close()

if __name__ == '__main__':
    run()