import os
import json
import html
from datetime import datetime

DATA_ROOT = "data"
SITE_ROOT = "."
# ⬇️ সব ভাষার ফোল্ডার এখন lang/ এর ভেতর তৈরি হবে (যেমন: ./lang/en/, ./lang/bn/)
LANG_DIR = "lang"

# ⬇️ আপনার GitHub Pages URL
BASE_URL = "https://shifat100.github.io/daily-jokes"

# ইনলাইন SVG Favicon
FAVICON_SVG = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%230f172a'/%3E%3Cpath d='M9 18c1.8 3.5 5 5 7 5s5.2-1.5 7-5' stroke='%2338bdf8' stroke-width='2.4' stroke-linecap='round' fill='none'/%3E%3Ccircle cx='11' cy='12' r='2' fill='%23f8fafc'/%3E%3Ccircle cx='21' cy='12' r='2' fill='%23f8fafc'/%3E%3C/svg%3E"

# -----------------------------------------------------------------
# BCP-47 display names
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
    return LANG_META.get(code, code)


def hreflang_of(code: str) -> str:
    return code


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def strip_meta(text: str) -> str:
    """মেটা হেডার রিমুভ করে মূল জোক বের করা"""
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
    
    # URL এখন /lang/ ফোল্ডারের ভেতরে পয়েন্ট করবে
    url = f"{BASE_URL}/{LANG_DIR}/{lang}/{slug}.html"
    lang_hub_url = f"{BASE_URL}/{LANG_DIR}/{lang}/"

    title_short = joke[:70].replace("\n", " ").strip()
    title = f"{title_short} — {name} Joke | Daily Jokes"
    desc = joke[:155].replace("\n", " ").strip()

    # hreflang block
    hl_lines = []
    for l in all_langs:
        hl_lines.append(
            f'  <link rel="alternate" hreflang="{hreflang_of(l)}" href="{BASE_URL}/{LANG_DIR}/{l}/" />'
        )
    xdef = "en" if "en" in all_langs else (all_langs[0] if all_langs else lang)
    hl_lines.append(
        f'  <link rel="alternate" hreflang="x-default" href="{BASE_URL}/{LANG_DIR}/{xdef}/" />'
    )
    hreflang_block = "\n".join(hl_lines)

    ld = {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": title_short,
        "text": joke,
        "inLanguage": lang,
        "genre": "Comedy",
        "url": url,
        "isPartOf": {"@type": "WebSite", "name": "Daily Jokes", "url": f"{BASE_URL}/"},
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
  <link rel="icon" type="image/svg+xml" href="{FAVICON_SVG}" />
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
<body style="background:#f8fafc;color:#0f172a;margin:0;padding:0;">
  <main style="max-width:680px;margin:3rem auto;padding:1.5rem;background:#ffffff;border:1px solid #e2e8f0;border-radius:14px;font-family:Georgia,serif;line-height:1.85;font-size:1.1rem;box-shadow:0 4px 6px rgba(0,0,0,0.03);">
    <nav style="font-size:.85rem;margin-bottom:1.5rem;font-family:sans-serif;color:#64748b;">
      <a href="{BASE_URL}/" style="color:#2563eb;text-decoration:none;">Home</a> ›
      <a href="{lang_hub_url}" style="color:#2563eb;text-decoration:none;">{esc(name)}</a> ›
      <span>{esc(slug)}</span>
    </nav>
    <h1 style="font-size:1.25rem;margin-bottom:1rem;font-family:sans-serif;">{esc(name)} Joke</h1>
    <article style="white-space:pre-wrap;word-break:break-word;">{esc(joke)}</article>
    <p style="margin-top:2.5rem;font-size:.875rem;font-family:sans-serif;">
      <a href="/index.html" style="color:#2563eb;text-decoration:none;font-weight:600;">← Back</a>
    </p>
  </main>
</body>
</html>"""


def build_language_page(lang: str, files: list) -> str:
    name = display_name(lang)
    lang_hub_url = f"{BASE_URL}/{LANG_DIR}/{lang}/"
    links = "\n".join(
        f'      <li style="margin-bottom:.5rem;"><a href="{BASE_URL}/{LANG_DIR}/{lang}/{f[:-4]}.html" style="color:#2563eb;text-decoration:none;">{esc(f[:-4])}</a></li>'
        for f in files
    )
    return f"""<!DOCTYPE html>
<html lang="{esc(lang)}">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(name)} Jokes — Daily Humor Collection</title>
  <meta name="description" content="Read daily {esc(name)} jokes — fresh comedy and humor in {esc(name)}." />
  <link rel="canonical" href="{lang_hub_url}" />
  <link rel="icon" type="image/svg+xml" href="{FAVICON_SVG}" />
