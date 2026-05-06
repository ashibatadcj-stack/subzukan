"""
A8.net で VOD・動画配信系プログラムを検索してプログラム情報を一括取得（v2）

- 検索結果ページの .pgList カードから「プログラム名」「広告主名」「カテゴリ」「提携状況」を取得
- カテゴリで「動画配信／映像／エンタメ」等を含むもののみ採用
- 結果を a8_vod_candidates.json に保存

使い方:
    python search_a8_vod.py
"""
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).parent
SESSION_FILE = BASE_DIR / '.a8_session.json'
OUTPUT_FILE = BASE_DIR / 'a8_vod_candidates.json'

# 検索キーワード
KEYWORDS = [
    "VOD", "動画配信", "見放題",
    "U-NEXT", "Hulu", "Lemino", "DAZN", "ABEMA",
    "dアニメストア", "FOD", "DMM TV", "TELASA", "WOWOW",
    "サブスク", "音楽配信", "電子書籍",
]

# A8の実カテゴリ名で採用するキーワード（A8では VOD は「動画」カテゴリに分類）
CATEGORY_INCLUDE = ["動画", "映像", "映画", "音楽", "書籍", "出版", "本"]
# カテゴリで除外するキーワード（VODのオマケで引っかかる回線・通信系）
CATEGORY_EXCLUDE = ["回線", "格安SIM", "プロバイダ", "クレジットカード", "保険", "投資", "金融"]


def search_url(keyword: str) -> str:
    return (
        "https://pub.a8.net/a8v2/media/searchAction/keyword.do"
        f"?action=search&viewType=0&keyword={quote(keyword)}"
        "&sortColumn=newArrivalYmd"
    )


def collect_programs(page) -> list[dict]:
    """検索結果ページの .pgList カードから情報を抽出"""
    return page.evaluate(r"""
        () => {
            const cards = Array.from(document.querySelectorAll('.pgList'));
            return cards.map(card => {
                const detailBox = card.querySelector('.detailBox');
                if (!detailBox) return null;

                // 広告主とプログラム名
                const pgNameBox = card.querySelector('.pgNameBox');
                let advertiser = '';
                let pgName = '';
                if (pgNameBox) {
                    const pgNameEl = pgNameBox.querySelector('.pgName');
                    pgName = pgNameEl ? pgNameEl.innerText.trim() : '';
                    // pgNameBox の直下テキストノードに広告主が入っていることが多い
                    const childNodes = Array.from(pgNameBox.childNodes);
                    for (const n of childNodes) {
                        if (n.nodeType === Node.TEXT_NODE) {
                            const t = n.textContent.trim();
                            if (t) { advertiser = t; break; }
                        } else if (n.nodeType === Node.ELEMENT_NODE && !n.classList.contains('pgName')) {
                            const t = (n.innerText || '').trim();
                            if (t && t !== pgName) { advertiser = t; break; }
                        }
                    }
                }

                // detailBox 内の本文テキストを行で割る
                const detailText = detailBox.innerText.trim();
                const lines = detailText.split('\n').map(s => s.trim()).filter(Boolean);

                // ID, カテゴリ, 提携状況を抽出
                let progId = '', category = '', status = '', device = '';
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i];
                    const next = lines[i + 1] || '';
                    if (line === 'プログラムID') progId = next;
                    if (line === 'カテゴリ') category = next;
                    if (line === '提携状況') status = next;
                    if (line === '成果対象デバイス') device = next;
                }

                // insIdsリンクの最初のhref
                const aIns = card.querySelector('a[href*="insIds="]');
                const detail_url = aIns ? aIns.getAttribute('href') : '';
                if (!progId && detail_url) {
                    const m = detail_url.match(/insIds=([sS0-9]+)/);
                    if (m) progId = m[1];
                }

                return {
                    id: progId,
                    name: pgName,
                    advertiser: advertiser,
                    category: category,
                    status: status,
                    device: device,
                    detail_url: detail_url.startsWith('http') ? detail_url : ('https://pub.a8.net' + detail_url),
                };
            }).filter(p => p && p.id);
        }
    """)


def is_vod_category(cat: str, advertiser: str = "", name: str = "") -> bool:
    if not cat:
        # カテゴリが取れなかったら、案件名から判定
        joined = (advertiser + " " + name).lower()
        return any(k.lower() in joined for k in ["vod", "動画", "見放題", "アニメスト", "wowow"])
    # 除外カテゴリならNG
    if any(x in cat for x in CATEGORY_EXCLUDE):
        return False
    # 採用カテゴリならOK
    return any(x in cat for x in CATEGORY_INCLUDE)


def main():
    if not SESSION_FILE.exists():
        print(f"❌ {SESSION_FILE} がありません。`python login_a8.py` を先に実行してください。")
        sys.exit(1)
    session = json.loads(SESSION_FILE.read_text(encoding="utf-8"))

    aggregated: dict[str, dict] = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=session)
        page = ctx.new_page()

        for kw in KEYWORDS:
            url = search_url(kw)
            print(f"\n[検索] {kw}")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(2000)
            except Exception as e:
                print(f"  失敗: {e}")
                continue

            if "login" in page.url.lower() or "asLogout" in page.url:
                print("⚠️ セッション切れ。`python login_a8.py` で再ログインしてください。")
                browser.close()
                sys.exit(1)

            programs = collect_programs(page)
            print(f"  -> {len(programs)} 件発見")
            for p in programs:
                pid = p["id"]
                # 集約
                existing = aggregated.get(pid)
                if existing:
                    existing.setdefault("matched_keywords", []).append(kw)
                else:
                    p["matched_keywords"] = [kw]
                    aggregated[pid] = p
            time.sleep(0.6)

        browser.close()

    all_candidates = list(aggregated.values())

    # VOD系のみ抽出
    vod_only = [
        p for p in all_candidates
        if is_vod_category(p.get("category", ""), p.get("advertiser", ""), p.get("name", ""))
    ]
    others = [p for p in all_candidates if p not in vod_only]

    # ヒット数の多い順、次にカテゴリの優先度
    vod_only.sort(key=lambda x: -len(x.get("matched_keywords", [])))

    output_data = {
        "vod_candidates": vod_only,
        "other_candidates": others,
    }
    OUTPUT_FILE.write_text(
        json.dumps(output_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"\n=== 完了 ===")
    print(f"VOD/エンタメ系: {len(vod_only)} 件")
    print(f"その他（参考）: {len(others)} 件")
    print(f"保存先: {OUTPUT_FILE.relative_to(BASE_DIR)}\n")

    print("--- 【VOD/エンタメ系】TOP30 ---")
    for i, p in enumerate(vod_only[:30], 1):
        kws = ', '.join(p.get('matched_keywords', []))
        nm = (p.get("name") or "")[:38]
        adv = (p.get("advertiser") or "")[:18]
        cat = p.get("category", "")
        st = p.get("status", "")
        print(f"{i:2d}. {p['id']:18} | {cat:8} | {st:6} | {adv:18} | {nm}")
        print(f"    hit: [{kws}]")


if __name__ == "__main__":
    main()
