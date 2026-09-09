# Sevim'in Mutfağı

A static website of Sevim Girgin's recipes, mirrored from her
[Nefis Yemek Tarifleri profile](https://www.nefisyemektarifleri.com/u/sevimdefnesedef/tarifler/).

Live at **https://sevim.girg.in**

## How it works

| File | Purpose |
|---|---|
| `scrape.py` | Polite, incremental scraper → `data/` (JSON + photos + raw HTML) |
| `build_site.py` | Generates the static site → `site/` (incl. CNAME + .nojekyll) |
| `.github/workflows/update.yml` | Manual CI: scrape → build → deploy to GitHub Pages |

`scrape.py` is incremental: it re-checks the profile list pages and only
downloads recipes it hasn't seen before. Safe to re-run anytime.

## Updating the site

When she publishes new recipes, either:

- **GitHub**: Actions → "Update recipes" → **Run workflow** (manual only,
  nothing runs on a schedule), or
- **Locally**: `python3 scrape.py && python3 build_site.py`, then commit
  `data/` and redeploy (push `site/` to the `gh-pages` branch).

## Local preview

```sh
python3 build_site.py
cd site && python3 -m http.server 8000   # http://localhost:8000
```

## Hosting setup notes

- Served by GitHub Pages from the `gh-pages` branch (created by the workflow
  or a manual push of `site/`).
- Custom domain: `sevim.girg.in` via the `CNAME` file generated into `site/`.
  DNS needs A records for `sevim.girg.in` pointing at GitHub's Pages IPs
  (185.199.108.153 – 185.199.111.153). HTTPS is enabled automatically once
  DNS resolves (Settings → Pages → Enforce HTTPS).
