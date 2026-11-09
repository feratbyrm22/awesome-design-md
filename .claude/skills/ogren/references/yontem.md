# Öğrenme ve öğretme kuramı (özet)

Kaynak: [LearnHarness](https://github.com/amosblomqvist/learnharness) `docs/teaching-methodology.md`
ve öğretmen/ölçücü/pratik prompt'ları (AGPL-3.0). Burada Türkçe ve kısaltılmış olarak uyarlandı.

## 1. İki bilgi durumu

- **Mevcut anlayış:** öğrenenin apaçık doğru kabul ettiği, üzerine güvenle inşa edilebilecek önermeler.
- **Hedef anlayış:** henüz tutmadığı ama tutmak istediği şey. Öğrenen bunu çoğu zaman net söyleyemez;
  netleştirmek tanımın parçasıdır.

Ölçüm ikisini de keskinleştirir. Öğretim birinciden ikinciye taşır.

## 2. Öğrenmek = hedefin apaçık doğru gelmesi

Bitiş koşulu hatırlama, soru cevaplama veya kapsam değildir. Hedef ona **apaçık doğru** geldiğinde
öğrenilmiştir. Beyin bir bilgiye ancak (a) daha temel bir şeyin onu ileride çürütmeyeceğinden emin
olduğunda ve (b) bilgi başka bilgilere bağlı olduğunda tam bağlanır. "Apaçık doğru" hissi, bu iki
koşulun karşılandığının yaşantısıdır.

## 3. "Klik" anı

Gevşek, yalnız bilgiler ("öyle işte") birkaç temel bilgiden üretilen bir yapıya çöker. Önceden ayrı
ayrı tutulan her düğümün daha temel bir şeyden türediği görülür. "Ne"yi değil "neden"i bilmek.

## 4. Bilgi bir yapıdır

Anlayış bir grafiktir: **düğümler önermeler, kenarlar bağlantılar**. Bağlantılar ve akıl yürütme
adımları da birer bilgidir. Hiçbir şeye bağlanmayan önerme kırılgandır; yapıya gömülü olan kendini korur.

## 5. Öğretmek = bilgileri doğru sırayla, her seferinde tek akıl yürütme adımıyla sunmak

Tuttuğu yerden başla. Her yeni bilgi, tutulan bir şeye **tek** akıl yürütme adımıyla bağlanır.

- **Her iniş apaçıktır:** yeni bilgi, dayandığı şeyin apaçıklığını miras alır.
- **Hatalar anında ortaya çıkar:** boşluk, üstüne basıldığı anda görünür; küçük ve yeri belli olduğu
  için ucuza onarılır. Apaçık tutulmayan bir şeyin üstüne asla inşa etme.

## 6. Temeller — İlke i: önce koşulsuz doğrular

Bazı önermeler tutulan hiçbir şeyden türetilemez: bağımlılık ağacının dibi. Bunlar **koşulsuz doğru**
olmalı — şartsız, çekincesiz, olduğu gibi kabul edilebilir. "Genellikle…" diyorsan henüz koşulsuz doğru
değildir; daha aşağı in.

- En güçlü iki biçim: **evrensel önermeler** ("tüm X, Y'dir", "hiçbir X, Y değildir"; özel hâli
  "TÜM X, {____} yoluyla yapılır" — ör. "Bilgisayarlar arasındaki tüm iletişim paket göndererek
  yapılır") ve **gerçek tanımlar** (özellik listesi kılığında tanım değil).
- "Aksiyom" kelimesini hiçbir şeyden türemeyen gerçek kökler için sakla; varsayılan terim "koşulsuz doğru".
- Temeli onun üstüne inşa etmeden önce, ona gerçekten sağlam geldiğini kısaca kontrol et.
- Temel **motive** edilebilir: onu gerektiren bir sorun ya da soru, kabulü kolaylaştırır.

## 7. Türetme — İlke ii: "Bunu ben nasıl keşfedebilirdim?"

Bilgi, var olmak zorunda olduğu görünür bir neden yoksa keyfi hisseder; beyin keyfi bilgiye bağlanmaz.
Çözüm: dayatılmış değil, **keşfedilmiş** hissettirmek.

- En baştan: bunu neden yapıyoruz? Hangi temel sorun bizi bu yola soktu?
- Her ara adımı da motive et: neden bu formül, neden denklemi bu şekilde değiştiriyoruz?
- Çıktı: bağlantısız önermeleri bağlantılı önermelere çevirmek — grafiğe kenar eklemek.
- Usta referans: 3Blue1Brown. Hiçbir şey yoktan çıkmaz.

## 8. İki bağımsız optimizasyon

- **Çaba dağılımı:** öğrenenin çabasının *oranı* malzemeye gitsin. Lojistik (ne, hangi sırayla, hangi
  kaynaktan, güvenilir mi) sistemin işidir. Zorluk kaldırılmaz; zorluk malzemede olmalıdır.
- **Minimal ağaç:** mevcuttan hedefe en küçük önerme kümesi, en kısa türetme derinliğiyle. Bildiği
  yeniden öğretilmez; yol dışındaki hiçbir şey öğretilmez, ne kadar ilginç olsa da. Rota öğretim
  sırasında doğaçlanmaz, planlamada aranır.

Kullanıcının gördüğü plan bu ağacın **düşük çözünürlüklü** görünümüdür; düğümler akıl yürütme
adımlarıyla bire bir eşleşmez. Plan harita, öğretim yoldur.

## 9. Sunum

Her adım en berrak biçimde. Bazı adımlar açıkça söylenir (koşulsuz doğrular). Bağlantı dokusunun çoğu
akışa gömülür. Düzeltilen hata açıklık değil **laf kalabalığı**dır: yöntemi icra etmek (etiketli
bölümler, yapıyı yeniden anlatmak, meta-anlatım). Her cümle ya anlayış yerleştirir ya da yüktür.

## 10. Kontroller — her akıl yürütme adımından sonra

Her adım, adımın oturduğunu doğrulayan puanlı bir soruyla biter. Ritim: adım → kontrol →
onarım-ya-da-devam.

İyi kontrol:
- Oturumda anlatılanlardan akıl yürüterek cevaplanabilir (yoksa yazı-tura).
- Az önceki cümleyi geri okutmaz.
- Bilgiyi **uygulatır**: yeni bir duruma, bir tahmine, bir uzantıya.
- Yanlış cevap hangi yanlış modelin tutulduğunu **adlandırır**.
- Cevap hüküm değil sinyaldir: şanslı doğru hiçbir şeydir; dürüst bir soruda yanlış altındır.

## Tahmin ve kontrol

| | Tahmin | Kontrol |
| --- | --- | --- |
| Ne zaman | Adımı öğretmeden önce | Adımı öğrettikten sonra |
| Konusu | Henüz öğretilmemiş sonraki adım | Az önce öğretilen adım |
| İşlevi | Motivasyon; denemek esas | Senin için veri: devam / onar |
| Sonrası | Öğretim tahmini açıkça çözerek başlar | Iska → teşhis ve onarım |

## Güven

Her cevap için öğrenen % güven verebilir (seçtiği cevabın doğru olma olasılığı).

| Durum | Anlamı | Ne yap |
| --- | --- | --- |
| Doğru + yüksek güven | Sağlam bilgi | Devam |
| Doğru + düşük güven | Kırılgan ya da şans | Bir pekiştirme dokunuşu, kutlama yok |
| Yanlış + yüksek güven | **Yerleşmiş yanılgı** — en güçlü sinyal | Çatlağı adlandır, nazikçe yokla, etrafından yeniden öğret |
| Yanlış + düşük güven | Sarsak yakın ıska ya da dürüst boşluk | Küçük bir düzeltme genelde yeter |
| "Bilmiyorum" | Tahmin etmeyi reddetti | Gerçek boşluk, yanlış değil |

n seçenekli soruda şans 1/n'dir; seçtiğine ≤ 1/n güven veriyorsa kendi seçimine inanmıyordur (tuzak
şüphesi) — bunu dürüstlük say.

## Düşünme alanı

Öğrenenin kendi kelimeleriyle yazdığı/söylediği düşünce, anlayışının en hassas aktarımıdır. Hepsini
oku. Dikte edilmiş olabilir: bozuk bir kelime, kavram hatası değil tanıma hatasıdır.

## Ses

Bu bölüm varsayılanları siler, yerine bir şey koymaz:
- Övgü, coşku, gösteri tepkisi yok.
- Onay eğilimi yok; "bu doğru değil", "bu bir yanılgı" sıradan çıktılardır.
- Yapay derinlik yok, sahte kesinlik yok, ahlak dersi yok.
- Dolgu yok, yumuşatma yok, refleks çekince yok. Kuru üslup.

Sıcaklık, varsa, işçiliktir: ölçülmüş, planlanmış, onun sınırına nişan alınmış iş.
