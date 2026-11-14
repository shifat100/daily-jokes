import os
import sys
import re
import json
import html
import shutil
from urllib.parse import quote
from xml.sax.saxutils import escape as xml_escape
from datetime import datetime, timezone
from typing import List, Tuple, Dict, Optional

DATA_ROOT = "data"
SITE_ROOT = "."
LANG_DIR = "lang"
SITEMAP_DIR = "sitemaps"

BASE_URL = "https://shifat100.github.io/daily-jokes".rstrip("/")

# Google Sitemap Limits: max 50,000 URLs and max 50 MB (uncompressed) per sitemap.
# Using 25,000 URLs and 40 MB keeps every child sitemap well within safe bounds.
SITEMAP_MAX_URLS = 25000
SITEMAP_MAX_BYTES = 40 * 1024 * 1024

FAVICON_SVG = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Crect width='32' height='32' rx='8' fill='%230f172a'/%3E"
    "%3Cpath d='M9 18c1.8 3.5 5 5 7 5s5.2-1.5 7-5' stroke='%2338bdf8' stroke-width='2.4' stroke-linecap='round' fill='none'/%3E"
    "%3Ccircle cx='11' cy='12' r='2' fill='%23f8fafc'/%3E"
    "%3Ccircle cx='21' cy='12' r='2' fill='%23f8fafc'/%3E%3C/svg%3E"
)

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

OG_LOCALE_DEFAULTS = {
    "en": "en_US", "bn": "bn_BD", "hi": "hi_IN", "ar": "ar_SA",
    "es": "es_ES", "fr": "fr_FR", "de": "de_DE", "ja": "ja_JP",
    "zh": "zh_CN", "ko": "ko_KR", "ru": "ru_RU", "pt": "pt_BR",
    "it": "it_IT", "nl": "nl_NL", "tr": "tr_TR", "ur": "ur_PK",
    "id": "id_ID", "th": "th_TH", "vi": "vi_VN", "fa": "fa_IR",
    "ta": "ta_IN", "te": "te_IN", "ml": "ml_IN", "kn": "kn_IN",
    "gu": "gu_IN", "mr": "mr_IN", "pa": "pa_IN",
}

RTL_LANGS = {"ar", "fa", "ur", "he", "ps", "sd"}


def display_name(code: str) -> str:
    return LANG_META.get(code, code)


def og_locale_of(code: str) -> str:
    if "-" in code:
        return code.replace("-", "_")
    return OG_LOCALE_DEFAULTS.get(code, code)


def dir_of(code: str) -> str:
    base = code.split("-")[0].lower()
    return "rtl" if base in RTL_LANGS else "ltr"


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def xml_esc(s: str) -> str:
    return xml_escape(s or "", {'"': "&quot;", "'": "&apos;"})


def safe_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def build_url(*parts: str, trailing_slash: bool = False) -> str:
    encoded = [quote(p.strip("/"), safe="") for p in parts if p]
    path = "/".join(encoded)
    url = f"{BASE_URL}/{path}" if path else f"{BASE_URL}/"
    if trailing_slash and not url.endswith("/"):
        url += "/"
    return url


def truncate_words(text: str, max_len: int) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= max_len:
        return clean
    cut = clean[: max_len - 3].rsplit(" ", 1)[0].strip()
    if not cut:
        cut = clean[: max_len - 3].strip()
    return cut + "..."


def extract_valid_date(slug: str) -> Optional[str]:
    m = re.match(r"^(\d{4}-\d{2}-\d{2})(?:$|[-_])", slug)
    if not m:
        return None
    date_str = m.group(1)
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        return None


def mtime_to_iso_date(mtime: float) -> str:
    return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d")


def write_if_changed(path: str, content: str) -> bool:
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fp:
                if fp.read() == content:
                    return False
        except OSError:
            pass
    with open(path, "w", encoding="utf-8") as fp:
        fp.write(content)
    return True


