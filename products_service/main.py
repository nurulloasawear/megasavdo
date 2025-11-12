# products_service/main.py
import ssl
import os
import subprocess
from http.server import HTTPServer
from api import GraphQLHandler

# ========================
# SERTIFIKAT YARATISH (bir marta)
# ========================
def generate_ssl_cert():
    cert_path = 'cert.pem'
    key_path = 'key.pem'
    
    if os.path.exists(cert_path) and os.path.exists(key_path):
        print(f"Sertifikatlar topildi: {cert_path}, {key_path}")
        return cert_path, key_path

    print("Sertifikatlar yaratilmoqda... (bir marta)")
    cmd = [
        'openssl', 'req', '-x509', '-newkey', 'rsa:4096',
        '-keyout', key_path, '-out', cert_path,
        '-days', '365', '-nodes',
        '-subj', '/CN=localhost/O=ProductsService/C=UZ'
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"Sertifikatlar muvaffaqiyatli yaratildi:")
        print(f"   Sertifikat: {cert_path}")
        print(f"   Kalit: {key_path}")
    except subprocess.CalledProcessError as e:
        print("Sertifikat yaratishda xato:")
        print(e.stderr.decode())
        exit(1)
    
    return cert_path, key_path

# ========================
# HTTPS SERVER
# ========================
def run_server():
    HOST = 'localhost'
    PORT = 8444

    # Sertifikat yaratish
    cert_file, key_file = generate_ssl_cert()

    # Server yaratish
    server = HTTPServer((HOST, PORT), GraphQLHandler)

    # SSL sozlash
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=cert_file, keyfile=key_file)

    server.socket = context.wrap_socket(server.socket, server_side=True)

    # Xizmatni ishga tushirish
    print("=" * 60)
    print(" PRODUCTS SERVICE — ISHLAYAPTI!")
    print("=" * 60)
    print(f" HTTPS Server: https://{HOST}:{PORT}")
    print(f" GraphQL Endpoint: POST https://localhost:{PORT}/graphql")
    print(f" Test sahifasi: https://localhost:{PORT}/")
    print("=" * 60)
    print("Xizmatni to'xtatish uchun: Ctrl+C")
    print("=" * 60)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nXizmat to'xtatildi.")
    finally:
        server.server_close()

# ========================
# ISHGA TUSHIRISH
# ========================
if __name__ == '__main__':
    run_server()