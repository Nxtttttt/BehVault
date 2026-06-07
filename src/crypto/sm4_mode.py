"""SM4 modes of operation: ECB and CBC with PKCS7 padding."""

import os

from src.crypto.sm4_core import SM4Core


class SM4ECB:
    def __init__(self, key: bytes):
        if len(key) != 16:
            raise ValueError("Key must be 16 bytes")
        self.key = key

    def encrypt(self, data: bytes) -> bytes:
        padded = self._pkcs7_pad(data, 16)
        result = bytearray()
        for i in range(0, len(padded), 16):
            result += SM4Core.encrypt_block(padded[i:i + 16], self.key)
        return bytes(result)

    def decrypt(self, data: bytes) -> bytes:
        if len(data) % 16 != 0:
            raise ValueError("Ciphertext length must be multiple of 16")
        result = bytearray()
        for i in range(0, len(data), 16):
            result += SM4Core.decrypt_block(data[i:i + 16], self.key)
        return self._pkcs7_unpad(bytes(result))

    @staticmethod
    def _pkcs7_pad(data: bytes, block_size: int) -> bytes:
        pad_len = block_size - (len(data) % block_size)
        return data + bytes([pad_len] * pad_len)

    @staticmethod
    def _pkcs7_unpad(data: bytes) -> bytes:
        pad_len = data[-1]
        if pad_len < 1 or pad_len > 16:
            raise ValueError("Invalid PKCS7 padding")
        return data[:-pad_len]


class SM4CBC:
    def __init__(self, key: bytes, iv: bytes = None):
        if len(key) != 16:
            raise ValueError("Key must be 16 bytes")
        self.key = key
        self.iv = iv or os.urandom(16)
        if len(self.iv) != 16:
            raise ValueError("IV must be 16 bytes")

    def encrypt(self, data: bytes) -> bytes:
        padded = SM4ECB._pkcs7_pad(data, 16)
        result = bytearray()
        prev = self.iv
        for i in range(0, len(padded), 16):
            block = bytes(a ^ b for a, b in zip(padded[i:i + 16], prev))
            enc = SM4Core.encrypt_block(block, self.key)
            result += enc
            prev = enc
        # Prepend IV to ciphertext
        return self.iv + bytes(result)

    def decrypt(self, data: bytes, iv_prepended: bool = True) -> bytes:
        if iv_prepended:
            if len(data) < 32:
                raise ValueError("Ciphertext too short")
            iv = data[:16]
            data = data[16:]
        else:
            iv = self.iv
        if len(data) % 16 != 0:
            raise ValueError("Ciphertext length must be multiple of 16")
        result = bytearray()
        prev = iv
        for i in range(0, len(data), 16):
            dec = SM4Core.decrypt_block(data[i:i + 16], self.key)
            result += bytes(a ^ b for a, b in zip(dec, prev))
            prev = data[i:i + 16]
        return SM4ECB._pkcs7_unpad(bytes(result))