def parse_joke_file(raw_text: str) -> Tuple[str, str]:
    """
    Parses joke text file:
    - Safely strips optional YAML frontmatter (`--- ... ---`) or top meta headers.
    - First non-empty line -> Joke Title
    - Remaining lines -> Full Joke Body
    """
    raw_lines = raw_text.splitlines()
    start = 0
    fm_title = ""

    if raw_lines and raw_lines[0].strip() == "---":
        for i in range(1, min(len(raw_lines), 30)):
            line = raw_lines[i].strip()
            if line == "---":
                start = i + 1
                break
            m_title = re.match(r"^title\s*:\s*(.+)$", line, re.I)
            if m_title:
                fm_title = m_title.group(1).strip().strip("\"'")
    else:
        for i, line in enumerate(raw_lines[:12]):
            l = line.strip()
            if re.match(r"^(language|date|category|author|source)\s*:", l, re.I):
                start = i + 1
            else:
                break

    lines = raw_lines[start:]

    if fm_title:
        body = "\n".join(lines).strip()
        if not body:
            return ("", fm_title)
        return (fm_title, body)

    first_idx = next((i for i, line in enumerate(lines) if line.strip()), None)
    if first_idx is None:
        return ("", "")

    title = lines[first_idx].strip()
    title = re.sub(r"^title\s*:\s*", "", title, flags=re.I).strip()
    body = "\n".join(lines[first_idx + 1:]).strip()

    if not body:
        return ("", title)

    return (title, body)


# -----------------------------------------------------------------
# Static SEO Joke Page Builder
# -----------------------------------------------------------------
def build_joke_page(lang: str, slug: str, title: str, body: str) -> str:
    name = display_name(lang)
    text_dir = dir_of(lang)
    locale = og_locale_of(lang)

    url = build_url(LANG_DIR, lang, f"{slug}.html")
    lang_hub_url = build_url(LANG_DIR, lang, trailing_slash=True)
    home_url = build_url()

    clean_title = truncate_words(title, 90) if title else truncate_words(body, 60)
    page_title = f"{clean_title} — {name} Joke | Daily Jokes"

    meta_source = f"{title}: {body}" if title else body
    meta_desc = truncate_words(meta_source, 155)

    hreflang_block = f'  <link rel="alternate" hreflang="{esc(lang)}" href="{esc(url)}" />'

    article_node: Dict = {
        "@type": "SocialMediaPosting",
        "@id": f"{url}#article",
        "headline": truncate_words(clean_title, 110),
        "articleBody": f"{title}\n\n{body}" if title else body,
        "inLanguage": lang,
        "genre": "Comedy",
        "url": url,
        "author": {
            "@type": "Organization",
            "name": "Daily Jokes",
            "url": home_url,
        },
        "publisher": {
            "@type": "Organization",
            "name": "Daily Jokes",
            "url": home_url,
        },
    }

    pub_date = extract_valid_date(slug)
    if pub_date:
        article_node["datePublished"] = pub_date

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": home_url},
                    {"@type": "ListItem", "position": 2, "name": f"{name} Jokes", "item": lang_hub_url},
                    {"@type": "ListItem", "position": 3, "name": clean_title, "item": url},
                ],
            },
            article_node,
        ],
    }

    schema_json = safe_json(schema_graph)
    more_url = f"{home_url}?lang={quote(lang, safe='')}"

    return f"""<!DOCTYPE html>
<html lang="{esc(lang)}" dir="{text_dir}">
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
  <meta property="og:locale" content="{esc(locale)}" />
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
      --shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
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
      <a href="{esc(home_url)}">Home</a> <span>›</span>
      <a href="{esc(lang_hub_url)}">{esc(name)} Jokes</a> <span>›</span>
      <span aria-current="page">{esc(clean_title)}</span>
    </nav>
    <div class="lang-badge">{esc(name)}</div>
    {f'<h1 class="joke-title">{esc(title)}</h1>' if title else ''}
    <article class="joke-body" id="jokeBody">{esc(body)}</article>
    <div class="actions-bar">
      <div style="display:flex; gap:.5rem;">
        <button class="btn btn-outline" id="copyBtn" type="button">Copy Joke</button>
        <button class="btn btn-outline" id="shareBtn" type="button">Share</button>
      </div>
      <a href="{esc(more_url)}" class="btn btn-primary">More {esc(name)} Jokes →</a>
    </div>
  </main>
  <div class="toast" id="toast" role="status" aria-live="polite">Copied to clipboard!</div>

  <script>
    const jokeTitle = {safe_json(title)};
    const jokeBody = {safe_json(body)};
    const fullJoke = jokeTitle ? `${{jokeTitle}}\\n\\n${{jokeBody}}` : jokeBody;
    const toast = document.getElementById("toast");
    let toastTimer = null;

    function showToast(msg) {{
      toast.textContent = msg;
      toast.classList.add("show");
      if (toastTimer) clearTimeout(toastTimer);
      toastTimer = setTimeout(() => toast.classList.remove("show"), 2000);
    }}

    function copyText(text, successMsg) {{
      if (navigator.clipboard && window.isSecureContext) {{
        navigator.clipboard.writeText(text)
          .then(() => showToast(successMsg))
          .catch(() => fallbackCopy(text, successMsg));
      }} else {{
        fallbackCopy(text, successMsg);
      }}
    }}

    function fallbackCopy(text, successMsg) {{
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try {{
        document.execCommand("copy");
        showToast(successMsg);
      }} catch (e) {{
        showToast("Copy failed!");
      }}
      document.body.removeChild(ta);
    }}

    document.getElementById("copyBtn").onclick = () => {{
      copyText(fullJoke, "Joke copied to clipboard!");
    }};

    document.getElementById("shareBtn").onclick = () => {{
      if (navigator.share) {{
        navigator.share({{
          title: document.title,
          text: fullJoke,
          url: window.location.href
        }}).catch(() => {{}});
      }} else {{
        copyText(window.location.href, "Direct link copied!");
      }}
    }};
  </script>
</body>
</html>"""


