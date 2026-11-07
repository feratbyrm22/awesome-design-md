# TEMA.md — Ürün videosu kuralları

Bu dosya her kurgunun başında okunur. Bir düzeltme yapıldığında **Hata günlüğü** bölümüne yazılır,
aynı hata bir daha yapılmaz. Kurallar skill'den ayrı tutulur: skill *sırayı*, bu dosya *görünümü* belirler.

## Format
- Dikey 9:16. Taslak **1080×1920** (1080p), final **2160×3840** (4K). 30 fps, H.264, yuv420p.
- Süre: 20–30 sn. Ürün başına ~5 sn sahne.
- Taslak `projeler/<tarih>-<ad>/onizleme/` içine, final `yayinlananlar/<tarih>-<ad>/` içine gider.

## Güvenli alan (1080×1920 koordinatlarında)
Reels / TikTok / Shorts / Ozon arayüzü (butonlar, açıklama, profil) bu bölgelerin üstünü kapatır.

| Kenar | Sınır | Neden |
|---|---|---|
| Üst | 200 px | durum çubuğu, sekme başlıkları |
| Alt | 1600 px (alttan 320 px) | açıklama, müzik satırı, butonlar |
| Sol / sağ | 64 px | ekran kenarı, sağdaki beğeni sütunu |

- **Hiçbir yazı** bu sınırların dışına çıkamaz. Bilerek taşan dekor (kayan yazı vb.) `data-safe="ignore"` ile işaretlenir.
- Kontrol aracı: `brand/araclar/guvenli-alan.js` (sınırlar orada da aynı tutulur).

## Fontlar
- Başlık: **Inter Display**, 800–900 kalınlık, harf aralığı -2…-4 px.
- Gövde / etiket: Inter Display 600–700.
- Minimum yazı boyu: 30 px (1080p'de). Daha küçüğü telefonda okunmaz.

## Renkler
| Rol | Renk |
|---|---|
| Koyu zemin | `#0b0b1a`, mor `#2b1f5c` |
| Altın vurgu | `#d9b35a` / açık `#f5e3a8` |
| Kolajen moru | `#5b2d96` |
| Lacivert (Nutraxin) | `#06122e` → `#0d3d8f` |
| Turkuaz (Oral-B) | `#169c95`, yazı `#0b2a7a` |
| Mint | `#7fe3d6` |

Ürün sahnesinin rengi ürünün ambalajından alınır.

## Yerleşim (başlık nereye gelir)
- Sahne başlığı / marka: üst güvenli çizginin hemen altı (y ≈ 220–420).
- Ürün görseli: ekranın orta üçte biri (y ≈ 280–1100).
- Ana rakam (mg, ml, doz): ürünün hemen altı, y ≈ 1150–1450.
- Rozet / etiket: ürün kartının köşesine biner, listenin üstüne binmez.
- Rakam + birim her zaman tek satır (`white-space:nowrap`).

## Efekt kütüphanesi (kodla çizilir, video modeli yok)
text punch · kinetic words · mask up · type on · marquee · shimmer · sticker · whip pan · wipe ·
sweep · circle in · card flip · flash cut · film grain · speed lines · starburst · sparkles · rings ·
number counter · ui highlight

Örnek uygulamalar: `projeler/2026-11-07-urun-tanitim/index.html`.

## İçerik kuralları
- Ambalajda yazmayan bir iddia (sağlık etkisi, "en iyi", indirim) yazılmaz.
- **Fiyat, kayıtta olmadan videoya konmaz.** Fiyat yalnızca `urunler.md`'deki satış fiyatından alınır.
- Gerçek fotoğraf (ör. Nutraxin ev çekimi) yerine beyaz zeminli ürün görseli tercih edilir.

## Ses
- Hedef: **-14 LUFS**, tepe ≤ -1 dBTP. `kare-tarama.py` ölçer.
- Ses yoksa rapor "video sessiz" der; müzik yayın öncesi (CapCut / platform) eklenebilir.

## Hata günlüğü
Her düzeltme buraya bir satır olarak eklenir.

| Tarih | Hata | Kural |
|---|---|---|
| 2026-11-07 | Daire geçişinde önceki sahnenin listesi yeni sahnenin üstünde kaldı | Her `.scene` → `isolation:isolate`; z-index sahne dışına sızamaz |
| 2026-11-07 | Eğik (skew) geçiş paneli başlamadan sol üstte görünüyordu | Eğik paneller, eğim payı dahil tamamen ekran dışından başlar (-1800 px) |
| 2026-11-07 | "1.050 mg" iki satıra kırıldı | Rakam + birim `white-space:nowrap`, dar sütunda font küçültülür |
| 2026-11-07 | "30 TABLET" rozeti listenin arkasında kaldı | Rozetlere z-index ver, listelerin üstüne değil kart köşesine koy |
| 2026-11-07 | 9 yazı alt güvenli alanın altındaydı (çip, rozet, ml) | Alt sınır 1600 px; render öncesi `guvenli-alan.js` zorunlu |
