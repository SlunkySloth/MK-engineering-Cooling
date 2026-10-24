# History, known issues and gotchas

## How the project got here

1. **Capture:** westernequipments.com was captured into the repo. Tag `original-replica` (commit `98bd6a9`) is that untouched copy.
2. **Redesign** (commits `36a4846`, `5c40b38`): the WordPress pages were replaced by this static generator.
   - Fast WebP images, one CSS file and one JS file. Output went from 234 MB to 68 MB at the time.
   - Added instant search, catalogue filters, compare, enquiry forms and the mega menu.
3. **MK branding** (by the owner, plus `9156dbc`):
   - MK logo and icon (the original ribbon "MK Engineering" design, not the "v2" oval).
   - Phones, emails, Madurai and Trichy addresses with Google Maps links.
   - "Brands we deal with" and clients strips.
   - Company nav hidden, footer Company column removed.
4. **Dealer brands** (`9156dbc`):
   - Symphony and Elanpro catalogues, with prices removed on request.
   - The Products menu became brand-based: Western Equipments → Symphony → Elanpro.
   - Category FAQs removed.
5. **Launch:** PR #1 merged `redesign` into `main` (`c9058a0`), then `vercel.json` was added (`f85a219`). `mkengg.in` went live on Vercel.

`brand/logo-options/` holds the logo concepts made along the way (A–J, symbolic S1–S4). None of them is used yet.

## Known issues / to-do

- **MK identity is done; product content stays Western's.**
  - `site.json` → `name` is `MK Engineering`, so every title ends in "| MK Engineering".
  - MK's own copy lives in `src/mk_content.py`: home hero, About, Service, and the `REWRITES` that reword captured "Western offers…" text.
  - Western's corporate pages and blog are no longer published (`REMOVED_PATHS` in `build.py`; any link to them goes to `/about-us/`).
  - Product and category text still names Western as the *product brand*, which is correct.
- **Industries page:** still Western's captured content, reworded via `mk_content.REWRITES`. Check new sentences there if the capture changes.
- **Analytics, email and sitemap:** not set up; see `docs/deployment.md`.
- **Western listing-only products:** 52 products and the brochure PDFs link to westernequipments.com.

## Gotchas (learned the hard way)

- **`dist/` is rebuilt from scratch on every build** (except `dist/img/`). Anything hand-placed in `dist/` disappears, as the logo preview page once did. Generate everything from `src/`.
- **Every page shares `base.html`.** Changing the header, menu or footer changes all 500+ pages, so check several page types.
- **Hidden elements** need explicit `[hidden] { display: none }` rules when the component sets `display` (see `docs/architecture.md`). Without them, the catalogue filters counted results but never hid cards. That has been fixed.
- **Filter chips sit outside `[data-catalog]`**, in the page header. Query them document-wide.
- **No network at build time.** Never make the build fetch from the internet. Fetch scripts write to `source/`, and the build reads only local files.
- **Large repo.** `source/` and `dist/` hold hundreds of MB of images. Avoid tools that rewrite the whole history. Once, a corrupted object in the local git pack broke checkouts; it was repaired by restoring the blob from GitHub, unpacking the rest and repacking. If git reports `packed object … is corrupt`, recover the object from the remote rather than recloning blindly.
- **`html.escape` captured text** before it reaches a template field that is rendered with `|safe` (spec labels and values, notes).
- **Merging to `main` needs a review.** Claude Code's auto mode blocks merging a PR nobody has reviewed. The owner reviews it, then merges with `gh pr merge <n> --merge`.

## The owner's preferences (from working with them)

- Wants a modern, clean, fast UI and asks for things to "keep the design language" when changing content.
- Non-technical about hosting and DNS: give step-by-step instructions with exact field values, and flag upsell popups.
- Wants changes pushed to GitHub when a piece of work is done. Commit messages follow the style of the existing history.
