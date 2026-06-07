import os

from src.crypto.file_crypto import FileEncryptor
from src.crypto.key_manager import KeyManager
from src.database.db_manager import DatabaseManager


class VaultManager:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def import_file(self, user_id: int, filepath: str, vault_key: bytes) -> int:
        filename = os.path.basename(filepath)
        with open(filepath, "rb") as f:
            content = f.read()
        enc_filename = FileEncryptor.encrypt_filename(filename, vault_key)
        enc_content = FileEncryptor.encrypt_content(content, vault_key)
        return self.db.save_file(user_id, enc_filename, enc_content)

    def decrypt_file(self, file_id: int, vault_key: bytes, output_dir: str) -> str:
        record = self.db.get_file(file_id)
        if record is None:
            raise FileNotFoundError(f"File {file_id} not found")
        filename = FileEncryptor.decrypt_filename(record["enc_filename"], vault_key)
        content = FileEncryptor.decrypt_content(record["enc_content"], vault_key)
        output_path = os.path.join(output_dir, filename)
        with open(output_path, "wb") as f:
            f.write(content)
        return output_path

    def delete_file(self, file_id: int):
        self.db.delete_file(file_id)

    def list_files(self, user_id: int) -> list[dict]:
        return self.db.get_files(user_id)

    def decrypt_filename_preview(self, file_id: int, vault_key: bytes) -> str:
        record = self.db.get_file(file_id)
        if record is None:
            raise FileNotFoundError(f"File {file_id} not found")
        return FileEncryptor.decrypt_filename(record["enc_filename"], vault_key)
