---
name: urun-video-kurgu
description: Ozon.ru ürünleri için dikey tanıtım videosu kurgusu. Ürün görselleri veya "video yap" isteği geldiğinde kullanılır. Sıra hiç değişmez; onay gereken yerde durur, gerisini sormadan yapar.
---

# Ürün video kurgusu

Çalışma klasörü: `urun-video/`. Kurallar (font, renk, güvenli alan, başlık yeri, hata günlüğü)
`urun-video/brand/TEMA.md` içindedir. **Her kurguya o dosyayı okuyarak başla.**

## Klasörler
| Klasör | İçerik |
|---|---|
| `brand/` | TEMA.md, logolar, fontlar, ses efektleri |
| `brand/araclar/` | her videoda yazılan / geliştirilen script'ler (ortak; her video bir sonrakini hızlandırır) |
| `projeler/<YYYY-AA-GG>-<ad>/` | o an kurgulanan video: `index.html`, görseller, `onizleme/` |
| `yayinlananlar/<YYYY-AA-GG>-<ad>/` | final 4K video, kapak, caption |
| `urunler.md` | ürün alış / fatura kaydı |

## Sıra (değişmez)

1. **Ürün bilgisi ve fatura kaydı.** Videodaki her ürün `urunler.md`'de var mı bak. Yoksa satır aç.
   Alış fiyatı, adet, tarih, nereden, fatura no, **kim aldı (ben / kuzen)** eksikse kullanıcıya
   sor ve kaydet. Tahmin yazma. Videoya fiyat konacaksa yalnızca bu kayıttan al.
2. **Görseller.** Ambalaj yazılarını görselden oku (mg, ml, doz, içerik). Ambalajda olmayan iddia yazma.
   Logo / ürün görseli internetten indirilecekse önce kullanıcıya sor, resmî kaynağı kullan.
3. **3 kanca seçeneği → DUR.** Açılış için 3 farklı kanca öner (ör. "YENİ ÜRÜNLER" / soru / rakam).
   Kullanıcı seçer.
4. **Storyboard → DUR.** Seçilen kancayla sahneleri kur, her sahneden 1 kare çıkar
   (`render.js ... stills`), yan yana tek görselde göster. Kullanıcı onaylar ya da düzeltir.
5. **Render öncesi kontrol (otomatik).** `node brand/araclar/guvenli-alan.js <proje>`
   Güvenli alan dışı yazı veya yazı çakışması varsa düzelt, tekrar çalıştır. Temiz olmadan render etme.
6. **1080p taslak (otomatik).** `node brand/araclar/render.js <proje> video <proje>/onizleme/taslak-1080p.mp4`
7. **Render sonrası tarama (otomatik).** `python3 -I brand/araclar/kare-tarama.py <video> --izin <bilerek konan flaş anları>`
   1-3 karelik hata varsa düzelt ve 6'ya dön. Ses varsa seviyeyi raporlar.
8. **Rötuş → DUR.** Taslağı kullanıcıya gönder. Her düzeltmeyi uygula **ve TEMA.md hata günlüğüne yaz.**
9. **Final (onaydan sonra).**
   - 4K: `node brand/araclar/render.js <proje> video yayinlananlar/<ad>/final-4k.mp4 --4k`
   - Kapak: `node brand/araclar/render.js <proje> kapak <sn> yayinlananlar/<ad>/kapak.jpg`
   - Caption: `yayinlananlar/<ad>/caption.md` — Türkçe ve Rusça (Ozon). Ambalaj bilgisi + kayıttaki fiyat.
   - 4K final için de 7. adımı çalıştır.
10. **Yayın (sormadan yapma).** Drive'a yükleme ve içerik takvimine ekleme kullanıcı onayıyla yapılır.

## Yeni araç yazarsan
`brand/araclar/` içine koy, dosyanın başına kullanım satırı yaz. Bir sonraki video onu kullanır.
