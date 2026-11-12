import os
import json
import html
from datetime import datetime

DATA_ROOT = "data"
SITE_ROOT = "."          # GitHub Pages root
BASE_URL = "https://YOUR-USERNAME.github.io/YOUR-REPO"   # ← আপনার URL বসান

LANG_LABELS = {
    "english": ("English", "en"), "bengali": ("Bengali", "bn"),
    "hindi": ("Hindi", "hi"), "arabic": ("Arabic", "ar"),
    "spanish": ("Spanish", "es"), "french": ("French", "fr"),
    "german": ("German", "de"), "japanese": ("Japanese", "ja"),
    "chinese": ("Chinese", "zh"), "korean": ("Korean", "ko"),
    "russian": ("Russian", "ru"), "italian": ("Italian", "it"),
    "portuguese": ("Portuguese", "pt"), "dutch": ("Dutch", "nl"),
    "turkish": ("Turkish", "tr"), "urdu": ("Urdu", "ur"),
}

def strip_meta(text):
    """Remove leading Language:/Date:/--- header lines."""
    lines = text.split("\n")
    start = 0
    for i, line in enumerate(lines[:12]):
        l = line.strip()
        if l == "" or l.startswith("---") or l.lower().startswith(("language:", "date:", "title:", "author:")):
            start = i + 1
        else:
            break
    body = "\n".join(lines[start:]).strip()
    return body or text.strip()

def esc(s):
    return html.escape(s, quote=True)

def build_page(lang, fname, joke, all_langs):
    code, iso = LANG_LABELS.get(lang, (lang.capitalize(), lang[:2]))
    slug = fname[:-4]  # strip .txt
    url = f"{BASE_URL}/{lang}/{slug}.html"
    title_short = joke[:70].replace("\n", " ").strip()
    title = f"{title_short} — {code} Joke | Daily Jokes"
    desc = joke[:155].replace("\n", " ").strip()

    # hreflang block
    hreflang = "\n".join(
        f'  <link rel="alternate" hreflang="{LANG_LABELS.get(l, (l, l[:2]))[1]}" href="{BASE_URL}/{l}/">'
        for l in all_langs
    )
    hreflang += f'\n  <link rel="alternate" hreflang="x-default" href="{BASE_URL}/english/">'

    # JSON-LD
    ld = {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": title_short,
        "text": joke,
        "inLanguage": iso,
        "genre": "Comedy",
        "url": url,
        "isPartOf": {"@type": "WebSite", "name": "Daily Jokes", "url": BASE_URL + "/"},
        "datePublished": slug if len(slug) == 10 else None,
    }
    ld = {k: v for k, v in ld.items() if v is not None}

    return f"""<!DOCTYPE html>
<html lang="{iso}">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}" />
  <link rel="canonical" href="{url}" />
  {hreflang}
  <meta property="og:type" content="article" />
  <meta property="og:title" content="{esc(title)}" />
  <meta property="og:description" content="{esc(desc)}" />
  <meta property="og:url" content="{url}" />
  <meta property="og:site_name" content="Daily Jokes" />
  <meta name="twitter:card" content="summary" />
  <meta name="twitter:title" content="{esc(title)}" />
  <meta name="twitter:description" content="{esc(desc)}" />
  <script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body>
  <main style="max-width:680px;margin:2rem auto;padding:0 1.25rem;font-family:Georgia,serif;line-height:1.85;font-size:1.0625rem;">
    <nav style="font-size:.8125rem;margin-bottom:1.5rem;">
      <a href="{BASE_URL}/">Home</a> ›
      <a href="{BASE_URL}/{lang}/">{code}</a> ›
      <span>{esc(slug)}</span>
    </nav>
    <h1 style="font-size:1.25rem;margin-bottom:1rem;">{esc(code)} Joke</h1>
    <article style="white-space:pre-wrap;">{esc(joke)}</article>
    <p style="margin-top:2rem;font-size:.8125rem;">
      <a href="{BASE_URL}/{lang}/">← All {code} jokes</a>
    </p>
  </main>
</body>
</html>"""

def main():
    with open(os.path.join(DATA_ROOT, "languages.json"), encoding="utf-8") as f:
        langs = [x["code"] for x in json.load(f)["languages"]]

    urls = []
    for lang in langs:
        folder = os.path.join(DATA_ROOT, lang)
        out_dir = os.path.join(SITE_ROOT, lang)
        os.makedirs(out_dir, exist_ok=True)

        files = sorted(
            [f for f in os.listdir(folder) if f.lower().endswith(".txt")],
            reverse=True
        )

        # ---- language landing page ----
        links = "\n".join(
            f'<li><a href="{BASE_URL}/{lang}/{f[:-4]}.html">{f[:-4]}</a></li>'
            for f in files
        )
        landing = f"""<!DOCTYPE html>
<html lang="{LANG_LABELS.get(lang, (lang, lang[:2]))[1]}">
<head>
  <meta charset="UTF-8" />
  <title>{esc(lang.capitalize())} Jokes — Daily Collection</title>
  <meta name="description" content="Read daily {esc(lang)} jokes. Fresh comedy in {esc(lang)}." />
  <link rel="canonical" href="{BASE_URL}/{lang}/" />
</head>
<body>
  <h1>{esc(lang.capitalize())} Jokes</h1>
  <ul>{links}</ul>
</body>
</html>"""
        with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as fp:
            fp.write(landing)
        urls.append(f"{BASE_URL}/{lang}/")

        # ---- per-joke static pages ----
        for fname in files:
            with open(os.path.join(folder, fname), encoding="utf-8") as fp:
                raw = fp.read()
            joke = strip_meta(raw)
            page = build_page(lang, fname, joke, langs)
            out_path = os.path.join(out_dir, fname[:-4] + ".html")
            with open(out_path, "w", encoding="utf-8") as fp:
                fp.write(page)
            urls.append(f"{BASE_URL}/{lang}/{fname[:-4]}.html")
            print(f"✅ {out_path}")

    # ---- sitemap.xml ----
    today = datetime.now().strftime("%Y-%m-%d")
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sm.append(f"<url><loc>{esc(u)}</loc><lastmod>{today}</lastmod></url>")
    sm.append("</urlset>")
    with open(os.path.join(SITE_ROOT, "sitemap.xml"), "w", encoding="utf-8") as fp:
        fp.write("\n".join(sm))

    # ---- robots.txt ----
    with open(os.path.join(SITE_ROOT, "robots.txt"), "w", encoding="utf-8") as fp:
        fp.write(f"User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}/sitemap.xml\n")

    print(f"\n🌍 {len(urls)} URLs in sitemap.")

if __name__ == "__main__":
    main()
