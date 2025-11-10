import ssl
from http.server import HTTPServer
from api import GraphQLHandler
from pathlib import Path

if __name__ == '__main__':
    cert_file = Path("cert.pem")
    key_file = Path("key.pem")

    # Agar mavjud bo'lmasa, Python ichida self-signed sertifikat yaratish
    if not cert_file.exists() or not key_file.exists():
        import tempfile
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import serialization, hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        import datetime

        # private key yaratish
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )

        # self-signed sertifikat yaratish
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, u'localhost')
        ])
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        ).sign(key, hashes.SHA256())

        # fayllarga yozish
        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        with open(key_file, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))

    # HTTPS server yaratish
    server = HTTPServer(('localhost', 8443), GraphQLHandler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert_file, key_file)
    server.socket = ctx.wrap_socket(server.socket, server_side=True)

    print("Users Service: https://localhost:8443/graphql")
    server.serve_forever()
