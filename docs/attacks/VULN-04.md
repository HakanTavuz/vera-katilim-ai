# VULN-04: Eksi tutarla transfer

**OWASP:** A04:2021 Insecure Design
**Kod:** app/routes/transfers.py → `execute_transfer()` (`# VULN-04` yorumu)

## 1. Açıklama

Transfer tutarı için sıfırdan büyük olma ve bakiye kontrolü yok. Bakiye oku-hesapla-yaz şeklinde transaction dışında güncelleniyor.

## 2. Adımlar

1. `ayse.yilmaz` ile giriş yap, Para transferi sayfasına git.
2. Alıcı IBAN: `TR000000000000000000000003` (Zeynep), tutar: `-50000`
3. Gönder. Ayşe'nin bakiyesi 50.000 TL artar, Zeynep'in bakiyesi aynı oranda düşer.
4. Bakiye üstü tutar (`9999999`) da kabul edilir, hesap eksiye düşer. Admin "Şüpheli işlemler"de eksi bakiyeli hesapları görür.

## 3. Ekran görüntüsü: açık mod

`SECURE_MODE=false`

![VULN-04 saldırı](img/VULN-04-attack.png)

## 4. Etki

Başka müşterilerin hesabından para çekme, sınırsız kredi. Doğrudan finansal kayıp.

## 5. Düzeltme

```python
if amount <= 0: return False, "Tutar sıfırdan büyük olmalı."
conn.execute("BEGIN IMMEDIATE")
cur = conn.execute("UPDATE accounts SET balance = balance - ? WHERE id = ? AND balance >= ?", ...)
if cur.rowcount != 1: ROLLBACK  # yetersiz bakiye
```
Bakiye kontrolü ve düşme tek SQL ifadesinde yapılır; paralel iki istek aynı parayı iki kez harcayamaz (race condition).

## 6. Ekran görüntüsü: güvenli mod

`SECURE_MODE=true`

![VULN-04 engellendi](img/VULN-04-blocked.png)

## Notlar

- Deneme sayısı / başarı:
- Kullanılan araç:
