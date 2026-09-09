#!/usr/bin/env python3
"""Build a static website from the scraped recipe data.

Usage:  python3 build_site.py
Input:  data/            (produced by scrape.py)
Output: site/            (self-contained static site, GitHub Pages ready)
"""

import html
import json
import os
import re
import shutil

DATA = "data"
SITE = "site"

CSS = """
:root { --accent:#c0392b; --bg:#fdf8f3; --card:#fff; --text:#333; --muted:#888; }
* { box-sizing:border-box; margin:0; padding:0; }
body { font-family:-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;
       background:var(--bg); color:var(--text); line-height:1.6; }
a { color:var(--accent); text-decoration:none; }
header { background:var(--accent); color:#fff; padding:1.2rem 1rem; text-align:center; }
header h1 { font-size:1.6rem; font-weight:600; }
header p { opacity:.85; font-size:.9rem; margin-top:.2rem; }
.wrap { max-width:1100px; margin:0 auto; padding:1rem; }
.toolbar { display:flex; flex-wrap:wrap; gap:.6rem; margin:1.2rem 0; }
#search { flex:1; min-width:200px; padding:.55rem .9rem; border:1px solid #ddd;
          border-radius:24px; font-size:1rem; background:#fff; }
.cats { display:flex; flex-wrap:wrap; gap:.4rem; margin-bottom:1.2rem; }
.cat { padding:.25rem .8rem; border-radius:20px; border:1px solid #ddd; background:#fff;
       cursor:pointer; font-size:.85rem; }
.cat.active { background:var(--accent); color:#fff; border-color:var(--accent); }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:1rem; }
.card { background:var(--card); border-radius:10px; overflow:hidden;
        box-shadow:0 1px 4px rgba(0,0,0,.08); transition:transform .15s; }
.card:hover { transform:translateY(-3px); }
.card img { width:100%; height:170px; object-fit:cover; display:block; }
.card .body { padding:.7rem .9rem; }
.card h3 { font-size:1rem; font-weight:600; }
.card h3 a { color:var(--text); }
.card .meta { font-size:.8rem; color:var(--muted); margin-top:.3rem; }
.count { color:var(--muted); font-size:.85rem; margin-bottom:.6rem; }
/* recipe page */
.recipe-hero { width:100%; max-height:420px; object-fit:cover; border-radius:12px; }
.recipe-head { margin:1rem 0; }
.badges { display:flex; flex-wrap:wrap; gap:.5rem; margin:.6rem 0; }
.badge { background:#fff; border:1px solid #eee; border-radius:8px;
         padding:.3rem .7rem; font-size:.85rem; }
.cols { display:grid; grid-template-columns:1fr 1.6fr; gap:2rem; margin-top:1rem; }
@media (max-width:700px){ .cols { grid-template-columns:1fr; } }
h2 { font-size:1.15rem; margin-bottom:.6rem; border-bottom:2px solid var(--accent);
     display:inline-block; padding-bottom:.15rem; }
ul.ing { list-style:none; }
ul.ing li { padding:.35rem 0 .35rem 1.4rem; position:relative; border-bottom:1px dashed #eee; }
ul.ing li::before { content:"•"; color:var(--accent); position:absolute; left:.3rem; }
ol.steps { padding-left:1.3rem; }
ol.steps li { margin-bottom:.7rem; padding-left:.3rem; }
.photos { display:grid; grid-template-columns:repeat(auto-fill,minmax(180px,1fr));
          gap:.6rem; margin-top:1rem; }
.photos img { width:100%; border-radius:8px; cursor:pointer; }
.back { display:inline-block; margin-bottom:.8rem; }
footer { text-align:center; color:var(--muted); font-size:.8rem; padding:2rem 1rem; }
@media print { header,.toolbar,.back,footer,.photos { display:none; } }
"""


def esc(s):
    return html.escape(s or "", quote=True)


def human_time(iso):
    """PT30M -> '30 dk', PT1H15M -> '1 sa 15 dk'"""
    if not iso:
        return ""
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?", iso)
    if not m:
        return ""
    h, mn = int(m.group(1) or 0), int(m.group(2) or 0)
    parts = []
    if h:
        parts.append(f"{h} sa")
    if mn:
        parts.append(f"{mn} dk")
    return " ".join(parts)


def page(title, body, root=""):
    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{root}style.css">
