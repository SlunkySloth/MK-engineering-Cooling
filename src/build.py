"""Build the static site into dist/ from the captured content in source/.

    python src/build.py           # full build
    python src/build.py --dump    # also write extracted data to build-data.json
"""
import hashlib
import html
import json
import re
import shutil
import sys
import time
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

import extract as X
from images import Images

ROOT = X.ROOT
SRC = Path(__file__).resolve().parent
DIST = ROOT / 'dist'
ORIGIN = X.ORIGIN

PAGE_TITLES = {
    '/about-us/': ('About us', 'company'),
    '/factories/': ('Factories', 'company'),
    '/research/': ('Research & Development', 'company'),
    '/sustainability/': ('Sustainability', 'company'),
    '/careers/': ('Careers', 'company'),
    '/industries/': ('Industries', 'industries'),
    '/service/': ('Service', 'service'),
    '/no-gift-policy/': ('No Gift Policy', ''),
    '/cashback-offers/': ('Cashback Offers', ''),
}
SKIP_SECTIONS = {'E-Waste Location'}  # interactive locator that depended on the old server
TYPOS = {'Recommeded products': 'Recommended products', 'Lenght:': 'Length:', 'expIore': 'explore'}
SPEC_PRIORITY = ['gross vol', 'net vol', 'capacity', 'production', 'ice production', 'temperature', 'storage', 'external dimension', 'dimension', 'refrigerant']


def fix_typos(s):
    for a, b in TYPOS.items():
        s = s.replace(a, b)
    return s


def nicedate(d):
    try:
        return date.fromisoformat(d).strftime('%-d %b %Y')
    except ValueError:
        return d


def short(value, limit=26):
    """One-line, plain-text version of a spec value for compact cards."""
    s = re.sub(r'\s+', ' ', re.sub(r'<br\s*/?>', ' / ', value))
    s = html.unescape(re.sub('<[^>]+>', '', s)).strip(' /')
    return s if len(s) <= limit else s[:limit - 1].rstrip(' /,') + '…'


def slug_of(path):
    return path.rstrip('/').split('/')[-1]


