"""Field-level AES-256-GCM encryption for IBAN, TC kimlik no and phone.

Stored format: base64(nonce(12) || ciphertext || tag(16)).
In production the key would live in Vault / a cloud KMS, never next to the data.
"""
import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings

NONCE_SIZE = 12


def _key() -> bytes:
    raw = settings.DATA_ENCRYPTION_KEY
    if not raw:
        raise RuntimeError("DATA_ENCRYPTION_KEY is missing in .env")
    key = base64.b64decode(raw)
    if len(key) != 32:
        raise RuntimeError("DATA_ENCRYPTION_KEY must be 32 bytes (base64 encoded)")
    return key


def encrypt_field(plaintext: str, key: bytes | None = None) -> str:
    nonce = os.urandom(NONCE_SIZE)
    ct = AESGCM(key or _key()).encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("ascii")


def decrypt_field(token: str, key: bytes | None = None) -> str:
    blob = base64.b64decode(token)
    nonce, ct = blob[:NONCE_SIZE], blob[NONCE_SIZE:]
    return AESGCM(key or _key()).decrypt(nonce, ct, None).decode("utf-8")


def normalize_iban(iban: str) -> str:
    return "".join(iban.split()).upper()


def iban_index(iban: str) -> str:
    """Deterministic lookup value so we can find an account by IBAN
    without storing the IBAN in clear text (random nonces make ciphertexts unsearchable)."""
    index_key = hashlib.sha256(b"securebank-iban-index" + _key()).digest()
    return hmac.new(index_key, normalize_iban(iban).encode(), hashlib.sha256).hexdigest()


def format_iban(iban: str) -> str:
    iban = normalize_iban(iban)
    return " ".join(iban[i:i + 4] for i in range(0, len(iban), 4))


def mask_iban(iban_or_last4: str) -> str:
    last4 = normalize_iban(iban_or_last4)[-4:]
    return f"TR** **** **** **** **** {last4}"


def mask_tc(tc: str) -> str:
    return f"{tc[:2]}*******{tc[-2:]}" if len(tc) == 11 else "***********"


def mask_phone(phone: str) -> str:
    digits = "".join(c for c in phone if c.isdigit())
    return f"*** *** ** {digits[-2:]}" if len(digits) >= 2 else "***"
