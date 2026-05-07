"""
IndexNow API でBing/Yandex/NaverにURL更新を通知するスクリプト

使い方:
    python notify_indexnow.py                     # sitemap.xmlの全URLを送信
    python notify_indexnow.py --urls "https://subzukan.com/articles/foo.html https://subzukan.com/articles/bar.html"

仕様:
- IndexNow（https://www.indexnow.org/）はMicrosoft Bingが主導する複数検索エンジン共通のインデックス通知プロトコル
- Bing / Yandex / Naver / Seznam / IndexNow API 採用検索エンジンに一括通知
- 1リクエスト最大10,000URLまで
- 認証はホスト直下のキーファイルで行う
- レスポンス 200/202 = 成功
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE_DIR = Path(__file__).parent
DOCS_DIR = BASE_DIR / "docs"
SITEMAP_PATH = DOCS_DIR / "sitemap.xml"

# IndexNow設定
HOST = "subzukan.com"
KEY = "e5289aed76f0fdd9dedc2edf2609b447"
KEY_LOCATION = f"https://{HOST}/{KEY}.txt"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/IndexNow"

# 標準出力をUTF-8に
sys.stdout.reconfigure(encoding="utf-8")


def read_sitemap_urls(sitemap_path: Path) -> list[str]:
    """sitemap.xml から <loc> タグのURLを抽出"""
    if not sitemap_path.exists():
        raise FileNotFoundError(f"sitemap.xml が見つかりません: {sitemap_path}")
    content = sitemap_path.read_text(encoding="utf-8")
    return re.findall(r"<loc>([^<]+)</loc>", content)


def post_indexnow(urls: list[str]) -> tuple[int, str]:
    """IndexNow API にPOSTし、(status_code, response_body) を返す"""
    payload = {
        "host": HOST,
        "key": KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": urls,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(
        INDEXNOW_ENDPOINT,
        data=data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, body
    except URLError as e:
        return -1, f"URLError: {e.reason}"


def main():
    parser = argparse.ArgumentParser(description="IndexNow API で検索エンジンにURL更新を通知")
    parser.add_argument(
        "--urls",
        nargs="*",
        help="通知する個別URLをスペース区切りで指定（省略時はsitemap.xml全URL）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際には送信せず、対象URLだけ表示",
    )
    args = parser.parse_args()

    # URLリスト決定
    if args.urls:
        urls = args.urls
        print(f"[INFO] CLI 指定の {len(urls)} 件のURLを通知します")
    else:
        urls = read_sitemap_urls(SITEMAP_PATH)
        print(f"[INFO] sitemap.xml の {len(urls)} 件のURLを通知します")

    # 表示用に最初と最後だけ
    print("--- 対象URL（先頭3件）---")
    for u in urls[:3]:
        print(f"  {u}")
    if len(urls) > 3:
        print(f"  ... 他 {len(urls) - 3} 件")

    if args.dry_run:
        print("\n[DRY-RUN] 送信スキップ")
        return

    # キーファイル存在確認（HTTP）
    print(f"\n[INFO] keyLocation: {KEY_LOCATION}")
    print(f"[INFO] エンドポイント: {INDEXNOW_ENDPOINT}")

    # 送信
    status, body = post_indexnow(urls)
    print(f"\n[結果] HTTP {status}")
    if body:
        print(f"[Body] {body[:200]}")

    if status in (200, 202):
        print(f"\n✅ 成功: {len(urls)} 件のURLをIndexNowに通知しました")
        print("（Bing/Yandex/Naverに反映されるまで数時間〜数日）")
    elif status == 400:
        print("\n❌ 400 Bad Request: ペイロード形式エラー（URLリストやキー設定を確認）")
        sys.exit(1)
    elif status == 403:
        print(f"\n❌ 403 Forbidden: keyファイル({KEY_LOCATION})が見つからない")
        print("→ docs/{KEY}.txt をpushしてGitHub Pagesに反映済みか確認")
        sys.exit(1)
    elif status == 422:
        print("\n❌ 422 Unprocessable Entity: URLが無効・hostと一致しない・キー不一致")
        sys.exit(1)
    elif status == 429:
        print("\n⚠️ 429 Too Many Requests: レート制限。少し待ってから再試行")
        sys.exit(1)
    else:
        print(f"\n❌ エラー: HTTP {status}")
        sys.exit(1)


if __name__ == "__main__":
    main()
