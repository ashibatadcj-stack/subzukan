# サブスク図鑑

国内主要サブスク（VOD・動画配信サービス）を実契約レビュー＋比較表で紹介する図鑑型アフィリエイトメディア。
データ駆動の静的サイトジェネレータで、`vods_data.py` と `articles_data.py` を編集すれば
HTMLが再生成される。`card-affiliate` PJ をベースに横展開した姉妹プロジェクト。

ドメイン: `subzukan.com`（取得・GitHub Pagesカスタムドメイン設定は後工程）。

---

## ディレクトリ構成

```
vod-affiliate/
├── vods_data.py             # VODサービス10件＋クイズ＋比較軸
├── articles_data.py         # 記事メタ15本
├── generate.py              # トップ + 記事HTML生成（Claude API は任意）
├── create_new_vod_pages.py  # 個別VODサービスページ生成
├── generate_seo_files.py    # sitemap.xml / robots.txt 生成
├── a8_banner_fetcher.py     # A8.netからバナーHTML取得（Playwright）
├── auto_discover.py         # A8新案件自動検出＋Claude記事生成
├── analytics/               # GA4 + Search Console レポート
└── docs/                    # GitHub Pages 公開ディレクトリ
    ├── index.html
    ├── services/<id>.html   # 個別VODページ（10件）
    ├── articles/<slug>.html # 記事（15本）
    ├── sitemap.xml
    ├── robots.txt
    └── assets/{common.css, common.js}
```

---

## セットアップ

```powershell
cd C:\Users\ashib\vod-affiliate
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# .env を編集して ANTHROPIC_API_KEY / A8_COOKIE / SITE_URL を設定
```

`ANTHROPIC_API_KEY` は **未設定でもページ生成は通る**（`generate.py` がスケルトン本文にフォールバックする）。
記事本文を Claude で量産したい時だけ設定する。

---

## 日次／更新オペレーション

### 1. 全ページを再生成

```powershell
python create_new_vod_pages.py     # docs/services/ を再生成
python generate.py                  # docs/index.html + docs/articles/ を再生成
python generate_seo_files.py        # docs/sitemap.xml + docs/robots.txt を再生成
```

GA4測定IDを全ページに一括埋め込みたい時:

```powershell
python generate_seo_files.py G-XXXXXXXXXX
```

### 2. ローカル動作確認

```powershell
start docs\index.html
```

ブラウザで開くと、3問のクイズ → ランキング表示 → 記事カテゴリ一覧 が見える。

### 3. アクセス解析（GA4 + Search Console）

`analytics/setup.md` の手順に従って **新サイト用の** サービスアカウントを作成し、
GA4プロパティID と Search Console プロパティURL を `analytics/.env` に設定:

```dotenv
GA4_PROPERTY_ID=123456789
GSC_SITE_URL=https://subzukan.com/
GOOGLE_APPLICATION_CREDENTIALS=analytics/credentials/service-account.json
```

レポート生成:

```powershell
python analytics/run.py --days 28
python analytics/daily_cycle.py --days 28   # AI対応方針付き
```

---

## A8.net 連携

### バナー取得

`a8_banner_fetcher.py` の `PROGRAM_CATALOG` に登録されているプログラムIDから
バナーHTMLを取得・キャッシュして記事に埋め込む。
**初期状態では全プログラムIDが `TBD-<vod_id>` のプレースホルダー**。
A8参加申請が通った正規IDに差し替えること。

### 案件自動発見

`auto_discover.py` は A8.net をクロールして VOD カテゴリの新案件を検出し、
Claude API で記事を自動生成する。
- `A8_CATEGORY_ID` をエンタメ／VODカテゴリの正しいIDに調整
- `A8_COOKIE` を `.env` に設定（A8管理画面ログイン後にDevToolsで取得）

---

## デプロイ（GitHub Pages）

1. GitHubで新規リポジトリ作成（例: `vod-affiliate`）
2. `git init` → `git remote add origin ...` → `git push`
3. リポジトリ Settings > Pages > Source: `main` ブランチ / `/docs`
4. カスタムドメイン使用時は `docs/CNAME` に `subzukan.com` 等を記述

---

## 残タスク（公開前にユーザー側で実施）

| # | 項目 | 場所 |
|---|---|---|
| 1 | A8.net で新サイトをメディア登録 → 審査 | A8管理画面 |
| 2 | VOD系プログラム（U-NEXT/Hulu/DAZN等）に参加申請 | A8管理画面 |
| 3 | 各VODのアフィリエイトURLを反映 | `vods_data.py` の `affiliate_url` |
| 4 | `a8_banner_fetcher.py` の `PROGRAM_CATALOG` を正規IDに置換 | コード |
| 5 | `auto_discover.py` の `A8_CATEGORY_ID` を確認 | コード |
| 6 | ドメイン取得＆DNS設定 | お名前.com等 |
| 7 | GA4プロパティ作成 → 測定IDを `generate.py` の `GA_ID` と `create_new_vod_pages.py` に反映 | コード |
| 8 | Search Console プロパティ登録 → サイトマップ送信 | Search Console |
| 9 | サービスアカウントへ閲覧権限付与 | analytics/setup.md 参照 |
| 10 | GitHubリポジトリ作成 → Pagesで公開 | GitHub |

---

## 既存PJ（card-affiliate）との関係

- ベースアーキテクチャ（データ駆動・テンプレート・analyticsモジュール）は共通
- ロジックの共通化は **行わない**（各サイトで独立して進化させる方針）
- `card-affiliate` 側の改善が有用な場合は手動で取り込む
