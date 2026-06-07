"""Vault and file crypto tests."""

import sys
import os
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.crypto.file_crypto import FileEncryptor
from src.crypto.key_manager import KeyManager
from src.database.db_manager import DatabaseManager
from src.vault.vault_manager import VaultManager


def test_filename_encrypt_decrypt():
    key, _ = KeyManager.derive_key("testkey")
    original = "机密文件_top_secret.pdf"
    enc = FileEncryptor.encrypt_filename(original, key)
    assert enc != original
    dec = FileEncryptor.decrypt_filename(enc, key)
    assert dec == original


def test_content_encrypt_decrypt():
    key = KeyManager.generate_random_key()
    sizes = [1, 16, 100, 1024, 10000]
    for size in sizes:
        content = os.urandom(size)
        enc = FileEncryptor.encrypt_content(content, key)
        dec = FileEncryptor.decrypt_content(enc, key)
        assert dec == content, f"Round-trip failed at size {size}"


def test_key_derivation_deterministic():
    pw = "mypassword"
    salt = os.urandom(16)
    k1, _ = KeyManager.derive_key(pw, salt)
    k2, _ = KeyManager.derive_key(pw, salt)
    assert k1 == k2


def test_key_derivation_different():
    pw1 = "password1"
    pw2 = "password2"
    k1, _ = KeyManager.derive_key(pw1)
    k2, _ = KeyManager.derive_key(pw2)
    assert k1 != k2


def test_vault_import_decrypt():
    db_path = os.path.join(tempfile.gettempdir(), "test_vault.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    db = DatabaseManager(db_path)
    vault = VaultManager(db)

    db.create_user("vault_test", "hash", "{}")
    user_id = 1

    key = KeyManager.generate_random_key()
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"Hello BehVault! This is secret content.")
        tmp_path = f.name

    file_id = vault.import_file(user_id, tmp_path, key)
    assert file_id > 0

    files = vault.list_files(user_id)
    assert len(files) == 1

    output_dir = tempfile.mkdtemp()
    output_path = vault.decrypt_file(file_id, key, output_dir)
    with open(output_path, "rb") as f:
        content = f.read()
    assert content == b"Hello BehVault! This is secret content."

    vault.delete_file(file_id)
    assert len(vault.list_files(user_id)) == 0

    db.close()
    os.remove(db_path)
    os.unlink(tmp_path)


def test_vault_wrong_key():
    db_path = os.path.join(tempfile.gettempdir(), "test_vault2.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    db = DatabaseManager(db_path)
    vault = VaultManager(db)

    db.create_user("vt2", "hash", "{}")

    key1 = KeyManager.generate_random_key()
    key2 = KeyManager.generate_random_key()

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"secret data")
        tmp_path = f.name

    file_id = vault.import_file(1, tmp_path, key1)

    try:
        vault.decrypt_file(file_id, key2, tempfile.mkdtemp())
        assert False, "Should have raised an error"
    except (ValueError, Exception):
        pass

    vault.delete_file(file_id)
    db.close()
    os.remove(db_path)
    os.unlink(tmp_path)


if __name__ == "__main__":
    test_filename_encrypt_decrypt()
    test_content_encrypt_decrypt()
    test_key_derivation_deterministic()
    test_key_derivation_different()
    test_vault_import_decrypt()
    test_vault_wrong_key()
    print("All vault tests passed!")
