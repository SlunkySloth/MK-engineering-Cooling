"""MK Engineering's own copy: home hero, About and Service pages, and rewording of
captured Western text that described Western as the company.

Keep claims factual: MK Engineering supplies, installs and services equipment
from the brands it deals in. Don't add years, numbers or certifications that
the owner hasn't confirmed.
"""
import re

COMPANY = 'MK Engineering'
PRODUCTS_IMG = '/wp-content/uploads/2026/10/Western-Refrigeration-Products.jpg'

HOME = {
    'eyebrow': 'MK Engineering · Madurai & Trichy',
    'title_html': 'Cooling equipment, <span>supplied</span> and serviced',
    'lead': 'MK Engineering helps businesses across Tamil Nadu choose, install and look after commercial '
            'refrigeration and cooling equipment from <strong>Western, Symphony and Elanpro</strong>, '
            'with local support from our offices in Madurai and Trichy.',
    'meta_title': 'MK Engineering | Commercial refrigeration and cooling in Madurai & Trichy',
    'meta_description': 'MK Engineering supplies, installs and services commercial refrigeration, freezers, '
                        'air coolers and cold-chain equipment from Western, Symphony and Elanpro across Tamil Nadu.',
}


def p(html):
    return {'type': 'p', 'html': html}


def card(title, text, eyebrow='', img=None, buttons=()):
    return {'title': title, 'eyebrow': eyebrow, 'img': {'src': img, 'alt': title} if img else None,
            'html': [text] if text else [], 'buttons': list(buttons)}


def section(title, eyebrow='', text=(), images=(), buttons=(), cards=(), numbered=False, anchor=''):
    images = [{'src': s, 'alt': title} for s in images]
    return {'title': title, 'eyebrow': eyebrow, 'anchor': anchor, 'text': list(text), 'images': images,
            'buttons': list(buttons), 'cards': list(cards), 'numbered': numbered, 'soft': bool(cards),
            'layout': 'split' if images and len(images) <= 2 and text else 'stack'}


def pages(site, brands):
    """About and Service pages. `brands` is the brand menu (name, href, count, logo)."""
    offices = [card(l['name'], l['address'], eyebrow='Office', buttons=[{'text': 'Get directions', 'href': l['maps_url']}])
               for l in site['locations']]
    brand_cards = [card(b['name'], f"{b['text']}: {b['count']} models in our catalogue.", img=b['logo'],
                        buttons=[{'text': f"Browse {b['name']}", 'href': b['href']}]) for b in brands]
    for c in brand_cards:
        c['cover'] = False
    clients = ', '.join(c['name'] for c in site.get('clients', []))
    about = {
        'title': 'About us',
        'lead': f'{COMPANY} supplies, installs and services commercial refrigeration and cooling equipment '
                'for businesses across Tamil Nadu, from our offices in Madurai and Trichy.',
        'sections': [
            section('Cooling equipment, and the people behind it', 'Who we are', images=[PRODUCTS_IMG], text=[
                p('Shops, restaurants, hotels, bakeries, dairies, hospitals and factories all depend on equipment that '
                  'keeps things cold. We help them pick the right model for their space and daily use, deliver and '
                  'install it, and keep it running afterwards.'),
                p('We deal in trusted brands, so you can compare options in one place and get honest advice on what '
                  'fits your requirement and budget.'),
            ], buttons=[{'text': 'Browse products', 'href': '/products/'}, {'text': 'Contact us', 'href': '/contact-us/'}]),
            section('What we do', 'Our services', numbered=True, cards=[
                card('Advice', 'Tell us what you need to store, display or serve. We suggest the models that fit.'),
                card('Supply', 'Equipment from Western, Symphony, Elanpro and the other brands we deal with.'),
                card('Installation', 'Delivery and installation at your site, so the equipment works as it should from day one.'),
                card('Service', 'Support and service after installation. Call either office when you need us.'),
            ]),
            section('Brands we deal with', 'Our catalogue', cards=brand_cards),
            *([section('Businesses we work with', 'Our clients', text=[p(f'Our clients include {clients}.')])] if clients else []),
            section('Visit or call us', 'Our offices', cards=offices),
        ],
    }
    service = {
        'title': 'Installation & service',
        'lead': 'Buying cooling equipment is only the start. We install it properly and support you afterwards, '
                'across Tamil Nadu from Madurai and Trichy.',
        'sections': [
            section('How we work', 'From enquiry to running equipment', numbered=True, cards=[
                card('Understand your requirement', 'Space, capacity, daily use and budget. We help you narrow down the options.'),
                card('Clear quote', 'Model, availability, delivery and installation for your location.'),
                card('Delivery and installation', 'We deliver and install the equipment at your site.'),
                card('After-sales service', 'Contact us for service and support with your installation.'),
            ]),
            section('Need service?', 'Support', text=[
                p('Call either office or send an enquiry with your equipment model and location, and our team will get back to you.'),
            ], buttons=[{'text': 'Contact us', 'href': '/contact-us/'}]),
            section('Our offices', 'Madurai & Trichy', cards=offices),
        ],
    }
    return {'/about-us/': about, '/service/': service}


# Captured Western text that speaks as the company -> MK Engineering wording.
REWRITES = [
    (r'Western takes pride in its role as an innovative partner', f'{COMPANY} takes pride in being a reliable partner'),
    (r'At Western, we pride ourselves', f'At {COMPANY}, we pride ourselves'),
    (r'with Western\.', f'with {COMPANY}.'),
    (r'Western offers', 'We supply'),
]


def rewrite(s):
    for pat, rep in REWRITES:
        s = re.sub(pat, rep, s)
    return s
