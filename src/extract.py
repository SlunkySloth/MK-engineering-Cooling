"""Read the captured site in source/ and return its content as plain data.

Nothing here decides how the new site looks; templates do that. Every
function returns dicts/lists of strings so the result can be dumped to JSON
for inspection (python src/build.py --dump).
"""
import re
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup, Tag

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'source'
ORIGIN = 'https://westernequipments.com'

INLINE_TAGS = {'strong', 'b', 'em', 'i', 'a', 'br', 'sup', 'sub', 'span', 'u'}


def soup(path):
    return BeautifulSoup(Path(path).read_text(encoding='utf-8'), 'lxml')


def page(url_path):
    """Soup for a site path such as '/about-us/', or None if not captured."""
    f = SOURCE / url_path.strip('/') / 'index.html'
    return soup(f) if f.exists() else None


def text(el):
    return re.sub(r'\s+', ' ', el.get_text(' ', strip=True)).strip() if el else ''


def local_path(href):
    """Strip the original origin so site links become root-relative."""
    if not href:
        return href
    href = href.strip()
    if href.startswith(ORIGIN):
        href = href[len(ORIGIN):] or '/'
    return href


def img_src(el):
    for attr in ('data-nectar-img-src', 'data-src', 'src'):
        v = el.get(attr)
        if v and not v.startswith('data:'):
            return local_path(v)
    m = re.search(r'background-image:\s*url\(([^)]+)\)', el.get('style', ''))
    return local_path(m.group(1).strip('\'"')) if m else None


def inline_html(el):
    """Inner HTML of el, keeping only simple inline formatting."""
    el = BeautifulSoup(str(el), 'lxml').find(el.name)
    for t in el.find_all(True):
        if t.name not in INLINE_TAGS:
            t.unwrap()
            continue
        keep = {'href': local_path(t['href'])} if t.name == 'a' and t.get('href') else {}
        t.attrs = keep
        if t.name == 'span':
            t.unwrap()
    html = ''.join(str(c) for c in el.contents)
    return re.sub(r'\s+', ' ', html).replace('&nbsp;', ' ').strip()


def rich_html(container):
    """Article body: headings, paragraphs, lists, images and quotes, cleaned."""
    out = []
    for el in container.find_all(['h2', 'h3', 'h4', 'h5', 'p', 'ul', 'ol', 'img', 'blockquote', 'table']):
        if el.find_parent(['ul', 'ol', 'blockquote', 'table']) and el.name not in ('img',):
            continue
        if el.name == 'img':
            src = img_src(el)
            if src:
                out.append({'type': 'img', 'src': src, 'alt': el.get('alt', '')})
        elif el.name in ('ul', 'ol'):
            items = [inline_html(li) for li in el.find_all('li', recursive=False)]
            if items:
                out.append({'type': el.name, 'items': items})
        elif el.name == 'table':
            rows = [[inline_html(c) for c in tr.find_all(['td', 'th'])] for tr in el.find_all('tr')]
            out.append({'type': 'table', 'rows': rows})
        else:
            h = inline_html(el)
            if text(el):
                out.append({'type': el.name, 'html': h})
    return out


# --------------------------------------------------------------------------
# Catalogue
# --------------------------------------------------------------------------

def category_tree():
    s = page('/products/')
    root = s.select_one('.widget_product_categories ul.product-categories')

    def walk(ul, parent):
        nodes = []
        for li in ul.find_all('li', recursive=False):
            a = li.find('a')
            path = local_path(a['href'])
            node = {
                'name': text(a),
                'path': path,
                'slug': path.rstrip('/').split('/')[-1],
                'parent': parent,
                'children': [],
            }
            sub = li.find('ul', recursive=False)
            if sub:
                node['children'] = walk(sub, path)
            nodes.append(node)
        return nodes

    return walk(root, None)


def menu_ranges():
    """Category 'Capacity: …' lines from the original mega menu, keyed by path."""
    s = page('/')
    out = {}
    for a in s.select('ul.sf-menu a[href^="/products/"]'):
        title = a.select_one('.menu-title-text')
        desc = a.select_one('.menu-item-desc')
        if desc:
            out[local_path(a['href'])] = text(desc)
        elif title and ':' in text(a):
            out[local_path(a['href'])] = text(a).split(text(title), 1)[-1].strip()
    return out


