import os
import threading
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class EncryptionUnavailable(Exception):
    """The server-managed encryption key is missing or unusable."""


_create_lock = threading.Lock()


def _read_or_create_key() -> bytes:
    if settings.ENCRYPTION_KEY:
        return settings.ENCRYPTION_KEY.encode()

    path = settings.ENCRYPTION_KEY_FILE
    if path.exists():
        return path.read_bytes().strip()

    if not settings.ENCRYPTION_KEY_AUTOCREATE:
        raise EncryptionUnavailable(
            "No encryption key is configured. Set MARKETMESH_ENCRYPTION_KEY "
            "or create the key file named by MARKETMESH_ENCRYPTION_KEY_FILE."
        )

    with _create_lock:
        if path.exists():
            return path.read_bytes().strip()
        path.parent.mkdir(parents=True, exist_ok=True)
        key = Fernet.generate_key()
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(key)
        return key


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    try:
        return Fernet(_read_or_create_key())
    except ValueError as exc:
        raise EncryptionUnavailable("The configured encryption key is not a valid Fernet key.") from exc


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise EncryptionUnavailable(
            "The stored API key cannot be decrypted with the current encryption key. "
            "Remove it and save it again."
        ) from exc


def reset_cache() -> None:
    _fernet.cache_clear()
