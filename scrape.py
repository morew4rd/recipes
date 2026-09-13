#!/usr/bin/env python3
"""Polite scraper for one user's recipes on nefisyemektarifleri.com.

Usage:
    python3 scrape.py            # full run (list + recipes + images)
    python3 scrape.py --list     # only refresh the recipe URL list
    python3 scrape.py --parse    # only (re)parse already-downloaded raw HTML

Output layout:
    data/raw/<slug>.html       raw page source (never re-downloaded)
    data/recipes/<slug>.json   parsed recipe
    data/images/<file>.jpg     recipe photos (full size)
    data/index.json            list of all recipes (slug, title, image, ...)
"""

import argparse
import html as htmlmod
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request

BASE = "https://www.nefisyemektarifleri.com"
USER = "sevimdefnesedef"
LIST_URL = f"{BASE}/u/{USER}/tarifler/"

DATA = "data"
RAW_DIR = os.path.join(DATA, "raw")
REC_DIR = os.path.join(DATA, "recipes")
IMG_DIR = os.path.join(DATA, "images")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/120.0.0.0 Safari/537.36")

# politeness settings (seconds)
PAGE_DELAY = (4.0, 9.0)
IMG_DELAY = (1.0, 3.0)


def fetch(url, binary=False):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read() if binary else r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code in (403, 429, 503):
            print(f"\n!!! Got HTTP {e.code} for {url} — likely rate-limited. "
                  "Aborting; wait a while and re-run (it resumes).")
            sys.exit(2)
        raise


def pause(lo, hi):
    t = random.uniform(lo, hi)
    time.sleep(t)


# ---------------------------------------------------------------- list pages

def collect_recipe_urls():
    """Walk paginated profile list pages and return [(slug, url), ...]."""
    seen, page = {}, 1
    while True:
        url = LIST_URL if page == 1 else f"{LIST_URL}page/{page}/"
        print(f"[list] page {page}: {url}")
        doc = fetch(url)
        cards = re.findall(
            r'<h3><a class="title" href="(https://www\.nefisyemektarifleri\.com/([a-z0-9-]+)/)"',
            doc)
        new = 0
        for full, slug in cards:
            if slug not in seen:
                seen[slug] = full
                new += 1
        print(f"       {new} new recipes (total {len(seen)})")
        has_next = re.search(r'class="jscroll-next', doc)
        if not has_next or new == 0:
            break
        page += 1
        if page > 60:
            print("too many pages, stopping")
            break
        pause(*PAGE_DELAY)
    urls = sorted(seen.items())
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "urls.json"), "w", encoding="utf-8") as f:
        json.dump([{"slug": s, "url": u} for s, u in urls], f,
                  ensure_ascii=False, indent=1)
    return urls


# ------------------------------------------------------------------ parsing

def strip_tags(s):
    return htmlmod.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def parse_recipe(slug, url, doc):
    def one(pat, flags=0):
        m = re.search(pat, doc, flags)
        return m.group(1) if m else None

    title = strip_tags(one(r"<h1[^>]*>(.*?)</h1>", re.S) or "")
    # drop the trailing " Tarifi" marketing suffix variants? keep as-is.
    date = one(r'datePublished"?\s*content="([^"]+)"') or ""

    # categories from the GTM dataLayer payload ("mainCategory":"X","subCategory":"Y")
    categories = []
    dl = one(r'dataLayer\.push\s*\(\s*(\{.*?\})\s*\);', re.S)
    if dl:
        for key in ("mainCategory", "subCategory"):
            m = re.search(rf'"{key}":"([^"]+)"', dl)
            if m and m.group(1) not in categories:
                categories.append(m.group(1))

    # short info: servings
    serves = ""
    m = re.search(r'recipeYield"\s*content="(\d+)"', doc)
    si = re.search(r'<ul class="short-info">(.*?)</ul>', doc, re.S)
    if si:
        m2 = re.search(r"<span>([^<]*)</span>\s*Kişilik", si.group(1))
        if m2:
            serves = m2.group(1).strip() + " kişilik"

    def t(prop):
        return one(rf'itemprop="{prop}"\s*content="([^"]+)"') or ""

    ing = [strip_tags(x) for x in re.findall(
        r'<li itemprop="recipeIngredient"[^>]*>(.*?)</li>', doc, re.S)]

    ol = one(r'<ol class="recipe-instructions"[^>]*>(.*?)</ol>', re.S) or ""
    steps = [strip_tags(x) for x in re.findall(r"<li>(.*?)</li>", ol, re.S)]

    imgs = re.findall(
        r"<figure[^>]*class='recipe-image[^']*'[^>]*>.*?data-lazy-src=\"([^\"]+)\"",
        doc, re.S)
    # de-dup, keep order; skip tracking pixels
    seen_i, images = set(), []
    for u in imgs:
        if u not in seen_i and "1x1.gif" not in u:
            seen_i.add(u)
            images.append(u)

    return {
        "slug": slug,
        "url": url,
        "title": title,
        "author": "sevim girgin",
        "datePublished": date[:10],
        "categories": categories,
        "servings": serves,
        "times": {"prep": t("prepTime"), "cook": t("cookTime"),
                  "total": t("totalTime")},
        "ingredients": ing,
        "instructions": steps,
        "images": [],   # filled in with local paths after download
        "imageUrls": images,
    }


