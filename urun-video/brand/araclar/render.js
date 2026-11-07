// Kullanım:
//   node render.js <proje-klasörü> video  <çıktı.mp4> [--4k]
//   node render.js <proje-klasörü> stills <saniye> [<saniye> ...]   -> proje/onizleme/still_<t>.jpg
//   node render.js <proje-klasörü> kapak  <saniye> <çıktı.jpg>     -> 4K kapak görseli
// Proje sayfası window.render(t, frame), window.SURE (sn) ve window.SCENES sağlamalıdır.
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const [proj, mode, ...rest] = process.argv.slice(2);
const FPS = 30;
const is4k = rest.includes('--4k');
(async () => {
  const b = await chromium.launch();
  const scale = (is4k || mode === 'kapak') ? 2 : 1;
  const pg = await b.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: scale });
  await pg.goto('file://' + path.resolve(proj, 'index.html'));
  await pg.evaluate(() => document.fonts.ready);
  const DUR = await pg.evaluate(() => window.SURE);
  const shot = async (t, f, opts) => { await pg.evaluate(([t, f]) => render(t, f), [t, f]); return pg.screenshot(opts); };
  if (mode === 'stills') {
    const dir = path.resolve(proj, 'onizleme'); fs.mkdirSync(dir, { recursive: true });
    for (const t of rest.map(Number)) await shot(t, Math.round(t * FPS), { path: path.join(dir, `still_${t}.jpg`), type: 'jpeg', quality: 75 });
  } else if (mode === 'kapak') {
    const t = Number(rest[0]);
    await shot(t, Math.round(t * FPS), { path: rest[1], type: 'jpeg', quality: 92 });
  } else {
    const out = rest[0];
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
      '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', is4k ? '18' : '20', '-preset', 'medium', '-movflags', '+faststart', out],
      { stdio: ['pipe', 'inherit', 'inherit'] });
    for (let f = 0; f < Math.round(FPS * DUR); f++) {
      const buf = await shot(f / FPS, f, { type: 'jpeg', quality: 92 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
  }
  await b.close();
})();
