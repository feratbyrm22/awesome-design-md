# urun-video

Ozon.ru ürünleri için kodla çizilen dikey tanıtım videoları.

- Akış: `../.claude/skills/urun-video-kurgu/SKILL.md`
- Kurallar ve hata günlüğü: `brand/TEMA.md`
- Ürün / fatura kaydı: `urunler.md`
- Araçlar: `brand/araclar/` (render, güvenli alan kontrolü, kare tarama)

Gerekenler: Node + Playwright (Chromium), ffmpeg, Python 3 + numpy.

```bash
P=projeler/2026-11-07-urun-tanitim
node brand/araclar/guvenli-alan.js $P                       # render öncesi kontrol
node brand/araclar/render.js $P video $P/onizleme/taslak-1080p.mp4
python3 -I brand/araclar/kare-tarama.py $P/onizleme/taslak-1080p.mp4 --izin 3.2,18.8
node brand/araclar/render.js $P video yayinlananlar/<ad>/final-4k.mp4 --4k   # onaydan sonra
```