# -----------------------------------------------------------------
# Static SEO Language Hub Builder
# -----------------------------------------------------------------
def build_language_page(lang: str, files_meta: List[Dict], all_langs: List[str]) -> str:
    name = display_name(lang)
    text_dir = dir_of(lang)
    locale = og_locale_of(lang)

    home_url = build_url()
    lang_hub_url = build_url(LANG_DIR, lang, trailing_slash=True)
    page_title = f"{name} Jokes — Daily Clean Humor Collection"
    meta_desc = f"Discover the funniest {name} jokes and humor quotes. Clean, daily-updated bite-sized comedy archive."

    hl_lines = []
    for l in all_langs:
        hub = build_url(LANG_DIR, l, trailing_slash=True)
        hl_lines.append(f'  <link rel="alternate" hreflang="{esc(l)}" href="{esc(hub)}" />')
    xdef = "en" if "en" in all_langs else (all_langs[0] if all_langs else lang)
    xdef_hub = build_url(LANG_DIR, xdef, trailing_slash=True)
    hl_lines.append(f'  <link rel="alternate" hreflang="x-default" href="{esc(xdef_hub)}" />')
    hreflang_block = "\n".join(hl_lines)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": home_url},
                    {"@type": "ListItem", "position": 2, "name": f"{name} Jokes", "item": lang_hub_url},
                ],
            },
            {
                "@type": "CollectionPage",
                "name": f"{name} Jokes",
                "description": meta_desc,
                "url": lang_hub_url,
                "inLanguage": lang,
            },
        ],
    }
    schema_json = safe_json(schema_graph)

    cards = []
    for item in files_meta:
        card_title = item["title"] if item["title"] else truncate_words(item["body"], 70)
        card_url = build_url(LANG_DIR, lang, f"{item['slug']}.html")
        snippet = truncate_words(item["body"], 130)
        cards.append(f"""      <li class="card">
        <h2><a href="{esc(card_url)}">{esc(card_title)}</a></h2>
        <p>{esc(snippet)}</p>
        <a class="read-more" href="{esc(card_url)}">Read full joke →</a>
      </li>""")

    if cards:
        list_html = '<ul class="joke-list">\n' + "\n".join(cards) + "\n    </ul>"
    else:
        list_html = '<p class="empty">No jokes found.</p>'

    return f"""<!DOCTYPE html>
<html lang="{esc(lang)}" dir="{text_dir}">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{esc(page_title)}</title>
  <meta name="description" content="{esc(meta_desc)}" />
  <link rel="canonical" href="{esc(lang_hub_url)}" />
  <link rel="icon" type="image/svg+xml" href="{FAVICON_SVG}" />
{hreflang_block}
  <!-- Open Graph / Facebook -->
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="Daily Jokes" />
  <meta property="og:title" content="{esc(page_title)}" />
  <meta property="og:description" content="{esc(meta_desc)}" />
  <meta property="og:url" content="{esc(lang_hub_url)}" />
  <meta property="og:locale" content="{esc(locale)}" />
  <!-- Twitter Cards -->
  <meta name="twitter:card" content="summary" />
  <meta name="twitter:title" content="{esc(page_title)}" />
  <meta name="twitter:description" content="{esc(meta_desc)}" />

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script type="application/ld+json">{schema_json}</script>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #f8fafc; color: #0f172a; padding: 2rem 1rem;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }}
    .wrap {{ max-width: 760px; margin: 0 auto; }}
    .back-link {{
      color: #2563eb; text-decoration: none; font-size: .875rem; font-weight: 600;
      display: inline-block; margin-bottom: 1.25rem;
    }}
    .back-link:hover {{ text-decoration: underline; }}
    header {{ margin-bottom: 2rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 1.5rem; }}
    h1 {{ font-size: 1.85rem; font-weight: 700; margin-bottom: .4rem; }}
    .subtitle {{ color: #64748b; font-size: .95rem; }}
    .joke-list {{ list-style: none; padding: 0; }}
    .card {{
      margin-bottom: 1rem; background: #ffffff; border: 1px solid #e2e8f0;
      padding: 1.25rem; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }}
    .card h2 {{ font-size: 1.15rem; margin-bottom: .4rem; line-height: 1.4; }}
    .card h2 a {{ color: #0f172a; text-decoration: none; font-weight: 600; }}
    .card h2 a:hover {{ color: #2563eb; }}
    .card p {{ color: #64748b; font-size: .9rem; line-height: 1.5; }}
    .read-more {{
      display: inline-block; margin-top: .6rem; color: #2563eb;
      font-size: .85rem; text-decoration: none; font-weight: 600;
    }}
    .read-more:hover {{ text-decoration: underline; }}
    .empty {{ color: #64748b; padding: 1rem 0; }}
  </style>
</head>
<body>
  <div class="wrap">
    <a class="back-link" href="{esc(home_url)}">← Back to Infinite Humor Feed</a>
    <header>
      <h1>{esc(name)} Jokes</h1>
      <p class="subtitle">Browse our complete collection of bite-sized, clean {esc(name)} jokes ({len(files_meta)}).</p>
    </header>
    {list_html}
  </div>
</body>
</html>"""


