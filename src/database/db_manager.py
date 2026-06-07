import sqlite3
import os

from src.database.schema import ALL_TABLES


class DatabaseManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "behvault.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    def _init_schema(self):
        for sql in ALL_TABLES:
            self.conn.execute(sql)
        self.conn.commit()

    # ─── users ────────────────────────────────────────────────

    def create_user(self, username: str, password_hash: str, template_blob: str = None) -> int:
        cursor = self.conn.execute(
            "INSERT INTO users (username, password_hash, template_blob) VALUES (?, ?, ?)",
            (username, password_hash, template_blob),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_user(self, user_id: int) -> dict | None:
        cursor = self.conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def get_user_by_username(self, username: str) -> dict | None:
        cursor = self.conn.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def update_user_template(self, user_id: int, template_blob: str):
        self.conn.execute("UPDATE users SET template_blob = ? WHERE id = ?", (template_blob, user_id))
        self.conn.commit()

    def delete_user(self, user_id: int):
        self.conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        self.conn.commit()

    def list_users(self) -> list[dict]:
        cursor = self.conn.execute("SELECT id, username, created_at FROM users ORDER BY id")
        return [dict(row) for row in cursor.fetchall()]

    # ─── samples ──────────────────────────────────────────────

    def save_sample(self, user_id: int, features_json: str) -> int:
        cursor = self.conn.execute(
            "INSERT INTO samples (user_id, features_json) VALUES (?, ?)",
            (user_id, features_json),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_samples(self, user_id: int, limit: int = None) -> list[dict]:
        if limit is not None:
            cursor = self.conn.execute(
                "SELECT * FROM samples WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            )
        else:
            cursor = self.conn.execute(
                "SELECT * FROM samples WHERE user_id = ? ORDER BY id", (user_id,)
            )
        return [dict(row) for row in cursor.fetchall()]

    def get_sample_count(self, user_id: int) -> int:
        cursor = self.conn.execute("SELECT COUNT(*) FROM samples WHERE user_id = ?", (user_id,))
        return cursor.fetchone()[0]

    # ─── login_logs ───────────────────────────────────────────

    def save_login_log(self, user_id: int, risk_score: int, result: str) -> int:
        cursor = self.conn.execute(
            "INSERT INTO login_logs (user_id, risk_score, result) VALUES (?, ?, ?)",
            (user_id, risk_score, result),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_login_logs(self, user_id: int, limit: int = 100) -> list[dict]:
        cursor = self.conn.execute(
            "SELECT * FROM login_logs WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
        return [dict(row) for row in cursor.fetchall()]

    # ─── files ────────────────────────────────────────────────

    def save_file(self, user_id: int, enc_filename: bytes, enc_content: bytes, key_hint: str = "") -> int:
        cursor = self.conn.execute(
            "INSERT INTO files (user_id, enc_filename, enc_content, key_hint) VALUES (?, ?, ?, ?)",
            (user_id, enc_filename, enc_content, key_hint),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_files(self, user_id: int) -> list[dict]:
        cursor = self.conn.execute(
            "SELECT id, user_id, enc_filename, key_hint, created_at FROM files WHERE user_id = ? ORDER BY id",
            (user_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_file(self, file_id: int) -> dict | None:
        cursor = self.conn.execute("SELECT * FROM files WHERE id = ?", (file_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def delete_file(self, file_id: int):
        self.conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()
