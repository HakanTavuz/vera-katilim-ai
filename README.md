# VERA Katılım — Secure Banking Assistant (educational)

My final-year graduation project. It is a small internet banking site with an AI chat assistant, built so I can run security tests against it. The whole thing runs only on localhost and every customer record is made up.

Banks are starting to put AI assistants in front of real accounts. I wanted to show what that opens up: an assistant that can read balances and move money becomes a new way into the bank if it is wired carelessly. So I built the features twice. One version leaves the common mistakes in, the other fixes them, and a single setting in `.env` (`SECURE_MODE`) flips the whole app between the two. The red "VULNERABLE" / green "SECURE" badge in the corner shows which one is running.

It covers the classic web risks from the OWASP Top 10 (2021) and the newer ones from the OWASP Top 10 for LLM Applications (2025). Twelve issues are built in on purpose. Each is marked in the code with a comment like `# VULN-07: ... | OWASP: LLM01:2025`, so I can point to the exact line when I present it.

## What it has

Customer side: sign up and log in, a dashboard with balance and recent activity, money transfer, transaction history, cards, bill payments and a profile. The AI assistant (DeepSeek, tool-calling) can check the balance, read transactions and start a transfer. Admin side: a customer list and a suspicious-activity page. IBAN, national ID and phone are encrypted field by field with AES-256-GCM, so a stolen copy of the database still hides them.

## What the two modes change

In vulnerable mode the assistant decides whose account to read, transfers go through without asking, login has no rate limit, passwords are stored as plain MD5, and user text is pasted straight into the system prompt. In secure mode the account comes from the server session, a transfer only leaves as a draft until the user presses Confirm, tool output is wrapped as untrusted data and masked, passwords use bcrypt, and login has rate limiting and lockout. Every vulnerability has a step-by-step attack note under `docs/attacks/`.

## Built with

Python 3.11, FastAPI, Jinja2, raw SQLite (no ORM, so SQL injection stays visible in the code), Tailwind via CDN, bcrypt, and the `cryptography` library for AES. Tests run with pytest.

## Running it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill SECRET_KEY and DATA_ENCRYPTION_KEY
python -m scripts.seed
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000. The Turkish setup section below has the same steps in more detail, plus the test logins.

## Please read

This app is insecure by design and is only for learning. Run it on your own machine and nothing else. Do not deploy it or aim it at any real service or person. The bank, the customers, the IBANs and the ID numbers are all invented.

---

# VERA Katılım AI

> **Eğitim amaçlı, bilerek açık bırakılmış uygulama.**
> Sadece kendi bilgisayarında (`127.0.0.1`) çalıştır. Gerçek hiçbir bankaya, sisteme veya kişiye karşı kullanma.
> VERA Katılım uydurma bir bankadır, tüm müşteri verileri uydurmadır.

Proje konusu: yapay zekâ destekli bankacılık asistanlarının güvenliği. OWASP Top 10 (2021) ve
OWASP LLM Top 10 (2025) kapsamında sızma testi.

Ana soru: bankalar AI asistanlarına geçiyor. Bu hangi yeni riskleri getiriyor ve bu riskler nasıl önlenir?

## Kurulum

### Yerelde

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` içinde `SECRET_KEY` ve `DATA_ENCRYPTION_KEY` alanlarını doldur:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"
```

Sonra:

```bash
python -m scripts.seed
uvicorn app.main:app --reload
```

Adres: http://127.0.0.1:8000 · API dokümanı: http://127.0.0.1:8000/docs

### Docker

```bash
docker compose up --build
```

Port sadece `127.0.0.1:8000`'e bağlanır, ağdaki başka bir cihaz erişemez.
Veritabanını sıfırlamak için: `docker compose down -v`.

## Güvenlik modu

`.env` içindeki tek bir değişken bütün açıkları açar veya kapatır:

```
SECURE_MODE=false   # açıklar aktif
SECURE_MODE=true    # tüm düzeltmeler aktif
```

Değiştirdikten sonra sunucuyu yeniden başlat. Sağ üstteki rozet modu gösterir (kırmızı VULNERABLE / yeşil SECURE).

Her açık kodda şu yorumla işaretlidir, raporda satıra doğrudan referans verilebilir:

```python
# VULN-XX: <kısa açıklama> | OWASP: <kategori>
if settings.SECURE_MODE:
    ...  # düzeltilmiş kod
else:
    ...  # açık kod
```

Hepsini listelemek için: `grep -rn "VULN-" app/`

Parolalar seed sırasında o anki moda göre saklanır (açık modda MD5, güvenli modda bcrypt). Giriş kodu
hash'in biçimine bakarak ikisini de tanır, yani mod değiştirince yeniden seed gerekmez. Güvenli modda
MD5'li bir kullanıcı giriş yapınca hash'i otomatik bcrypt'e yükseltilir. VULN-05'in "önce/sonra"
ekran görüntüsü için modu değiştirip `python -m scripts.seed` çalıştır.

## Test kullanıcıları (hepsi uydurma)

