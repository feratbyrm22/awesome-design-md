# Öğrenme ajanı (`/ogren`)

[LearnHarness](https://github.com/amosblomqvist/learnharness)'in öğretim yöntemini Claude Code'a
taşıyan, Türkçe konuşan bir öğrenme ajanı.

## Nasıl çalışır

1. **Ölç** — hedefini somutlaştırır, sonra her bilgi dalında ikili arama ile neyi kesin bildiğini
   (taban) ve nerede koptuğunu (tavan) bulur.
2. **Planla** — koşulsuz doğrulardan hedefe giden en küçük bağımlılık ağacını çıkarır, mermaid
   haritası olarak gösterir, onayını ister.
3. **Öğret** — tahmin → anlatım → kontrol döngüsü. Her seferinde tek akıl yürütme adımı; her adım bir
   uygulama sorusuyla kontrol edilir; yanlış anlaşılan adım onarılmadan üstüne bir şey kurulmaz.
4. **Kaydet** — oturum kaydı ve kalıcı bilgi grafiği (`ogrenme/`). Sonraki oturumlar buradan devam eder.
5. **Pratik** — grafikteki bilgiyi, adını söylemeden gerektiren çeşitli problemler.

## Kullanım

```
/ogren türevde zincir kuralı
/ogren devam
/ogren pratik kalkülüs
/ogren grafik
```

Sorular seçenekli gelir. **"Other"** ile kendi düşünceni ve güvenini (ör. "%60, çünkü…") yazmak,
ajanın seni çok daha iyi anlamasını sağlar.

## Dosyalar

| Dosya | Görev |
| --- | --- |
| `.claude/skills/ogren/SKILL.md` | Ana öğretmen: iş akışı |
| `.claude/skills/ogren/references/yontem.md` | Öğretim kuramı (Türkçe özet) |
| `.claude/skills/ogren/references/veri-formati.md` | Oturum ve grafik dosya biçimi |
| `.claude/agents/arastirmaci.md` | Arka planda doğrulama/araştırma alt ajanı |
| `.claude/agents/bilgi-cikarici.md` | Oturumdan bilgi grafiğine önerme çıkaran alt ajan |

Yöntem LearnHarness'ten (AGPL-3.0) uyarlanmıştır.
