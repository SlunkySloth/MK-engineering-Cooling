# MK-engineering-Cooling

Website of MK Engineering, live at https://www.mkengg.in. Static site for a commercial refrigeration catalogue (Western Equipments, Symphony and Elanpro). The content (products, specifications, images, company pages, blog) comes from a capture of https://westernequipments.com/ kept in `source/`. A build script turns it into a fast, lightweight site in `dist/`.

## Preview

```
python src/build.py                                # regenerate dist/
python -m http.server 8080 --directory dist        # open http://localhost:8080
python validate.py                                 # check for broken links and missing assets
```

The first build converts every image to WebP (about 3 minutes). Later builds reuse them and take about 25 seconds.

## Layout

| Path | What it is |
| --- | --- |
| `src/site.json` | Company name, logo, phone numbers, email, address, social links, headline stats and menus. Change these to rebrand. |
| `src/extract.py` | Reads the captured pages in `source/` and returns products, categories, page sections, blog posts. |
| `src/templates/` | Jinja2 page templates (home, catalogue, product, content pages, contact, blog, compare). |
| `src/assets/` | The site's only stylesheet and script, plus the self-hosted Manrope font. |
| `src/build.py` | Runs extraction, renders every page, writes the search index and compare data, and converts images. |
| `source/` | The original captured site. Read-only input; not served. |
| `dist/` | Generated output. This is what gets hosted. |

## Features

- Instant search across all 192 models, categories, pages and articles (`/` or Ctrl+K).
- Catalogue with category tree, sub-category chips, text filter and sort. Filters are kept in the URL, so filtered views can be shared.
- Product pages with image gallery and zoom, highlighted key specs, full spec table, feature diagrams, brochure download and related products.
- Compare up to four models side by side; differing values are highlighted.
- Enquiry and contact forms. With no server, they open the visitor's email app with the details filled in, addressed to the email in `site.json`.
- Responsive images (WebP, sized per layout), lazy loading, one CSS file, one small JS file, no third-party requests except the Google Maps embed on the contact page.

## Limits

- 52 of the 192 products were only captured as listing entries (name and thumbnail). Their cards link to the original site.
- Brochure PDFs link to the original site. Copies are kept in `reference-documents/`.
- The e-waste collection-point locator and the careers application form needed the original server and are not included.

`mirror.py` captures public pages and assets into `source/` (`.capture/` is its download cache). Source content and brand assets belong to their respective owners.

For a full guide to the project (architecture, brands, deployment, known issues), see `AGENTS.md` and the `docs/` folder.
