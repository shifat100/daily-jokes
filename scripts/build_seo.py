import os
import json
import html
from datetime import datetime

DATA_ROOT = "data"
SITE_ROOT = "."

# ⬇️⬇️ এখানে আপনার GitHub Pages URL বসান ⬇️⬇️
BASE_URL = "https://shifat100.github.io/daily-jokes"

# -----------------------------------------------------------------
# BCP-47 display names. Unknown codes fall back to the code itself.
# -----------------------------------------------------------------
LANG_META = {
    "en":     "English",
    "en-US":  "English (US)",
    "en-GB":  "English (UK)",
    "bn":     "Bengali",
    "bn-BD":  "Bengali (Bangladesh)",
    "bn-IN":  "Bengali (India)",
    "hi":     "Hindi",
    "hi-IN":  "Hindi (India)",
    "ar":     "Arabic",
    "ar-SA":  "Arabic (Saudi Arabia)",
    "ar-EG":  "Arabic (Egypt)",
    "es":     "Spanish",
    "es-ES":  "Spanish (Spain)",
    "es-MX":  "Spanish (Mexico)",
    "fr":     "French",
    "fr-FR":  "French (France)",
    "fr-CA":  "French (Canada)",
    "de":     "German",
    "de-DE":  "German (Germany)",
    "ja":     "Japanese",
    "ja-JP":  "Japanese (Japan)",
    "zh":     "Chinese",
    "zh-CN":  "Chinese (Simplified)",
    "zh-TW":  "Chinese (Traditional)",
    "ko":     "Korean",
    "ko-KR":  "Korean (Korea)",
    "ru":     "Russian",
    "ru-RU":  "Russian (Russia)",
    "pt":     "Portuguese",
    "pt-BR":  "Portuguese (Brazil)",
    "pt-PT":  "Portuguese (Portugal)",
    "it":     "Italian",
    "it-IT":  "Italian (Italy)",
    "nl":     "Dutch",
    "tr":     "Turkish",
    "ur":     "Urdu",
    "ur-PK":  "Urdu (Pakistan)",
    "id":     "Indonesian",
    "th":     "Thai",
    "vi":     "Vietnamese",
    "fa":     "Persian",
    "ta":     "Tamil",
    "te":     "Telugu",
    "ml":     "Malayalam",
    "kn":     "Kannada",
    "gu":     "Gujarati",
    "mr":     "Marathi",
    "pa":     "Punjabi",
}


def display_name(code: str) -> str:
    """Bengali (Bangladesh) from bn-BD, or fall back to the raw code."""
    if code in LANG_META:
        return LANG_META[code]
    return code


def hreflang_of(code: str) -> str:
    """BCP-47 tags work directly as hreflang values."""
    return code


def primary_lang(code: str) -> str:
    """bn-BD → bn  (used for x-default fallback)."""
    return code.split("-")[0]


# -----------------------------------------------------------------
# HTML helpers
# -----------------------------------------------------------------
def esc(s: str) -> str:
    return html.escape(s, quote=True)


def strip_meta(text: str) -> str:
    """Remove leading Language:/Date:/--- header lines so only the joke shows."""
    lines = text.split("\n")
    start = 0
    for i, line in enumerate(lines[:12]):
        l = line.strip()
        if (
            l == ""
            or l.startswith("---")
            or l.lower().startswith(("language:", "date:", "title:", "author:", "source:"))
        ):
            start = i + 1
        else:
            break
    body = "\n".join(lines[start:]).strip()
    return body or text.strip()


# -----------------------------------------------------------------
# Static page builder
# -----------------------------------------------------------------
def build_joke_page(lang: str, fname: str, joke: str, all_langs: list) -> str:
    name = display_name(lang)
    slug = fname[:-4]
    url = f"{BASE_URL}/{lang}/{slug}.html"

    title_short = joke[:70].replace("\n", " ").strip()
    title = f"{title_short} — {name} Joke | Daily Jokes"
    desc = joke[:155].replace("\n", " ").strip()

    # hreflang block for every language we have
    hl_lines = []
    for l in all_langs:
        hl_lines.append(
            f'  <link rel="alternate" hreflang="{hreflang_of(l)}" href="{BASE_URL}/{l}/" />'
        )
    # x-default → en if available, else en-US, else first language
    if "en" in all_langs:
        xdef = "en"
    elif "en-US" in all_langs:
        xdef = "en-US"
    else:
        xdef = all_langs[0] if all_langs else lang
    hl_lines.append(
        f'  <link rel="alternate" hreflang="x-default" href="{BASE_URL}/{xdef}/" />'
    )
    hreflang_block = "\n".join(hl_lines)

    # JSON-LD structured data (CreativeWork + Comedy genre)
    ld = {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": title_short,
        "text": joke,
        "inLanguage": lang,
        "genre": "Comedy",
        "url": url,
        "isPartOf": {"@type": "WebSite", "name": "Daily Jokes", "url": BASE_URL + "/"},
    }
    if len(slug) == 10 and slug[4] == "-" and slug[7] == "-":
        ld["datePublished"] = slug

    return f"""<!DOCTYPE html>
<html lang="{esc(lang)}">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}" />
  <link rel="canonical" href="{esc(url)}" />
{hreflang_block}
  <meta property="og:type" content="article" />
  <meta property="og:title" content="{esc(title)}" />
  <meta property="og:description" content="{esc(desc)}" />
  <meta property="og:url" content="{esc(url)}" />
  <meta property="og:site_name" content="Daily Jokes" />
  <meta property="og:locale" content="{esc(lang.replace('-', '_'))}" />
  <meta name="twitter:card" content="summary" />
  <meta name="twitter:title" content="{esc(title)}" />
  <meta name="twitter:description" content="{esc(desc)}" />
  <script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body>
  <main style="max-width:680px;margin:2rem auto;padding:0 1.25rem;font-family:Georgia,serif;line-height:1.85;font-size:1.0625rem;color:#1c1917;">
    <nav style="font-size:.8125rem;margin-bottom:1.5rem;">
      <a href="{BASE_URL}/">Home</a> ›
      <a href="{BASE_URL}/{lang}/">{esc(name)}</a> ›
      <span>{esc(slug)}</span>
    </nav>
    <h1 style="font-size:1.25rem;margin-bottom:1rem;">{esc(name)} Joke</h1>
    <article style="white-space:pre-wrap;">{esc(joke)}</article>
    <p style="margin-top:2rem;font-size:.8125rem;">
      <a href="{BASE_URL}/{lang}/">← All {esc(name)} jokes</a>
    </p>
  </main>
</body>
</html>"""


