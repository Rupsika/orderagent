"""
security.py

Password hashing (PBKDF2-HMAC-SHA256, stdlib only) and JWT session
tokens (PyJWT) for real authentication on top of the SQLite backend.
"""

import os
import hmac
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "60"))

# OWASP recommends 600,000 iterations for PBKDF2-HMAC-SHA256.
PBKDF2_ITERATIONS = 600_000
# Hashes created before the iteration count was stored ("salt$digest") used this.
LEGACY_PBKDF2_ITERATIONS = 200_000
HASH_SCHEME = "pbkdf2_sha256"


def _pbkdf2(password: str, salt_hex: str, iterations: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), iterations).hex()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = _pbkdf2(password, salt, PBKDF2_ITERATIONS)
    return f"{HASH_SCHEME}${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    parts = password_hash.split("$")
    try:
        if len(parts) == 4 and parts[0] == HASH_SCHEME:
            _, iterations, salt, digest_hex = parts
            iterations = int(iterations)
        elif len(parts) == 2:
            salt, digest_hex = parts
            iterations = LEGACY_PBKDF2_ITERATIONS
        else:
            return False
        expected = _pbkdf2(password, salt, iterations)
    except ValueError:
        return False
    return hmac.compare_digest(expected, digest_hex)


def needs_rehash(password_hash: str) -> bool:
    """True if the hash uses an older/weaker format and should be upgraded."""
    parts = password_hash.split("$")
    return not (len(parts) == 4 and parts[0] == HASH_SCHEME and parts[1] == str(PBKDF2_ITERATIONS))


def create_access_token(customer_id: str) -> str:
    payload = {
        "sub": customer_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Returns customer_id if valid, else None."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None
