"""SM4 cipher correctness tests against GB/T 32907-2016 test vectors."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.crypto.sm4_core import SM4Core
from src.crypto.sm4_mode import SM4ECB, SM4CBC


def test_encrypt_block_official_vector():
    """GB/T 32907-2016 Appendix A.1: single block encryption."""
    key = bytes.fromhex("0123456789abcdeffedcba9876543210")
    plain = bytes.fromhex("0123456789abcdeffedcba9876543210")
    expected = bytes.fromhex("681edf34d206965e86b3e94f536e4246")
    result = SM4Core.encrypt_block(plain, key)
    assert result == expected, f"Expected {expected.hex()}, got {result.hex()}"


def test_decrypt_block_official_vector():
    """GB/T 32907-2016: decrypt the encrypted block."""
    key = bytes.fromhex("0123456789abcdeffedcba9876543210")
    plain = bytes.fromhex("0123456789abcdeffedcba9876543210")
    cipher = SM4Core.encrypt_block(plain, key)
    result = SM4Core.decrypt_block(cipher, key)
    assert result == plain


def test_encrypt_decrypt_round_trip():
    """Random key/plain round-trip test."""
    for i in range(100):
        key = os.urandom(16)
        plain = os.urandom(16)
        enc = SM4Core.encrypt_block(plain, key)
        dec = SM4Core.decrypt_block(enc, key)
        assert dec == plain, f"Round-trip failed at iteration {i}"


def test_ecb_mode():
    """SM4-ECB with PKCS7 padding."""
    key = os.urandom(16)
    ecb = SM4ECB(key)
    for length in [1, 15, 16, 17, 31, 32, 33, 64, 100, 255, 256]:
        data = os.urandom(length)
        enc = ecb.encrypt(data)
        dec = ecb.decrypt(enc)
        assert dec == data, f"ECB round-trip failed at length {length}"


def test_cbc_mode():
    """SM4-CBC with IV prepended."""
    key = os.urandom(16)
    iv = os.urandom(16)
    cbc = SM4CBC(key, iv)
    for length in [1, 15, 16, 17, 31, 32, 64, 100, 256]:
        data = os.urandom(length)
        enc = cbc.encrypt(data)
        dec = cbc.decrypt(enc)
        assert dec == data, f"CBC round-trip failed at length {length}"


def test_cbc_iv_randomness():
    """CBC produces different ciphertext for same plaintext with random IV."""
    key = os.urandom(16)
    data = b"test message"
    cbc1 = SM4CBC(key)
    cbc2 = SM4CBC(key)
    enc1 = cbc1.encrypt(data)
    enc2 = cbc2.encrypt(data)
    assert enc1 != enc2, "CBC with random IV should produce different ciphertexts"


def test_invalid_key_size():
    """Ensure ValueError for invalid key/block sizes."""
    try:
        SM4Core.encrypt_block(b"short", b"16-byte-key-here")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_pkcs7_padding_edge():
    """Test PKCS7 padding edge cases."""
    key = os.urandom(16)
    ecb = SM4ECB(key)
    data = b"A" * 16  # exact block
    enc = ecb.encrypt(data)
    dec = ecb.decrypt(enc)
    assert dec == data


def test_gmssl_compatibility():
    """Verify single block matches gmssl output."""
    try:
        from gmssl.sm4 import CryptSM4, SM4_ENCRYPT
        key = bytes.fromhex("0123456789abcdeffedcba9876543210")
        plain = bytes.fromhex("0123456789abcdeffedcba9876543210")
        self_enc = SM4Core.encrypt_block(plain, key)
        gmssl_cipher = CryptSM4()
        gmssl_cipher.set_key(key, SM4_ENCRYPT)
        gmssl_enc = gmssl_cipher.crypt_ecb(plain)
        assert self_enc == gmssl_enc[:16], f"Self: {self_enc.hex()}, gmssl: {gmssl_enc[:16].hex()}"
    except ImportError:
        pass  # gmssl not installed, skip


if __name__ == "__main__":
    test_encrypt_block_official_vector()
    test_decrypt_block_official_vector()
    test_encrypt_decrypt_round_trip()
    test_ecb_mode()
    test_cbc_mode()
    test_cbc_iv_randomness()
    test_invalid_key_size()
    test_pkcs7_padding_edge()
    test_gmssl_compatibility()
    print("All SM4 tests passed!")
