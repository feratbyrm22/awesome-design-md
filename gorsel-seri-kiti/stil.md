# stil.md — Video kapağı serisi

Kapsam: yalnız video kapağı (1280×720, 16:9). Reklam ve sunum için ayrı dosya aç.
Durum: TASLAK. Aşağıdaki değerler başlangıç önerisidir; referans analizinden gelen gerçek değerlerle değiştir. `[doğrula]` etiketli her şey editörde kontrol edilmeden kesin sayılmaz.

## Her istekte modele söylenecek
Ekli stil dosyasını uygula. Bu kez [konu] için tasarım hazırla. Referansın metnini ve nesnelerini kullanma. Başlık sığmıyorsa yazıyı okunamayacak kadar küçültme; alternatif yerleşim öner.

## A. SABİTLER (seride asla değişmez)
- Tuval: 1280×720. Güvenli kenar boşluğu: 64 px her yönde.
- Zemin: koyu nötr `#14161A` [doğrula]. Gradyan, doku, desen yok.
- Metin rengi: `#FFFFFF`. İkincil metin: `#B8BCC4`.
- Vurgu rengi: tek renk `#FFC400` [doğrula]. Yalnız: başlıktaki **tek** anahtar kelime VEYA etiket çipi. İkisi aynı kartta olmaz.
- Yazı ailesi: tek aile, 2 ağırlık (800 başlık, 500 diğer). Font adı [doğrula]; yedek: Inter/system-ui.
- Hiyerarşi (3 kademe, fazlası yok):
  1. Başlık: 96 px, satır aralığı 1.05, büyük harf yok.
  2. Alt satır: 36 px, ikincil renk, en çok 1 satır.
  3. Etiket çipi: 28 px, isteğe bağlı.
- Başlık konumu: sol hizalı, sol-alt blok; ana görsel varsa sağ %45.
- Yasak efektler: gölge, dış parıltı, 3B yazı, kontur, yarı saydam yazı zemini, emoji.

## B. DEĞİŞKENLER (her kartta değişir)
- Konu, başlık metni, alt satır, etiket.
- Ana görsel (içerik + kırpma). Ana görsel alanı: sağ %45, tam yükseklik.
- Vurgulanan anahtar kelime (başlıkta 1 kelime).

## C. TAŞMA VE BOŞ DURUM KURALLARI (zor örneklerden çıkar)
1. Başlık ≤ 3 satır. Varsayılan 96 px; 3 satıra sığmazsa 80 px'e in. **72 px'in altına inme.**
2. Görsel varken başlık 72 px'te bile 3 satırı aşıyorsa (kontrol örneği 2'de 80 px → 5 satır oldu): önce metni kısaltmayı öner; olmuyorsa görseli %35'e daralt, o da olmuyorsa görseli arka plana değil, kartın dışına al ve kartı görselsiz yerleşimle (kural 3) kur. 72 px'te de sığmıyorsa alternatif yerleşim: ana görsel yoksa tam genişlik; varsa görseli %35'e daralt. Önce kısalt (metni kısaltmayı öner), sonra yerleşim değiştir.
3. Ana görsel yoksa: sağ alan boş bırakılmaz, süs eklenmez. Başlık bloğu tam genişliğe yayılır, vurgu rengi ince bir 8 px dikey şerit olarak sol kenarda tek kez kullanılır.
4. Alt satır yoksa blok başlık alanıyla dikey ortalanır; boşluğu sahte metinle doldurma.
5. Rastgele ikon, şekil, parçacık yok.

## D. Doğrulama listesi
- [ ] 3 örnekte de renkler ve font aynı
- [ ] Başlık hiçbirinde kenar boşluğuna taşmıyor, ≥72 px
- [ ] Görselsiz kartta süs yok
- [ ] Referans metni/logosu hiçbirinde yok

## E. Sürüm notları
- v0.1 — ilk taslak.
- v0.2 — kontrol turu 1: uzun başlık görselli kartta 5 satır → C2 genişletildi (kısalt → görseli daralt → görselsiz yerleşim). Şablon `.m-uzun` hâlâ yalnız 80 px yapıyor; görsel daraltma varyantı henüz şablonda yok.
