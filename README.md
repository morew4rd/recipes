# Sevim'in Mutfağı

A static website of Sevim Girgin's recipes, mirrored from her
[Nefis Yemek Tarifleri profile](https://www.nefisyemektarifleri.com/u/sevimdefnesedef/tarifler/).

## How it works

| File | Purpose |
|---|---|
| `scrape.py` | Polite, incremental scraper → `data/` (JSON + photos + raw HTML) |
| `build_site.py` | Generates the static site → `site/` |
| `.github/workflows/update.yml` | Weekly CI: scrape → build → deploy to GitHub Pages |

`scrape.py` is incremental: it re-checks the profile list pages and only
downloads recipes it hasn't seen before. Safe to re-run anytime.

## Local usage

```sh
python3 scrape.py          # update data/ (new recipes only)
python3 build_site.py      # rebuild site/
cd site && python3 -m http.server 8000   # preview at http://localhost:8000
```

## GitHub Pages setup (one-time)

1. Push this repo to GitHub (including `data/` — CI needs it for incremental updates).
2. In the repo: **Settings → Pages → Source: "Deploy from a branch"**, branch `gh-pages`, folder `/ (root)`.
   (The `gh-pages` branch is created automatically by the first CI run.)
3. Actions → "Update recipes" → **Run workflow** for the first deploy.

After that, the site updates itself every Monday. If she publishes a recipe
and you don't want to wait: Actions → "Update recipes" → Run workflow.

Note: GitHub disables scheduled workflows after 60 days of repo inactivity;
you'll get an email — just click re-enable.
