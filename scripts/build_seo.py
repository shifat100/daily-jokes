import os
import json
import html
import re
from datetime import datetime

DATA_ROOT = "data"
SITE_ROOT = "."
LANG_DIR = "lang"

BASE_URL = "https://shifat100.github.io/daily-jokes"

FAVICON_SVG = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%230f172a'/%3E%3Cpath d='M9 18c1.8 3.5 5 5 7 5s5.2-1.5 7-5' stroke='%2338bdf8' stroke-width='2.4' stroke-linecap='round' fill='none'/%3E%3Ccircle cx='11' cy='12' r='2' fill='%23f8fafc'/%3E%3Ccircle cx='21' cy='12' r='2' fill='%23f8fafc'/%3E%3C/svg%3E"

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
    return html.escape(s or "", quote=True)


def parse_joke_file(raw_text: str) -> tuple[str, str]:
    """
    Parses joke text file:
    Line 0 -> Joke Title
    Remaining lines -> Full Joke Body
    Also handles optional frontmatter headers if present.
    """
    raw_lines = raw_text.splitlines()
    start = 0

    # Skip frontmatter/meta headers if present
    for i, line in enumerate(raw_lines[:12]):
        l = line.strip()
        if (
            l.startswith("---")
            or re.match(r"^(language|date|category|author|source)\s*:", l, re.I)
        ):
            start = i + 1
        else:
            break

    lines = raw_lines[start:]
    
    # Locate first non-empty line as title
    first_idx = next((i for i, line in enumerate(lines) if line.strip()), None)
    if first_idx is None:
        return ("", raw_text.strip())

    title = lines[first_idx].strip()
    title = re.sub(r"^title\s*:\s*", "", title, flags=re.I).strip()

    body = "\n".join(lines[first_idx + 1:]).strip()

    # Fallback if text is only a single line
    if not body:
        return ("", title)

    return (title, body)


