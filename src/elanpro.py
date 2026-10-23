"""Elanpro commercial refrigeration, read from the capture made by fetch-elanpro.py.

Products come out in the same shape as the Symphony products (see symphony.py):
the shared templates render cards, product pages, search and compare for them.
Each product sits in one of Elanpro's top-level ranges; its own sub-category
is kept as `sub` and used for the filter chips on the range page.
"""
import html
import json
import re

from bs4 import BeautifulSoup

from extract import SOURCE

NAME = 'Elanpro'
ROOT_PATH = '/elanpro/'
MENU_TEXT = 'Commercial & pharma refrigeration'
TITLE = 'Elanpro commercial refrigeration'
META = 'Elanpro visi coolers, freezers, supermarket, kitchen, bar, ice machine, pharma and laboratory refrigeration'
GROUPS = [  # menu column title, top-level category slugs
    ('Retail & display', ['retail', 'super-market', 'beverage', 'confectionery-showcase', 'vending-machine']),
    ('Kitchen & bar', ['professional-kitchen', 'bar-refrigeration', 'beer-tower', 'mini-bar-mini-fridge', 'ice-machine-flakers']),
    ('Specialty', ['pharma', 'cold-room', 'water-cooler', 'water-dispenser']),
]
KEY_WORDS = ['capacity', 'temperature', 'dimension', 'size', 'production']


def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(s or '')).strip()


def specs_of(description):
    soup = BeautifulSoup(description or '', 'lxml')
    out = []
    for tr in soup.find_all('tr'):
        cells = [clean(c.get_text(' ', strip=True)) for c in tr.find_all(['td', 'th'])]
        if len(cells) >= 2 and cells[0] and cells[1] and cells[0].lower() != 'specification':
            out.append({'label': html.escape(cells[0]), 'value': html.escape(cells[1])})
    return out


def features_of(short_description):
    soup = BeautifulSoup(short_description or '', 'lxml')
    items = [clean(el.get_text(' ', strip=True)) for el in soup.find_all(['li', 'p'])]
    return [i for i in dict.fromkeys(items) if 2 < len(i) < 160]


def key_specs(specs):
    out = []
    for word in KEY_WORDS:
        s = next((s for s in specs if word in s['label'].lower() and s not in out), None)
        if s:
            out.append(s)
        if len(out) == 2:
            break
    return out


def catalogue():
    fp, fc = SOURCE / 'elanpro' / 'products.json', SOURCE / 'elanpro' / 'categories.json'
    if not fp.exists() or not fc.exists():
        return {'products': {}, 'categories': {}, 'groups': []}
    raw, rawcats = json.loads(fp.read_text()), json.loads(fc.read_text())
    by_id = {c['id']: c for c in rawcats}

    def top_of(c):
        while c['parent'] and c['parent'] in by_id:
            c = by_id[c['parent']]
        return c

    def depth(c):
        d = 0
        while c['parent'] and c['parent'] in by_id:
            c, d = by_id[c['parent']], d + 1
        return d

    cats = {}
    for c in rawcats:
        if not c['parent']:
            path = f"{ROOT_PATH}{c['slug']}/"
            cats[path] = {'slug': c['slug'], 'name': clean(c['name']), 'path': path, 'count': 0, 'subs': {}}
    products = {}
    for p in raw:
        images = [im['local'] for im in p['images'] if im.get('local') and (SOURCE / im['local'].lstrip('/')).exists()]
        pcats = [by_id[c['id']] for c in p['categories'] if c['id'] in by_id]
        if not images or not pcats:
            continue
        leaf = max(pcats, key=depth)
        top = top_of(leaf)
        cpath = f"{ROOT_PATH}{top['slug']}/"
        name = clean(p['name'])
        specs = specs_of(p['description'])
        url = f"{ROOT_PATH}product/{p['slug']}/"
        sub = clean(leaf['name']) if leaf is not top else ''
        no_photo = all('comingsoon' in i.lower() for i in images)  # Elanpro's own "image coming soon" artwork
        products[url] = {
            'url': url, 'name': name, 'title': name, 'brand': NAME, 'local': True,
            'images': images, 'thumb': images[0], 'specs': specs, 'key_specs': key_specs(specs),
            'features': features_of(p['short_description']), 'notes': [],
            'hotspot': None, 'brochure': None, 'tags': [], 'related': [],
            'cats': [ROOT_PATH, cpath], 'cat_slugs': [top['slug']] + ([leaf['slug']] if sub else []),
            'primary_cat': cpath, 'primary_cat_name': cats[cpath]['name'], 'sub': sub,
            'model': clean(p.get('sku')), 'no_photo': no_photo,
        }
        cats[cpath]['count'] += 1
        if sub:
            s = cats[cpath]['subs'].setdefault(leaf['slug'], {'slug': leaf['slug'], 'name': sub, 'count': 0})
            s['count'] += 1
    # Models with real photos first; placeholders never become range thumbnails.
    products = dict(sorted(products.items(), key=lambda kv: kv[1]['no_photo']))
    for c in cats.values():
        members = [p for p in products.values() if p['primary_cat'] == c['path']]
        c['thumb'] = next((p['thumb'] for p in members if not p['no_photo']), members[0]['thumb'] if members else None)
        c['subs'] = sorted(c['subs'].values(), key=lambda s: -s['count'])
        c['blurb'] = ', '.join(s['name'] for s in c['subs'][:3])
    cats = {k: v for k, v in cats.items() if v['count']}
    order = [slug for _, slugs in GROUPS for slug in slugs]
    cats = dict(sorted(cats.items(), key=lambda kv: order.index(kv[1]['slug']) if kv[1]['slug'] in order else 99))
    groups = [(title, [f'{ROOT_PATH}{s}/' for s in slugs if f'{ROOT_PATH}{s}/' in cats]) for title, slugs in GROUPS]
    leftover = [p for p in cats if all(p not in g for _, g in groups)]
    if leftover:
        groups[-1][1].extend(leftover)
    return {'products': products, 'categories': cats, 'groups': groups}
