# Kurulum, güvenlik modu ve açık listesi

Bu dosya projenin ayrıntılı kurulum ve referans belgesidir. Kısa tanıtım için ana [README](../README.md) dosyasına bak.

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

Her açık kodda şu yorumla işaretlidir:

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
MD5'li bir kullanıcı giriş yapınca hash'i otomatik bcrypt'e yükseltilir.

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
| VULN-01 | SQL injection (giriş) | A03:2021 | [VULN-01](attacks/VULN-01.md) |
| VULN-02 | IDOR | A01:2021 | [VULN-02](attacks/VULN-02.md) |
| VULN-03 | Stored XSS | A03:2021 | [VULN-03](attacks/VULN-03.md) |
| VULN-04 | Eksi tutarla transfer | A04:2021 | [VULN-04](attacks/VULN-04.md) |
| VULN-05 | MD5 parola | A02:2021 | [VULN-05](attacks/VULN-05.md) |
| VULN-06 | Brute-force koruması yok | A07:2021 | [VULN-06](attacks/VULN-06.md) |
| VULN-07 | Doğrudan prompt injection | LLM01:2025 | [VULN-07](attacks/VULN-07.md) |
| VULN-08 | Başka müşterinin verisi | LLM02:2025 | [VULN-08](attacks/VULN-08.md) |
| VULN-09 | System prompt sızıntısı | LLM07:2025 | [VULN-09](attacks/VULN-09.md) |
| VULN-10 | Onaysız transfer | LLM06:2025 | [VULN-10](attacks/VULN-10.md) |
| VULN-11 | Dolaylı prompt injection | LLM01:2025 | [VULN-11](attacks/VULN-11.md) |
| VULN-12 | Asistan çıktısında XSS | LLM05:2025 | [VULN-12](attacks/VULN-12.md) |

## AES-256-GCM katmanı

`iban`, `tc_kimlik_no` ve `phone` alanları veritabanında `base64(nonce || ciphertext || tag)` biçiminde
şifreli durur, her kayıtta ayrı rastgele nonce kullanılır ([app/crypto.py](../app/crypto.py)).
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
test edilen şey modelin ne söylediği değil, kodun modele neye izin verdiğidir.
Gerçek model üzerindeki başarı oranları `docs/attacks/` altındaki notlara elle yazılır.
