"""Prints the raw database contents: what an attacker sees after stealing securebank.db.

    python -m scripts.dump_db
"""
import sqlite3
import sys

from app.config import settings


def short(value, width: int) -> str:
    text = "NULL" if value is None else str(value)
    return text if len(text) <= width else text[:width - 1] + "…"


def dump_table(conn, table: str, columns: list[str], width: int = 34) -> None:
    rows = conn.execute(f"SELECT {', '.join(columns)} FROM {table}").fetchall()
    print(f"\n=== {table} ({len(rows)} rows) ===")
    print(" | ".join(c.ljust(width) for c in columns))
    print("-" * (len(columns) * (width + 3)))
    for row in rows:
        print(" | ".join(short(v, width).ljust(width) for v in row))


def main() -> None:
    try:
        conn = sqlite3.connect(f"file:{settings.DATABASE_PATH}?mode=ro", uri=True)
    except sqlite3.OperationalError:
        sys.exit(f"Database not found: {settings.DATABASE_PATH}. Run `python -m scripts.seed` first.")

    print(f"Raw dump of {settings.DATABASE_PATH}")
    dump_table(conn, "users", ["id", "username", "password_hash", "tc_kimlik_enc", "phone_enc"], 30)
    dump_table(conn, "accounts", ["id", "user_id", "iban_enc", "iban_last4", "balance"], 30)
    print("\nIBAN, TC and phone columns are AES-256-GCM ciphertexts. Without DATA_ENCRYPTION_KEY they are useless.")
    print("password_hash: 32 hex chars = MD5 (crackable in seconds), $2b$... = bcrypt.")


if __name__ == "__main__":
    main()
