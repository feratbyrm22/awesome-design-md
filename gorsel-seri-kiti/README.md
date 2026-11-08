# Görsel Seri Kiti (video kapağı ile başla)

Beğendiğin görseli PNG olarak değil, **tarif** olarak sakla. Dört parça:

| Parça | Yer | Görevi |
|---|---|---|
| Referans klasörü | `referanslar/` | Kullanım hakkın olan 3 görsel + her birinde neyi beğendiğin (`NOTLAR.md`) |
| Stil dosyası | `stil.md` | Sabitler / değişkenler / kurallar. Her istekte modele eklenir |
| Düzenlenebilir şablon | `sablon/kapak.html` | Renk ve yazı stilleri CSS değişkeni; metinler elle düzenlenir |
| Kontrol örnekleri | `kontrol/` | Aynı şablonla 3 zor içerik: kısa başlık, uzun başlık, görselsiz kart |

Akış: `referanslar/` doldur → `analiz-promptu.md` ile çözümlet → çıktıyı doğrula, `stil.md`'ye indir → `kontrol/` üçlüsünü yan yana aç → kural eksiklerini `stil.md`'de düzelt → `revizyon.md` kalıbıyla tek tek düzelt.

Önizleme: `kontrol/index.html` (üç örnek yan yana).
Sonraki işte eski PNG'yi değil `stil.md` + `sablon/` aç; değişen kararı `stil.md` sürüm notuna yaz.