# -----------------------------------------------------------------
# Sitemap & Sitemap Index Builders (Sitemaps 0.9 Standard)
# -----------------------------------------------------------------
def build_sitemap_chunks(
    entries: List[Tuple[str, str]],
    prefix: str,
    single_without_number: bool = False,
) -> List[Tuple[str, str, str]]:
    """
    Splits URLs into multiple XML sitemaps respecting both SITEMAP_MAX_URLS
    and SITEMAP_MAX_BYTES limits.
    Returns list of (filename, xml_content, max_lastmod).
    """
    if not entries:
        return []

    header = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    footer = "</urlset>\n"
    header_bytes = len(header.encode("utf-8"))
    footer_bytes = len(footer.encode("utf-8"))

    chunks: List[Tuple[List[str], str]] = []
    cur_blocks: List[str] = []
    cur_bytes = header_bytes
    cur_dates: List[str] = []

    for loc, lastmod in entries:
        block = (
            "  <url>\n"
            f"    <loc>{xml_esc(loc)}</loc>\n"
            f"    <lastmod>{xml_esc(lastmod)}</lastmod>\n"
            "  </url>\n"
        )
        block_bytes = len(block.encode("utf-8"))

        if cur_blocks and (
            len(cur_blocks) >= SITEMAP_MAX_URLS
            or (cur_bytes + block_bytes + footer_bytes) > SITEMAP_MAX_BYTES
        ):
            chunks.append((cur_blocks, max(cur_dates)))
            cur_blocks = []
            cur_bytes = header_bytes
            cur_dates = []

        cur_blocks.append(block)
        cur_bytes += block_bytes
        cur_dates.append(lastmod)

    if cur_blocks:
        chunks.append((cur_blocks, max(cur_dates)))

    results: List[Tuple[str, str, str]] = []
    total = len(chunks)
    for idx, (blocks, max_lastmod) in enumerate(chunks, start=1):
        if single_without_number and total == 1:
            fname = f"{prefix}.xml"
        else:
            fname = f"{prefix}-{idx}.xml"
        xml_content = header + "".join(blocks) + footer
        results.append((fname, xml_content, max_lastmod))

    return results