class Site:
    def __init__(self):
        self.config = json.loads((SRC / 'site.json').read_text())
        self.images = Images(X.SOURCE, DIST / 'img')
        self._img_cache = {}
        self.pages = {}  # output path -> html
        self.generated = set()

    # ---------------------------------------------------------------- links
    def link(self, href):
        href = X.local_path(href or '')
        if not href or href.startswith(('#', 'mailto:', 'tel:', 'http://', 'https://', '//', 'javascript:')):
            return href
        path, _, frag = href.partition('#')
        path, _, query = path.partition('?')
        if path and not path.endswith('/') and not re.search(r'\.\w{2,5}$', path):
            path += '/'
        path = self.aliases.get(path, path)
        if path in self.generated:
            return path + (f'?{query}' if query else '') + (f'#{frag}' if frag else '')
        return ORIGIN + href

    def is_external(self, href):
        return self.link(href).startswith('http')

    def links(self, s):
        def repl(m):
            target = self.link(html.unescape(m.group(1)))
            extra = ' target="_blank" rel="noopener"' if target.startswith('http') else ''
            return f'href="{html.escape(target)}"{extra}'
        return Markup(re.sub(r'href="([^"]*)"', repl, fix_typos(str(s))))

    def img(self, src, widths=(480, 960)):
        key = (src, tuple(widths))
        if key not in self._img_cache:
            self._img_cache[key] = self.images.get(src, widths)
        return self._img_cache[key]

    # ---------------------------------------------------------------- data
    def load(self):
        t = time.time()
        self.cat = X.catalogue()
        self.home = X.home()
        self.timeline = X.timeline()
        self.posts = X.blog()
        self.contact = X.contact()
        self.menu = X.menu_products()
        self.content = {p: X.content_page(p) for p in PAGE_TITLES}
        self.aliases = self.cat['aliases']
        print(f'extracted in {time.time() - t:.1f}s: {len(self.cat["products"])} products, '
              f'{len(self.cat["categories"])} categories, {len(self.posts)} posts')

        cats = self.cat['categories']
        products = self.cat['products']
        for n in cats.values():
            n['count'] = sum(n['path'] in p['cats'] for p in products.values())
        for t in self.cat['tags'].values():
            t['members'] = [m for m in t['members'] if m in products]
        for post in self.posts:
            words = sum(len(re.sub('<[^>]+>', '', b.get('html', '') + ' '.join(b.get('items', []))).split()) for b in post['body'])
            post['minutes'] = max(1, round(words / 200))
            first = next((b['html'] for b in post['body'] if b['type'] == 'p'), '')
            post['excerpt'] = re.sub(r'\s+', ' ', re.sub('<[^>]+>', '', first)).strip()

        # Every URL we will write, so links can be resolved before rendering.
        self.generated = {'/', '/products/', '/contact-us/', '/blog/', '/compare/', *PAGE_TITLES, *cats,
                          *self.cat['tags'], *(p for p, v in products.items() if v['local']),
                          *(post['url'] for post in self.posts), *self.aliases}

    def card(self, p):
        specs = p['specs']
        key = []
        for word in SPEC_PRIORITY:
            for s in specs:
                if s['label'] and word in re.sub('<[^>]+>', '', s['label']).lower() and s not in key:
                    key.append(s)
                    break
            if len(key) == 2:
                break
        key = [{'label': s['label'], 'value': short(s['value'])} for s in key]
        spec_text = ' '.join(re.sub('<[^>]+>', ' ', s['label'] + ' ' + s['value']) for s in specs)
        return {
            'name': p['name'],
            'url': p['url'],
            'href': p['url'] if p['local'] else ORIGIN + p['url'],
            'local': p['local'],
            'thumb': p.get('thumb') or p.get('list_thumb'),
            'cat': p['primary_cat_name'],
            'cat_slugs': sorted({slug_of(c) for c in p['cats']}),
            'key_specs': key,
            'search': re.sub(r'\s+', ' ', f"{p['name']} {p['primary_cat_name']} {spec_text}").lower(),
        }

    def highlights(self, p):
        out = []
        for word in SPEC_PRIORITY:
            for s in p['specs']:
                if s['label'] and word in re.sub('<[^>]+>', '', s['label']).lower() and s not in out:
                    out.append(s)
                    break
            if len(out) == 3:
                break
        return out

    # ---------------------------------------------------------------- content pages
    def prepare_sections(self, path, page_title):
        cats = self.cat['categories']
        products = self.cat['products']
        out = []
        lead = ''
        for sec in self.content[path]['sections']:
            if sec['title'] in SKIP_SECTIONS:
                continue
            body, cards = X.cards_from(sec['blocks'])
            texts = [b for b in body if b['type'] in ('p', 'list', 'h')]
            images = [b for b in body if b['type'] == 'img']
            buttons = [b for b in body if b['type'] == 'button']
            for c in cards:
                c['eyebrow'] = fix_typos(c['eyebrow'])
                if not c['img'] and c['buttons']:
                    # Recommended-product cards without artwork: borrow a product photo.
                    target = self.link(c['buttons'][0]['href'])
                    target = self.aliases.get(target, target)
                    match = next((p for p in products.values() if target in p['cats'] and p['local']), None)
                    if match:
                        c['img'] = {'src': match['thumb'], 'alt': ''}
            if not texts and not images and not cards and not buttons:
                continue
            s = {
                'eyebrow': sec['eyebrow'], 'title': sec['title'], 'anchor': sec['anchor'],
                'text': texts, 'images': images, 'buttons': buttons, 'cards': cards,
                'layout': 'split' if images and len(images) <= 2 and (texts or buttons) else 'stack',
                'numbered': bool(cards) and all(not c['img'] and not c['html'] for c in cards),
                'soft': bool(cards),
            }
            if sec['title'] == 'Journey':
                s['special'] = 'timeline'
            # Intro row that only repeats the page name: use it as the page lead.
            if not out and not lead and not images and not cards and len(texts) <= 2 and \
                    (not sec['title'] or sec['title'].lower() in (page_title.lower(), 'research and development', 'factories', 'industries', 'careers')):
                parts = [f"<strong>{t['text']}</strong>" if t['type'] == 'h' else t.get('html', '') for t in texts]
                lead = ' '.join(parts)
                continue
            out.append(s)
        if path == '/factories/':
            for s in out:
                if s['title'] == 'Crafting Solutions':
                    s['cards'] = [{'title': '', 'eyebrow': '', 'img': None, 'html': [t['html']], 'buttons': []} for t in s['text']]
                    s['text'], s['numbered'], s['soft'] = [], True, True
        if path == '/careers/':
            for s in out:
                for c in s['cards']:
                    c['buttons'] = [b for b in c['buttons'] if not b['href'].startswith('#')]
        return out, lead

    # ---------------------------------------------------------------- rendering
    def env(self):
        env = Environment(loader=FileSystemLoader(SRC / 'templates'), autoescape=select_autoescape(['html']),
                          trim_blocks=True, lstrip_blocks=True)
        env.filters.update(link=self.link, is_external=self.is_external, links=self.links, nicedate=nicedate,
                           logo_name=lambda s: '' if re.search(r'New-Project|^\d', Path(s).stem) else
                           re.sub(r'^\d+-|-\d+$', '', Path(s).stem).replace('-', ' '))
        hashes = {f.name: hashlib.md5(f.read_bytes()).hexdigest()[:8] for f in (SRC / 'assets').glob('*.*')}
        menu_columns = [[dict(m, range=fix_typos(m['range'])) for m in col] for col in self.menu]
        env.globals.update(
            site=self.config, images=self.img, asset=lambda n: f'/assets/{n}?v={hashes[n]}',
            menu_columns=menu_columns, product_total=len(self.cat['products']),
            footer_categories=[{'label': m['label'], 'path': m['path']} for col in self.menu for m in col][:8],
            year=date.today().year, logo=self.config['logo'], favicon=self.config['favicon'],
            touch_icon=self.config['touch_icon'],
            footer_blurb='A Hoshizaki group company manufacturing commercial refrigeration across four plants in India.',
        )
        return env

    def write(self, path, html_text):
        f = DIST / (path.strip('/') + '/index.html' if path.endswith('/') else path.lstrip('/'))
        if path == '/':
            f = DIST / 'index.html'
        f.parent.mkdir(parents=True, exist_ok=True)
        html_text = re.sub(r'\n\s*\n+', '\n', html_text)
        f.write_text(html_text, encoding='utf-8')
        self.pages[path] = f

    def build(self):
        t0 = time.time()
        self.load()
        if DIST.exists():
            for child in DIST.iterdir():
                if child.name != 'img':
                    shutil.rmtree(child) if child.is_dir() else child.unlink()
        DIST.mkdir(exist_ok=True)
        env = self.env()
        cats = self.cat['categories']
        products = self.cat['products']
        cards = {u: self.card(p) for u, p in products.items()}
        ordered = list(products)  # capture order: detail pages first, then listing-only

        def crumbs_for(path):
            trail = []
            n = cats.get(path)
            while n:
                trail.insert(0, {'name': n['name'], 'path': n['path']})
                n = cats.get(n['parent'])
            return [{'name': 'Products', 'path': '/products/'}] + trail

        range_cards = []
        menu_lookup = {m['path']: m for col in self.menu for m in col}
        for rc in self.home['range_cards']:
            target = self.aliases.get(rc['path'], rc['path'])
            m = menu_lookup.get(rc['path']) or menu_lookup.get(target)
            n = cats.get(target)
            range_cards.append({'path': rc['path'] if rc['path'] in self.generated else target, 'img': rc['img'],
                                'name': m['label'] if m else (n['name'] if n else ''),
                                'range': fix_typos(m['range']) if m else (n.get('range') or (f"{n['count']} models" if n else ''))})

        common = dict(range_cards=range_cards)

        # Home
        logos = self.home['logos']
        half = (len(logos) + 1) // 2
        industries_links = {'Hotels': '/industries/#foodservice', 'Cafe': '/industries/#foodservice',
                            'Retail': '/industries/#retail', 'Bar': '/industries/#beverage'}
        for ind in self.home['industries']:
            ind['href'] = next((v for k, v in industries_links.items() if ind['title'].startswith(k)), '/industries/')
        for b in self.home['banners']:
            target = products.get(b['href'] or '')
            b['alt'] = f"{target['name']} – {target['primary_cat_name']}" if target else 'Featured product range'
        self.write('/', env.get_template('home.html').render(
            home=self.home, posts=self.posts, logo_rows=[logos[:half], logos[half:]],
            meta_title=self.home['meta_title'], meta_description=self.home['meta_description'], **common))

        # Catalogue: all products
        top = self.cat['tree']
        self.write('/products/', env.get_template('catalog.html').render(
            title='All products', trail=[{'name': 'Products'}],
            lead=f'{len(products)} models across {len(top)} categories. Filter instantly, open any model for full specifications, or tick Compare to see models side by side.',
            chips=[{'name': 'All', 'filter': '', 'count': len(products)}] + [{'name': n['name'], 'filter': n['slug'], 'count': n['count']} for n in top],
            chips_label='Filter by category', current='/products/', open_paths=set(), tree=top,
            items=[cards[u] for u in ordered], show_tiles=True, section='products',
            meta_title=f"Products | {self.config['name']}",
            meta_description=f"Browse {len(products)} commercial refrigeration models: visi coolers, deep freezers, stainless steel kitchen refrigeration, ice machines and more.",
            **common))

        # Categories (and the alias URL used by the original menu)
        for path, n in list(cats.items()) + [(a, cats[t]) for a, t in self.aliases.items()]:
            members = [cards[u] for u in ordered if n['path'] in products[u]['cats']]
            open_paths = set()
            m = n
            while m:
                open_paths.add(m['path'])
                m = cats.get(m['parent'])
            if n['children']:
                chips = [{'name': 'All', 'path': n['path'], 'count': n['count']}] + [{'name': c['name'], 'path': c['path'], 'count': c['count']} for c in n['children']]
            elif n['parent']:
                parent = cats[n['parent']]
                chips = [{'name': 'All ' + parent['name'], 'path': parent['path'], 'count': parent['count']}] + [{'name': c['name'], 'path': c['path'], 'count': c['count']} for c in parent['children']]
            else:
                chips = []
            rng = fix_typos(n.get('range', ''))
            lead = f"{n['count']} model{'s' if n['count'] != 1 else ''}" + (f' · {rng}' if rng else '')
            self.write(path, env.get_template('catalog.html').render(
                title=n['name'], trail=crumbs_for(n['path']), lead=lead, chips=chips, chips_label='Sub-categories',
                current=n['path'], open_paths=open_paths, tree=top, items=members, faq=n.get('faq'),
                section='products', meta_title=n.get('meta_title') or f"{n['name']} | {self.config['name']}",
                meta_description=n.get('meta_description') or f"{n['name']} range from {self.config['name']}: {lead}.",
                **common))

        # Tags
        for path, t in self.cat['tags'].items():
            members = [cards[u] for u in t['members']]
            self.write(path, env.get_template('catalog.html').render(
                title=t['name'][:1].upper() + t['name'][1:], trail=[{'name': 'Products', 'path': '/products/'}, {'name': t['name']}],
                lead=f"{len(members)} model{'s' if len(members) != 1 else ''} tagged “{t['name']}”.", chips=[],
                current=path, open_paths=set(), tree=top, items=members, section='products',
                meta_title=f"{t['name']} | {self.config['name']}", **common))

        # Product detail pages
        for u, p in products.items():
            if not p['local']:
                continue
            rel = [r for r in p['related'] if r in products and r != u]
            if len(rel) < 4:
                rel += [o for o in ordered if o != u and o not in rel and p['primary_cat'] in products[o]['cats']][:4 - len(rel)]
            p['highlights'] = self.highlights(p)
            spec_desc = ', '.join(f"{re.sub('<[^>]+>', '', s['label'])} {re.sub('<[^>]+>', '', s['value'])}" for s in p['specs'][:4] if s['label'])
            self.write(u, env.get_template('product.html').render(
                p=p, related=[cards[r] for r in rel[:4]], trail=crumbs_for(p['primary_cat']) + [{'name': p['name']}],
                section='products', meta_title=f"{p['name']} – {p['primary_cat_name']} | {self.config['name']}",
                meta_description=f"{p['name']} {p['primary_cat_name'].lower()} by {self.config['name']}. {spec_desc}."))

        # Content pages
        for path, (title, section) in PAGE_TITLES.items():
            sections, lead = self.prepare_sections(path, title)
            pg = self.content[path]
            self.write(path, env.get_template('content.html').render(
                title=title, trail=[{'name': title}], lead=lead, eyebrow='', sections=sections, timeline=self.timeline,
                section=section, show_cta=path not in ('/no-gift-policy/',),
                meta_title=pg['meta_title'], meta_description=pg['meta_description']))

        self.write('/contact-us/', env.get_template('contact.html').render(
            contact=self.contact, section='contact', meta_title=f"Contact us | {self.config['name']}",
            meta_description=f"Contact {self.config['name']} for sales and service: {self.config['phones'][0]['display']}, {self.config['email']}."))
        self.write('/blog/', env.get_template('blog.html').render(
            posts=self.posts, section='blog', meta_title=f"Blog | {self.config['name']}"))
        for post in self.posts:
            others = [o for o in self.posts if o is not post][:3]
            self.write(post['url'], env.get_template('post.html').render(
                post=post, others=others, section='blog', meta_title=f"{post['title']} | {self.config['name']}",
                meta_description=post['meta_description'] or post['excerpt'][:160]))
        self.write('/compare/', env.get_template('compare.html').render(section='products', meta_title=f"Compare products | {self.config['name']}"))
        self.write('/404.html', env.get_template('404.html').render(meta_title=f"Page not found | {self.config['name']}"))

        # Data files for search and compare
        index = []
        for u in ordered:
            c, p = cards[u], products[u]
            th = self.img(c['thumb'], [160])
            index.append({'t': c['name'], 'u': c['href'], 'k': 'Product', 'c': c['cat'], 'i': th['src'] if th else '',
                          's': ' '.join(re.sub('<[^>]+>', '', s['value']) for s in p['specs'])})
        for n in cats.values():
            index.append({'t': n['name'], 'u': n['path'], 'k': 'Category', 'c': cats[n['parent']]['name'] if n['parent'] else ''})
        for path, (title, _) in PAGE_TITLES.items():
            index.append({'t': title, 'u': path, 'k': 'Page'})
        index += [{'t': 'Contact us', 'u': '/contact-us/', 'k': 'Page'}, {'t': 'Blog', 'u': '/blog/', 'k': 'Page'}]
        for post in self.posts:
            th = self.img(post['img'], [160])
            index.append({'t': post['title'], 'u': post['url'], 'k': 'Article', 'c': post['category'], 'i': th['src'] if th else ''})
        (DIST / 'search-index.json').write_text(json.dumps(index, ensure_ascii=False, separators=(',', ':')))
        compare = {}
        for u, p in products.items():
            if p['local']:
                th = self.img(p['thumb'], [320])
                compare[u] = {'name': p['name'], 'url': u, 'cat': p['primary_cat_name'], 'img': th['src'] if th else '',
                              'specs': [[s['label'], s['value']] for s in p['specs']]}
        (DIST / 'products.json').write_text(json.dumps(compare, ensure_ascii=False, separators=(',', ':')))

        # Static assets
        shutil.copytree(SRC / 'assets', DIST / 'assets')
        favicon = self.images.resolve(self.config['favicon'])
        if favicon:
            for key in ('favicon', 'touch_icon'):
                f = X.SOURCE / self.config[key].lstrip('/')
                dst = DIST / self.config[key].lstrip('/')
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dst)

        made, total, removed = self.images.render()
        print(f'{len(self.pages)} pages, {total} images ({made} converted, {removed} removed) in {time.time() - t0:.1f}s')
        if '--dump' in sys.argv:
            (ROOT / 'build-data.json').write_text(json.dumps(
                {'catalogue': {k: v for k, v in self.cat.items() if k != 'tree'}, 'home': self.home, 'posts': self.posts},
                default=list, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    Site().build()
