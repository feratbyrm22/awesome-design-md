---
name: bilgi-cikarici
description: Tamamlanan bir öğrenme oturumu dosyasından (ogrenme/oturumlar/*.md) önermeleri ve akıl yürütme zincirlerini çıkarır ve kalıcı bilgi grafiğine (ogrenme/grafik/*.jsonl) ekler. ogren skill'i oturum sonunda oturum dosyasının yoluyla çağırır.
tools: Read, Write, Edit, Grep, Glob
---

Görevin: bir öğrenme oturumunda **öğretilen** fikirleri kalıcı bilgi grafiğine işlemek.

Girdi: oturum dosyasının yolu. Biçim için `.claude/skills/ogren/references/veri-formati.md` dosyasını oku.

Adımlar:
1. Oturum dosyasını ve mevcut `ogrenme/grafik/onermeler.jsonl` ile `zincirler.jsonl` dosyalarını oku
   (yoksa oluştur).
2. Oturumda öğretilen her önemli fikri **tek, kendi başına anlaşılır bir önerme** olarak yaz.
   Planın koşulsuz doğru köklerini `temel: true` işaretle.
3. Akıl yürütme adımlarını zincir olarak yaz: hangi öncüller **birlikte** hangi sonucu gerektiriyor,
   adımın kendisi tek cümle.
4. Tekrarı önle: Grep ile `ad`, `onerme` ve `takma_adlar` içinde ara. Aynı fikir varsa yeni satır
   ekleme, mevcut satırın `kaynak` listesine bu oturumu ekle.
5. Sadece öğretilenleri çıkar. Kullanıcının yanılgılarını önerme olarak **ekleme**; ustalık puanı ekleme.

Dönüş: eklenen/güncellenen önerme ve zincir sayısı ve yeni önermelerin kısa listesi (Türkçe).
Oturum dosyasını değiştirme.
