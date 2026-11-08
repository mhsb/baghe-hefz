#!/usr/bin/env python3
"""
ساخت فایل صوتی هر سوره از فایل‌های آیه‌به‌آیه (برای کم‌کردن تعداد فایل‌ها)

ورودی : پوشه‌ای که فایل‌های آیه‌به‌آیه در آن است، با نام‌هایی مثل 114001.mp3 (سه رقم سوره + سه رقم آیه)
خروجی : audio/078.mp3 ... audio/114.mp3  و  audio/timings.json  (زمان شروع هر آیه)

اجرا  :  python3 tools/make-audio.py پوشهٔ_آیه‌ها            (خروجی در پوشهٔ audio کنار برنامه)
          python3 tools/make-audio.py پوشهٔ_آیه‌ها --bitrate 96k
نیاز  :  Python 3 و ffmpeg
هر آیه یک بار رمزگشایی و همهٔ آیه‌های سوره یک‌جا و فقط یک بار دوباره فشرده می‌شود؛
پس زمان شروع هر آیه دقیق است و کیفیت به‌خاطر چندبار فشرده‌سازی پایین نمی‌آید.
"""
import argparse, array, json, math, pathlib, re, shutil, subprocess, sys

AYAHS = {78: 40, 79: 46, 80: 42, 81: 29, 82: 19, 83: 36, 84: 25, 85: 22, 86: 17, 87: 19, 88: 26, 89: 30, 90: 20,
         91: 15, 92: 21, 93: 11, 94: 8, 95: 8, 96: 19, 97: 5, 98: 8, 99: 8, 100: 11, 101: 11, 102: 8, 103: 3,
         104: 9, 105: 5, 106: 4, 107: 7, 108: 3, 109: 6, 110: 3, 111: 5, 112: 4, 113: 5, 114: 6}
RATE = 44100
NAME = re.compile(r'^(\d{1,3})[_\-]?(\d{3})\.(mp3|m4a|wav|ogg|aac)$', re.I)


def decode(path):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 's16le', '-ac', '1', '-ar', str(RATE), '-'],
                       capture_output=True)
    if r.returncode or not r.stdout:
        raise RuntimeError(f'خواندن {path.name} ناموفق بود: {r.stderr.decode(errors="ignore")[:200]}')
    return r.stdout


def find_bism(src, out):
    """بسم‌الله جدا (فایل 001001.mp3 = آیهٔ اول حمد). مدت آن را می‌دهد، یا None"""
    for d in (src, out):
        for p in (d / '001001.mp3', d / '1_001.mp3'):
            if p.exists():
                try:
                    return len(decode(p)) / 2 / RATE
                except RuntimeError:
                    pass
    return None


