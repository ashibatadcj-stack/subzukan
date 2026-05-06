"""
search_a8_vod.py で発見した候補に対して、詳細ページからプログラム名を補完。

a8_vod_candidates.json を読み込み、name が空のものに対して
A8.net のプログラム詳細ページにアクセスしてタイトルを取得する。

実行: python enrich_a8_candidates.py
"""
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).parent
SESSION_FILE = BASE_DIR / '.a8_session.json'
CANDIDATES_FILE = BASE_DIR / 'a8_vod_candidates.json'

# 補完対象の上限（取得するヒット数の多い順から N件）
ENRICH_LIMIT = 50


def fetch_program_name(page, prog: dict) -> dict:
    """詳細ページにアクセスしてプログラム名・補足情報を取得"""
    detail_url = prog.get("detail_url") or f"https://pub.a8.net/a8v2/media/programDetailAction.do?insId={prog['id']}"
    try:
        page.goto(detail_url, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(800)

        # ログインに飛んだ判定
        if "login" in page.url.lower() or "asLogout" in page.url:
            print(f"  ⚠️ セッション切れ: {prog['id']}")
            return prog

        # h1 か h2 か .programName を取得
        for sel in ["h1", "h2.programName", ".programName", ".programTitle", "h2"]:
            el = page.query_selector(sel)
            if el:
                text = el.inner_text().strip()
                if text and len(text) < 120 and "A8.net" not in text and "ログイン" not in text:
                    prog["name"] = text[:80]
                    break

        # 報酬や提携状況なども取れるなら取得
        body_text = page.evaluate("() => document.body.innerText")
        # 「成果報酬」「成果地点」「報酬」などのキーワード行を抜粋
        reward_lines = []
        for line in body_text.split('\n'):
            line = line.strip()
            if any(k in line for k in ["成果報酬", "成果地点", "報酬"]):
                if len(line) < 200:
                    reward_lines.append(line)
        if reward_lines:
            prog["reward_summary"] = reward_lines[:3]

    except Exception as e:
        print(f"  ❌ {prog['id']}: {e}")
    return prog


def main():
    if not CANDIDATES_FILE.exists():
        print(f"❌ {CANDIDATES_FILE} がありません。先に search_a8_vod.py を実行してください。")
        sys.exit(1)
    if not SESSION_FILE.exists():
        print(f"❌ {SESSION_FILE} がありません。先に login_a8.py を実行してください。")
        sys.exit(1)

    candidates = json.loads(CANDIDATES_FILE.read_text(encoding="utf-8"))
    session = json.loads(SESSION_FILE.read_text(encoding="utf-8"))

    # ヒット数の多い順に上位 ENRICH_LIMIT 件
    targets = sorted(candidates, key=lambda x: -len(x.get("matched_keywords", [])))[:ENRICH_LIMIT]
    print(f"補完対象: {len(targets)} 件 / 全{len(candidates)}件")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=session)
        page = ctx.new_page()

        for i, prog in enumerate(targets, 1):
            if prog.get("name"):
                continue
            print(f"[{i}/{len(targets)}] {prog['id']}")
            fetch_program_name(page, prog)
            time.sleep(0.4)

        browser.close()

    # 保存
    CANDIDATES_FILE.write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\n保存完了: {CANDIDATES_FILE.relative_to(BASE_DIR)}")

    # TOP表示
    enriched = [p for p in candidates if p.get("name")]
    print(f"\n=== 名前取得済み {len(enriched)} 件 / 全{len(candidates)} 件 ===")
    for i, p in enumerate(sorted(enriched, key=lambda x: -len(x.get("matched_keywords", [])))[:30], 1):
        kws = ', '.join(p.get('matched_keywords', []))
        print(f"{i:2d}. {p['id']:30} | {p.get('name','')[:38]:38} | hit:[{kws[:50]}]")


if __name__ == "__main__":
    main()
