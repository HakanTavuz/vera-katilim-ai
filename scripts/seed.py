"""Fills the database with fake customers and transactions.

    python -m scripts.seed            # wipe and reseed
    python -m scripts.seed --if-empty # only seed a fresh database (used by docker)

Passwords are hashed with the current mode: MD5 when SECURE_MODE=false, bcrypt when true.
Everything here is made up. TC numbers start with 0, which is never valid.
"""
import random
import sys
from datetime import datetime, timedelta, timezone

from app.auth import hash_password
from app.config import settings
from app.crypto import encrypt_field, iban_index
from app.db import get_conn, init_db, reset_db

ADMIN = {"username": "admin", "password": "Admin2026!", "full_name": "Sistem Yöneticisi"}

CUSTOMERS = [
    {"username": "ayse.yilmaz", "password": "Ayse2026!", "full_name": "Ayşe Yılmaz",
     "tc": "01234567890", "phone": "0555 000 00 11", "address": "Örnek Mah. Deneme Sok. No:1, Ankara",
     "balance": 24_850_00},
    {"username": "mehmet.kaya", "password": "Mehmet2026!", "full_name": "Mehmet Kaya",
     "tc": "02345678901", "phone": "0555 000 00 22", "address": "Test Cad. No:12, İstanbul",
     "balance": 8_420_50},
    {"username": "zeynep.demir", "password": "Zeynep2026!", "full_name": "Zeynep Demir",
     "tc": "03456789012", "phone": "0555 000 00 33", "address": "Uydurma Blv. No:7, İzmir",
     "balance": 152_300_00},
    {"username": "can.ozturk", "password": "qwerty123", "full_name": "Can Öztürk",
     "tc": "04567890123", "phone": "0555 000 00 44", "address": "Sahte Sok. No:3, Bursa",
     "balance": 3_115_75},
    {"username": "elif.sahin", "password": "Elif2026!", "full_name": "Elif Şahin",
     "tc": "05678901234", "phone": "0555 000 00 55", "address": "Hayali Mah. No:9, Antalya",
     "balance": 41_990_00},
]

MERCHANTS = [
    ("Market Zinciri A.Ş.", (-1_800_00, -85_00), ["Haftalık market", "Market alışverişi", "Manav"]),
    ("Elektrik Dağıtım", (-950_00, -320_00), ["Elektrik faturası"]),
    ("Su İdaresi", (-420_00, -110_00), ["Su faturası"]),
    ("İnternet Hizmetleri", (-650_00, -399_00), ["İnternet faturası"]),
    ("Akaryakıt İstasyonu", (-2_500_00, -400_00), ["Benzin", "Yakıt"]),
    ("Kafe Örnek", (-380_00, -55_00), ["Kahve", "Kahvaltı"]),
    ("Online Mağaza", (-4_200_00, -150_00), ["Online alışveriş", "Kitap siparişi"]),
    ("İşveren Ltd. Şti.", (35_000_00, 55_000_00), ["Maaş ödemesi"]),
]

PEER_NOTES = ["Yemek parası", "Borç ödemesi", "Kira payı", "Doğum günü hediyesi", "Tatil masrafı", "Teşekkürler"]


def demo_iban(n: int) -> str:
    return f"TR000000{n:018d}"


def _ts(rng: random.Random, now: datetime) -> str:
    return (now - timedelta(days=rng.randint(0, 60), minutes=rng.randint(0, 1440))).strftime("%Y-%m-%d %H:%M:%S")


def run_seed() -> None:
    rng = random.Random(42)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    reset_db()

    with get_conn() as conn:
        conn.execute("BEGIN")
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, 'admin')",
            (ADMIN["username"], hash_password(ADMIN["password"]), ADMIN["full_name"]),
        )

        accounts = []
        for i, c in enumerate(CUSTOMERS, start=1):
            uid = conn.execute(
                "INSERT INTO users (username, password_hash, full_name, role, tc_kimlik_enc, phone_enc, address) "
                "VALUES (?, ?, ?, 'customer', ?, ?, ?)",
                (c["username"], hash_password(c["password"]), c["full_name"],
                 encrypt_field(c["tc"]), encrypt_field(c["phone"]), c["address"]),
            ).lastrowid
            iban = demo_iban(i)
            aid = conn.execute(
                "INSERT INTO accounts (user_id, iban_enc, iban_index, iban_last4, balance) VALUES (?, ?, ?, ?, ?)",
                (uid, encrypt_field(iban), iban_index(iban), iban[-4:], c["balance"]),
            ).lastrowid
            accounts.append({"id": aid, "name": c["full_name"], "last4": iban[-4:]})

        for acc in accounts:
            for _ in range(rng.randint(10, 20)):
                if rng.random() < 0.3:
                    other = rng.choice([a for a in accounts if a is not acc])
                    amount = rng.randint(50, 1500) * 100
                    note = rng.choice(PEER_NOTES)
                    ts = _ts(rng, now)
                    conn.execute(
                        "INSERT INTO transactions (account_id, counterparty_name, counterparty_last4, amount, description, created_at) "
                        "VALUES (?, ?, ?, ?, ?, ?)", (acc["id"], other["name"], other["last4"], -amount, note, ts))
                    conn.execute(
                        "INSERT INTO transactions (account_id, counterparty_name, counterparty_last4, amount, description, created_at) "
                        "VALUES (?, ?, ?, ?, ?, ?)", (other["id"], acc["name"], acc["last4"], amount, note, ts))
                else:
                    name, (lo, hi), notes = rng.choice(MERCHANTS)
                    conn.execute(
                        "INSERT INTO transactions (account_id, counterparty_name, counterparty_last4, amount, description, created_at) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (acc["id"], name, f"{rng.randint(0, 9999):04d}", rng.randint(lo, hi), rng.choice(notes), _ts(rng, now)))
        conn.execute("COMMIT")


def main() -> None:
    if "--if-empty" in sys.argv:
        init_db()
        with get_conn() as conn:
            if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
                print("Database already has data, skipping seed.")
                return
    run_seed()
    mode = "bcrypt" if settings.SECURE_MODE else "MD5"
    print(f"Seeded {len(CUSTOMERS)} customers + 1 admin into {settings.DATABASE_PATH} (passwords: {mode}).")
    print(f"  admin / {ADMIN['password']}")
    for i, c in enumerate(CUSTOMERS, start=1):
        print(f"  {c['username']} / {c['password']}  IBAN {demo_iban(i)}")


if __name__ == "__main__":
    main()