def split_bism(pcm, bd):
    """آیهٔ اولِ بیشتر سوره‌ها در فایل EveryAyah با «بسم‌الله» شروع می‌شود. مکث بعد از بسم‌الله را پیدا می‌کند و
    (پایان بسم‌الله، شروع آیه) را به ثانیه برمی‌گرداند؛ اگر پیدا نشد None."""
    smp = array.array('h'); smp.frombytes(bytes(pcm[:len(pcm) // 2 * 2]))
    fr = int(RATE * .02); n = len(smp) // fr
    if n * .02 < bd + 1.0:
        return None
    rms = [math.sqrt(sum(x * x for x in smp[i * fr:(i + 1) * fr]) / fr) for i in range(int(min(n, (bd + 3) / .02)))]
    thr = max(120, .07 * max(rms))
    runs, i = [], 0
    while i < len(rms):
        if rms[i] < thr:
            j = i
            while j < len(rms) and rms[j] < thr:
                j += 1
            if (j - i) * .02 >= .16:
                runs.append((i * .02, j * .02))
            i = j
        else:
            i += 1
    cand = [r for r in runs if max(1.0, bd - 1.6) <= r[0] <= bd + 1.6]
    if not cand:
        return None
    r = min(cand, key=lambda r: abs(r[0] - bd))
    return round(r[0] + .1, 2), round(max(r[0] + .1, r[1] - .1), 2)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src', help='پوشهٔ فایل‌های آیه‌به‌آیه')
    ap.add_argument('--out', default=str(pathlib.Path(__file__).resolve().parent.parent / 'audio'), help='پوشهٔ خروجی')
    ap.add_argument('--bitrate', default='64k', help='کیفیت mp3 (پیش‌فرض 64k، تک‌کاناله)')
    ap.add_argument('--no-bism', action='store_true', help='بسم‌الله را از آیهٔ اول جدا نکن')
    ap.add_argument('--gap', type=float, default=0.0, help='مکث اضافه بین آیه‌ها به ثانیه (پیش‌فرض ۰)')
    a = ap.parse_args()
    if not shutil.which('ffmpeg'):
        sys.exit('ffmpeg نصب نیست. اول آن را نصب کنید (ffmpeg.org).')
    src, out = pathlib.Path(a.src), pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    found = {}
    for p in sorted(src.rglob('*')):
        m = NAME.match(p.name)
        if m and p.is_file():
            s, v = int(m.group(1)), int(m.group(2))
            if s in AYAHS and 1 <= v <= AYAHS[s]:
                found.setdefault(s, {})[v] = p

    tfile = out / 'timings.json'
    timings = json.loads(tfile.read_text()) if tfile.exists() else {}
    done, bad = [], []
    bd = None if a.no_bism else find_bism(src, out)
    bism = timings.get('b', {}) if isinstance(timings.get('b'), dict) else {}
    print('مدت بسم‌الله جدا:', f'{bd:.1f} ثانیه' if bd else 'پیدا نشد (جداسازی بسم‌الله انجام نمی‌شود)')
    for s, n in AYAHS.items():
        have = found.get(s, {})
        missing = [v for v in range(1, n + 1) if v not in have]
        if not have:
            continue
        if missing:
            bad.append((s, missing)); continue
        pcm, starts, pos = bytearray(), [], 0.0
        gap = b'\0\0' * int(RATE * a.gap)
        for v in range(1, n + 1):
            starts.append(round(pos, 3))
            d = decode(have[v]) + gap
            if v == 1 and bd:
                sp = split_bism(d, bd)
                if sp:
                    bism[str(s)] = [0, sp[0]]; starts[-1] = sp[1]
                    print(f'  سورهٔ {s}: بسم‌الله 0 تا {sp[0]} ثانیه، آیهٔ ۱ از {sp[1]}')
                else:
                    bism.pop(str(s), None)
                    print(f'  سورهٔ {s}: بسم‌الله در فایل آیهٔ اول پیدا نشد (فقط آیه است؟)')
            pcm += d; pos += len(d) / 2 / RATE
        enc = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 's16le', '-ar', str(RATE), '-ac', '1', '-i', '-',
                              '-c:a', 'libmp3lame', '-b:a', a.bitrate, str(out / f'{s:03d}.mp3')], input=bytes(pcm))
        if enc.returncode:
            sys.exit(f'ساخت فایل سورهٔ {s} ناموفق بود')
        timings[str(s)] = starts
        done.append(s)
        print(f'سورهٔ {s}: {n} آیه، {pos:.1f} ثانیه')
    if bism:
        timings['b'] = bism
    tfile.write_text(json.dumps(timings), encoding='utf8')
    (out / 'timings.js').write_text('window.HIFZ_TIMINGS=' + json.dumps(timings) + ';', encoding='utf8')   # برای باز کردن مستقیم index.html بدون سرور (file://)
    print(f'\nساخته شد: {len(done)} سوره  ->  {out}')
    for s, miss in bad:
        print(f'ناقص (ساخته نشد): سورهٔ {s}، آیه‌های {miss}')
    if not found:
        print('هیچ فایلی با نام درست پیدا نشد. نام فایل‌ها باید مثل 114001.mp3 باشد.')


if __name__ == '__main__':
    main()
