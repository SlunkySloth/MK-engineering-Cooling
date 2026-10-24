# Deployment

## Overview

| Piece | Where | Cost |
|---|---|---|
| Code | GitHub `SlunkySloth/MK-engineering-Cooling` | Free |
| Hosting | Vercel, project **`dist`** (team "Padmanaban's projects", Hobby plan), connected to the GitHub repo | Free |
| Domain | `mkengg.in`, registered at **Hostinger** (domain only, no hosting plan) | About ₹550/yr + GST; renews at ₹899/yr |
| DNS | Hostinger's own nameservers (`*.dns-parking.com`), not Cloudflare | Included |

## How a change goes live

1. Edit `src/` (or the data), run `python src/build.py`, then `python validate.py`.
2. Commit **both** the `src/` changes and the regenerated `dist/`.
3. Push to `main`. Vercel builds nothing; it serves `dist/` straight away, as set in `vercel.json`:
   ```json
   { "framework": null, "buildCommand": "", "installCommand": "", "outputDirectory": "dist" }
   ```
4. The production deploy finishes in a minute or two. Its status appears as the "Vercel" commit status on GitHub:
   ```bash
   gh api repos/SlunkySloth/MK-engineering-Cooling/commits/<sha>/status
   ```

> **Do not delete `vercel.json`.** Without it, Vercel serves the repo root, which has no `index.html`, and every URL returns 404. This happened once, right after the first merge to `main`.

Pushes to other branches create preview deployments only.

## Domain and DNS (at Hostinger)

These are the records in Hostinger → Domains → mkengg.in → DNS / Nameservers. Do not add others for the website:

| Type | Name | Value |
|---|---|---|
| A | `@` | `216.198.79.1` (Vercel) |
| CNAME | `www` | `245f6d258795e9d1.vercel-dns-017.com` (Vercel, specific to this project) |

- In Vercel, `mkengg.in` 308-redirects to **`www.mkengg.in`**, which is the canonical address.
- Vercel issues and renews the SSL certificate automatically.
- The project's own Vercel URL, `dist-psi-navy-18.vercel.app`, also serves the site.
- When adding email, add MX and TXT records next to these and leave the A and CNAME records untouched.
- Hostinger's "Host your web app" popup when saving DNS is an upsell. Choose "No thanks, point my domain".

## Cloudflare (abandoned)

A Cloudflare Pages setup was attempted first but stopped, because Cloudflare reported the account email (mkengineering.try@gmail.com) as unverified. That attempt left behind:
- `wrangler.jsonc` and `.wrangler/` in the repo root, both untracked
- a git stash named "wrangler files", which also holds a `.gitignore` change for wrangler

They aren't used, so they can be deleted if the site stays on Vercel. Don't commit them.

## Not set up yet

- **Visitor analytics.**
  1. Enable *Analytics* on the Vercel `dist` project.
  2. Add `<script defer src="/_vercel/insights/script.js"></script>` to `base.html`.
- **Email** such as `sales@mkengg.in`. The plan is Zoho Mail's free plan; add its MX, SPF and DKIM records at Hostinger. The site currently uses two Gmail addresses (`site.json` → `emails`).
- **Search engines.** Google Search Console, plus a sitemap and `robots.txt`, which the build does not generate yet.
