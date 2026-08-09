# natural-photo-enhance

Fotoğrafı her açıdan iyileştiren, ama **yapay zekâ eliyle yapıldığı anlaşılmayan** bir rötuş
pipeline'ı.

## Neden üretken model yok?

İstenen şeyin ("iyi görünsün ama AI olduğu belli olmasın") doğru çözümü, üretken model
*kullanmamak*. Face restoration / AI upscaler / inpainting araçları var olmayan piksel
üretir: gözenekleri siler, yüz geometrisini kaydırır, gözü ve dişi standart bir kalıba
oturtur. İnsanlar bunu isimlendiremeseler bile fark eder — "bu fotoğrafta bir tuhaflık var"
hissinin kaynağı budur. Ayrıca üretken izler tespit edilebilir.

Bu araç bunun yerine profesyonel retouch işini kodlar: her aşama, zaten karede olan
piksellerin sınırlı ve yerel bir dönüşümü. Yüz geometrisi, gözenek dokusu ve lens karakteri
hiç ellenmez.

```
generative_steps: 0        <- her çıktının raporunda yer alır
```

## Kurulum

```bash
pip install -r requirements.txt
```

## Kullanım

```bash
python enhance.py foto.jpg                       # natural preset
python enhance.py foto.jpg --preset studio
python enhance.py foto.jpg --all -o cikti/       # dört varyantı birden üret
python enhance.py foto.jpg --strength 0.7        # her şeyi yarıya indir
python enhance.py foto.jpg --report rapor.json   # ölçümleri yaz
```

Ayna selfie'si için (tişört yazısı ters okunuyorsa):

```bash
python enhance.py foto.jpg --unmirror --all -o cikti/
```

Yüz algılama için OpenCV Haar cascade dosyaları kuruluysa kullanılır; yoksa araç ten rengi
maskesine düşer ve çalışmaya devam eder. Yüz kutusunu elle de verebilirsiniz:

```bash
python enhance.py foto.jpg --face 300,200,480,480
```

### Presetler

| preset    | ne yapar                                                        |
|-----------|-----------------------------------------------------------------|
| `natural` | Günlük, inandırıcı. Varsayılan.                                  |
| `studio`  | Daha temiz ışık, biraz daha heykelsi modelleme (softbox hissi).  |
| `outdoor` | Gün ışığı: serin gölgeler, daha çok renk, daha az yumuşatma.     |
| `mono`    | Editoryal siyah-beyaz; burada grain en kritik unsur.             |

## Pipeline

| # | aşama | ne yapar |
|---|-------|----------|
| 1 | beyaz ayarı | Nötre yakın piksellerden renk kaymasını hesaplar, kanal kazancı ±%12 ile sınırlı |
| 2 | ton | Siyah/beyaz noktası + adaptif gamma; **luminans üzerinden**, kanal oranları korunarak |
| 3 | yerel kontrast | CLAHE, yalnızca yapısal banda; grain ayrıştırılıp dokunulmadan geri eklenir |
| 4 | renk | Vibrance — ten korunur, nötrler tamamen dışarıda tutulur |
| 5 | ten | Frekans ayrımı: lekeli düşük frekans yumuşatılır, **yüksek frekans hiç ellenmez** |
| 6 | dodge & burn | Geniş ölçekli gölgelenmeyi düzler, gözenek ölçeğine inmez |
| 7 | gözler | Yalnızca yüz kutusu biliniyorsa, hafif yerel netlik |
| 8 | derinlik | Çok hafif kenar düşüşü, özneyi oturtmak için |
| 9 | keskinlik | Kenar maskesiyle kapılanmış unsharp; halo tavanı sabit |
| 10| grain | Ölçülen gürültü seviyesi geri enjekte edilir |

## Gerçekçilik korkulukları

Yapay görünmenin dört klasik işareti var; her biri için ölçülen bir sınır konuldu:

**1. Mumsu cilt.** Frekans ayrımı yalnızca düşük bandı yumuşatır. Ayrıca çıktı, cilt
mikro-dokusunun en az %72'sini korumak zorunda — koruyamıyorsa rötuş, korumaya yetecek
orana kadar geri harmanlanır (`texture_floor`).

**2. Aşırı rötuş.** Lokal aşamalar cildi en fazla ΔE 4 kadar oynatabilir
(`retouch_delta_e`). Bu bütçe **yalnızca rötuşa** işler; pozlama ve beyaz ayarı düzeltmesi
bütçeden düşülmez, çünkü onlar her fotoğrafçının yaptığı dürüst düzeltmelerdir.

**3. Yapay temizlik.** Gürültüsü silinmiş bir yüz, gürültülü bir karenin üstünde en yüksek
sesle bağıran ipucudur. Grain aşaması eksik kalan gürültüyü kareler toplamı yöntemiyle geri
ekler. Hedef, ton eğrisinin histogram ağırlıklı ortalama eğimiyle ölçeklenir: karartılmış bir
kareyi parlatmak gürültüyü fiziksel olarak yükseltir, sabit bir hedef bunu görmezden gelip
gerçek dokuyu kazımak anlamına gelirdi.

**4. Turuncu ten.** Kontrast ve doygunluk kromayı büyütür, ten ise izleyicinin doğru rengini
ezbere bildiği tek özne. Ortalama ten kroması, beyaz ayarlı karedeki değerin 1.2 katını ve
mutlak C\* 38'i aşamaz; ton kayması 4 dereceyle sınırlı.

Her çalıştırma bu sayıları raporlar:

```
natural  -> foto--natural.jpg
           retouch dE 3.32/4.0 (kept 100%)   skin texture 92% (floor 72%)
           noise 0.0254 vs 0.0186 expected   faces 1
```

## Testler

```bash
python test_enhance.py
```

11 kontrol çalışır. Bunlar üslup denetimi değil, aracın iddialarının ölçümü:
`--strength 0` gerçekten kimlik dönüşümü mü, rötuş gerçekten iş yapıyor mu (yoksa korkuluklar
onu no-op'a mı çevirdi), ten maskesi arka plana taşıyor mu, gamma karanlık kareyi
aydınlatıyor mu, cilt kroması kaçıyor mu, guard aşırı ayarları gerçekten geri çekiyor mu.

## Bilinen sınırlar

- Doğrulama **sentetik** test kareleri üzerinde yapıldı. Sayısal korkuluklar gerçek
  fotoğraflarda da geçerli ama presetlerin estetik dozu kendi karenizde bir kez
  `--strength` ile ayarlanmalı; en iyi yol `--all` çıkıp yan yana bakmak.
- Yüz algılama, OpenCV'nin Haar cascade XML'leri kurulu değilse devre dışı kalır. Ten maskesi
  o durumda da çalışır; sadece gözlere özel aşama atlanır ve maske ele/kola da uygulanabilir.
  `--face` ile kutuyu elle vermek bunu çözer.
- Ten maskesi renk tabanlıdır; ten rengine yakın duvar veya kıyafet bir miktar maskeye
  girebilir. Etkisi düşük frekansla sınırlı olduğu için görünür bir bozulma yapmaz.
- 12MP bir kare için tipik süre birkaç saniye; `--all` dört kat sürer.
