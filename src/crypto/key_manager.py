import os
import hashlib


class KeyManager:
    SALT_SIZE = 16

    @staticmethod
    def derive_key(password: str, salt: bytes = None) -> tuple[bytes, bytes]:
        """Derive a 16-byte SM4 key from password using SHA-256 based KDF.
        Returns (key, salt)."""
        if salt is None:
            salt = os.urandom(KeyManager.SALT_SIZE)
        raw = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000, dklen=16)
        return raw, salt

    @staticmethod
    def generate_random_key() -> bytes:
        return os.urandom(16)

    @staticmethod
    def generate_iv() -> bytes:
        return os.urandom(16)
