# Architecture

## Build pipeline

`python src/build.py` runs `Site().build()`:

1. **Load** (`Site.load`)
   - `extract.catalogue()` reads the Western capture: products, the category tree (52), tags and one alias URL.
   - `extract.home()`, `timeline()`, `blog()`, `contact()`, `menu_products()` and `content_page()` read the other Western pages.
   - `self.brands` holds the dealer brands, in menu order: `[symphony.catalogue(), elanpro.catalogue()]`, each with `mod` set to its module. A brand with no captured data is skipped.
   - `self.generated` is the set of every URL that will be written, so `link()` can tell internal links from links to elsewhere.
2. **Clean** `dist/`. Everything except `dist/img/` is deleted, so WebP conversions are reused.
3. **Render** with Jinja2 (`Site.env` sets the filters and globals):
   - home, `/products/`, Western category and tag pages, Western product pages
   - `Site.render_brand()` for each dealer brand: the brand page, range pages and product pages
   - content pages (`PAGE_TITLES`), contact, blog, compare, 404
4. **Data files**:
   - `dist/search-index.json`, used by the search palette
   - `dist/products.json`, used by the compare page; only products with a detail page
5. **Assets**: copy `src/assets/` to `dist/assets/` (URLs carry an md5 `?v=` cache-buster) and copy the favicons.
6. **Images**: `Images.render()` converts every requested size to WebP in parallel and prunes unused files.

`python src/build.py --dump` also writes `build-data.json` (gitignored) with the extracted data, for debugging.

## Links

`Site.link(href)` normalises a path:
- It adds a trailing slash and applies aliases.
- If the target is in `self.generated`, it returns the local path.
- **Anything not generated is pointed at the original Western site** (`ORIGIN` in `extract.py`). That is how listing-only Western products and brochure PDFs still work.

Templates use the `|link`, `|links` (rewrites `href`s inside HTML) and `|is_external` filters.

## Product shape

Every product is a dict like the one below. Dealer brands produce it in `symphony.py` and `elanpro.py`, and Western products come from `extract.py`.

```python
{
  'url': '/elanpro/product/edc-902-f3/', 'name': 'EDC 902 F3', 'local': True,
  'brand': 'Elanpro',                      # absent for Western
  'images': ['/elanpro/img/...webp', ...], 'thumb': '/elanpro/img/...webp',
  'specs': [{'label': 'Capacity', 'value': '120 L'}, ...],   # already HTML-escaped
  'key_specs': [...2 specs for cards...], 'features': ['...'], 'notes': [],
  'cats': ['/elanpro/', '/elanpro/retail/'], 'cat_slugs': ['retail', 'upright-showcase-chiller'],
  'primary_cat': '/elanpro/retail/', 'primary_cat_name': 'Retail', 'sub': 'Upright Showcase Chiller',
  'hotspot': None, 'brochure': None, 'tags': [], 'related': [],
}
```

`Site.card(p)` turns a product into the smaller dict that `product_card()` in `macros.html` renders. `cat_slugs` drive the filter chips: a card is shown when the selected chip's slug is in its `data-cats`.

## Templates (`src/templates/`)

| Template | Used for |
|---|---|
| `base.html` | Shell: SVG icon sprite, top bar, header with the **brand mega menu** (`brand_menu` global), mobile drawer, footer, search, enquiry and compare dialogs. The Company, Service and Blog nav items are commented out ("Hidden for now"). |
| `macros.html` | `icon`, `img` (responsive `<img>` from `Images.get`), `crumbs`, `page_head`, `product_card`, `buttons`, `text_blocks`, `section`, `cta` |
| `catalog.html` | Every listing: optional range tiles (`tiles`, otherwise `range_cards`), sidebar tree (`tree`, `tree_root`), chips, toolbar, product grid |
| `product.html` | Product detail: gallery and lightbox, highlights, actions, key features, spec table, hotspots, related products |
| `home.html`, `content.html`, `contact.html`, `blog.html`, `post.html`, `compare.html`, `404.html` | The rest |

## Mega menu data

`brand_menu` is a list built in `Site.env()`:

```python
{'name': 'Symphony', 'logo': '/wp-content/uploads/mk/brands/symphony.png', 'href': '/symphony/',
 'count': 65, 'text': 'Air coolers & tower fans',
 'columns': [{'title': 'Air coolers', 'items': [{'label', 'path', 'thumb', 'range'}, ...]}, ...]}
```

- Western comes first and uses `menu_columns`, built from the captured Western menu and grouped into 'Display & freezing', 'Kitchen & bar' and 'Specialty & retail'.
- The other brands use their module's `groups`.
- Logos come from `site.json` → `brands`, matched by name. Western's entry is named `Western`.

In the menu markup, every brand panel sits in the same grid cell, and hidden panels use `visibility: hidden`, so the menu keeps the height of the tallest brand. `site.js` switches the panel on brand `mouseenter` or `focus`.

## Front-end (`src/assets/site.js`)

All features are progressive enhancements:
- **Header and drawer:** header shadow on scroll, mobile drawer, Escape closes menus.
- **Mega menu:** brand switching.
- **Search palette:** opened with `/` or Ctrl+K; searches `search-index.json`.
- **Catalogue filters:** a text filter, chips and sort, kept in the URL (`?cat=&q=`). The chips live in the page header, *outside* `[data-catalog]`, so they are queried document-wide.
- **Compare:** up to 4 products, stored in `localStorage`, using `products.json`, with a tray at the bottom of the screen.
- **Enquiry forms:** `mailto:` forms addressed to the emails in `site.json`, because there is no backend.
- **Galleries and widgets:** carousel, gallery and lightbox, hotspots, share button.

## CSS notes

- Design tokens are defined in `:root`.
- Components that set their own `display` would otherwise ignore the `hidden` attribute, so they need explicit rules: `.product-card[hidden], .thumbs[hidden], .empty[hidden] { display: none; }`. Add a selector there if you make another component hideable.
- Breakpoints: 1100px (desktop nav replaced by the drawer), 900px and 640px.
