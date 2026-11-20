# VULN-02: IDOR (başka hesabın görüntülenmesi)

**OWASP:** A01:2021 Broken Access Control
**Kod:** app/routes/accounts.py → `_load_account_for()` (`# VULN-02` yorumu)

## 1. Açıklama

Hesap sayfası ve API, URL'deki `account_id`'nin oturumdaki kullanıcıya ait olup olmadığını kontrol etmiyor.

## 2. Adımlar

1. `ayse.yilmaz` ile giriş yap. Dashboard'daki "Hesap detayı" `/account/1` adresine gider.
2. Adres çubuğunda `/account/2` yaz: Mehmet Kaya'nın IBAN'ı, bakiyesi ve tüm hareketleri görünür.
3. API üzerinden de aynısı: `/api/transactions?account_id=3`
4. Burp Intruder ile `account_id` 1-10 arası denenerek tüm hesaplar sayılabilir.

## 3. Ekran görüntüsü: açık mod

`SECURE_MODE=false`

![VULN-02 saldırı](img/VULN-02-attack.png)

## 4. Etki

Herhangi bir müşteri diğer tüm müşterilerin bakiye ve hesap hareketlerini görebilir. KVKK ve bankacılık sırrı ihlali.

## 5. Düzeltme

```python
if settings.SECURE_MODE:
    if account["user_id"] != user["id"]:
        return None  # "bulunamadı" ile aynı cevap
```
Yetkisiz erişimde 403 yerine 404 dönülür, böylece hangi id'lerin var olduğu da anlaşılmaz.

## 6. Ekran görüntüsü: güvenli mod

`SECURE_MODE=true`

![VULN-02 engellendi](img/VULN-02-blocked.png)

## Notlar

- Deneme sayısı / başarı:
- Kullanılan araç:
