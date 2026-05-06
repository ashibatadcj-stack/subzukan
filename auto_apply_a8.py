"""
A8.net サブスク図鑑メディアでの参加申請を自動化

使い方:
    python auto_apply_a8.py             # 既定リストを順次申請
    python auto_apply_a8.py --dry-run   # 確認画面まで進めて送信せず終了

要件:
    .a8_session.json があること（python login_a8.py で更新済）

ロジック:
    1. 各プログラムIDについて、検索結果ページから詳細申請URLを取得
    2. 詳細ページで selectedWebsiteIds=002 (サブスク図鑑) を選択
    3. 「提携申請をする」or「プログラムと提携する」ボタンをクリック
    4. 確認画面で同意・送信
    5. 結果ログを subzukan_a8_apply_log.json に保存
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).parent
SESSION_FILE = BASE_DIR / '.a8_session.json'
LOG_FILE = BASE_DIR / 'subzukan_a8_apply_log.json'

# 申請対象のプログラム（subzukan メディアで未提携・優先度高）
# search_keywords は複数キーワードを順に試行（最初にヒットしたもので申請）
TARGETS = [
    # ★★★ コアスコープ（既に申請完了）
    # {"id": "s00000015623001", "name": "audiobook.jp",
    #  "search_keywords": ["オーディオブック", "audiobook"]},
    # {"id": "s00000022237001", "name": "Amebaマンガ",
    #  "search_keywords": ["Amebaマンガ", "漫画 読み放題", "Ameba", "電子コミック", "電子書籍"]},
    # {"id": "s00000005174001", "name": "Fujisan.co.jp",
    #  "search_keywords": ["Fujisan", "雑誌", "電子書籍"]},

    # ★★ 拡張①：学び放題・オンライン英会話（親和性高）
    {"id": "s00000026109001", "name": "GLOBIS 学び放題",
     "search_keywords": ["GLOBIS 学び放題", "グロービス", "学び放題"]},
    {"id": "s00000026707001", "name": "DMM英会話",
     "search_keywords": ["DMM英会話", "オンライン英会話 DMM", "DMM"]},
    {"id": "s00000018953001", "name": "キャンブリー",
     "search_keywords": ["キャンブリー", "Cambly", "ネイティブ 英会話"]},
    {"id": "s00000026697001", "name": "スピーク",
     "search_keywords": ["スピーク", "AI英会話", "英会話 アプリ"]},
    {"id": "s00000015388002", "name": "スタディサプリENGLISH（TOEIC対策）",
     "search_keywords": ["スタディサプリENGLISH", "スタディサプリ TOEIC", "TOEIC対策"]},

    # ★★ 拡張②：フィットネス・ヨガ
    {"id": "s00000020569001", "name": "SOELU",
     "search_keywords": ["SOELU", "オンラインヨガ", "ヨガ"]},
    {"id": "s00000024602001", "name": "chocoZAP",
     "search_keywords": ["chocoZAP", "チョコザップ", "RIZAP"]},
]

# サブスク図鑑のサイトID
SUBZUKAN_SITE_ID = "002"

INTERVAL_SEC = 8  # 連続申請の間隔


def get_detail_url(page, prog_id: str, keywords) -> tuple[str | None, str | None]:
    """検索結果から該当プログラムカードの詳細URLを取得。
    keywords は単一文字列でもリストでもよい。リストなら順に試行。
    返り値: (detail_url, hit_keyword)
    """
    if isinstance(keywords, str):
        keywords = [keywords]

    for kw in keywords:
        url = (
            "https://pub.a8.net/a8v2/media/searchAction/keyword.do"
            f"?action=search&viewType=0&keyword={quote(kw)}"
            "&sortColumn=newArrivalYmd"
        )
        page.goto(url, wait_until='domcontentloaded', timeout=20000)
        page.wait_for_timeout(1500)

        detail = page.evaluate(f"""
            () => {{
                const card = document.querySelector('#pg-{prog_id}');
                if (!card) return null;
                const a = card.querySelector('a[name=programDetailButton]');
                return a ? a.href : null;
            }}
        """)
        if detail:
            return detail, kw
    return None, None


def apply_one(page, prog: dict, dry_run: bool = False) -> dict:
    result = {
        "id": prog["id"],
        "name": prog["name"],
        "started_at": datetime.now().isoformat(),
        "status": "未試行",
        "messages": [],
    }
    log = result["messages"].append

    try:
        keywords = prog.get("search_keywords") or [prog.get("search_keyword", "")]
        log(f"[1] 検索 keywords={keywords}")
        detail_url, hit_kw = get_detail_url(page, prog["id"], keywords)
        if not detail_url:
            result["status"] = "ERROR_検索結果に見つからず"
            log(f"  全キーワードで未発見: {keywords}")
            return result
        log(f"  ヒットキーワード: '{hit_kw}'")
        log(f"  詳細URL: {detail_url[:140]}")

        log(f"[2] 詳細ページに移動")
        page.goto(detail_url, wait_until='domcontentloaded', timeout=20000)
        page.wait_for_timeout(2500)

        # 提携状況を確認
        body = page.evaluate('() => document.body.innerText')
        if "未提携" not in body:
            # 既に申請中・提携中
            for s in ["申請中", "提携中"]:
                if s in body:
                    result["status"] = f"SKIP_既に{s}"
                    log(f"  既に{s}のためスキップ")
                    return result
            result["status"] = "SKIP_状態不明"
            return result

        log(f"[3] サブスク図鑑(value={SUBZUKAN_SITE_ID})を選択")
        select_exists = page.evaluate(r"""
            () => !!document.querySelector('select[name=selectedWebsiteIds]')
        """)
        if not select_exists:
            result["status"] = "ERROR_サイト選択UIなし"
            return result
        page.select_option('select[name=selectedWebsiteIds]', SUBZUKAN_SITE_ID)
        page.wait_for_timeout(500)

        log("[4] 申請ボタンをクリック")
        # 「提携申請をする」or「プログラムと提携する」ボタンを探す
        # ページ内のテキストから候補を見つける
        clicked = False
        for label in ["提携申請をする", "プログラムと提携する", "提携を申請する", "申請する"]:
            try:
                btn = page.locator(f"text={label}").first
                if btn.count() > 0 and btn.is_visible():
                    if dry_run:
                        log(f"  [DRY-RUN] '{label}' を発見・クリック省略")
                        result["status"] = "DRY_RUN_OK"
                        return result
                    btn.click()
                    log(f"  '{label}' をクリック")
                    clicked = True
                    break
            except Exception as e:
                log(f"  '{label}' クリック試行失敗: {e}")
        if not clicked:
            result["status"] = "ERROR_申請ボタン未発見"
            return result

        # 確認画面
        page.wait_for_timeout(2500)
        log(f"[5] 確認画面 URL={page.url}")

        confirm_body = page.evaluate('() => document.body.innerText')
        log(f"  画面冒頭: {confirm_body[:200].strip()[:200]}")

        # 同意チェックや「申請する」ボタン
        # まず「同意する」「同意します」のチェックボックスを探す
        agree_clicked = False
        try:
            agree = page.locator('input[type=checkbox]').filter(has_text="同意")
            if agree.count() > 0:
                agree.first.check()
                log("  同意チェック")
                agree_clicked = True
        except Exception:
            pass

        # 申請完了ボタン
        for label in ["申請する", "送信する", "同意して申請", "確定する"]:
            try:
                b = page.locator(f"text={label}").first
                if b.count() > 0 and b.is_visible():
                    b.click()
                    log(f"  最終ボタン '{label}' クリック")
                    page.wait_for_timeout(3000)
                    final_body = page.evaluate('() => document.body.innerText')
                    if any(s in final_body for s in ["完了", "受付", "申請されました", "申請しました", "提携しました"]):
                        result["status"] = "OK_申請完了"
                        log("  申請完了確認")
                    else:
                        result["status"] = "WARN_完了文言未確認"
                        log(f"  完了画面: {final_body[:300]}")
                    return result
            except Exception as e:
                log(f"  '{label}' 失敗: {e}")

        # 確認画面で完了せず → 確認画面の本文だけで判断
        if any(s in confirm_body for s in [
            "申請を受け付けました", "申請が完了", "提携を申請しました",
            "プログラムと提携しました", "申請しました"
        ]):
            result["status"] = "OK_申請完了"
            log("  確認画面に完了メッセージ")
        else:
            result["status"] = "WARN_確認画面で停止"
            log("  確認画面の最終ボタンを発見できず")
    except Exception as e:
        result["status"] = f"ERROR_{type(e).__name__}"
        log(f"  例外: {e}")
    finally:
        result["finished_at"] = datetime.now().isoformat()
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", help="特定IDのみ申請")
    args = ap.parse_args()

    if not SESSION_FILE.exists():
        print(f"❌ {SESSION_FILE} なし。先に python login_a8.py を実行してください。")
        sys.exit(1)

    targets = TARGETS
    if args.only:
        targets = [t for t in TARGETS if t["id"] == args.only]

    session = json.loads(SESSION_FILE.read_text(encoding='utf-8'))
    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(storage_state=session)
        page = ctx.new_page()

        for i, prog in enumerate(targets, 1):
            print(f"\n========== [{i}/{len(targets)}] {prog['name']} ({prog['id']}) ==========")
            r = apply_one(page, prog, dry_run=args.dry_run)
            for m in r["messages"]:
                print(f"  {m}")
            print(f"  → 結果: {r['status']}")
            results.append(r)
            if i < len(targets):
                print(f"  ({INTERVAL_SEC}秒待機)")
                time.sleep(INTERVAL_SEC)
        browser.close()

    LOG_FILE.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\n=== ログ保存: {LOG_FILE.name} ===")
    print("\n=== サマリ ===")
    for r in results:
        print(f"  {r['id']:18} | {r['name']:18} | {r['status']}")


if __name__ == "__main__":
    main()
