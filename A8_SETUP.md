# A8.net アフィリエイトリンク取得 完全ガイド

サブスク図鑑（vod-affiliate）で A8 のアフィリエイトリンクを取得・反映するまでの全手順。
**card-affiliate の A8 アカウントを共用** する前提で組まれています。

---

## 全体フロー（8ステップ）

| # | ステップ | 担当 | 所要時間 | 依存 |
|---|---|---|---|---|
| 1 | ドメイン取得（subzukan.com） | ユーザー | 30分 | - |
| 2 | GitHubリポジトリ作成 → Pages 公開 | ユーザー | 30分 | 1 |
| 3 | カスタムドメインを GitHub Pages に紐付け | ユーザー | 1〜24時間（DNS伝播） | 1, 2 |
| 4 | A8.net にメディア追加（サブスク図鑑を新規登録） | ユーザー | 10分 + **審査3〜7日** | 3 |
| 5 | VOD系プログラムへの参加申請（10〜15件） | ユーザー | 30分 + **承認2〜14日** | 4 |
| 6 | 承認されたプログラムの提携リンクを取得 | スクリプト | 5分 | 5 |
| 7 | `vods_data.py` の `affiliate_url` に反映 | スクリプト | 5分 | 6 |
| 8 | 全ページ再ビルド → push | スクリプト | 5分 | 7 |

**現時点で着手できるのは 5〜7 の準備**。
ステップ 1〜4 はユーザー側の手作業＋A8 の審査待ちが必要です。

---

## ステップ 1: ドメイン取得

### 確定ドメイン
- **`subzukan.com`**（お名前.com で取得）

### 手続き
お名前.com で `subzukan` を検索 → `.com` を選択 → Whois情報公開代行を有効化（無料） → 申込み。
初年度キャンペーンで `.com` は年750〜1,500円前後。

---

## ステップ 2: GitHub Pages 公開

```powershell
cd C:\Users\ashib\vod-affiliate
git init
git add .
git commit -m "Initial commit: subzukan"

# GitHub Web UI で `subzukan` リポジトリを作成
git remote add origin https://github.com/ashibatadcj-stack/subzukan.git
git push -u origin main
```

リポジトリの **Settings > Pages** で：
- Source: `main` ブランチ
- Folder: `/docs`

数分後に `https://ashibatadcj-stack.github.io/subzukan/` で公開される。

---

## ステップ 3: カスタムドメイン紐付け

1. ドメインのDNSで以下のCNAMEレコードを設定：
   - `subzukan.com` → `ashibatadcj-stack.github.io`
2. `docs/CNAME` ファイルを作成し、内容に `subzukan.com` を記述
3. GitHub Pages の Settings > Pages > Custom domain に `subzukan.com` を入力
4. Enforce HTTPS にチェック（DNS伝播後）

---

## ステップ 4: A8.net にメディア追加

card-affiliate と同じA8アカウントでログインして、メディアを追加する。

1. https://pub.a8.net/ にログイン
2. ヘッダーの「**メディア管理**」→「**メディア追加・変更**」
3. 「メディアを追加する」ボタン
4. 必要事項を入力：
   - メディア名：`サブスク図鑑`
   - サイトURL：`https://subzukan.com/`（公開済みであること）
   - メディア種別：`Webサイト`
   - カテゴリ：`エンタメ・趣味 > 動画配信`（または最も近いもの）
   - サイト紹介文：READMEに記載のサイト概要をベースに作成
5. 提出 → **A8の審査（3〜7日）** を待つ
6. 審査通過すると、メディア追加完了メールが届く

---

## ステップ 5: VOD系プログラムへの参加申請

審査通過後、以下のVODプログラムに順番に参加申請する。

### 申請優先度の高いプログラム（A8で実在を要確認）

| サービス | 想定プログラム名 | 単価目安 | 優先度 |
|---|---|---|---|
| U-NEXT | U-NEXT 31日間無料体験 | 1,000〜2,500円 | ★★★ |
| Hulu | Hulu 月額プラン | 800〜1,500円 | ★★★ |
| dアニメストア | dアニメストア 31日間無料 | 500〜1,200円 | ★★★ |
| DAZN | DAZN | 1,500〜3,000円 | ★★★ |
| Lemino | Lemino プレミアム | 800〜1,200円 | ★★ |
| ABEMA | ABEMAプレミアム | 800〜1,200円 | ★★ |
| FOD | FODプレミアム | 800〜1,200円 | ★★ |
| DMM TV | DMM TV | 500〜1,000円 | ★★ |
| TELASA | TELASA | 500〜800円 | ★ |
| WOWOW | WOWOWオンデマンド | 1,500〜2,500円 | ★ |

実際のプログラムIDは **ステップ5実行前に `search_a8_vod.py` で事前調査** すれば、
A8の検索画面で再検索する手間が省けます（後述）。

---

## ステップ 6: 提携リンクを取得（スクリプト実行）

参加申請が **承認** されたプログラムだけ、リンク取得スクリプトを実行する。

```powershell
cd C:\Users\ashib\vod-affiliate
python get_affiliate_link.py s00000XXXXX
```

`.a8_session.json` の認証Cookieを使ってA8の管理画面に自動アクセスし、
提携URL（`https://px.a8.net/svt/ejp?a8mat=...`）を出力する。

---

## ステップ 7: `vods_data.py` への反映

取得した提携URLを `vods_data.py` の各VODの `affiliate_url` フィールドに貼り付ける。
編集後：

```powershell
python create_new_vod_pages.py   # docs/services/ を再生成
python generate.py                # docs/index.html + docs/articles/ を再生成
```

---

## ステップ 8: 公開反映

```powershell
git add docs/ vods_data.py
git commit -m "Update: VODアフィリエイトリンク反映"
git push
```

GitHub Pages が自動でリビルドし、数分後に本番に反映される。

---

## 現時点で着手できる作業（ユーザー操作不要）

```powershell
cd C:\Users\ashib\vod-affiliate

# A. card-affiliate のセッションCookieを共用してプログラムIDを事前調査
python search_a8_vod.py

# B. 個別プログラムの提携URLを取得（A8参加承認後に使用）
python get_affiliate_link.py s00000XXXXX
```

`search_a8_vod.py` は A8 検索ページから「VOD」「動画配信」「U-NEXT」等のキーワードで
プログラムIDをリストアップし、`a8_vod_candidates.json` として保存します。

---

## トラブルシューティング

| 症状 | 対処 |
|---|---|
| `.a8_session.json` がない / 古い | `python login_a8.py` でブラウザログイン → セッション再保存 |
| メディア審査落ち | 記事が15本以上掲載済み・問い合わせ先・運営者情報が揃っているか確認 |
| プログラム参加申請却下 | サイトのジャンル整合性・記事の質を確認。再申請可能なものもある |
| 提携URLが取れない | A8側でメンテナンス中の可能性。時間を置いて再試行 |

---

## 参考：card-affiliate との関係

- A8アカウント・支払い口座は **共用**
- メディアは A8 の管理画面上で別物として登録
- セッションCookie（`.a8_session.json`）は同じものが両PJで使える
- プログラム参加申請は **メディアごと** に必要（card 用に承認されていても subzukan で再申請が必要）
