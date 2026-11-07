#!/usr/bin/env python3
"""Render SONRASI kontrol: 1-3 karelik hataları (ani çakan/kaybolan kareler) ve ses seviyesini tarar.

Kullanım: python3 kare-tarama.py <video.mp4> [--izin 3.2,18.8]
  --izin: bilerek konan flaş/kesme anları (sn); ±0.4 sn içindeki bulgular yok sayılır.

Mantık: kare i, öncesi (i-1) ve k kare sonrası (i+k, k=1..3) birbirine benzerken
aradaki kareler ikisinden de çok farklıysa bu bir "kısa süreli bozuk kare"dir.
"""
import subprocess, sys, json
import numpy as np

path = sys.argv[1]
izin = []
if '--izin' in sys.argv:
    izin = [float(x) for x in sys.argv[sys.argv.index('--izin') + 1].split(',')]

W, H = 108, 192
raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', path, '-vf', f'scale={W}:{H}', '-f', 'rawvideo',
                      '-pix_fmt', 'gray', '-'], capture_output=True, check=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)
fps = float(eval(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                 'stream=r_frame_rate', '-of', 'csv=p=0', path], capture_output=True, text=True).stdout.strip()))
d = lambda a, b: float(np.abs(fr[a] - fr[b]).mean())

bulgular = []
for i in range(1, len(fr) - 4):
    for k in (1, 2, 3):
        once_sonra = d(i - 1, i + k)
        ara = min(d(i - 1, j) for j in range(i, i + k))
        if ara > 18 and once_sonra < ara * 0.3:
            t = i / fps
            if not any(abs(t - z) <= 0.4 for z in izin):
                bulgular.append((i, k, t, ara, once_sonra))
            break

print(f'{len(fr)} kare tarandı ({len(fr)/fps:.1f} sn, {fps:g} fps).')
if bulgular:
    print(f'{len(bulgular)} şüpheli kısa kare:')
    for i, k, t, a, o in bulgular:
        print(f'  kare {i} (t={t:.2f} sn): {k} karelik sapma, fark {a:.0f} / komşular arası {o:.0f}')
else:
    print('1-3 karelik hata bulunmadı.')

# Ses seviyesi
has_audio = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=index',
                            '-of', 'csv=p=0', path], capture_output=True, text=True).stdout.strip()
if not has_audio:
    print('Ses: video sessiz (ses kanalı yok).')
else:
    out = subprocess.run(['ffmpeg', '-i', path, '-af', 'loudnorm=print_format=json', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    j = json.loads(out[out.rindex('{'):out.rindex('}') + 1])
    lufs, tp = float(j['input_i']), float(j['input_tp'])
    ok = -16 <= lufs <= -12 and tp <= -1
    print(f'Ses: {lufs:.1f} LUFS, tepe {tp:.1f} dBTP -> {"OK" if ok else "HEDEF DIŞI (hedef -14 LUFS, tepe <= -1 dBTP)"}')
sys.exit(1 if bulgular else 0)
