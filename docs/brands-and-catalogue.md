# Brands and catalogue

## Western Equipments (Western Refrigeration)

- **Source:** a full capture of https://westernequipments.com in `source/`, made with `mirror.py` and repaired by `finalize.py` and `repair-assets.py`. These are one-off tools, not part of the build.
- **Extraction:** `src/extract.py` parses the captured WordPress/WooCommerce pages with BeautifulSoup.
- **Products:** 192 in total.
  - 140 have captured detail pages (`local: True`).
  - 52 were only captured as listing entries. Their cards link to the original site and show "Details on original site".
- **URLs:** Categories live under `/products/...` (52, nested) and product pages under `/product/...`. One alias exists: `/products/stainless-steel/under-counter-product/preparation-table/` points to the static-cooling path.
- **Pages:**
  - The About, Factories, R&D, Sustainability, Careers, Industries and Service pages, plus the blog (5 posts), still contain Western's own company content.
  - The Company, Service and Blog nav links are hidden in `base.html`, but the pages are still generated and linked from elsewhere.
- **FAQs:** category FAQs were removed on request. The data still exists in the capture, but the template no longer renders it.

## Symphony

- **Fetch:** `fetch-symphony.py` reads the public Shopify feed at `shop.symphonylimited.com/products.json` and saves:
  - `source/symphony/products.json`, the raw records (water heaters skipped)
  - up to 8 photos per product as WebP (1400px) in `source/symphony/img/`
- **Module:** `src/symphony.py`. Constants: `NAME`, `ROOT_PATH='/symphony/'`, `MENU_TEXT`, `TITLE`, `META`.
- **Ranges:** decided by `category_of()` from `product_type` and the title:
  - Desert Coolers, Tower Coolers, Personal Coolers, Commercial & Industrial, Tower Fans
  - "commercial" or "industrial" in the title wins over the product type
- **Specs:** tank capacity, room size, air throw, power, colour and model code, found with regexes over the title, description and tags. Features are the description's `<li>` items; comparison tables are skipped.
- **Prices:** captured (`variants[].price`, `compare_at_price`) but **not published**. Do not add them back unless the owner asks.

## Elanpro

- **Fetch:** `fetch-elanpro.py` reads the public WooCommerce Store API (`elanpro.net/wp-json/wc/store/v1/products` and `/products/categories`) and saves:
  - `source/elanpro/products.json` and `categories.json`
  - up to 6 photos per product in `source/elanpro/img/`
- **Fetch etiquette:** the script fetches politely, with 3 threads and pauses. Elanpro's robots.txt restricts AI collection; MK Engineering is an authorised Elanpro dealer and chose to proceed. Keep refreshes infrequent and polite.
- **Module:** `src/elanpro.py`.
- **Ranges:** the 14 top-level WooCommerce categories. Each product's deepest category becomes `sub`, which feeds the sub-category chips on its range page.
- **Menu:** columns are set by `GROUPS`: Retail & display, Kitchen & bar, Specialty.
- **Specs:** the rows of the description's spec table. Features are the short description's `<p>`/`<li>` text.
- **Placeholder photos:** 34 products only have Elanpro's "IMAGE coming soon" artwork (`comingSoon.png`).
  - They are flagged `no_photo` and sorted last.
  - They are never used as range thumbnails.
  - Replace them if the dealer gets real photos.
- **Prices:** Elanpro lists none (all 0). Nothing to hide.
- **Logo:** Elanpro's site only has a white logo. It was recoloured to Elanpro blue `#005FAF` and saved as `source/wp-content/uploads/mk/brands/elanpro.png`.

## Adding another dealer brand

1. **Write `fetch-<brand>.py`.** It should save the raw data plus WebP photos into `source/<brand>/`. Prefer an official JSON feed (Shopify `products.json` or WooCommerce Store API) over HTML scraping, and keep the request rate low.
2. **Write `src/<brand>.py`** with:
   - the constants `NAME`, `ROOT_PATH`, `MENU_TEXT`, `TITLE` and `META`
   - a `catalogue()` function that returns `{'products': {...}, 'categories': {...}, 'groups': [(title, [paths])]}`
   - Products follow the shape in `docs/architecture.md`. Categories need `slug`, `name`, `path`, `count`, `thumb`, and optionally `blurb` and `subs`. The two existing modules are the templates to copy.
3. **Register it:** add the module to the tuple in `Site.load()` (`for mod in (symphony, elanpro)`), in the order it should appear in the menu.
4. **Add the logo:** put it in `source/wp-content/uploads/mk/brands/` and add `{"name": NAME, "img": ...}` to `site.json` → `brands`. The name must match `NAME`.
5. **Build, validate and check** the menu, the brand page, a range page and a product page.

## Search and compare

`search-index.json` entries look like `{t: title, u: url, k: kind, c: context, i: thumb, s: spec text}`. Their kinds are Product, Category, Page and Article.

Dealer-brand products are prefixed with the brand name, e.g. "Symphony Diet 3D 55i+". `products.json` (compare) holds every product that has a detail page.
