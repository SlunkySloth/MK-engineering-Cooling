"""Capture Elanpro's product catalogue (names, specifications, features, photos) into source/elanpro/.

    python fetch-elanpro.py

MK Engineering is an authorised Elanpro dealer. Reads the public WooCommerce
store feed of elanpro.net, politely (few requests at a time), and saves:
  source/elanpro/products.json     raw product records
  source/elanpro/categories.json   product category tree
  source/elanpro/img/              product photos as WebP
The site build reads only these local files, so it never needs the network.
"""
import json
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

from PIL import Image

SITE = 'https://elanpro.net'
OUT = Path(__file__).resolve().parent / 'source' / 'elanpro'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36'
MAX_IMAGES = 6
IMAGE_WIDTH = 1400


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def paged(endpoint):
    out, page = [], 1
    while True:
        batch = json.loads(get(f'{SITE}/wp-json/wc/store/v1/{endpoint}?per_page=100&page={page}'))
        if not batch:
            return out
        out += batch
        page += 1
        time.sleep(2)


def main():
    (OUT / 'img').mkdir(parents=True, exist_ok=True)
    items = paged('products')
    cats = paged('products/categories')
    jobs = {}
    for p in items:
        for im in p['images'][:MAX_IMAGES]:
            stem = re.sub(r'[^a-z0-9]+', '-', Path(im['src'].split('?')[0]).stem.lower()).strip('-')[:70]
            name = f'{stem}-{im["id"]}.webp'
            im['local'] = f'/elanpro/img/{name}'
            jobs[im['src']] = OUT / 'img' / name

    def fetch(job):
        url, dst = job
        if dst.exists():
            return 0
        with Image.open(BytesIO(get(url))) as im:
            im = im.convert('RGBA') if im.mode in ('P', 'LA', 'RGBA') else im.convert('RGB')
            im.thumbnail((IMAGE_WIDTH, IMAGE_WIDTH))
            im.save(dst, 'WEBP', quality=88, method=5)
        time.sleep(0.2)
        return 1

    with ThreadPoolExecutor(3) as pool:
        fetched = sum(pool.map(fetch, jobs.items()))
    (OUT / 'products.json').write_text(json.dumps(items, ensure_ascii=False, indent=1))
    (OUT / 'categories.json').write_text(json.dumps(cats, ensure_ascii=False, indent=1))
    print(f'{len(items)} products, {len(cats)} categories, {len(jobs)} images ({fetched} downloaded) -> {OUT}')


if __name__ == '__main__':
    main()