| Kullanıcı | Parola | Rol | IBAN |
|---|---|---|---|
| `admin` | `Admin2026!` | admin | - |
| `ayse.yilmaz` | `Ayse2026!` | müşteri | TR00 0000 0000 0000 0000 0000 01 |
| `mehmet.kaya` | `Mehmet2026!` | müşteri | TR00 0000 0000 0000 0000 0000 02 |
| `zeynep.demir` | `Zeynep2026!` | müşteri | TR00 0000 0000 0000 0000 0000 03 |
| `can.ozturk` | `qwerty123` | müşteri | TR00 0000 0000 0000 0000 0000 04 |
| `elif.sahin` | `Elif2026!` | müşteri | TR00 0000 0000 0000 0000 0000 05 |

`can.ozturk` hesabının parolası brute-force (VULN-06) gösterimi için bilerek zayıf seçildi.
TC numaraları 0 ile başlar, bu yüzden hiçbiri geçerli bir TC kimlik numarası değildir.

## AI asistan

DeepSeek API'si (`deepseek-chat`) OpenAI uyumlu istemciyle, tool calling ile kullanılır.
`.env` içine `DEEPSEEK_API_KEY` yaz. Anahtar yoksa uygulama çalışmaya devam eder, asistan
"API anahtarı tanımlı değil" der.

| Araç | Açık mod | Güvenli mod |
|---|---|---|
| `get_balance` | `account_id`'yi model seçer | kimlik oturumdan gelir |
| `get_transactions` | `account_id`'yi model seçer, açıklamalar düz metin | kendi hesabı, `<untrusted_data>` bloğu |
| `get_customer_profile` | `customer_id`'yi model seçer, TC/telefon/IBAN çözülmüş | kendi profili, maskeli |
| `transfer_money` | herhangi bir hesaptan onaysız transfer | sadece taslak, kullanıcı Onayla'ya basmalı |

## Açıklar

| Kod | Açık | OWASP | Not |
|---|---|---|---|
| VULN-01 | SQL injection (giriş) | A03:2021 | [docs/attacks/VULN-01.md](docs/attacks/VULN-01.md) |
| VULN-02 | IDOR | A01:2021 | [VULN-02](docs/attacks/VULN-02.md) |
| VULN-03 | Stored XSS | A03:2021 | [VULN-03](docs/attacks/VULN-03.md) |
| VULN-04 | Eksi tutarla transfer | A04:2021 | [VULN-04](docs/attacks/VULN-04.md) |
| VULN-05 | MD5 parola | A02:2021 | [VULN-05](docs/attacks/VULN-05.md) |
| VULN-06 | Brute-force koruması yok | A07:2021 | [VULN-06](docs/attacks/VULN-06.md) |
| VULN-07 | Doğrudan prompt injection | LLM01:2025 | [VULN-07](docs/attacks/VULN-07.md) |
| VULN-08 | Başka müşterinin verisi | LLM02:2025 | [VULN-08](docs/attacks/VULN-08.md) |
| VULN-09 | System prompt sızıntısı | LLM07:2025 | [VULN-09](docs/attacks/VULN-09.md) |
| VULN-10 | Onaysız transfer | LLM06:2025 | [VULN-10](docs/attacks/VULN-10.md) |
| VULN-11 | Dolaylı prompt injection | LLM01:2025 | [VULN-11](docs/attacks/VULN-11.md) |
| VULN-12 | Asistan çıktısında XSS | LLM05:2025 | [VULN-12](docs/attacks/VULN-12.md) |

## AES-256-GCM katmanı

`iban`, `tc_kimlik_no` ve `phone` alanları veritabanında `base64(nonce || ciphertext || tag)` biçiminde
şifreli durur, her kayıtta ayrı rastgele nonce kullanılır ([app/crypto.py](app/crypto.py)).
IBAN ile hesap bulabilmek için ayrıca HMAC-SHA256 ile üretilmiş bir arama değeri (`iban_index`) saklanır.

Anahtar sadece `.env` içindeki `DATA_ENCRYPTION_KEY`'dir, kodda veya veritabanında bulunmaz.
Gerçek bir sistemde bu anahtar HashiCorp Vault veya bir bulut KMS hizmetinde tutulur.

Saldırgan veritabanı dosyasını çalarsa ne görür:

```bash
python -m scripts.dump_db
```

## Testler

```bash
pytest -v
```

`tests/test_vulns.py` her açığın açık modda çalıştığını, güvenli modda engellendiğini kontrol eder.
LLM'in kendisi deterministik olmadığı için AI testleri sahte (senaryolu) bir istemci kullanır;
test edilen şey modelin ne söylediği değil, kodumuzun modele neye izin verdiğidir.
Gerçek model üzerindeki başarı oranları `docs/attacks/` altındaki notlara elle yazılır.

## Fikir kaynakları

- OWASP Top 10 (2021): https://owasp.org/Top10/
- OWASP Top 10 for LLM Applications (2025): https://genai.owasp.org/llm-top-10/
- İlham alınan açık kaynak eğitim projeleri: OWASP Juice Shop, DVWA, Damn Vulnerable LLM Agent
