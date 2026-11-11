#!/usr/bin/env python3
"""
دانلود صدای استاد پرهیزگار (جزء ۳۰) از EveryAyah و آماده‌سازی برای برنامه

اجرا از پوشهٔ پروژه:
    python3 tools/fetch-everyayah.py            فقط دانلود  ->  audio-src/114001.mp3 ...
    python3 tools/fetch-everyayah.py --build    دانلود + ساخت audio/078.mp3 ... و timings.json (نیاز به ffmpeg)
    python3 tools/fetch-everyayah.py --images   دانلود تصویر آیه‌ها  ->  images/114_5.png ... (برای کار کاملاً آفلاین)

فایل‌هایی که قبلاً دانلود شده‌اند دوباره دانلود نمی‌شوند؛ اگر وسط کار قطع شد، دوباره اجرا کنید.
پوشهٔ audio-src فقط مرحلهٔ میانی است؛ لازم نیست روی GitHub بگذارید (در .gitignore بیاید).
"""
import argparse, pathlib, shutil, subprocess, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

AYAHS = {78: 40, 79: 46, 80: 42, 81: 29, 82: 19, 83: 36, 84: 25, 85: 22, 86: 17, 87: 19, 88: 26, 89: 30, 90: 20,
         91: 15, 92: 21, 93: 11, 94: 8, 95: 8, 96: 19, 97: 5, 98: 8, 99: 8, 100: 11, 101: 11, 102: 8, 103: 3,
         104: 9, 105: 5, 106: 4, 107: 7, 108: 3, 109: 6, 110: 3, 111: 5, 112: 4, 113: 5, 114: 6}
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent


def get(url, dest, tries=4):
    if dest.exists() and dest.stat().st_size > 100:
        return 'skip'
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'baghe-hifz-fetch/1.0'})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            if len(data) < 100:
                raise ValueError('فایل خیلی کوچک است')
            tmp = dest.with_suffix('.part'); tmp.write_bytes(data); tmp.replace(dest)
            return 'ok'
        except (urllib.error.URLError, OSError, ValueError) as e:
            err = e
            time.sleep(1.5 * (i + 1))
    return f'fail: {err}'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dest', default=str(ROOT / 'audio-src'), help='پوشهٔ فایل‌های آیه‌به‌آیه')
    ap.add_argument('--reciter', default='Parhizgar_48kbps', help='نام پوشهٔ قاری در EveryAyah')
    ap.add_argument('--base', default='https://everyayah.com/data', help='آدرس پایه')
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--images', action='store_true', help='به‌جای صدا، تصویر آیه‌ها را در پوشهٔ images دانلود کند')
    ap.add_argument('--img-url', default='{base}/images_png/{s}_{v}.png', help='الگوی آدرس تصویر (اگر آدرس EveryAyah فرق کرد)')
    ap.add_argument('--build', action='store_true', help='بعد از دانلود، فایل‌های هر سوره و timings.json را بسازد')
    a = ap.parse_args()
    if a.images and a.dest == str(ROOT / 'audio-src'):
        a.dest = str(ROOT / 'images')
    if a.build and not shutil.which('ffmpeg'):
        sys.exit('ffmpeg نصب نیست. اول آن را نصب کنید (ffmpeg.org)، یا بدون --build اجرا کنید.')
    dest = pathlib.Path(a.dest); dest.mkdir(parents=True, exist_ok=True)

    if a.images:
        jobs = [(a.img_url.format(base=a.base, s=s, v=v), dest / f'{s}_{v}.png') for s, n in AYAHS.items() for v in range(1, n + 1)]
    else:
        jobs = [(f'{a.base}/{a.reciter}/{s:03d}{v:03d}.mp3', dest / f'{s:03d}{v:03d}.mp3') for s, n in AYAHS.items() for v in range(1, n + 1)]
    total, failed, done = len(jobs), [], 0
    with ThreadPoolExecutor(a.threads) as ex:
        for (url, path), res in zip(jobs, ex.map(lambda j: get(*j), jobs)):
            done += 1
            if res.startswith('fail'):
                failed.append((path.name, res))
            if done % 25 == 0 or done == total:
                print(f'{done}/{total}', end='\r', flush=True)
    print(f'\nدانلود تمام شد: {total - len(failed)} از {total}')
    for n, r in failed[:15]:
        print('  ناموفق:', n, r)
    if failed:
        sys.exit('بعضی فایل‌ها دانلود نشد. اینترنت را بررسی و دوباره اجرا کنید (فایل‌های کامل دوباره دانلود نمی‌شوند).')
    if a.build and not a.images:
        sys.exit(subprocess.call([sys.executable, str(HERE / 'make-audio.py'), str(dest)]))
    if not a.images:
        print('برای ساخت فایل هر سوره:  python3 tools/make-audio.py', dest)


if __name__ == '__main__':
    main()