def menu_products():
    """The original Products mega menu, in order, split into its columns."""
    s = page('/')
    menu = s.select_one('ul.sf-menu')
    products_li = next(li for li in menu.find_all('li', recursive=False) if 'Products' in re.sub(r'\s+', '', text(li.find('a'))))
    columns = []
    for col in products_li.select(':scope > ul > li'):
        items = []
        for a in col.select('ul a[href^="/products/"]'):
            title = a.select_one('.menu-title-text')
            label = text(title) if title else text(a)
            rest = text(a)[len(label):].strip() if text(a).startswith(label) else ''
            items.append({'label': label, 'path': local_path(a['href']), 'range': rest})
        if items:
            columns.append(items)
    return columns


def category_extras(path):
    s = page(path)
    if not s:
        return {}
    faq = []
    acc = s.select_one('.woo-cat-faq #accordion')
    if acc:
        for h in acc.find_all('h5', recursive=False):
            ans = h.find_next_sibling('div')
            faq.append({'q': text(h), 'a': inline_html(ans) if ans else ''})
    title = s.title.string.strip() if s.title and s.title.string else ''
    desc = s.select_one('meta[name="description"]')
    return {'faq': faq, 'meta_title': title, 'meta_description': desc['content'] if desc else ''}


def listing_items(s):
    items = []
    for li in s.select('li.product'):
        a = li.select_one('a[href]')
        img = li.select_one('img')
        items.append({
            'name': text(li.select_one('h2')),
            'url': local_path(a['href']),
            'thumb': img_src(img) if img else None,
            'cat_slugs': [c[len('product_cat-'):] for c in li.get('class', []) if c.startswith('product_cat-')],
            'tag_slugs': [c[len('product_tag-'):] for c in li.get('class', []) if c.startswith('product_tag-')],
        })
    return items


def product(path):
    s = page(path)
    main = s.select_one('div.product.type-product')
    summary = s.select_one('.summary')
    gallery = []
    for g in s.select('.woocommerce-product-gallery__image'):
        a = g.find('a')
        img = g.find('img')
        full = local_path(a['href']) if a and a.get('href') else None
        gallery.append(full or img_src(img))
    gallery = list(dict.fromkeys(x for x in gallery if x))

    specs, notes = [], []
    sd = s.select_one('.woocommerce-product-details__short-description')
    if sd:
        for li in sd.find_all('li'):
            st = li.find('strong')
            if st:
                label = inline_html(st).rstrip().rstrip(':').strip()
                st.extract()
                specs.append({'label': label, 'value': inline_html(li)})
            elif text(li):
                specs.append({'label': '', 'value': inline_html(li)})
        for p in sd.find_all('p'):
            if text(p):
                notes.append(inline_html(p))

    hotspot = None
    hs = s.select_one('.nectar_image_with_hotspots')
    if hs and hs.find('img'):  # some originals have hotspots with no image; nothing to show
        points = []
        for w in hs.select('.nectar_hotspot_wrap'):
            st = w.get('style', '')
            top = re.search(r'top:\s*([\d.]+)%', st)
            left = re.search(r'left:\s*([\d.]+)%', st)
            tip = w.select_one('.nttip')
            title = text(tip.find(['h5', 'h4', 'h3'])) if tip and tip.find(['h5', 'h4', 'h3']) else text(tip)
            body = ' '.join(text(p) for p in tip.find_all('p')) if tip else ''
            points.append({'top': float(top.group(1)), 'left': float(left.group(1)), 'title': title, 'text': body})
        hotspot = {'image': img_src(hs.find('img')), 'points': points}

    crumbs = [local_path(a['href']) for a in s.select('nav.woocommerce-breadcrumb a[href]')]
    primary = next((c for c in reversed(crumbs) if c.startswith('/products/')), None)
    brochure = s.select_one('a.download_btn')
    return {
        'name': text(summary.select_one('h1.product_title')),
        'url': path,
        'local': True,
        'images': gallery,
        'thumb': gallery[0] if gallery else None,
        'specs': specs,
        'notes': notes,
        'hotspot': hotspot,
        'brochure': brochure['href'] if brochure and brochure.get('href') else None,
        'primary_cat': primary,
        'cat_slugs': [c[len('product_cat-'):] for c in main.get('class', []) if c.startswith('product_cat-')],
        'tags': [{'name': text(a), 'path': local_path(a['href'])} for a in s.select('.tagged_as a')],
        'related': list(dict.fromkeys(local_path(a['href']) for a in s.select('section.related li.product a[href]'))),
    }


