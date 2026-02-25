import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings

_key_bytes: bytes = bytes.fromhex(settings.ENCRYPTION_KEY)
_aesgcm = AESGCM(_key_bytes)

NONCE_SIZE = 12


def encrypt_field(plaintext: str) -> str:
    nonce = os.urandom(NONCE_SIZE)
    ciphertext = _aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def decrypt_field(ciphertext: str) -> str:
    raw = base64.b64decode(ciphertext)
    nonce = raw[:NONCE_SIZE]
    encrypted = raw[NONCE_SIZE:]
    plaintext_bytes = _aesgcm.decrypt(nonce, encrypted, None)
    return plaintext_bytes.decode("utf-8")
