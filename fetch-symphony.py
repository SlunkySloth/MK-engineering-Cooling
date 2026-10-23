"""Capture Symphony's air coolers and fans (names, prices, descriptions, photos) into source/symphony/.

    python fetch-symphony.py

Reads the public product feed of shop.symphonylimited.com and saves:
  source/symphony/products.json   raw product records (water heaters left out)
  source/symphony/img/            product photos as WebP, at most MAX_IMAGES per product
The site build reads only these local files, so it never needs the network.
"""
import json
import time
import urllib.request
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

SHOP = 'https://shop.symphonylimited.com'
OUT = Path(__file__).resolve().parent / 'source' / 'symphony'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36'
SKIP_TYPES = {'Water Heaters'}
MAX_IMAGES = 8
IMAGE_WIDTH = 1400


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def products():
    out, page = [], 1
    while True:
        batch = json.loads(get(f'{SHOP}/products.json?limit=250&page={page}'))['products']
        if not batch:
            return out
        out += batch
        page += 1
        time.sleep(1)


def main():
    (OUT / 'img').mkdir(parents=True, exist_ok=True)
    items = [p for p in products() if p['product_type'] not in SKIP_TYPES]
    jobs = []
    for p in items:
        for i, im in enumerate(p['images'][:MAX_IMAGES], 1):
            name = f"{p['handle'][:70]}-{i}.webp"
            im['local'] = f'/symphony/img/{name}'
            sep = '&' if '?' in im['src'] else '?'
            jobs.append((f"{im['src']}{sep}width={IMAGE_WIDTH}", OUT / 'img' / name))

    def fetch(job):
        url, dst = job
        if dst.exists():
            return 0
        with Image.open(BytesIO(get(url))) as im:
            im = im.convert('RGBA') if im.mode in ('P', 'LA', 'RGBA') else im.convert('RGB')
            im.thumbnail((IMAGE_WIDTH, IMAGE_WIDTH))
            im.save(dst, 'WEBP', quality=88, method=5)
        return 1

    with ThreadPoolExecutor(4) as pool:
        fetched = sum(pool.map(fetch, jobs))
    (OUT / 'products.json').write_text(json.dumps(items, ensure_ascii=False, indent=1))
    print(f'{len(items)} products, {len(jobs)} images ({fetched} downloaded) -> {OUT}')


if __name__ == '__main__':
    main()