def catalogue():
    tree = category_tree()
    flat = {}

    def index(nodes):
        for n in nodes:
            flat[n['path']] = n
            index(n['children'])

    index(tree)
    by_slug = {n['slug']: n for n in flat.values()}

    products = {}
    for f in sorted(SOURCE.glob('product/**/index.html')):
        path = '/' + str(f.parent.relative_to(SOURCE)) + '/'
        products[path] = product(path)

    # Listing pages reveal products whose detail pages were never captured,
    # plus tag membership for all of them.
    tag_members = {}
    for f in sorted(list(SOURCE.glob('products/**/index.html')) + list(SOURCE.glob('product-tag/**/index.html'))):
        s = soup(f)
        rel = '/' + str(f.parent.relative_to(SOURCE)) + '/'
        for item in listing_items(s):
            p = products.get(item['url'])
            if p is None:
                products[item['url']] = p = dict(item, local=False, images=[item['thumb']] if item['thumb'] else [],
                                                specs=[], notes=[], hotspot=None, brochure=None,
                                                primary_cat=None, tags=[], related=[])
            p['cat_slugs'] = sorted(set(p['cat_slugs']) | set(item['cat_slugs']))
            if rel.startswith('/product-tag/'):
                tag_members.setdefault(rel, []).append(item['url'])
            if not p.get('list_thumb') and item['thumb']:
                p['list_thumb'] = item['thumb']

    # Resolve every product to category paths including ancestors.
    for p in products.values():
        paths = set()
        for slug in p['cat_slugs']:
            n = by_slug.get(slug)
            while n:
                paths.add(n['path'])
                n = flat.get(n['parent'])
        p['cats'] = sorted(paths)
        if not p.get('primary_cat') or p['primary_cat'] not in flat:
            deepest = sorted(paths, key=lambda x: x.count('/'))
            p['primary_cat'] = deepest[-1] if deepest else None
        p['primary_cat_name'] = flat[p['primary_cat']]['name'] if p['primary_cat'] in flat else ''

    tags = {}
    for p in products.values():
        for t in p.get('tags', []):
            tags.setdefault(t['path'], {'name': t['name'], 'path': t['path'], 'members': set()})['members'].add(p['url'])
    for path, members in tag_members.items():
        s = page(path)
        name = text(s.select_one('h1')) if s and s.select_one('h1') else path.rstrip('/').split('/')[-1].replace('-', ' ').title()
        tags.setdefault(path, {'name': name, 'path': path, 'members': set()})['members'].update(members)
    for t in tags.values():
        t['members'] = sorted(t['members'])

    ranges = menu_ranges()
    for path, n in flat.items():
        n['range'] = ranges.get(path, '')
        n.update(category_extras(path))

    # The original menu links Preparation Table under Under Counter as well.
    aliases = {}
    for f in SOURCE.glob('products/**/index.html'):
        path = '/' + str(f.parent.relative_to(SOURCE)) + '/'
        slug = path.rstrip('/').split('/')[-1]
        if path not in flat and path != '/products/' and slug in by_slug:
            aliases[path] = by_slug[slug]['path']

    return {'tree': tree, 'categories': flat, 'products': products, 'tags': tags, 'aliases': aliases}


# --------------------------------------------------------------------------
# Generic content sections (About, Factories, Sustainability …)
# --------------------------------------------------------------------------

def top_rows(s):
    mc = s.select_one('.main-content')
    return [r for r in mc.select('.wpb_row') if not r.find_parent(class_='wpb_row')]