# -------------------------------------------------------------------- images

def download_images(recipe):
    local = []
    for u in recipe["imageUrls"]:
        name = u.rsplit("/", 1)[-1]
        dest = os.path.join(IMG_DIR, name)
        local.append(f"images/{name}")
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            continue
        print(f"    img {name}")
        try:
            with open(dest, "wb") as f:
                f.write(fetch(u, binary=True))
        except Exception as e:
            print(f"    !! image failed: {e}")
            local.pop()
        pause(*IMG_DELAY)
    recipe["images"] = local


# ---------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="only refresh URL list")
    ap.add_argument("--parse", action="store_true",
                    help="re-parse raw HTML into JSON without downloading")
    ap.add_argument("--limit", type=int, default=0, help="max recipes (testing)")
    args = ap.parse_args()

    for d in (RAW_DIR, REC_DIR, IMG_DIR):
        os.makedirs(d, exist_ok=True)

    urls_path = os.path.join(DATA, "urls.json")
    if args.parse and os.path.exists(urls_path):
        urls = [(e["slug"], e["url"]) for e in json.load(open(urls_path))]
    else:
        # normal runs always refresh the list so new recipes are discovered
        urls = collect_recipe_urls()
        if args.list:
            return

    if args.limit:
        urls = urls[:args.limit]

    index = []
    for i, (slug, url) in enumerate(urls, 1):
        raw_path = os.path.join(RAW_DIR, slug + ".html")
        json_path = os.path.join(REC_DIR, slug + ".json")

        if args.parse:
            if not os.path.exists(raw_path):
                continue
            doc = open(raw_path, encoding="utf-8").read()
            rec = parse_recipe(slug, url, doc)
            old = json.load(open(json_path)) if os.path.exists(json_path) else {}
            rec["images"] = old.get("images", [])
        else:
            if os.path.exists(json_path) and os.path.exists(raw_path):
                rec = json.load(open(json_path))
                missing = [p for p in rec["images"]
                           if not os.path.exists(os.path.join(DATA, p))]
                if not missing:
                    print(f"[{i}/{len(urls)}] skip {slug} (done)")
                    index.append(rec)
                    continue
            if not os.path.exists(raw_path):
                print(f"[{i}/{len(urls)}] GET {url}")
                doc = fetch(url)
                with open(raw_path, "w", encoding="utf-8") as f:
                    f.write(doc)
                pause(*PAGE_DELAY)
            else:
                doc = open(raw_path, encoding="utf-8").read()
            rec = parse_recipe(slug, url, doc)
            download_images(rec)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)
        index.append(rec)

    index.sort(key=lambda r: r["datePublished"], reverse=True)
    slim = [{"slug": r["slug"], "title": r["title"],
             "datePublished": r["datePublished"],
             "categories": r["categories"], "servings": r["servings"],
             "times": r["times"],
             "image": r["images"][0] if r["images"] else None}
            for r in index]
    with open(os.path.join(DATA, "index.json"), "w", encoding="utf-8") as f:
        json.dump(slim, f, ensure_ascii=False, indent=1)
    print(f"\nDone. {len(index)} recipes in {DATA}/")


if __name__ == "__main__":
    main()
