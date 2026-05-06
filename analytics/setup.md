# アナリティクスAPI連携 セットアップガイド（サブスク図鑑）

GA4 と Search Console のデータをPythonから自動取得するための設定手順です。
**card-affiliate のサービスアカウントを流用** するので、Google Cloud プロジェクト作成・サービスアカウント新規作成は **不要** です。

**所要時間：約5〜10分**

---

## 完了後にできること

```powershell
cd C:\Users\ashib\vod-affiliate
python analytics/run.py                # 直近28日のレポート生成
python analytics/run.py --days 90      # 期間指定
python analytics/run.py --report only  # キャッシュからレポートだけ再生成
```

→ `analytics/output/report-YYYY-MM-DD.md` が生成される。

---

## 流用する既存リソース

| 項目 | 値 | 備考 |
|---|---|---|
| **Google Cloud プロジェクト** | card-affiliate-analytics | 流用 |
| **サービスアカウント** | `card-affiliate-reader@card-affiliate-analytics.iam.gserviceaccount.com` | 流用 |
| **service-account.json** | `analytics/credentials/service-account.json` | コピー済 |

---

## Step 1: GA4プロパティを作成（5分）

1. https://analytics.google.com/ にアクセス
2. 左下「管理」→「プロパティを作成」
3. 設定：
   - プロパティ名: `サブスク図鑑`
   - レポートのタイムゾーン: 日本
   - 通貨: 日本円
4. データストリーム → ウェブ → URL `https://subzukan.com` / 名前 `サブスク図鑑 (Web)`
5. **画面に表示される「測定ID」** （`G-` で始まる）をコピー → `.env` の `GA_ID=` に貼る
6. **左下「管理」→「プロパティ詳細」→「プロパティID」**（数字のみ）をコピー → `analytics/.env` の `GA4_PROPERTY_ID=` に貼る

## Step 2: GA4 にサービスアカウントを追加（1分）

1. GA4 左下「管理」→ 「プロパティのアクセス管理」
2. 右上「+」→「ユーザーを追加」
3. メールアドレス: `card-affiliate-reader@card-affiliate-analytics.iam.gserviceaccount.com`
4. 役割: **閲覧者**
5. 「追加」

## Step 3: Search Console にプロパティ追加（3分）

1. https://search.google.com/search-console
2. プロパティ追加 → **「URLプレフィックス」** → `https://subzukan.com/` 入力
3. 所有権の確認方法 → **「HTMLタグ」** → 表示されるメタタグの `content="..."` の中身をコピー
4. ルート `.env` の `GSC_VERIFICATION=` に貼り付け
5. （後述）コードビルドで全ページに反映 → push → 反映確認後、Search Console 画面の「確認」ボタン

## Step 4: Search Console にサービスアカウントを追加（1分）

1. Search Console プロパティ確認後、「設定」→「ユーザーと権限」
2. 「ユーザーを追加」
3. メールアドレス: `card-affiliate-reader@card-affiliate-analytics.iam.gserviceaccount.com`
4. 権限: **制限付き**
5. 「追加」

## Step 5: 動作確認

```powershell
cd C:\Users\ashib\vod-affiliate
pip install -r analytics/requirements.txt
python analytics/run.py --days 7
```

成功すれば `analytics/output/report-YYYY-MM-DD.md` が生成される。

---

## ファイル構成

```
vod-affiliate/
├── .env                    # GA_ID / GSC_VERIFICATION（公開サイト側）
└── analytics/
    ├── .env                # GA4_PROPERTY_ID / GSC_SITE_URL
    └── credentials/
        └── service-account.json  # card-affiliate から流用
```

---

## トラブルシューティング

| エラー | 対処 |
|---|---|
| `403 PERMISSION_DENIED` | Step 2 / 4 のサービスアカウント追加が未完了。GA4/GSC で確認 |
| `404 NOT_FOUND`（GA4）| `GA4_PROPERTY_ID` が間違っている（数字のみ） |
| `404`（Search Console）| `GSC_SITE_URL` が登録済みプロパティと完全一致しているか確認（末尾スラッシュ含む） |
| データが空 | GA4は導入から24〜48時間データ未反映、Search Consoleは2〜3日のラグあり |
