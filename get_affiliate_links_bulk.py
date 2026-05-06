"""
複数プログラムIDのアフィリエイトリンクを一括取得

使い方:
    python get_affiliate_links_bulk.py
"""
import json
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).parent
SESSION_FILE = BASE_DIR / '.a8_session.json'

# 取得対象（提携中のみ）
TARGETS = [
    {"id": "s00000020569001", "name": "SOELU"},
    {"id": "s00000005174001", "name": "Fujisan.co.jp"},
    {"id": "s00000015623001", "name": "audiobook.jp"},
]


def get_first_text_link(page, prog_id: str) -> dict:
    """指定プログラムのテキストリンク（最も汎用的なURL）を取得"""
    url = f'https://pub.a8.net/a8v2/media/linkAction.do?insId={prog_id}'
    page.goto(url, wait_until='domcontentloaded', timeout=20000)
    page.wait_for_timeout(2500)

    if 'login' in page.url.lower() or 'asLogout' in page.url:
        return {"error": "セッション切れ"}

    body_text = page.evaluate('() => document.body.innerText')
    if '未契約' in body_text:
        return {"error": "未契約（プログラム未提携）"}

    html = page.evaluate('() => document.body.innerHTML')
    px_links = sorted(set(re.findall(r'https://px\.a8\.net[^\s\'"<>]+', html)))
    px_links = [l for l in px_links if not l.endswith('&quot;')]

    # textareaから「最初のテキストリンク」を取得
    textareas = page.query_selector_all('textarea')
    text_link_url = None
    for ta in textareas[:5]:
        val = ta.input_value() or ''
        # 単純なURL形式（HTMLタグなし）のtextareaがテキストリンク用
        if val.strip().startswith('https://px.a8.net') and '<' not in val:
            text_link_url = val.strip()
            break

    return {
        "first_link": px_links[0] if px_links else None,
        "text_link_url": text_link_url,
        "all_links_count": len(px_links),
    }


def main():
    if not SESSION_FILE.exists():
        print('❌ .a8_session.json なし')
        sys.exit(1)
    session = json.loads(SESSION_FILE.read_text(encoding='utf-8'))

    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=session)
        page = ctx.new_page()

        for t in TARGETS:
            print(f"\n[{t['id']}] {t['name']}")
            r = get_first_text_link(page, t['id'])
            r["id"] = t["id"]
            r["name"] = t["name"]
            results.append(r)
            for k, v in r.items():
                if k in ("id", "name"):
                    continue
                print(f"  {k}: {v}")

        browser.close()

    out = BASE_DIR / 'a8_affiliate_links.json'
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\n=== 保存: {out.name} ===")
    print()
    for r in results:
        u = r.get("text_link_url") or r.get("first_link") or r.get("error")
        print(f"  {r['id']:18} | {r['name']:18} | {u[:120] if u else 'N/A'}")


if __name__ == '__main__':
    main()
