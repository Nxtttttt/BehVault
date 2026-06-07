import os

from src.database.db_manager import DatabaseManager
from src.vault.vault_manager import VaultManager


class VaultService:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.vault = VaultManager(db)
        self._authenticated_users: dict[int, bytes] = {}

    def unlock(self, user_id: int, vault_key: bytes):
        self._authenticated_users[user_id] = vault_key

    def lock(self, user_id: int):
        self._authenticated_users.pop(user_id, None)

    def is_authenticated(self, user_id: int) -> bool:
        return user_id in self._authenticated_users

    def get_vault_key(self, user_id: int) -> bytes | None:
        return self._authenticated_users.get(user_id)

    def import_file(self, user_id: int, filepath: str) -> int:
        key = self._authenticated_users.get(user_id)
        if key is None:
            raise PermissionError("Vault locked")
        return self.vault.import_file(user_id, filepath, key)

    def decrypt_file(self, user_id: int, file_id: int, output_dir: str) -> str:
        key = self._authenticated_users.get(user_id)
        if key is None:
            raise PermissionError("Vault locked")
        os.makedirs(output_dir, exist_ok=True)
        return self.vault.decrypt_file(file_id, key, output_dir)

    def delete_file(self, user_id: int, file_id: int):
        if not self.is_authenticated(user_id):
            raise PermissionError("Vault locked")
        self.vault.delete_file(file_id)

    def list_files(self, user_id: int) -> list[dict]:
        return self.vault.list_files(user_id)
