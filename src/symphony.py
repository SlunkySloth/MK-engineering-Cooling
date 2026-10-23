"""Symphony air coolers and fans, read from the capture made by fetch-symphony.py.

Products come out in the same shape as extract.catalogue() products, plus
brand, key_specs and features, so the shared templates render them. Prices are
captured but deliberately not published.
"""
import html
import json
import re

from extract import SOURCE

NAME = 'Symphony'
ROOT_PATH = '/symphony/'
MENU_TEXT = 'Air coolers & tower fans'
TITLE = 'Symphony air coolers & fans'
META = 'Symphony desert, tower, personal and commercial air coolers and tower fans'
CATEGORIES = [  # slug, name, blurb
    ('desert-coolers', 'Desert Coolers', 'Large tanks and strong air throw for big rooms, shops and halls'),
    ('tower-coolers', 'Tower Coolers', 'Slim, space-saving coolers for bedrooms and offices'),
    ('personal-coolers', 'Personal Coolers', 'Compact coolers for small rooms, kitchens and desks'),
    ('commercial-coolers', 'Commercial & Industrial', 'Heavy-duty coolers for factories, warehouses and outdoor spaces'),
    ('tower-fans', 'Tower Fans', 'Bladeless and BLDC tower fans that boost AC cooling'),
]
EMOJI = re.compile('[\U0001F000-\U0001FAFF☀-➿️‍]')


def category_of(p):
    t, title = p['product_type'], p['title'].lower()
    if t == 'Commercial' or re.search(r'\b(commercial|industrial)\b', title):
        return 'commercial-coolers'
    if t == 'Tower Fan' or (t == 'BLDC' and 'fan' in title and 'cooler' not in title):
        return 'tower-fans'
    if t in ('Personal Cooler', 'Kitchen Fan'):
        return 'personal-coolers'
    if t in ('Tower Cooler', 'BLDC') or 'tower' in title:
        return 'tower-coolers'
    return 'desert-coolers'


def plain(s):
    s = html.unescape(re.sub(r'<[^>]+>', ' ', s))
    return re.sub(r'\s+', ' ', EMOJI.sub('', s)).strip(' –-|')


def bullets(body):
    """List items from the description, ignoring comparison tables."""
    body = re.sub(r'<table.*?</table>', '', body, flags=re.S | re.I)
    items = [plain(li) for li in re.findall(r'<li[^>]*>(.*?)</li>', body, re.S | re.I)]
    if not items:
        items = [plain(p) for p in re.findall(r'<p[^>]*>(.*?)</p>', body, re.S | re.I)]
    return [i for i in dict.fromkeys(items) if 3 < len(i) < 160]


def specs_of(p, text, cat):
    tags = p['tags']
    out = []
    if cat != 'tower-fans':
        m = (re.search(r'(\d+)\s?(?:L|litres?|liters?)\b[^.|]{0,12}?(?:water)?[- ]?tank', text, re.I)
             or re.search(r'tank(?: capacity)?[^\d.]{0,20}(\d+)\s?(?:L|litres?)\b', text, re.I)
             or next((m for t in tags if (m := re.fullmatch(r'(\d+)\s?(?:L|litre)', t.strip(), re.I))), None)
             or re.search(r'\b(\d{2,3})\s?(?:L|Litres?)\b', p['title']))
        if m:
            out.append(('Tank capacity', f'{m.group(1)} L'))
    m = re.search(r'rooms? (?:up ?to|of) (\d+)\s?m²(?:\s*\(?\s*(\d+)\s*sq\.?\s?ft)?', text, re.I)
    if m:
        out.append(('Room size', f'Up to {m.group(1)} m²' + (f' ({m.group(2)} sq.ft.)' if m.group(2) else '')))
    else:
        t = next((t for t in tags if re.fullmatch(r'\d+ Sq\. ?ft\.?', t.strip())), None)
        if t:
            out.append(('Room size', 'Up to ' + t.strip().replace('Sq. ft.', 'sq.ft.')))
    m = (re.search(r'(\d+(?:\.\d+)?)\s?(m|ft|feet)\.?\s+(?:of\s+)?(?:powerful\s+)?air\s?throw', text, re.I)
         or re.search(r'air\s?throw(?: of| up ?to)?\s+(\d+(?:\.\d+)?)\s?(m|ft|feet)\b', text, re.I))
    if m:
        out.append(('Air throw', f"{m.group(1)} {'ft' if m.group(2).lower().startswith('f') else 'm'}"))
    m = re.search(r'(\d{2,4})\s?(?:W\b|watts?)', text, re.I)
    if m:
        out.append(('Power consumption', f'{m.group(1)} W'))
    colours = [v for o in p['options'] if o['name'].lower() in ('color', 'colour') for v in o['values']]
    if colours:
        out.append(('Colour', ', '.join(colours)))
    sku = p['variants'][0].get('sku')
    if sku:
        out.append(('Model code', sku))
    return [{'label': k, 'value': html.escape(v)} for k, v in out]



def catalogue():
    f = SOURCE / 'symphony' / 'products.json'
    if not f.exists():
        return {'products': {}, 'categories': {}, 'groups': []}
    raw = json.loads(f.read_text())
    cats = {f'{ROOT_PATH}{slug}/': {'slug': slug, 'name': name, 'blurb': blurb, 'path': f'{ROOT_PATH}{slug}/', 'count': 0}
            for slug, name, blurb in CATEGORIES}
    products = {}
    for p in raw:
        images = [im['local'] for im in p['images'] if im.get('local') and (SOURCE / im['local'].lstrip('/')).exists()]
        if not images:
            continue
        cat = category_of(p)
        cpath = f'{ROOT_PATH}{cat}/'
        name = re.split(r'\s[|–]\s', p['title'])[0].strip()
        text = plain(p['title'] + ' | ' + p['body_html'])
        feats = bullets(p['body_html'])
        url = f"{ROOT_PATH}product/{p['handle']}/"
        specs = specs_of(p, text, cat)
        products[url] = {
            'url': url, 'name': name, 'title': p['title'], 'brand': 'Symphony', 'local': True,
            'images': images, 'thumb': images[0], 'specs': specs,
            'key_specs': [s for s in specs if s['label'] in ('Tank capacity', 'Room size', 'Air throw')][:2]
                         or specs[:1],
            'features': [x for x in feats if not x.lower().startswith('note')],
            'notes': [html.escape(x) for x in feats if x.lower().startswith('note')],
            'hotspot': None, 'brochure': None, 'tags': [], 'related': [],
            'cats': [ROOT_PATH, cpath], 'cat_slugs': [cat], 'primary_cat': cpath,
            'primary_cat_name': cats[cpath]['name'],
        }
        cats[cpath]['count'] += 1
    for c in cats.values():
        members = [p for p in products.values() if p['primary_cat'] == c['path']]
        c['thumb'] = members[0]['thumb'] if members else None
    cats = {k: v for k, v in cats.items() if v['count']}
    groups = [('Air coolers', [p for p in cats if 'fans' not in p]), ('Fans', [p for p in cats if 'fans' in p])]
    return {'products': products, 'categories': cats, 'groups': groups}