def build_language_page(lang: str, files: list) -> str:
    name = display_name(lang)
    links = "\n".join(
        f'      <li><a href="{BASE_URL}/{lang}/{f[:-4]}.html">{esc(f[:-4])}</a></li>'
        for f in files
    )
    return f"""<!DOCTYPE html>
<html lang="{esc(lang)}">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(name)} Jokes — Daily Collection</title>
  <meta name="description" content="Read daily {esc(name)} jokes — fresh comedy in {esc(name)}." />
  <link rel="canonical" href="{BASE_URL}/{lang}/" />
</head>
<body style="max-width:680px;margin:2rem auto;padding:0 1.25rem;font-family:system-ui,sans-serif;">
  <h1>{esc(name)} Jokes</h1>
  <ul style="line-height:2;">
{links}
  </ul>
</body>
</html>"""


# -----------------------------------------------------------------
# Main
# -----------------------------------------------------------------
def main():
    # 1. Ensure data/languages.json exists
    langs_json = os.path.join(DATA_ROOT, "languages.json")
    if not os.path.exists(langs_json):
        print("⚠️  data/languages.json missing — scanning data/ directly")
        languages = []
        if os.path.isdir(DATA_ROOT):
            for entry in sorted(os.listdir(DATA_ROOT)):
                folder = os.path.join(DATA_ROOT, entry)
                if os.path.isdir(folder) and not entry.startswith("."):
                    files = [
                        f for f in os.listdir(folder)
                        if f.lower().endswith(".txt") and not f.startswith(".")
                    ]
                    if files:
                        languages.append({"code": entry, "count": len(files)})
        os.makedirs(DATA_ROOT, exist_ok=True)
        with open(langs_json, "w", encoding="utf-8") as fp:
            json.dump(
                {"languages": languages, "updated": datetime.now().isoformat()},
                fp, ensure_ascii=False, indent=2,
            )

    with open(langs_json, encoding="utf-8") as fp:
        data = json.load(fp)

    langs = [x["code"] for x in data.get("languages", [])]
    if not langs:
        print("⚠️  No language folders found in data/. Nothing to build.")
        return

    print(f"🌍 Building SEO for {len(langs)} language(s): {', '.join(langs)}")

    urls = []
    today = datetime.now().strftime("%Y-%m-%d")

    for lang in langs:
        folder = os.path.join(DATA_ROOT, lang)
        if not os.path.isdir(folder):
            continue

        out_dir = os.path.join(SITE_ROOT, lang)
        os.makedirs(out_dir, exist_ok=True)

        files = sorted(
            [
                f for f in os.listdir(folder)
                if f.lower().endswith(".txt") and not f.startswith(".")
            ],
            reverse=True,
        )

        # Language landing page
        with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as fp:
            fp.write(build_language_page(lang, files))
        urls.append(f"{BASE_URL}/{lang}/")
        print(f"  📄 {lang}/index.html")

        # Per-joke pages
        for fname in files:
            with open(os.path.join(folder, fname), encoding="utf-8") as fp:
                raw = fp.read()
            joke = strip_meta(raw)
            page_html = build_joke_page(lang, fname, joke, langs)
            out_path = os.path.join(out_dir, fname[:-4] + ".html")
            with open(out_path, "w", encoding="utf-8") as fp:
                fp.write(page_html)
            urls.append(f"{BASE_URL}/{lang}/{fname[:-4]}.html")
            print(f"  📄 {lang}/{fname[:-4]}.html")

    # sitemap.xml
    sm = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for u in urls:
        sm.append(f"  <url><loc>{esc(u)}</loc><lastmod>{today}</lastmod></url>")
    sm.append("</urlset>")
    with open(os.path.join(SITE_ROOT, "sitemap.xml"), "w", encoding="utf-8") as fp:
        fp.write("\n".join(sm))
    print(f"🗺️  sitemap.xml — {len(urls)} URLs")

    # robots.txt
    with open(os.path.join(SITE_ROOT, "robots.txt"), "w", encoding="utf-8") as fp:
        fp.write(f"User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}/sitemap.xml\n")
    print("🤖 robots.txt written")


if __name__ == "__main__":
    main()