# -----------------------------------------------------------------
# Static SEO Joke Page Builder
# -----------------------------------------------------------------
def build_joke_page(lang: str, fname: str, title: str, body: str, all_langs: list) -> str:
    name = display_name(lang)
    slug = fname[:-4]
    
    url = f"{BASE_URL}/{LANG_DIR}/{lang}/{slug}.html"
    lang_hub_url = f"{BASE_URL}/{LANG_DIR}/{lang}/"

    # Clean display title and SEO meta descriptions
    clean_title = title if title else body[:60].replace("\n", " ").strip()
    page_title = f"{clean_title} — {name} Joke | Daily Jokes"
    
    meta_desc_source = f"{clean_title}: {body}" if title else body
    meta_desc = meta_desc_source.replace("\n", " ").strip()
    if len(meta_desc) > 155:
        meta_desc = meta_desc[:152] + "..."

    # Alternate hreflang tags
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

    # Schema.org structured data (Article + Breadcrumb)
    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{BASE_URL}/"},
                    {"@type": "ListItem", "position": 2, "name": f"{name} Jokes", "item": lang_hub_url},
                    {"@type": "ListItem", "position": 3, "name": clean_title, "item": url}
                ]
            },
            {
                "@type": "SocialMediaPosting",
                "@id": f"{url}#article",
                "headline": clean_title,
                "articleBody": f"{title}\n\n{body}" if title else body,
                "inLanguage": lang,
                "genre": "Comedy",
                "url": url,
                "publisher": {
                    "@type": "Organization",
                    "name": "Daily Jokes",
                    "url": f"{BASE_URL}/"
                }
            }
        ]
    }

    if len(slug) >= 10 and slug[4] == "-" and slug[7] == "-":
        pub_date = slug[:10]
        schema_graph["@graph"][1]["datePublished"] = pub_date

    schema_json = json.dumps(schema_graph, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="{esc(lang)}">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(page_title)}</title>
  <meta name="description" content="{esc(meta_desc)}" />
  <link rel="canonical" href="{esc(url)}" />
  <link rel="icon" type="image/svg+xml" href="{FAVICON_SVG}" />
{hreflang_block}
  <!-- Open Graph / Facebook -->
  <meta property="og:type" content="article" />
  <meta property="og:site_name" content="Daily Jokes" />
  <meta property="og:title" content="{esc(page_title)}" />
  <meta property="og:description" content="{esc(meta_desc)}" />
  <meta property="og:url" content="{esc(url)}" />
  <meta property="og:locale" content="{esc(lang.replace('-', '_'))}" />
  <!-- Twitter Cards -->
  <meta name="twitter:card" content="summary" />
  <meta name="twitter:title" content="{esc(page_title)}" />
  <meta name="twitter:description" content="{esc(meta_desc)}" />
  
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Lora:ital,wght@0,400;0,500;1,400&display=swap" rel="stylesheet">
  
  <script type="application/ld+json">{schema_json}</script>

  <style>
    :root {{
      --bg: #f8fafc; --surface: #ffffff; --border: #e2e8f0;
      --text: #0f172a; --text-muted: #64748b; --accent: #2563eb;
      --accent-bg: #eff6ff; --shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: var(--bg); color: var(--text); line-height: 1.6;
      min-height: 100vh; display: flex; flex-direction: column; padding: 1.5rem 1rem;
    }}
    .container {{
      max-width: 680px; width: 100%; margin: 2rem auto;
      background: var(--surface); border: 1px solid var(--border);
      border-radius: 16px; padding: 2rem; box-shadow: var(--shadow);
    }}
    .breadcrumbs {{
      font-size: .85rem; margin-bottom: 1.5rem; color: var(--text-muted);
      display: flex; align-items: center; gap: .4rem; flex-wrap: wrap;
    }}
    .breadcrumbs a {{ color: var(--accent); text-decoration: none; font-weight: 500; }}
    .breadcrumbs a:hover {{ text-decoration: underline; }}
    .lang-badge {{
      display: inline-block; font-size: .75rem; font-weight: 700;
      text-transform: uppercase; letter-spacing: .05em; background: var(--bg);
      color: var(--text-muted); border: 1px solid var(--border);
      padding: .25rem .55rem; border-radius: 6px; margin-bottom: 1rem;
    }}
    .joke-title {{
      font-size: 1.45rem; font-weight: 700; color: var(--text);
      line-height: 1.35; margin-bottom: 1.25rem; word-break: break-word;
    }}
    .joke-body {{
      font-family: 'Lora', Georgia, serif; font-size: 1.18rem;
      line-height: 1.85; color: #334155; white-space: pre-wrap;
      word-break: break-word; margin-bottom: 2rem;
    }}
    .actions-bar {{
      display: flex; gap: .75rem; border-top: 1px solid var(--border);
      padding-top: 1.5rem; flex-wrap: wrap; align-items: center; justify-content: space-between;
    }}
    .btn {{
      padding: .5rem 1rem; border-radius: 8px; font-size: .875rem;
      font-weight: 600; cursor: pointer; text-decoration: none;
      display: inline-flex; align-items: center; gap: .4rem; transition: all .15s;
    }}
    .btn-primary {{ background: var(--accent); color: #fff; border: 1px solid var(--accent); }}
    .btn-primary:hover {{ opacity: .9; }}
    .btn-outline {{ background: var(--surface); color: var(--text); border: 1px solid var(--border); }}
    .btn-outline:hover {{ background: var(--bg); }}
    .toast {{
      position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%) translateY(30px);
      background: var(--text); color: var(--surface); padding: .55rem 1.15rem;
      border-radius: 999px; font-size: .8rem; font-weight: 500; opacity: 0;
      transition: all .25s ease; pointer-events: none; z-index: 100;
    }}
    .toast.show {{ opacity: 1; transform: translateX(-50%) translateY(0); }}
  </style>
</head>
<body>
  <main class="container">
    <nav class="breadcrumbs" aria-label="Breadcrumb">
      <a href="{BASE_URL}/">Home</a> <span>›</span>
      <a href="{lang_hub_url}">{esc(name)} Jokes</a> <span>›</span>
      <span aria-current="page">{esc(clean_title)}</span>
    </nav>
    <div class="lang-badge">{esc(name)}</div>
    {f'<h1 class="joke-title">{esc(title)}</h1>' if title else ''}
    <article class="joke-body" id="jokeBody">{esc(body)}</article>
    <div class="actions-bar">
      <div style="display:flex; gap:.5rem;">
        <button class="btn btn-outline" id="copyBtn">Copy Joke</button>
        <button class="btn btn-outline" id="shareBtn">Share</button>
      </div>
      <a href="{BASE_URL}/?lang={esc(lang)}" class="btn btn-primary">More {esc(name)} Jokes →</a>
    </div>
  </main>
  <div class="toast" id="toast">Copied to clipboard!</div>

  <script>
    const jokeTitle = {json.dumps(title)};
    const jokeBody = {json.dumps(body)};
    const fullJoke = jokeTitle ? `${{jokeTitle}}\\n\\n${{jokeBody}}` : jokeBody;
    const toast = document.getElementById("toast");

    function showToast(msg) {{
      toast.textContent = msg;
      toast.classList.add("show");
      setTimeout(() => toast.classList.remove("show"), 2000);
    }}

    document.getElementById("copyBtn").onclick = () => {{
      navigator.clipboard.writeText(fullJoke).then(() => showToast("Joke copied to clipboard!"));
    }};

    document.getElementById("shareBtn").onclick = () => {{
      if (navigator.share) {{
        navigator.share({{
          title: document.title,
          text: fullJoke,
          url: window.location.href
        }}).catch(() => {{}});
      }} else {{
        navigator.clipboard.writeText(window.location.href).then(() => showToast("Direct link copied!"));
      }}
    }};
  </script>
</body>
</html>"""


# -----------------------------------------------------------------
# Static SEO Language Hub Builder
# -----------------------------------------------------------------
def build_language_page(lang: str, files_meta: list) -> str:
    name = display_name(lang)
    lang_hub_url = f"{BASE_URL}/{LANG_DIR}/{lang}/"
    
    cards = []
    for item in files_meta:
        card_title = item["title"] if item["title"] else item["slug"]
        card_url = f"{BASE_URL}/{LANG_DIR}/{lang}/{item['slug']}.html"
        snippet = item["body"][:120].replace("\n", " ").strip() + "..."
        cards.append(f"""
        <li style="margin-bottom:1rem;background:#ffffff;border:1px solid #e2e8f0;padding:1.25rem;border-radius:12px;box-shadow:0 2px 4px rgba(0,0,0,0.02);">
          <h2 style="font-size:1.15rem;margin-bottom:.4rem;line-height:1.4;">
            <a href="{card_url}" style="color:#0f172a;text-decoration:none;font-weight:600;">{esc(card_title)}</a>
          </h2>
          <p style="color:#64748b;font-size:.9rem;line-height:1.5;">{esc(snippet)}</p>
          <a href="{card_url}" style="display:inline-block;margin-top:.6rem;color:#2563eb;font-size:.85rem;text-decoration:none;font-weight:600;">Read full joke →</a>
        </li>
        """)

    cards_html = "\n".join(cards) if cards else "<p>No jokes found.</p>"

    return f"""<!DOCTYPE html>
<html lang="{esc(lang)}">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(name)} Jokes — Daily Clean Humor Collection</title>
  <meta name="description" content="Discover funniest {esc(name)} jokes and humor quotes. Clean, daily-updated bite-sized comedy archive." />
  <link rel="canonical" href="{lang_hub_url}" />
  <link rel="icon" type="image/svg+xml" href="{FAVICON_SVG}" />
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body style="background:#f8fafc;color:#0f172a;margin:0;padding:2rem 1rem;font-family:'Inter',sans-serif;">
  <div style="max-width:760px;margin:0 auto;">
    <p style="margin-bottom:1.25rem;">
      <a href="{BASE_URL}/" style="color:#2563eb;text-decoration:none;font-size:.875rem;font-weight:600;">← Back to Infinite Humor Feed</a>
    </p>
    <header style="margin-bottom:2rem;border-bottom:1px solid #e2e8f0;padding-bottom:1.5rem;">
      <h1 style="font-size:1.85rem;font-weight:700;margin-bottom:.4rem;">{esc(name)} Jokes</h1>
      <p style="color:#64748b;font-size:.95rem;">Browse our complete collection of bite-sized, clean {esc(name)} jokes.</p>
    </header>
    <ul style="list-style:none;padding:0;">
{cards_html}
    </ul>
  </div>
