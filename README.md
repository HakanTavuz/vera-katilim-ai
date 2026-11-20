# VERA Katılım: AI Banking Security Lab

My graduation project on the security of AI-assisted banking. It is a small internet banking site with an AI assistant that I first attack and then fix. It runs only on localhost and all the data is made up.

The idea: if a bank's assistant can read balances and send money, an attacker can try to use the assistant itself. The app has a `SECURE_MODE` setting in `.env`. With `false` the common mistakes are left in, with `true` they are fixed. A badge in the top corner shows which mode is on.

There are 12 vulnerabilities from the OWASP Top 10 (2021) and the OWASP Top 10 for LLM Applications (2025): SQL injection, IDOR, stored XSS, MD5 passwords, no brute-force protection, broken transfer logic, prompt injection (direct and indirect), leaking another customer's data, system prompt leakage, transfers without confirmation and XSS in the assistant's output. Each one is marked in the code with a `VULN-XX` comment and has a test that checks it works in vulnerable mode and is blocked in secure mode.

## What's in it

Customer pages (accounts, transfers, cards, bill payments, transaction history, the AI assistant) and a small admin panel. The backend is FastAPI with plain SQLite. IBAN, national ID and phone number are stored encrypted with AES-256-GCM, so a copy of the database file doesn't show them.

## Stack

Python 3.11, FastAPI, Jinja2, SQLite (no ORM), Tailwind, bcrypt, `cryptography`, pytest. The assistant uses the DeepSeek API.

## Run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # fill SECRET_KEY and DATA_ENCRYPTION_KEY
python -m scripts.seed
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. The seed script prints the demo logins. Setup details, the list of vulnerabilities and the test users are in [docs/kurulum-ve-aciklar.md](docs/kurulum-ve-aciklar.md). Each attack has its own step-by-step note in [docs/attacks/](docs/attacks/).

The unit tests use a fake LLM. I also ran each LLM attack 10 times against the real model in both modes; the script and the results are in [docs/attacks/canli-olcum.md](docs/attacks/canli-olcum.md).

## Note

This app is insecure on purpose and only for learning. Run it on your own machine only. The bank, customers, IBANs and ID numbers are all fake.

## Türkçe

Yapay zekâ destekli bankacılığın güvenliği üzerine bitirme projem. AI asistanı olan basit bir internet bankacılığı sitesi. `.env` içindeki `SECURE_MODE` ile aynı uygulama açık ya da güvenli modda çalışıyor. OWASP Top 10 ve OWASP LLM Top 10'dan 12 açık var, her biri kodda işaretli ve testi yazılı. Kurulum, açık listesi ve saldırı notları `docs/` klasöründe. Sadece localhost'ta çalışır, bütün veriler uydurma.

## References

- OWASP Top 10 (2021): https://owasp.org/Top10/
- OWASP Top 10 for LLM Applications (2025): https://genai.owasp.org/llm-top-10/
