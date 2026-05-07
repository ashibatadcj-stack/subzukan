"""
Google Search Console に sitemap.xml の再送信を行うスクリプト

使い方:
    python notify_gsc.py                # 標準のsitemap.xmlを再送信
    python notify_gsc.py --list         # 登録済みsitemap一覧を表示
    python notify_gsc.py --inspect URL  # 特定URLのインデックス状況をチェック

仕様:
- Google Search Console API v1（searchconsole）を使用
- analytics/credentials/token.json の OAuth 認証情報を流用
- 必要スコープ: https://www.googleapis.com/auth/webmasters

Note:
- Sitemap submit は GSC に「再クロールしてください」のシグナルを送る
- 個別URL のインデックス登録リクエストは公式APIで非対応（GSC UIの手動操作のみ）
- 即時インデックスは保証されない（高品質コンテンツ＋内部リンク強化と組み合わせる前提）
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# 標準出力をUTF-8に
sys.stdout.reconfigure(encoding="utf-8")

# auth ヘルパは analytics/ 配下にある
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR / "analytics"))
from auth import get_credentials  # noqa: E402

SITE_URL = "https://subzukan.com/"           # GSCに登録した「ドメインプロパティ」or「URLプロパティ」
SITEMAP_URL = "https://subzukan.com/sitemap.xml"


def submit_sitemap(service, site_url: str, sitemap_url: str) -> None:
    """sitemap を再送信（更新シグナルを送る）"""
    print(f"[INFO] Sitemap再送信: {sitemap_url}")
    print(f"[INFO] Site:           {site_url}")
    try:
        service.sitemaps().submit(siteUrl=site_url, feedpath=sitemap_url).execute()
        print("✅ Sitemap再送信成功")
    except HttpError as e:
        print(f"❌ HTTPエラー {e.resp.status}: {e.error_details if hasattr(e, 'error_details') else e._get_reason()}")
        if e.resp.status == 403:
            print("→ 該当サイトのGSC所有権が確認されていない可能性")
        if e.resp.status == 404:
            print("→ siteUrlが間違っている可能性。GSCに登録されたプロパティと一致するか確認")
        sys.exit(1)


def list_sitemaps(service, site_url: str) -> None:
    """登録済みsitemap一覧を表示"""
    print(f"[INFO] {site_url} に登録されたsitemap一覧:\n")
    try:
        result = service.sitemaps().list(siteUrl=site_url).execute()
        sitemaps = result.get("sitemap", [])
        if not sitemaps:
            print("  （sitemap未登録）")
            return
        for sm in sitemaps:
            print(f"  Path:          {sm.get('path')}")
            print(f"    最終DL:      {sm.get('lastDownloaded', '-')}")
            print(f"    最終送信:    {sm.get('lastSubmitted', '-')}")
            print(f"    isPending:   {sm.get('isPending', False)}")
            print(f"    contents:    {sm.get('contents', [])}")
            print()
    except HttpError as e:
        print(f"❌ HTTPエラー {e.resp.status}: {e._get_reason()}")
        sys.exit(1)


def inspect_url(service, site_url: str, target_url: str) -> None:
    """特定URLのインデックス状況をチェック"""
    print(f"[INFO] URL検査: {target_url}\n")
    try:
        # URL Inspection API は別エンドポイント
        body = {
            "inspectionUrl": target_url,
            "siteUrl": site_url,
            "languageCode": "ja",
        }
        result = service.urlInspection().index().inspect(body=body).execute()
        idx = result.get("inspectionResult", {}).get("indexStatusResult", {})
        print(f"  Verdict:           {idx.get('verdict', '-')}")
        print(f"  Coverage State:    {idx.get('coverageState', '-')}")
        print(f"  Index Status:      {idx.get('indexingState', '-')}")
        print(f"  Last Crawl Time:   {idx.get('lastCrawlTime', '-')}")
        print(f"  Page Fetch State:  {idx.get('pageFetchState', '-')}")
        print(f"  Crawled As:        {idx.get('crawledAs', '-')}")
        print(f"  Robots TXT State:  {idx.get('robotsTxtState', '-')}")
        if idx.get("googleCanonical"):
            print(f"  Google Canonical:  {idx.get('googleCanonical')}")
        if idx.get("userCanonical"):
            print(f"  User Canonical:    {idx.get('userCanonical')}")
    except HttpError as e:
        print(f"❌ HTTPエラー {e.resp.status}: {e._get_reason()}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Google Search Console: sitemap再送信＆URL検査")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--list", action="store_true", help="登録済みsitemap一覧を表示")
    group.add_argument("--inspect", metavar="URL", help="指定URLのインデックス状況をチェック")
    args = parser.parse_args()

    # 認証
    print("[INFO] 認証中...")
    creds = get_credentials()
    service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)

    if args.list:
        list_sitemaps(service, SITE_URL)
    elif args.inspect:
        inspect_url(service, SITE_URL, args.inspect)
    else:
        # デフォルト: sitemap再送信
        submit_sitemap(service, SITE_URL, SITEMAP_URL)
        print()
        # 続けて一覧表示
        list_sitemaps(service, SITE_URL)


if __name__ == "__main__":
    main()