</body>
</html>"""


# -----------------------------------------------------------------
# Main
# -----------------------------------------------------------------
def main():
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

    for lang in langs:
        folder = os.path.join(DATA_ROOT, lang)
        if not os.path.isdir(folder):
            continue

        out_dir = os.path.join(SITE_ROOT, LANG_DIR, lang)
        os.makedirs(out_dir, exist_ok=True)

        files = sorted(
            [
                f for f in os.listdir(folder)
                if f.lower().endswith(".txt") and not f.startswith(".")
            ],
            reverse=True,
        )

        files_meta = []

        # 1. Generate Individual Joke HTML Pages
        for fname in files:
            with open(os.path.join(folder, fname), encoding="utf-8") as fp:
                raw = fp.read()
            title, body = parse_joke_file(raw)
            slug = fname[:-4]
            files_meta.append({"slug": slug, "title": title, "body": body})

            page_html = build_joke_page(lang, fname, title, body, langs)
            out_path = os.path.join(out_dir, f"{slug}.html")
            with open(out_path, "w", encoding="utf-8") as fp:
                fp.write(page_html)
            urls.append(f"{BASE_URL}/{LANG_DIR}/{lang}/{slug}.html")
            print(f"  📄 {LANG_DIR}/{lang}/{slug}.html")

        # 2. Generate Language Hub Index Page
        with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as fp:
            fp.write(build_language_page(lang, files_meta))
        urls.append(f"{BASE_URL}/{LANG_DIR}/{lang}/")
        print(f"  📄 {LANG_DIR}/{lang}/index.html")

    # 3. sitemap.xml
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
