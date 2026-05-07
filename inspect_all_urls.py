"""
GSC URL Inspection API で全URLのインデックス状態を一括検査

使い方:
    python inspect_all_urls.py                   # sitemap.xmlの全URLを検査
    python inspect_all_urls.py --filter articles # articles/ 配下のみ
    python inspect_all_urls.py --output report.csv # CSVで出力

仕様:
- 各URLについてインデックス登録状態をチェック
- 未登録URLを抽出して output/unindexed_urls.txt に保存
- ユーザーは output/unindexed_urls.txt の内容を GSC UIに1つずつ貼って
  「インデックス登録をリクエスト」をクリック（最大の即効施策）

API仕様:
- 1日のクオータ: 2,000リクエスト/プロパティ（一般的）
- レート: 6リクエスト/分（推奨）
- Coverage State の値:
  - 「送信して登録されました」: 既にインデックス済み（PASS）
  - 「クロール済み — インデックス未登録」: クロール済みだがインデックスなし（要再検討）
  - 「検出 — 現在インデックス未登録」: 未クロール
  - 「URL は Google に認識されていません」: GSCに未登録
"""
from __future__ import annotations
import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR / "analytics"))
from auth import get_credentials  # noqa: E402

SITE_URL = "https://subzukan.com/"
SITEMAP_PATH = BASE_DIR / "docs" / "sitemap.xml"
OUTPUT_DIR = BASE_DIR / "output"


def read_sitemap_urls() -> list[str]:
    if not SITEMAP_PATH.exists():
        raise FileNotFoundError(f"sitemap.xml not found: {SITEMAP_PATH}")
    content = SITEMAP_PATH.read_text(encoding="utf-8")
    return re.findall(r"<loc>([^<]+)</loc>", content)


def inspect_url(service, url: str, retry: int = 2) -> dict:
    """1URLのインスペクト結果を返す"""
    body = {"inspectionUrl": url, "siteUrl": SITE_URL, "languageCode": "ja"}
    for attempt in range(retry + 1):
        try:
            result = service.urlInspection().index().inspect(body=body).execute()
            return result.get("inspectionResult", {})
        except HttpError as e:
            if attempt < retry and e.resp.status in (429, 500, 502, 503):
                wait = 5 * (attempt + 1)
                print(f"  [retry {attempt+1}/{retry}] HTTP {e.resp.status}, {wait}秒待機")
                time.sleep(wait)
            else:
                return {"error": f"HTTP {e.resp.status}: {e._get_reason()}"}
    return {"error": "max retries"}


def categorize(idx: dict) -> str:
    """Coverage State を簡易カテゴリに変換"""
    if "error" in idx:
        return "ERROR"
    coverage = idx.get("indexStatusResult", {}).get("coverageState", "")
    verdict = idx.get("indexStatusResult", {}).get("verdict", "")
    if "送信して登録" in coverage or "PASS" in verdict:
        return "INDEXED"
    if "クロール済み" in coverage and "未登録" in coverage:
        return "CRAWLED_NOT_INDEXED"
    if "検出" in coverage and "未登録" in coverage:
        return "DISCOVERED_NOT_CRAWLED"
    if "認識されていません" in coverage or "URL is unknown" in coverage:
        return "NOT_KNOWN"
    if not coverage:
        return "UNKNOWN"
    return "OTHER"


def main():
    parser = argparse.ArgumentParser(description="GSC URL Inspection 一括検査")
    parser.add_argument("--filter", help="URLに含まれるキーワード（例: articles, services）")
    parser.add_argument("--output", default="url_inspection_report.csv", help="CSV出力ファイル名")
    parser.add_argument("--delay", type=float, default=2.0, help="リクエスト間隔（秒・デフォルト2秒）")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("[INFO] 認証中...")
    creds = get_credentials()
    service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)

    urls = read_sitemap_urls()
    if args.filter:
        urls = [u for u in urls if args.filter in u]

    print(f"[INFO] {len(urls)} 件のURLを検査します（推定所要時間 約{len(urls) * args.delay / 60:.1f}分）\n")

    results = []
    summary = {"INDEXED": [], "CRAWLED_NOT_INDEXED": [], "DISCOVERED_NOT_CRAWLED": [],
               "NOT_KNOWN": [], "ERROR": [], "OTHER": [], "UNKNOWN": []}

    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url}")
        idx_full = inspect_url(service, url)
        idx = idx_full.get("indexStatusResult", {}) if "indexStatusResult" in idx_full else idx_full
        cat = categorize(idx_full)

        summary[cat].append(url)
        results.append({
            "url": url,
            "category": cat,
            "verdict": idx.get("verdict", ""),
            "coverage_state": idx.get("coverageState", ""),
            "indexing_state": idx.get("indexingState", ""),
            "page_fetch_state": idx.get("pageFetchState", ""),
            "robots_txt": idx.get("robotsTxtState", ""),
            "last_crawl": idx.get("lastCrawlTime", ""),
            "google_canonical": idx.get("googleCanonical", ""),
        })
        print(f"  → {cat}: {idx.get('coverageState', '')[:50]}")

        if i < len(urls):
            time.sleep(args.delay)

    # CSV出力
    csv_path = OUTPUT_DIR / args.output
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    # 未登録URLリスト
    unindexed_path = OUTPUT_DIR / "unindexed_urls.txt"
    unindexed = (
        summary["CRAWLED_NOT_INDEXED"] +
        summary["DISCOVERED_NOT_CRAWLED"] +
        summary["NOT_KNOWN"] +
        summary["UNKNOWN"]
    )
    unindexed_path.write_text("\n".join(unindexed), encoding="utf-8")

    # サマリ
    print("\n" + "=" * 60)
    print("  検査結果サマリ")
    print("=" * 60)
    for cat, lst in summary.items():
        if lst:
            label = {
                "INDEXED": "✅ インデックス済み",
                "CRAWLED_NOT_INDEXED": "⚠️ クロール済み・インデックス未登録",
                "DISCOVERED_NOT_CRAWLED": "🔵 検出・未クロール",
                "NOT_KNOWN": "❌ Google未認識",
                "ERROR": "🔴 エラー",
                "OTHER": "❓ その他",
                "UNKNOWN": "❓ 不明",
            }.get(cat, cat)
            print(f"  {label}: {len(lst)} 件")

    print(f"\n[OUT] CSV: {csv_path}")
    print(f"[OUT] 未登録URL一覧: {unindexed_path}")
    if unindexed:
        print(f"\n📌 次のアクション:")
        print(f"  output/unindexed_urls.txt の {len(unindexed)} 件のURLを")
        print(f"  GSC UI（https://search.google.com/search-console/）の")
        print(f"  「URL検査」に1つずつ貼って「インデックス登録をリクエスト」をクリック")


if __name__ == "__main__":
    main()
