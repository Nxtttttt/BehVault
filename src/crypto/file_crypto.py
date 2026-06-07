import os
import base64

from src.crypto.sm4_mode import SM4CBC, SM4ECB
from src.crypto.key_manager import KeyManager


class FileEncryptor:
    @staticmethod
    def encrypt_filename(filename: str, key: bytes) -> str:
        iv = KeyManager.generate_iv()
        cipher = SM4CBC(key, iv)
        enc = cipher.encrypt(filename.encode("utf-8"))
        return base64.urlsafe_b64encode(enc).decode("ascii")

    @staticmethod
    def decrypt_filename(enc_str: str, key: bytes) -> str:
        enc = base64.urlsafe_b64decode(enc_str.encode("ascii"))
        cipher = SM4CBC(key)
        return cipher.decrypt(enc, iv_prepended=True).decode("utf-8")

    @staticmethod
    def encrypt_content(content: bytes, key: bytes) -> bytes:
        iv = KeyManager.generate_iv()
        cipher = SM4CBC(key, iv)
        return cipher.encrypt(content)

    @staticmethod
    def decrypt_content(enc_content: bytes, key: bytes) -> bytes:
        cipher = SM4CBC(key)
        return cipher.decrypt(enc_content, iv_prepended=True)