</head>
<body>
{body}
</body>
</html>
"""


def recipe_page(r):
    t = r["times"]
    badges = []
    if r["servings"]:
        badges.append(f"🍽️ {esc(r['servings'])}")
    if t.get("prep"):
        badges.append(f"⏱️ Hazırlık: {human_time(t['prep'])}")
    if t.get("cook"):
        badges.append(f"🔥 Pişirme: {human_time(t['cook'])}")
    for c in r["categories"]:
        badges.append(f"🏷️ {esc(c)}")

    hero = f'<img class="recipe-hero" src="../{esc(r["images"][0])}" alt="{esc(r["title"])}">' \
        if r["images"] else ""
    photos = "".join(
        f'<a href="../{esc(p)}" target="_blank"><img src="../{esc(p)}" '
        f'alt="{esc(r["title"])}" loading="lazy"></a>'
        for p in r["images"][1:])
    photos_html = f'<h2>Fotoğraflar</h2><div class="photos">{photos}</div>' if photos else ""

    ing = "".join(f"<li>{esc(i)}</li>" for i in r["ingredients"])
    steps = "".join(f"<li>{esc(s)}</li>" for s in r["instructions"])

    body = f"""
<header><h1>{esc(r['title'])}</h1><p>{r['datePublished']}</p></header>
<div class="wrap">
<a class="back" href="../index.html">← Tüm tarifler</a>
{hero}
<div class="recipe-head"><div class="badges">{''.join(f'<span class="badge">{b}</span>' for b in badges)}</div></div>
<div class="cols">
  <section><h2>Malzemeler</h2><ul class="ing">{ing}</ul></section>
  <section><h2>Hazırlanışı</h2><ol class="steps">{steps}</ol></section>
</div>
{photos_html}
</div>
<footer>{esc(r['author'])} · <a href="{esc(r['url'])}">orijinal tarif</a></footer>
"""
    return page(r["title"], body, root="../")


def index_page(recipes):
    cards = []
    for r in recipes:
        first_img = r["images"][0] if r["images"] else None
        img = f'<img src="{esc(first_img)}" alt="{esc(r["title"])}" loading="lazy">' \
            if first_img else ""
        meta_bits = [b for b in (r["servings"],
                                 human_time(r["times"].get("total", ""))) if b]
        cards.append(f"""
<div class="card" data-title="{esc(r['title'].lower())}" data-cat="{esc('|'.join(r['categories']).lower())}">
  <a href="tarif/{esc(r['slug'])}.html">{img}</a>
  <div class="body">
    <h3><a href="tarif/{esc(r['slug'])}.html">{esc(r['title'])}</a></h3>
    <div class="meta">{esc(' · '.join(meta_bits))}</div>
  </div>
</div>""")

    cats = sorted({c for r in recipes for c in r["categories"]})
    cat_btns = '<button class="cat active" data-cat="">Tümü</button>' + "".join(
        f'<button class="cat" data-cat="{esc(c.lower())}">{esc(c)}</button>' for c in cats)

    body = f"""
<header><h1>Sevim'in Mutfağı</h1><p>{len(recipes)} tarif</p></header>
<div class="wrap">
  <div class="toolbar">
    <input id="search" type="search" placeholder="Tarif ara... (ör. börek, çorba, patates)">
  </div>
  <div class="cats">{cat_btns}</div>
  <div class="count"><span id="count">{len(recipes)}</span> tarif gösteriliyor</div>
  <div class="grid" id="grid">{''.join(cards)}</div>
</div>
<footer>Afiyet olsun ❤️</footer>
<script>
const cards = [...document.querySelectorAll('.card')];
const search = document.getElementById('search');
const count = document.getElementById('count');
let activeCat = '';
function apply() {{
  const q = search.value.toLowerCase().trim();
  let n = 0;
  for (const c of cards) {{
    const ok = (!q || c.dataset.title.includes(q)) &&
               (!activeCat || c.dataset.cat.split('|').includes(activeCat));
    c.style.display = ok ? '' : 'none';
    if (ok) n++;
  }}
  count.textContent = n;
}}
search.addEventListener('input', apply);
document.querySelectorAll('.cat').forEach(b => b.addEventListener('click', () => {{
  document.querySelector('.cat.active').classList.remove('active');
  b.classList.add('active');
  activeCat = b.dataset.cat;
  apply();
}}));
</script>
"""
    return page("Sevim'in Mutfağı", body)


def main():
    index = json.load(open(os.path.join(DATA, "index.json"), encoding="utf-8"))

    if os.path.exists(SITE):
        shutil.rmtree(SITE)
    os.makedirs(os.path.join(SITE, "tarif"))
    shutil.copytree(os.path.join(DATA, "images"), os.path.join(SITE, "images"))

    recipes = []
    for e in index:
        p = os.path.join(DATA, "recipes", e["slug"] + ".json")
        if os.path.exists(p):
            recipes.append(json.load(open(p, encoding="utf-8")))

    for r in recipes:
        with open(os.path.join(SITE, "tarif", r["slug"] + ".html"), "w",
                  encoding="utf-8") as f:
            f.write(recipe_page(r))

    with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_page(recipes))
    with open(os.path.join(SITE, "style.css"), "w", encoding="utf-8") as f:
        f.write(CSS)
    open(os.path.join(SITE, ".nojekyll"), "w").close()  # GitHub Pages

    print(f"Built site/ with {len(recipes)} recipes.")


if __name__ == "__main__":
    main()