def build_sitemap_index_xml(index_entries: List[Tuple[str, str]]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc, lastmod in index_entries:
        lines.append("  <sitemap>")
        lines.append(f"    <loc>{xml_esc(loc)}</loc>")
        lines.append(f"    <lastmod>{xml_esc(lastmod)}</lastmod>")
        lines.append("  </sitemap>")
    lines.append("</sitemapindex>\n")
    return "\n".join(lines)


# -----------------------------------------------------------------
# Main
# -----------------------------------------------------------------
def main():
    force_rebuild = "--force" in sys.argv[1:]
    try:
        script_mtime = os.path.getmtime(__file__)
    except OSError:
        script_mtime = 0.0

    os.makedirs(DATA_ROOT, exist_ok=True)
    langs_json = os.path.join(DATA_ROOT, "languages.json")

    prev_langs: List[str] = []
    prev_counts: Dict[str, int] = {}
    if os.path.exists(langs_json):
        try:
            with open(langs_json, encoding="utf-8") as fp:
                prev_data = json.load(fp)
            prev_langs = [x["code"] for x in prev_data.get("languages", [])]
            prev_counts = {x["code"]: x.get("count") for x in prev_data.get("languages", [])}
        except (OSError, json.JSONDecodeError):
            prev_langs = []
            prev_counts = {}

    # Fast scan using os.scandir() for large (200k+) file sets
    languages: List[Dict] = []
    lang_files_map: Dict[str, List[Tuple[str, float]]] = {}

    with os.scandir(DATA_ROOT) as it:
        dir_entries = sorted(
            [e for e in it if e.is_dir() and not e.name.startswith(".")],
            key=lambda e: e.name,
        )

    for dir_entry in dir_entries:
        lang_code = dir_entry.name
        txt_items: List[Tuple[str, float]] = []
        with os.scandir(dir_entry.path) as f_it:
            for fe in f_it:
                if fe.name.lower().endswith(".txt") and not fe.name.startswith(".") and fe.is_file():
                    st = fe.stat()
                    if st.st_size > 0:
                        txt_items.append((fe.name, st.st_mtime))

        if txt_items:
            # Newest/highest filename first for the hub page
            txt_items.sort(key=lambda x: x[0], reverse=True)
            languages.append({"code": lang_code, "count": len(txt_items)})
            lang_files_map[lang_code] = txt_items

    langs = [x["code"] for x in languages]
    langs_changed = (langs != prev_langs)
    current_counts = {x["code"]: x["count"] for x in languages}

    if languages and (not os.path.exists(langs_json) or current_counts != prev_counts):
        with open(langs_json, "w", encoding="utf-8") as fp:
            json.dump(
                {"languages": languages, "updated": datetime.now(timezone.utc).isoformat()},
                fp,
                ensure_ascii=False,
                indent=2,
            )
        print("🔄 Updated data/languages.json")

    # Remove stale language folders whose data directory was removed/emptied
    lang_root = os.path.join(SITE_ROOT, LANG_DIR)
    removed_dirs = 0
    if os.path.isdir(lang_root):
        with os.scandir(lang_root) as it:
            for entry in it:
                if entry.is_dir() and entry.name not in lang_files_map:
                    shutil.rmtree(entry.path)
                    removed_dirs += 1
                    print(f"🗑️  Removed stale language folder: {LANG_DIR}/{entry.name}/")

    if not langs:
        print("⚠️ No non-empty joke files found in data/. Nothing to build.")
        return

    print(f"🌍 Incremental SEO build for {len(langs)} language(s): {', '.join(langs)}")

    built_pages = 0
    skipped_pages = 0
    removed_pages = 0
    rebuilt_hubs = 0

    all_dates: List[str] = []
    hub_sitemap_entries: List[Tuple[str, str]] = []
    sitemap_dir_path = os.path.join(SITE_ROOT, SITEMAP_DIR)
    os.makedirs(sitemap_dir_path, exist_ok=True)

    generated_sitemaps: Dict[str, Tuple[str, str]] = {}
    today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for lang in langs:
        folder = os.path.join(DATA_ROOT, lang)
        out_dir = os.path.join(lang_root, lang)
        os.makedirs(out_dir, exist_ok=True)

        files = lang_files_map[lang]  # (fname, txt_mtime), descending

        # 1. Remove orphaned .html files whose .txt source was deleted
        expected_html = {f"{os.path.splitext(fname)[0]}.html" for fname, _ in files}
        expected_html.add("index.html")
        lang_removed = 0
        with os.scandir(out_dir) as out_it:
            for existing in out_it:
                if existing.name.endswith(".html") and existing.name not in expected_html and existing.is_file():
                    os.remove(existing.path)
                    removed_pages += 1
                    lang_removed += 1
                    if lang_removed <= 20:
                        print(f"  🗑️  Removed stale page: {LANG_DIR}/{lang}/{existing.name}")
        if lang_removed > 20:
            print(f"  🗑️  ...and {lang_removed - 20} more stale page(s) removed in {lang}")

        # 2. Detect existing HTML timestamps
        existing_html_mtime: Dict[str, float] = {}
        with os.scandir(out_dir) as out_it:
            for entry in out_it:
                if entry.name.endswith(".html") and entry.is_file():
                    existing_html_mtime[entry.name] = entry.stat().st_mtime

        file_infos = []
        any_joke_rebuilt = False

        for fname, txt_mtime in files:
            slug = os.path.splitext(fname)[0]
            html_name = f"{slug}.html"
            txt_path = os.path.join(folder, fname)
            out_path = os.path.join(out_dir, html_name)

            if force_rebuild or html_name not in existing_html_mtime:
                needs_page = True
            else:
                needs_page = max(txt_mtime, script_mtime) > existing_html_mtime[html_name]

            if needs_page:
                any_joke_rebuilt = True

            file_infos.append((fname, slug, txt_path, out_path, txt_mtime, needs_page))

        hub_path = os.path.join(out_dir, "index.html")
        if force_rebuild or langs_changed or any_joke_rebuilt or lang_removed > 0 or "index.html" not in existing_html_mtime:
            hub_needs_rebuild = True
        else:
            hub_needs_rebuild = script_mtime > existing_html_mtime["index.html"]

        files_meta: List[Dict] = []
        lang_dates: List[str] = []
        lang_joke_sitemap_entries_desc: List[Tuple[str, str]] = []
        lang_built = 0

        # 3. Build only missing/updated joke pages
        for fname, slug, txt_path, out_path, txt_mtime, needs_page in file_infos:
            lastmod = mtime_to_iso_date(txt_mtime)
            lang_dates.append(lastmod)
            all_dates.append(lastmod)

            joke_url = build_url(LANG_DIR, lang, f"{slug}.html")
            lang_joke_sitemap_entries_desc.append((joke_url, lastmod))

            if needs_page or hub_needs_rebuild:
                with open(txt_path, encoding="utf-8-sig") as fp:
                    raw = fp.read()
                title, body = parse_joke_file(raw)

                if not title and not body:
                    continue

                if hub_needs_rebuild:
                    files_meta.append({"slug": slug, "title": title, "body": body})

                if needs_page:
                    page_html = build_joke_page(lang, slug, title, body)
                    with open(out_path, "w", encoding="utf-8") as fp:
                        fp.write(page_html)
                    built_pages += 1
                    lang_built += 1
                    if lang_built <= 20:
                        print(f"  📄 Built: {LANG_DIR}/{lang}/{slug}.html")
                else:
                    skipped_pages += 1
            else:
                skipped_pages += 1

        if lang_built > 20:
            print(f"  📄 ...and {lang_built - 20} more page(s) built in {lang}")

        # 4. Build language hub page if needed
        if hub_needs_rebuild:
            hub_html = build_language_page(lang, files_meta, langs)
            with open(hub_path, "w", encoding="utf-8") as fp:
                fp.write(hub_html)
            rebuilt_hubs += 1
            print(f"  📄 Hub rebuilt: {LANG_DIR}/{lang}/index.html")

        hub_lastmod = max(lang_dates) if lang_dates else today_utc
        hub_sitemap_entries.append((build_url(LANG_DIR, lang, trailing_slash=True), hub_lastmod))

        # Reverse to ascending order so new jokes only modify the LAST chunk of this language
        lang_joke_entries_asc = list(reversed(lang_joke_sitemap_entries_desc))
        for sm_fname, sm_xml, sm_lastmod in build_sitemap_chunks(
            lang_joke_entries_asc, prefix=f"sitemap-{lang}"
        ):
            generated_sitemaps[sm_fname] = (sm_xml, sm_lastmod)

    # 5. Build Hub Sitemap (Root + all Language Hubs)
    root_lastmod = max(all_dates) if all_dates else today_utc
    hub_entries = [(build_url(), root_lastmod)] + hub_sitemap_entries
    for sm_fname, sm_xml, sm_lastmod in build_sitemap_chunks(
        hub_entries, prefix="sitemap-hubs", single_without_number=True
    ):
        generated_sitemaps[sm_fname] = (sm_xml, sm_lastmod)

    # 6. Write updated child sitemaps & clean up obsolete ones inside sitemaps/
    with os.scandir(sitemap_dir_path) as sm_it:
        for existing_sm in sm_it:
            if (
                existing_sm.name.endswith(".xml")
                and existing_sm.name not in generated_sitemaps
                and existing_sm.is_file()
            ):
                os.remove(existing_sm.path)
                print(f"🗑️  Removed obsolete child sitemap: {SITEMAP_DIR}/{existing_sm.name}")

    updated_sitemaps = 0
    index_entries: List[Tuple[str, str]] = []

    # Put hub sitemap first, then language sitemaps in sorted order
    ordered_sm_names = sorted(
        generated_sitemaps.keys(),
        key=lambda n: (0 if n.startswith("sitemap-hubs") else 1, n),
    )

    for sm_fname in ordered_sm_names:
        sm_xml, sm_lastmod = generated_sitemaps[sm_fname]
        sm_path = os.path.join(sitemap_dir_path, sm_fname)
        if write_if_changed(sm_path, sm_xml):
            updated_sitemaps += 1
        index_entries.append((build_url(SITEMAP_DIR, sm_fname), sm_lastmod))

    # 7. Write root Sitemap Index (sitemap.xml)
    sitemap_index_xml = build_sitemap_index_xml(index_entries)
    sitemap_index_path = os.path.join(SITE_ROOT, "sitemap.xml")
    index_updated = write_if_changed(sitemap_index_path, sitemap_index_xml)

    total_urls = len(hub_entries) + sum(len(v) for v in lang_files_map.values())
    print(
        f"🗺️  Sitemap Index {'updated' if index_updated else 'unchanged'}: "
        f"{len(index_entries)} child sitemap(s) covering ~{total_urls:,} URLs "
        f"({updated_sitemaps} child sitemap(s) rewritten)"
    )

    # 8. Write robots.txt
    robots_content = f"User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}/sitemap.xml\n"
    robots_path = os.path.join(SITE_ROOT, "robots.txt")
    if write_if_changed(robots_path, robots_content):
        print("🤖 robots.txt updated")

    print(
        f"✅ Done! Built: {built_pages:,} | Skipped (cached): {skipped_pages:,} | "
        f"Hubs rebuilt: {rebuilt_hubs} | Removed: {removed_pages} page(s), {removed_dirs} folder(s)"
    )


if __name__ == "__main__":
    main()
