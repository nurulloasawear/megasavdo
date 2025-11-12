# orders_service/main.py
import ssl
import os
import subprocess
import logging
from http.server import HTTPServer
from api import GraphQLHandler

# ========================
# LOGGING
# ========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("OrdersService")

# ========================
# SERTIFIKAT YARATISH (bir marta)
# ========================
def generate_ssl_cert():
    cert_path = 'cert.pem'
    key_path = 'key.pem'
    
    if os.path.exists(cert_path) and os.path.exists(key_path):
        logger.info(f"Sertifikatlar topildi: {cert_path}, {key_path}")
        return cert_path, key_path

    logger.info("Sertifikatlar yaratilmoqda... (bir marta)")
    cmd = [
        'openssl', 'req', '-x509', '-newkey', 'rsa:4096',
        '-keyout', key_path, '-out', cert_path,
        '-days', '365', '-nodes', '-batch',
        '-subj', '/CN=localhost/O=OrdersService/C=UZ'
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info("Sertifikatlar muvaffaqiyatli yaratildi:")
        logger.info(f"   Sertifikat: {cert_path}")
        logger.info(f"   Kalit: {key_path}")
    except subprocess.CalledProcessError as e:
        logger.error("Sertifikat yaratishda xato:")
        logger.error(e.stderr)
        exit(1)
    except FileNotFoundError:
        logger.error("OpenSSL topilmadi! `sudo apt install openssl` yoki `brew install openssl`")
        exit(1)
    
    return cert_path, key_path

# ========================
# HTTPS SERVER
# ========================
def run_server():
    HOST = 'localhost'
    PORT = 8445

    # Sertifikat yaratish
    cert_file, key_file = generate_ssl_cert()

    # Server yaratish
    server = HTTPServer((HOST, PORT), GraphQLHandler)

    # SSL sozlash
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=cert_file, keyfile=key_file)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL')

    server.socket = context.wrap_socket(server.socket, server_side=True)

    # Banner
    banner = f"""
╔══════════════════════════════════════════════════════════╗
║                 ORDERS SERVICE — ISHLAYAPTI!             ║
╚══════════════════════════════════════════════════════════╝
   HTTPS Server: https://{HOST}:{PORT}
   GraphQL Endpoint: POST https://localhost:{PORT}/graphql
   Test sahifasi: https://localhost:{PORT}/
   Xizmatni to'xtatish: Ctrl+C
"""
    logger.info(banner)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nXizmat to'xtatildi.")
    finally:
        server.server_close()
        logger.info("Server yopildi.")

# ========================
# ISHGA TUSHIRISH
# ========================
if __name__ == '__main__':
    run_server()