def row_blocks(row):
    """Flatten a page-builder row into an ordered list of simple blocks."""
    out = []
    seen_imgs = set()
    for e in row.descendants:
        if not isinstance(e, Tag):
            continue
        if e.find_parent(['form', 'select', 'script', 'style', 'noscript']):
            continue
        if e.name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            btn = e.find_parent('a') or e.find('a')
            if e.find_parent(class_=re.compile(r'nectar-cta|nectar-button')) or (btn and btn.get('href') and e.name in ('h5', 'h6')):
                continue
            if text(e):
                out.append({'type': 'h', 'level': int(e.name[1]), 'text': text(e)})
        elif e.name == 'p' and not e.find_parent(['li', 'a']) and text(e):
            if e.find_parent(class_=re.compile(r'nectar-cta')):
                continue
            out.append({'type': 'p', 'html': inline_html(e)})
        elif e.name in ('ul', 'ol') and not e.find_parent(['ul', 'ol']):
            items = [inline_html(li) for li in e.find_all('li', recursive=False) if text(li)]
            if items:
                out.append({'type': 'list', 'items': items})
        elif e.name == 'img' or (e.name == 'div' and (e.get('data-nectar-img-src') or 'background-image' in e.get('style', ''))):
            src = img_src(e)
            if src and src not in seen_imgs and not src.startswith('/external/'):
                seen_imgs.add(src)
                out.append({'type': 'img', 'src': src, 'alt': e.get('alt', '') if e.name == 'img' else ''})
        elif e.name == 'a' and e.get('href') and text(e):
            cls = ' '.join(e.get('class', []))
            if 'nectar-button' in cls or e.find_parent(class_=re.compile(r'nectar-cta|nectar-button')):
                out.append({'type': 'button', 'text': text(e), 'href': local_path(e['href'])})
        elif e.name == 'a' and e.get('href', '').startswith(('https://www.youtube.com', 'https://youtu.be')):
            out.append({'type': 'button', 'text': text(e) or 'Watch video', 'href': e['href']})
    # Collapse duplicate buttons produced by nested CTA markup.
    clean = []
    for b in out:
        if b['type'] == 'button' and clean and clean[-1].get('href') == b['href'] and clean[-1]['type'] == 'button':
            continue
        clean.append(b)
    return clean


def to_sections(blocks):
    """Group blocks into sections led by an h1/h2 title (h3 before it is the eyebrow)."""
    sections = []
    cur = None
    pending = []
    i = 0
    while i < len(blocks):
        b = blocks[i]
        if b['type'] == 'h' and b['level'] in (1, 2):
            eyebrow = ''
            if pending and pending[-1]['type'] == 'h' and pending[-1]['level'] >= 3:
                eyebrow = pending.pop()['text']
            cur = {'eyebrow': eyebrow, 'title': b['text'], 'blocks': pending}
            pending = []
            sections.append(cur)
        elif cur is None:
            pending.append(b)
        else:
            cur['blocks'].append(b)
        i += 1
    if pending:
        if sections:
            sections[-1]['blocks'].extend(pending)
        else:
            sections.append({'eyebrow': '', 'title': '', 'blocks': pending})
    return sections


def cards_from(blocks):
    """Split blocks into (body, cards). A card starts at an h4/h3 (optionally preceded by an image)."""
    body, cards = [], []
    card = None
    pending_img = None
    for b in blocks:
        if b['type'] == 'h' and b['level'] >= 3:
            if card and card['level'] < b['level'] and not card['html'] and not card['buttons']:
                # "Recommended products" (h3) followed by "Visi Cooler" (h4) is one card.
                card.update(eyebrow=card['title'], title=b['text'], level=b['level'])
                continue
            card = {'title': b['text'], 'eyebrow': '', 'img': pending_img, 'html': [], 'buttons': [], 'level': b['level']}
            pending_img = None
            cards.append(card)
        elif b['type'] == 'img' and (cards or any(x['type'] == 'h' and x['level'] >= 3 for x in blocks[blocks.index(b):])):
            if card and not card['img'] and not card['html'] and not card['buttons']:
                card['img'] = b
            else:
                pending_img = b
                card = None
        elif card is not None and b['type'] == 'p':
            card['html'].append(b['html'])
        elif card is not None and b['type'] == 'button':
            card['buttons'].append(b)
        else:
            body.append(b)
    if pending_img:
        body.append(pending_img)
    return body, cards


