import sqlite3
from contextlib import contextmanager

from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    full_name       TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'customer',
    tc_kimlik_enc   TEXT,
    phone_enc       TEXT,
    address         TEXT,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until    TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS accounts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    iban_enc    TEXT NOT NULL,
    iban_index  TEXT NOT NULL UNIQUE,
    iban_last4  TEXT NOT NULL,
    balance     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS transactions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id          INTEGER NOT NULL REFERENCES accounts(id),
    counterparty_name   TEXT NOT NULL,
    counterparty_last4  TEXT NOT NULL,
    amount              INTEGER NOT NULL,
    description         TEXT NOT NULL DEFAULT '',
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS transfer_drafts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    from_account_id INTEGER NOT NULL REFERENCES accounts(id),
    to_iban_enc     TEXT NOT NULL,
    to_iban_last4   TEXT NOT NULL,
    amount          INTEGER NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'pending',
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_tx_account ON transactions(account_id, created_at);
"""


def connect() -> sqlite3.Connection:
    # isolation_level=None lets us control BEGIN/COMMIT ourselves
    conn = sqlite3.connect(settings.DATABASE_PATH, isolation_level=None, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def reset_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            "DROP TABLE IF EXISTS transfer_drafts; DROP TABLE IF EXISTS transactions;"
            "DROP TABLE IF EXISTS accounts; DROP TABLE IF EXISTS users;"
        )
        conn.executescript(SCHEMA)