</head>
<body style="background:#f8fafc;color:#0f172a;max-width:680px;margin:3rem auto;padding:1.5rem;font-family:system-ui,-apple-system,sans-serif;">
  <p><a href="{BASE_URL}/" style="color:#2563eb;text-decoration:none;font-size:.875rem;">← Back to Home Feed</a></p>
  <h1 style="margin-bottom:1.5rem;">{esc(name)} Jokes</h1>
  <ul style="line-height:1.8;list-style:none;padding:0;">
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
        print("⚠️ data/languages.json missing — scanning data/ directly")
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
        print("⚠️ No language folders found in data/. Nothing to build.")
        return

    print(f"🌍 Building SEO pages inside '{LANG_DIR}/' for {len(langs)} language(s): {', '.join(langs)}")

    urls = []
    today = datetime.now().strftime("%Y-%m-%d")

    # 2. Build files inside lang/<lang>/
    for lang in langs:
        folder = os.path.join(DATA_ROOT, lang)
        if not os.path.isdir(folder):
            continue

        # আউটপুট ফোল্ডার হবে: ./lang/bn/, ./lang/en/ ইত্যাদি
        out_dir = os.path.join(SITE_ROOT, LANG_DIR, lang)
        os.makedirs(out_dir, exist_ok=True)

        files = sorted(
            [
                f for f in os.listdir(folder)
                if f.lower().endswith(".txt") and not f.startswith(".")
            ],
            reverse=True,
        )

        # Language landing page (lang/<lang>/index.html)
        with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as fp:
            fp.write(build_language_page(lang, files))
        urls.append(f"{BASE_URL}/{LANG_DIR}/{lang}/")
        print(f"  📄 {LANG_DIR}/{lang}/index.html")

        # Per-joke pages (lang/<lang>/joke-slug.html)
        for fname in files:
            with open(os.path.join(folder, fname), encoding="utf-8") as fp:
                raw = fp.read()
            joke = strip_meta(raw)
            page_html = build_joke_page(lang, fname, joke, langs)
            out_path = os.path.join(out_dir, fname[:-4] + ".html")
            with open(out_path, "w", encoding="utf-8") as fp:
                fp.write(page_html)
            urls.append(f"{BASE_URL}/{LANG_DIR}/{lang}/{fname[:-4]}.html")
            print(f"  📄 {LANG_DIR}/{lang}/{fname[:-4]}.html")

    # 3. sitemap.xml (রুট ডিরেক্টরিতে থাকবে কিন্তু লিংক থাকবে lang/ এর)
    sm = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        f'  <url><loc>{esc(BASE_URL)}/</loc><lastmod>{today}</lastmod></url>'
    ]
    for u in urls:
        sm.append(f"  <url><loc>{esc(u)}</loc><lastmod>{today}</lastmod></url>")
    sm.append("</urlset>")
    with open(os.path.join(SITE_ROOT, "sitemap.xml"), "w", encoding="utf-8") as fp:
        fp.write("\n".join(sm))
    print(f"🗺️  sitemap.xml created at root with {len(urls) + 1} URLs")

    # 4. robots.txt
    with open(os.path.join(SITE_ROOT, "robots.txt"), "w", encoding="utf-8") as fp:
        fp.write(f"User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}/sitemap.xml\n")
    print("🤖 robots.txt created at root")


if __name__ == "__main__":
    main()
