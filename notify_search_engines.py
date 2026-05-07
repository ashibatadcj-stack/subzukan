"""
検索エンジン全体への更新通知ラッパー

使い方:
    python notify_search_engines.py             # IndexNow + GSC sitemap 両方を実行
    python notify_search_engines.py --skip-gsc  # IndexNow のみ
    python notify_search_engines.py --skip-indexnow  # GSC sitemap のみ

実行前提:
- docs/sitemap.xml が最新（python generate_seo_files.py 実行後）
- docs/<key>.txt が GitHub Pages に反映済み（push後 数分待つ）
- analytics/credentials/token.json が webmasters スコープで再認可済み

新規記事追加時の標準フロー:
    python generate.py
    python create_new_vod_pages.py
    python generate_seo_files.py
    git add docs/ && git commit && git push
    python notify_search_engines.py    ← これ
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).parent


def run(label: str, cmd: list[str]) -> bool:
    """サブプロセスを実行し、成功/失敗を返す"""
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")
    result = subprocess.run(cmd, cwd=BASE_DIR)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="IndexNow + GSC sitemap 一括通知")
    parser.add_argument("--skip-indexnow", action="store_true", help="IndexNowをスキップ")
    parser.add_argument("--skip-gsc", action="store_true", help="GSC sitemapをスキップ")
    args = parser.parse_args()

    if args.skip_indexnow and args.skip_gsc:
        print("両方スキップしたら何も実行されません")
        sys.exit(1)

    success = []
    failed = []

    # Phase A: IndexNow
    if not args.skip_indexnow:
        ok = run("Phase A: IndexNow（Bing/Yandex/Naver）", [sys.executable, "notify_indexnow.py"])
        (success if ok else failed).append("IndexNow")

    # Phase B: GSC sitemap
    if not args.skip_gsc:
        ok = run("Phase B: GSC Sitemap再送信（Google）", [sys.executable, "notify_gsc.py"])
        (success if ok else failed).append("GSC")

    # Summary
    print(f"\n{'=' * 60}")
    print("  完了")
    print(f"{'=' * 60}")
    if success:
        print(f"✅ 成功: {', '.join(success)}")
    if failed:
        print(f"❌ 失敗: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