def content_page(path):
    s = page(path)
    sections = []
    for r in top_rows(s):
        # Section per row: leading blocks in a row belong to that row's first title.
        rid = r.get('id') or ''
        secs = to_sections(row_blocks(r))
        for i, sec in enumerate(secs):
            sec['anchor'] = rid if i == 0 and not rid.startswith('fws_') else ''
        sections.extend(secs)
    title_el = s.select_one('meta[property="og:title"]')
    desc = s.select_one('meta[name="description"]')
    return {
        'path': path,
        'sections': sections,
        'meta_title': s.title.string.strip() if s.title and s.title.string else '',
        'meta_description': desc['content'] if desc else '',
        'og_title': title_el['content'] if title_el else '',
    }


def row_anchor_sections(path):
    """Sections where each top-level row keeps its id (used for in-page anchors)."""
    s = page(path)
    out = []
    for r in top_rows(s):
        rid = r.get('id') or ''
        secs = to_sections(row_blocks(r))
        for sec in secs:
            sec['anchor'] = '' if rid.startswith('fws_') else rid
        out.extend(secs)
    return out


# --------------------------------------------------------------------------
# Home, timeline, blog, contact
# --------------------------------------------------------------------------

def home():
    s = page('/')
    sliders = []
    for sl in s.select('.nectar-slider-wrap'):
        row = sl.find_parent(class_='wpb_row')
        kind = 'mobile' if 'mobile-banner' in row.get('class', []) else 'desktop'
        slides = []
        for x in sl.select('.swiper-slide'):
            bg = re.search(r'url\(([^)]+)\)', x.select_one('.image-bg')['style']).group(1)
            a = x.select_one('a.entire-slide-link')
            slides.append({'img': local_path(bg), 'href': local_path(a['href']) if a else None})
        sliders.append((kind, slides))
    desktop = next(v for k, v in sliders if k == 'desktop')
    mobile = next(v for k, v in sliders if k == 'mobile')
    by_href = {m['href']: m for m in mobile if m['href']}
    used = set()
    banners = []
    for d in desktop:
        m = by_href.get(d['href'])
        if m:
            used.add(m['img'])
        banners.append({'img': d['img'], 'mobile': m['img'] if m else None, 'href': d['href']})
    leftovers = [m for m in mobile if m['img'] not in used]
    for b in banners:
        if not b['mobile'] and leftovers:
            m = leftovers.pop(0)
            b['mobile'] = m['img']
            b['href'] = b['href'] or m['href']

    range_cards = []
    for box in s.select('.nectar-fancy-box'):
        a = box.select_one('a.box-link')
        bg = box.select_one('.box-bg')
        if a and bg and local_path(a['href']).startswith('/products/'):
            range_cards.append({'path': local_path(a['href']), 'img': img_src(bg)})

    rows = top_rows(s)
    blocks = [b for r in rows for b in row_blocks(r)]
    secs = to_sections(blocks)

    def sec(title_start):
        return next(x for x in secs if x['title'].startswith(title_start))

    logos = [b['src'] for b in sec('"Trusted by the Best"')['blocks'] if b['type'] == 'img']

    industries = []
    impact = next(r for r in rows if r.get('id') == 'impact')
    for b in to_sections(row_blocks(impact)):
        imgs = [x for x in b['blocks'] if x['type'] == 'img']
        ps = [x for x in b['blocks'] if x['type'] == 'p']
        industries.append({'title': b['title'], 'text': ps[0]['html'] if ps else '', 'img': imgs[0]['src'] if imgs else None})
    # Images sit in separate columns from their text; their DOM order matches the card order.
    imgs = list(dict.fromkeys(re.findall(r'/wp-content/uploads/[^)"\s]+\.(?:jpe?g|png|webp)', str(impact))))
    if len(imgs) == len(industries):
        for ind, src in zip(industries, imgs):
            ind['img'] = src

    sus = []
    srow = next(r for r in rows if 'E-Waste' in text(r) and 'CSR Policy' in text(r))
    for b in row_blocks(srow):
        if b['type'] == 'img':
            sus.append({'icon': b['src'], 'title': '', 'text': '', 'href': ''})
        elif b['type'] == 'h' and sus:
            if not sus[-1]['title']:
                sus[-1]['title'] = b['text']
            else:
                sus[-1]['text'] = b['text']
        elif b['type'] == 'button' and sus:
            sus[-1]['href'] = b['href'].replace('/sustainability#', '/sustainability/#')

    def first_p(t):
        return next(x['html'] for x in sec(t)['blocks'] if x['type'] == 'p')

    def first_img(t):
        # Images often precede their heading in the markup, so look across the whole row.
        row = next(r for r in rows if any(b['type'] == 'h' and b['text'].startswith(t.split()[0]) and t in text(r) for b in row_blocks(r)))
        return next((b['src'] for b in row_blocks(row) if b['type'] == 'img'), None)

    hero_img = next((b['src'] for b in blocks if b['type'] == 'img' and 'Western-Refrigeration-Products' in b['src']), None)
    return {
        'banners': banners,
        'range_cards': range_cards,
        'intro': {'eyebrow': 'Leading the', 'title': 'Future of Cooling Solutions', 'html': first_p('Future of Cooling'), 'img': hero_img},
        'rnd': {'html': first_p('Development'), 'img': first_img('Development')},
        'facilities': {'html': first_p('Art Facilities'), 'img': first_img('Art Facilities')},
        'industry_intro': next(x['html'] for x in blocks if x['type'] == 'p' and x['html'].startswith('Western takes pride')),
        'industries': industries,
        'logos': logos,
        'global': {'html': first_p('Local Excellence'), 'img': first_img('Local Excellence')},
        'sustainability': sus,
        'meta_title': s.title.string.strip(),
        'meta_description': (s.select_one('meta[name="description"]') or {}).get('content', ''),
    }


