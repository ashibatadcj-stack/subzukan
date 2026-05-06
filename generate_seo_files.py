"""sitemap.xml と robots.txt を生成（サブスク図鑑）"""
import os
from pathlib import Path
from datetime import date

from dotenv import load_dotenv

from articles_data import ARTICLES
from vods_data import VODS

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")
DOCS_DIR = BASE_DIR / "docs"
SITE_URL = os.environ.get("SITE_URL", "https://subzukan.com").rstrip("/")
TODAY = date.today().isoformat()


def generate_sitemap():
    urls = [
        f"""  <url>
    <loc>{SITE_URL}/</loc>
    <lastmod>{TODAY}</lastmod>
    <priority>1.0</priority>
    <changefreq>weekly</changefreq>
  </url>"""
    ]

    for vod in VODS:
        urls.append(f"""  <url>
    <loc>{SITE_URL}/services/{vod['id']}.html</loc>
    <lastmod>{TODAY}</lastmod>
    <priority>0.8</priority>
    <changefreq>monthly</changefreq>
  </url>""")

    for article in ARTICLES:
        urls.append(f"""  <url>
    <loc>{SITE_URL}/articles/{article['slug']}.html</loc>
    <lastmod>{TODAY}</lastmod>
    <priority>0.8</priority>
    <changefreq>monthly</changefreq>
  </url>""")

    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += "\n".join(urls)
    sitemap += "\n</urlset>"

    (DOCS_DIR / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    print("  -> docs/sitemap.xml を生成")


def generate_robots():
    robots = f"""User-agent: *
Allow: /

Sitemap: {SITE_URL}/sitemap.xml
"""
    (DOCS_DIR / "robots.txt").write_text(robots, encoding="utf-8")
    print("  -> docs/robots.txt を生成")


def inject_analytics(ga_id: str):
    ga_tag = f"""  <!-- Google Analytics -->
  <script async src=\"https://www.googletagmanager.com/gtag/js?id={ga_id}\"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', '{ga_id}');
  </script>"""

    html_files = list(DOCS_DIR.rglob("*.html"))
    updated = 0
    for path in html_files:
        content = path.read_text(encoding="utf-8")
        if ga_id in content:
            continue
        content = content.replace("</head>", f"{ga_tag}\n</head>")
        path.write_text(content, encoding="utf-8")
        updated += 1

    print(f"  -> {updated}ファイルにGoogle Analyticsタグを埋め込み")


if __name__ == "__main__":
    import sys
    print("=== SEOファイル生成 ===")
    generate_sitemap()
    generate_robots()

    if len(sys.argv) > 1:
        ga_id = sys.argv[1]
        print(f"\n=== Google Analytics ({ga_id}) 埋め込み ===")
        inject_analytics(ga_id)
    else:
        print("\n※ Google Analytics IDを引数で渡すと全ページに自動埋め込みします")
        print("  例: python generate_seo_files.py G-XXXXXXXXXX")

    print("\n完了")
