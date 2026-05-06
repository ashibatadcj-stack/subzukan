"""
A8.net の参加中プログラム一覧を取得（table 形式対応版）

- /a8v2/media/partnerProgramListAction.do?act=search&viewPage=cur
  に複数ページアクセス
- 各行のリンクから insId を抽出
- 周辺テキストから 広告主名・プログラム名・対応デバイス・成果報酬・提携日 をパース
"""
import json
import re
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).parent
SESSION_FILE = BASE_DIR / '.a8_session.json'
OUTPUT_FILE = BASE_DIR / 'a8_partner_programs.json'

LIST_URL_BASE = "https://pub.a8.net/a8v2/media/partnerProgramListAction.do?act=search&viewPage=cur"


def collect_programs(page) -> list[dict]:
    """テーブル形式の参加中プログラムから情報を抽出"""
    return page.evaluate(r"""
        () => {
            // 各「広告主名」セルの行を1プログラムとして扱う
            // ページ内の insId= or insIds= を含む全リンクの近接行から構造を取得
            const allLinks = Array.from(document.querySelectorAll('a[href*="insId"]'));
            const ids = new Set();
            for (const a of allLinks) {
                const m = a.href.match(/insIds?=([sS0-9]+)/);
                if (m) ids.add(m[1]);
            }
            // テーブル/リスト構造から各プログラムのテキストブロックを抽出
            // body 全体テキストを「広告主名」で分割するアプローチ
            const text = document.body.innerText;
            const blocks = text.split(/(?=広告主名\s*\n)/);
            const programs = [];
            for (const blk of blocks) {
                if (!blk.startsWith('広告主名')) continue;
                const lines = blk.split('\n').map(s => s.trim());
                const get = (key) => {
                    const i = lines.findIndex(l => l === key);
                    return (i >= 0 && i+1 < lines.length) ? lines[i+1] : '';
                };
                const adv = get('広告主名');
                const pname = get('プログラム名');
                if (!adv || !pname) continue;
                programs.push({
                    advertiser: adv,
                    name: pname,
                    device: get('対応デバイス'),
                    reward_first: get('成果報酬'),
                    epc: get('EPC'),
                    confirm_rate: get('確定率'),
                });
            }
            return { ids: Array.from(ids), programs };
        }
    """)


def get_pagination_links(page) -> list[str]:
    return page.evaluate(r"""
        () => {
            // ページャ「1 2 3 次のページ」のリンク
            const all = Array.from(document.querySelectorAll('a'));
            return all.filter(a => /partnerProgramListAction\.do/.test(a.href || '')
                                 && /pageId=|page=\d/.test(a.href || ''))
                .map(a => a.href);
        }
    """)


def main():
    if not SESSION_FILE.exists():
        print('❌ .a8_session.json なし')
        sys.exit(1)
    session = json.loads(SESSION_FILE.read_text(encoding='utf-8'))

    all_programs = []
    all_ids = set()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=session)
        page = ctx.new_page()

        # 1ページ目
        url = LIST_URL_BASE
        print(f"[1] {url}")
        page.goto(url, wait_until='domcontentloaded', timeout=20000)
        page.wait_for_timeout(2500)

        if 'login' in page.url.lower() or 'asLogout' in page.url:
            print('セッション切れ')
            sys.exit(1)

        d = collect_programs(page)
        all_programs.extend(d['programs'])
        all_ids.update(d['ids'])
        print(f"  programs: {len(d['programs'])} / ids: {len(d['ids'])}")

        # ページネーション（href にページ番号がある）
        page_urls = get_pagination_links(page)
        print(f"  ページネーション: {len(page_urls)}")
        seen = set([page.url])
        for purl in page_urls:
            if purl in seen:
                continue
            seen.add(purl)
            try:
                page.goto(purl, wait_until='domcontentloaded', timeout=20000)
                page.wait_for_timeout(1500)
                d2 = collect_programs(page)
                all_programs.extend(d2['programs'])
                all_ids.update(d2['ids'])
                print(f"[次] {len(d2['programs'])} / {purl[:120]}")
            except Exception as e:
                print(f"  失敗: {e}")
            time.sleep(0.5)

        browser.close()

    # IDとprogramを統合（順序順）
    # programsは順番にid対応、ids はユニーク集合
    # 個別にzipは不可能なので、別管理
    OUTPUT_FILE.write_text(
        json.dumps({
            "ids": list(all_ids),
            "programs": all_programs,
        }, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    print(f"\n=== 合計: {len(all_programs)} programs / {len(all_ids)} unique IDs ===")
    print(f"保存: {OUTPUT_FILE.relative_to(BASE_DIR)}")
    print()
    print('=== サブスク図鑑関連の提携中プログラム抽出 ===')
    targets_kw = ['動画', '配信', '見放題', 'ABEMA', 'スカパー', 'WOWOW', 'Hulu', 'U-NEXT', 'dアニメ',
                  'DMM', 'Lemino', 'TELASA', 'FOD', 'TSUTAYA',
                  '電子書籍', 'マンガ', '漫画', '読み放題', '雑誌', 'audiobook', 'オーディオブック', 'Fujisan',
                  '英会話', '学び', 'GLOBIS', 'スピーク', 'スタディサプリ', 'キャンブリー',
                  'ヨガ', 'フィットネス', 'SOELU', 'chocoZAP', 'RIZAP']
    for p in all_programs:
        text = p.get('name', '') + p.get('advertiser', '')
        if any(k in text for k in targets_kw):
            print(f"  ✅ {p.get('name','')[:60]} | {p.get('advertiser','')[:24]}")


if __name__ == '__main__':
    main()
