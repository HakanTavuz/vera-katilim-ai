# VULN-01: SQL injection (giriş formu)

**OWASP:** A03:2021 Injection
**Kod:** app/auth.py → `_vulnerable_login()` (`# VULN-01` yorumu)

## 1. Açıklama

Kullanıcı adı SQL sorgusuna string birleştirme ile ekleniyor. Saldırgan sorgunun yapısını değiştirip parolayı hiç bilmeden giriş yapabiliyor.

## 2. Adımlar

1. `SECURE_MODE=false` ile başlat, `/login` sayfasını aç.
2. Kullanıcı adı: `admin' --`  Parola: `herhangi`
3. `--` sorgunun geri kalanını (parola kontrolünü) yorum satırına çevirir. Admin paneline yönlendirilirsin.
4. Alternatif: `' OR 1=1 --` ilk kullanıcıyla (admin) giriş yapar.
5. Hatalı bir tırnak (`'`) gönderince sayfa veritabanı hatasını gösterir; bu da saldırganın sorguyu tahmin etmesini kolaylaştırır.

```bash
curl -i -X POST http://127.0.0.1:8000/login -d "username=admin' --&password=x"
# sadece localhost'a karşı:
sqlmap -u http://127.0.0.1:8000/login --data "username=a&password=b" -p username --level 2
```

## 3. Ekran görüntüsü: açık mod

`SECURE_MODE=false`

![VULN-01 saldırı](img/VULN-01-attack.png)

## 4. Etki

Kimlik doğrulama tamamen atlanır. Admin olarak tüm müşteri listesine erişim, veritabanının tamamının sızdırılması.

## 5. Düzeltme

```python
# önce
query = f"SELECT id FROM users WHERE username = '{username}' AND password_hash = '{_md5(password)}'"
# sonra
user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
```
Parametreli sorguda kullanıcı girdisi her zaman veri olarak gider, SQL olarak yorumlanmaz. Hata mesajı da genel tutulur.

## 6. Ekran görüntüsü: güvenli mod

`SECURE_MODE=true`

![VULN-01 engellendi](img/VULN-01-blocked.png)

## Notlar

- Deneme sayısı / başarı:
- Kullanılan araç:
