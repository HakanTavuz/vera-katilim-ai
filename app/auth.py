import hashlib
import os
import sqlite3
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Request

from app.config import settings
from app.db import get_conn

MAX_FAILED_LOGINS = 5
LOCK_MINUTES = 15
MAX_PASSWORD_BYTES = 72  # bcrypt ignores (and bcrypt>=5 rejects) anything longer
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))  # tests lower this to stay fast


class LoginRequired(Exception):
    pass


class Forbidden(Exception):
    pass


class RateLimiter:
    """Sliding-window limiter kept in memory. Good enough for a single process."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


login_limiter = RateLimiter(limit=10, window_seconds=60)


def _md5(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()


def _is_bcrypt(stored: str) -> bool:
    return stored.startswith(("$2a$", "$2b$", "$2y$"))


def hash_password(password: str) -> str:
    # VULN-05: passwords stored as unsalted MD5 | OWASP: A02:2021 Cryptographic Failures
    if settings.SECURE_MODE:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode()
    else:
        return _md5(password)


def verify_password(password: str, stored: str) -> bool:
    # The DB can hold both formats (seeded in one mode, used in the other), so look at the hash itself.
    if _is_bcrypt(stored):
        pw = password.encode()
        if len(pw) > MAX_PASSWORD_BYTES:
            return False
        return bcrypt.checkpw(pw, stored.encode())
    return stored == _md5(password)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def get_user(conn: sqlite3.Connection, user_id: int):
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def _vulnerable_login(conn: sqlite3.Connection, username: str, password: str):
    # VULN-01: username concatenated into SQL | OWASP: A03:2021 Injection
    query = (
        f"SELECT id FROM users WHERE username = '{username}' "
        f"AND password_hash = '{_md5(password)}'"
    )
    try:
        row = conn.execute(query).fetchone()
    except sqlite3.Error as exc:
        # leaking the DB error is part of the lesson: it helps the attacker tune the payload
        return None, f"Veritabanı hatası: {exc}"
    if row:
        return get_user(conn, row["id"]), None

    # accounts created in secure mode carry bcrypt hashes, MD5 comparison above can't match them
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if user and _is_bcrypt(user["password_hash"]) and verify_password(password, user["password_hash"]):
        return user, None
    return None, "Kullanıcı adı veya parola hatalı."


def _secure_login(conn: sqlite3.Connection, username: str, password: str, client_ip: str):
    # VULN-06: no rate limit or lockout on login | OWASP: A07:2021 Identification and Authentication Failures
    if not login_limiter.allow(client_ip):
        return None, "Çok fazla deneme yaptınız. Lütfen bir dakika sonra tekrar deneyin."

    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    generic_error = "Kullanıcı adı veya parola hatalı."

    if user is None:
        # burn similar time so response timing doesn't reveal which usernames exist
        bcrypt.checkpw(b"dummy", bcrypt.hashpw(b"dummy", bcrypt.gensalt(rounds=BCRYPT_ROUNDS)))
        return None, generic_error

    if user["locked_until"] and datetime.fromisoformat(user["locked_until"]) > _now():
        return None, f"Hesap çok sayıda hatalı deneme nedeniyle {LOCK_MINUTES} dakika kilitlendi."

    if not verify_password(password, user["password_hash"]):
        attempts = user["failed_attempts"] + 1
        locked_until = None
        if attempts >= MAX_FAILED_LOGINS:
            locked_until = (_now() + timedelta(minutes=LOCK_MINUTES)).isoformat()
            attempts = 0
        conn.execute(
            "UPDATE users SET failed_attempts = ?, locked_until = ? WHERE id = ?",
            (attempts, locked_until, user["id"]),
        )
        if locked_until:
            return None, f"Hesap çok sayıda hatalı deneme nedeniyle {LOCK_MINUTES} dakika kilitlendi."
        return None, generic_error

    new_hash = user["password_hash"]
    if not _is_bcrypt(new_hash):
        # legacy MD5 row: upgrade it now that we know the plain password
        new_hash = hash_password(password)
    conn.execute(
        "UPDATE users SET failed_attempts = 0, locked_until = NULL, password_hash = ? WHERE id = ?",
        (new_hash, user["id"]),
    )
    return get_user(conn, user["id"]), None


def authenticate(username: str, password: str, client_ip: str):
    with get_conn() as conn:
        if settings.SECURE_MODE:
            if len(password.encode()) > MAX_PASSWORD_BYTES:
                return None, "Kullanıcı adı veya parola hatalı."
            return _secure_login(conn, username, password, client_ip)
        else:
            return _vulnerable_login(conn, username, password)


def current_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    with get_conn() as conn:
        return get_user(conn, user_id)


def require_user(request: Request):
    user = current_user(request)
    if user is None:
        raise LoginRequired()
    return user


def require_admin(request: Request):
    user = require_user(request)
    if user["role"] != "admin":
        raise Forbidden()
    return user


def require_customer(request: Request):
    user = require_user(request)
    if user["role"] != "customer":
        raise Forbidden()
    return user
