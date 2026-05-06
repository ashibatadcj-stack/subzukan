"""A8の「動画」ジャンルで全プログラムを取得（U-NEXT等が見つからなかった対策）"""
import json
import re
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).parent
SESSION_FILE = BASE_DIR / '.a8_session.json'

# 動画関連のジャンルID
# A8では genreId=22 が「動画」だった（auto_discover_pw.py の card-affiliate 履歴より）
# ただし時期によって変わる可能性。複数試す。
GENRE_URL_TPL = (
    "https://pub.a8.net/a8v2/media/searchAction/keyword.do"
    "?action=search&viewType=0&genreId={gid}&sortColumn=newArrivalYmd"
)


def collect_programs(page):
    return page.evaluate(r"""
        () => {
            const cards = Array.from(document.querySelectorAll('.pgList'));
            return cards.map(card => {
                const detailBox = card.querySelector('.detailBox');
                if (!detailBox) return null;
                const pgNameBox = card.querySelector('.pgNameBox');
                let advertiser = '';
                let pgName = '';
                if (pgNameBox) {
                    const pgNameEl = pgNameBox.querySelector('.pgName');
                    pgName = pgNameEl ? pgNameEl.innerText.trim() : '';
                    for (const n of pgNameBox.childNodes) {
                        if (n.nodeType === Node.TEXT_NODE) {
                            const t = n.textContent.trim();
                            if (t) { advertiser = t; break; }
                        } else if (n.nodeType === Node.ELEMENT_NODE && !n.classList.contains('pgName')) {
                            const t = (n.innerText || '').trim();
                            if (t && t !== pgName) { advertiser = t; break; }
                        }
                    }
                }
                const lines = detailBox.innerText.trim().split('\n').map(s => s.trim()).filter(Boolean);
                let progId = '', category = '', status = '';
                for (let i = 0; i < lines.length; i++) {
                    if (lines[i] === 'プログラムID') progId = lines[i+1] || '';
                    if (lines[i] === 'カテゴリ') category = lines[i+1] || '';
                    if (lines[i] === '提携状況') status = lines[i+1] || '';
                }
                return { id: progId, name: pgName, advertiser, category, status };
            }).filter(p => p && p.id);
        }
    """)


def collect_pagination_urls(page):
    """ページネーションリンクから他のページURLを取得"""
    return page.evaluate(r"""
        () => {
            const pages = Array.from(document.querySelectorAll('a.pageNavi, .pagenavi a, [href*="pageId="]'));
            return Array.from(new Set(pages.map(a => a.href))).slice(0, 30);
        }
    """)


def main():
    if not SESSION_FILE.exists():
        print('❌ .a8_session.json なし')
        sys.exit(1)
    session = json.loads(SESSION_FILE.read_text(encoding='utf-8'))

    all_programs = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=session)
        page = ctx.new_page()

        # 動画系の可能性があるジャンルIDを試す
        for gid in [22, 27, 51]:
            url = GENRE_URL_TPL.format(gid=gid)
            print(f'\n[ジャンルID {gid}] {url}')
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=20000)
                page.wait_for_timeout(2500)
            except Exception as e:
                print(f'  失敗: {e}')
                continue

            if 'login' in page.url.lower() or 'asLogout' in page.url:
                print('セッション切れ')
                browser.close()
                sys.exit(1)

            programs = collect_programs(page)
            print(f'  -> {len(programs)} 件発見')
            for p in programs:
                if p['id'] not in all_programs:
                    p['genre_id'] = gid
                    all_programs[p['id']] = p

            # 次ページへ
            page_urls = collect_pagination_urls(page)
            print(f'  ページネーション {len(page_urls)} 件')
            for purl in page_urls[:10]:
                try:
                    page.goto(purl, wait_until='domcontentloaded', timeout=20000)
                    page.wait_for_timeout(1500)
                    extra = collect_programs(page)
                    for p in extra:
                        if p['id'] not in all_programs:
                            p['genre_id'] = gid
                            all_programs[p['id']] = p
                except Exception as e:
                    print(f'  ページ取得失敗: {e}')
                time.sleep(0.5)

        browser.close()

    print(f'\n=== 合計 {len(all_programs)} 件 ===')
    # サブスク図鑑掲載VODに該当するものを抽出
    target_keywords = {
        'U-NEXT': ['u-next', 'unext', 'ｕ─ｎｅｘｔ', 'ユーネクスト'],
        'Hulu': ['hulu', 'フールー', 'ｈｕｌｕ'],
        'Lemino': ['lemino', 'レミノ'],
        'DAZN': ['dazn', 'ダゾーン'],
        'FOD': ['fod', 'フジテレビオンデマンド', 'ＦＯＤ'],
        'TELASA': ['telasa', 'テラサ', 'ＴＥＬＡＳＡ'],
        'dアニメストア': ['dアニメ', 'ｄアニメ', 'ドコモ・アニメ'],
        'ABEMA': ['abema', 'アベマ'],
        'WOWOW': ['wowow'],
        'DMM TV': ['dmm tv', 'dmmtv', 'dmm.tv', 'dmmプレミアム'],
    }
    print('\n=== サブスク図鑑掲載VODに該当するプログラム ===')
    matched = {}
    for vod_name, kws in target_keywords.items():
        hits = []
        for p in all_programs.values():
            text = (p.get('name', '') + ' ' + p.get('advertiser', '')).lower()
            for kw in kws:
                if kw.lower() in text:
                    hits.append(p)
                    break
        if hits:
            print(f'\n## {vod_name}')
            for p in hits[:5]:
                print(f"  {p['id']:18} | {p.get('status','-'):6} | {p.get('advertiser','')[:20]:20} | {p.get('name','')[:60]}")
            matched[vod_name] = hits
        else:
            print(f'## {vod_name} ← A8で発見されず')

    out = BASE_DIR / 'a8_genre_results.json'
    out.write_text(json.dumps(list(all_programs.values()), ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n保存: {out.name}')


if __name__ == '__main__':
    main()
