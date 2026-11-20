# VERA Katılım: AI Banking Security Lab

A graduation project on the security of AI-assisted banking. It is a working internet banking site with an AI assistant, built as a lab to attack first and defend second. Everything runs on localhost and all data is invented.

Banks are wiring AI assistants to real accounts. Once that assistant can read balances and move money, it becomes a new way in. So this project builds the same bank twice: one copy with the common mistakes left in, one with them fixed. A single switch in `.env` (`SECURE_MODE`) flips the whole app between the two, and a badge in the corner shows which side you are on.

Twelve issues are built in, across the OWASP Top 10 (2021) and the OWASP Top 10 for LLM Applications (2025): SQL injection, IDOR, stored XSS, weak password storage, no brute-force protection, broken transfer logic, and the model-specific ones like prompt injection, system-prompt leakage, excessive agency and unsafe output handling. Each is tagged in the code and covered by a test that proves it fires in vulnerable mode and is blocked in secure mode.

## Inside

A complete customer side (accounts, transfers, cards, bill payments, transaction history, an AI assistant) and a small admin panel, on a FastAPI backend with raw SQLite. Sensitive fields (IBAN, national ID, phone) are encrypted with AES-256-GCM, so a stolen copy of the database still gives nothing away.

## Stack

Python 3.11, FastAPI, Jinja2, SQLite (no ORM), Tailwind, bcrypt, the `cryptography` library, and pytest.

## Run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # fill SECRET_KEY and DATA_ENCRYPTION_KEY
python -m scripts.seed
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. The seed script prints the demo logins. Full setup, the vulnerability map and the test users are in [docs/kurulum-ve-aciklar.md](docs/kurulum-ve-aciklar.md), and each attack has a step-by-step note under [docs/attacks/](docs/attacks/).

Beyond the per-mode unit tests, each LLM attack was also run 10 times against the live model in both modes; the measurement script and what the numbers say about relying on a model's own guardrails are in [docs/attacks/canli-olcum.md](docs/attacks/canli-olcum.md).

## Note

Insecure by design, for learning only. Run it on your own machine and nowhere else. The bank, the customers, the IBANs and the ID numbers are all made up.

## Türkçe

Yapay zekâ destekli bankacılığın güvenliği üzerine bitirme projesi. Çalışan bir internet bankacılığı sitesi ve bir AI asistanı; `.env` içindeki `SECURE_MODE` ile aynı uygulama hem açık hem güvenli modda çalışır. OWASP Top 10 ve OWASP LLM Top 10 kapsamında 12 açık var, her biri hem kodda işaretli hem testli. Kurulum adımları, açık haritası ve adım adım saldırı notları `docs/` klasöründe. Yalnızca localhost üzerinde çalışır, tüm veriler uydurmadır.

## References

- OWASP Top 10 (2021): https://owasp.org/Top10/
- OWASP Top 10 for LLM Applications (2025): https://genai.owasp.org/llm-top-10/
