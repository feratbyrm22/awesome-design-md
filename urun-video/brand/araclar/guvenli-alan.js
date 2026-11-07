// Render ÖNCESİ kontrol: güvenli alan + yazı çakışması.
// Kullanım: node guvenli-alan.js <proje-klasörü>
// Her sahnenin sonundan 0.4 sn önce (animasyonlar oturmuşken) tüm görünür yazıları ölçer.
// data-safe="ignore" taşıyan öğeler (ör. bilerek taşan kayan yazı) atlanır.
// Sınırlar TEMA.md'deki "Güvenli alan" bölümüyle aynı tutulmalıdır.
const { chromium } = require('playwright');
const path = require('path');
const SAFE = { left: 64, top: 200, right: 1016, bottom: 1600 };
(async () => {
  const b = await chromium.launch();
  const pg = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await pg.goto('file://' + path.resolve(process.argv[2], 'index.html'));
  await pg.evaluate(() => document.fonts.ready);
  const scenes = await pg.evaluate(() => window.SCENES);
  let hata = 0;
  for (const [ad, [bas, son]] of Object.entries(scenes)) {
    const t = son - 0.4;
    const sonuc = await pg.evaluate(([t, SAFE]) => {
      render(t, 1);
      const vis = el => { for (let e = el; e && e !== document.body; e = e.parentElement) {
        const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity < 0.05) return false;
        if (e.closest('[data-safe=ignore]')) return false; } return true; };
      const kutular = [];
      document.querySelectorAll('body *').forEach(el => {
        // Kutunun değil, harflerin gerçekten kapladığı alan ölçülür (Range ile).
        const tn = [...el.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim());
        if (!tn.length || !vis(el)) return;
        let l = 1e9, t = 1e9, r = -1e9, b = -1e9;
        for (const n of tn) { const rg = document.createRange(); rg.selectNodeContents(n);
          for (const q of rg.getClientRects()) { if (q.width < 1) continue; l = Math.min(l, q.left); t = Math.min(t, q.top); r = Math.max(r, q.right); b = Math.max(b, q.bottom); } }
        if (r - l < 2) return;
        // satır yüksekliğindeki boşluk payını çıkar (font kutusu harften ~%12 büyüktür)
        const pad = (b - t) * 0.12; t += pad; b -= pad;
        kutular.push({ yazi: tn.map(n => n.textContent.trim()).join(' ').slice(0, 30), l, t, r, b });
      });
      const sorun = [];
      for (const k of kutular) {
        const d = [];
        if (k.l < SAFE.left) d.push(`sol ${Math.round(SAFE.left - k.l)}px`);
        if (k.r > SAFE.right) d.push(`sağ ${Math.round(k.r - SAFE.right)}px`);
        if (k.t < SAFE.top) d.push(`üst ${Math.round(SAFE.top - k.t)}px`);
        if (k.b > SAFE.bottom) d.push(`alt ${Math.round(k.b - SAFE.bottom)}px`);
        if (d.length) sorun.push(`GÜVENLİ ALAN DIŞI  "${k.yazi}"  (${d.join(', ')})`);
      }
      for (let i = 0; i < kutular.length; i++) for (let j = i + 1; j < kutular.length; j++) {
        const a = kutular[i], c = kutular[j];
        const ox = Math.min(a.r, c.r) - Math.max(a.l, c.l), oy = Math.min(a.b, c.b) - Math.max(a.t, c.t);
        const ic = (a.l >= c.l && a.r <= c.r && a.t >= c.t && a.b <= c.b) || (c.l >= a.l && c.r <= a.r && c.t >= a.t && c.b <= a.b);
        if (ox > 4 && oy > 4 && !ic) sorun.push(`YAZI ÇAKIŞMASI  "${a.yazi}" ↔ "${c.yazi}"`);
      }
      return { n: kutular.length, sorun };
    }, [t, SAFE]);
    console.log(`${ad} (t=${t.toFixed(1)} sn, ${sonuc.n} yazı): ${sonuc.sorun.length ? 'SORUN VAR' : 'OK'}`);
    sonuc.sorun.forEach(s => console.log('   - ' + s));
    hata += sonuc.sorun.length;
  }
  await b.close();
  console.log(hata ? `\n${hata} sorun bulundu — render etmeden önce düzelt.` : '\nTüm sahneler temiz.');
  process.exit(hata ? 1 : 0);
})();
