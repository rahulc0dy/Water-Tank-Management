"""SQLite helpers for user management and authentication."""
from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

DB_PATH = Path(
    os.getenv(
        "WATERTANK_DB_FILE",
        Path(__file__).resolve().parent.parent / "var" / "app.db",
    )
)


def _ensure_dir() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_db_path() -> Path:
    _ensure_dir()
    return DB_PATH


def init_db() -> None:
    """Initialise the database schema if it does not yet exist."""
    _ensure_dir()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_login TEXT
            )
            """
        )
        conn.commit()


@contextmanager
def get_connection():
    """Context manager yielding a SQLite connection with row factory enabled."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _normalise_username(username: str) -> str:
    return username.strip().lower()


def _hash_password(password: str, salt: Optional[str] = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, digest = stored_hash.split("$", 1)
    except ValueError:
        return False
    candidate = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return secrets.compare_digest(candidate, digest)


def create_user(username: str, password: str) -> None:
    username_clean = _normalise_username(username)
    if len(username_clean) < 3:
        raise ValueError("Username must be at least 3 characters long")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters long")

    password_hash = _hash_password(password)
    created_at = datetime.utcnow().isoformat()

    with get_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username_clean, password_hash, created_at),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError("Username already exists") from exc


def authenticate_user(username: str, password: str) -> bool:
    username_clean = _normalise_username(username)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE username = ?",
            (username_clean,),
        ).fetchone()
        if row is None:
            return False
        if not _verify_password(password, row["password_hash"]):
            return False
        conn.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), row["id"]),
        )
        conn.commit()
        return True


def get_user(username: str) -> Optional[Dict[str, str]]:
    username_clean = _normalise_username(username)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT username, created_at, last_login FROM users WHERE username = ?",
            (username_clean,),
        ).fetchone()
        if row is None:
            return None
        return {
            "username": row["username"],
            "created_at": row["created_at"],
            "last_login": row["last_login"],
        }


def ensure_default_user() -> Optional[str]:
    """Create a default user from environment variables if provided."""
    username = os.getenv("WATERTANK_DEFAULT_USER")
    password = os.getenv("WATERTANK_DEFAULT_PASSWORD")
    if not username or not password:
        return None
    if get_user(username) is None:
        create_user(username, password)
    return _normalise_username(username)
    