def timeline():
    s = page('/about-us/')
    out = []
    for st in s.select('.ctl-story'):
        out.append({'year': text(st.select_one('.story-date')), 'title': text(st.select_one('.ctl-title'))})
    return out


def blog():
    s = page('/blog/')
    posts = []
    for art in s.select('article.post'):
        a = art.select_one('h3 a[href], .post-header a[href], a.entire-meta-link[href]')
        img = art.select_one('img')
        cat = art.select_one('.meta-category a')
        url = local_path(a['href'])
        p = page(url)
        if not p:
            continue
        body = p.select_one('.post-content .content-inner') or p.select_one('.post-content')
        pub = p.select_one('meta[property="article:published_time"]')
        desc = p.select_one('meta[name="description"]')
        posts.append({
            'title': text(p.select_one('h1.entry-title') or p.select_one('h1')) or text(art.select_one('h3')),
            'url': url,
            'img': img_src(img) if img else None,
            'category': text(cat) if cat else '',
            'date': pub['content'][:10] if pub else '',
            'body': rich_html(body),
            'meta_description': desc['content'] if desc else '',
        })
    return posts


def contact():
    s = page('/contact-us/')
    offices = []
    for h in s.find_all('h1'):
        t = text(h)
        if 'Office' in t:
            p = h.find_next('p')
            offices.append({'title': t, 'html': inline_html(p)})
    maps = list(dict.fromkeys(re.findall(r'https://www\.google\.com/maps/embed\?pb=[^"\'<> ]+', str(s))))
    sel = s.select_one('form.contact_form select[name="visitor_department"]')
    departments = [text(o) for o in sel.find_all('option')][1:] if sel else ['Sales', 'Services']
    interests = []
    for cb in s.select('form.contact_form input[name="woocats[]"]'):
        lab = cb.find_parent('label') or cb.find_next('label')
        if lab and text(lab):
            interests.append(text(lab))
    return {'offices': offices, 'maps': maps, 'departments': departments, 'interests': interests}


def simple_images(path):
    s = page(path)
    return [img_src(i) for i in s.select('.main-content img') if img_src(i) and not img_src(i).startswith('/external/')]
