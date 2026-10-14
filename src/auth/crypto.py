"""
Cryptographic password hashing and verification module.
Uses Python standard library PBKDF2-HMAC-SHA256 with random salt.
Zero external C-extension dependencies, fully portable across all operating systems.
"""

from __future__ import annotations

import hashlib
import secrets
from typing import Tuple


DEFAULT_ITERATIONS = 100_000
ALGORITHM_PREFIX = "pbkdf2_sha256"


def hash_password(password: str, iterations: int = DEFAULT_ITERATIONS) -> str:
    """
    Hash a plain text password using PBKDF2-HMAC-SHA256 with a unique random salt.
    Returns format: pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    salt_hex = secrets.token_hex(16)
    salt_bytes = salt_hex.encode("utf-8")
    pwd_bytes = password.encode("utf-8")
    
    derived_key = hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=pwd_bytes,
        salt=salt_bytes,
        iterations=iterations,
    )
    return f"{ALGORITHM_PREFIX}${iterations}${salt_hex}${derived_key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a stored hash using constant-time comparison.
    """
    if not plain_password or not hashed_password:
        return False
    
    parts = hashed_password.split("$")
    if len(parts) != 4:
        return False
    
    algorithm, iter_str, salt_hex, stored_hash = parts
    if algorithm != ALGORITHM_PREFIX:
        return False
    
    try:
        iterations = int(iter_str)
    except ValueError:
        return False
    
    salt_bytes = salt_hex.encode("utf-8")
    pwd_bytes = plain_password.encode("utf-8")
    
    derived_key = hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=pwd_bytes,
        salt=salt_bytes,
        iterations=iterations,
    )
    
    return secrets.compare_digest(derived_key.hex(), stored_hash)
