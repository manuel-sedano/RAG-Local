"""Hash y verificación de contraseñas (Argon2id + pepper)."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(plain: str, *, pepper: str) -> str:
    return _hasher.hash(plain + pepper)


def verify_password(plain: str, password_hash: str, *, pepper: str) -> bool:
    try:
        return _hasher.verify(password_hash, plain + pepper)
    except VerifyMismatchError:
        return False
