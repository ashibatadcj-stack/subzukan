"""
共通テンプレートヘルパ
- パンくず・JSON-LD・目次・FAQ・CTAバナー・著者ボックス・スコアバー等
- generate.py / create_new_vod_pages.py の双方から使う
"""
from __future__ import annotations
import json
import os
from html import escape
from pathlib import Path

from dotenv import load_dotenv

from content_data import EDITOR

# ルート .env を読み込む（GA_ID / GSC_VERIFICATION を環境変数で上書き可能に）
load_dotenv(Path(__file__).parent / ".env")

SITE_NAME = "サブスク図鑑"
SITE_URL = os.environ.get("SITE_URL", "https://subzukan.com").rstrip("/")
GA_ID = os.environ.get("GA_ID", "")  # 未設定なら gtag タグを出力しない
GSC_VERIFICATION = os.environ.get("GSC_VERIFICATION", "")  # Search Console所有権確認
SUBSCRIPT = "編集部レビューに基づく独立比較"


# --------------------------------------------------------------------
# 共通HTMLパーツ
# --------------------------------------------------------------------
def head_block(*, title: str, description: str, keywords: str = "",
               canonical_path: str = "", json_ld: str = "",
               extra_css: str = "") -> str:
    """ <head>...</head> を返す。canonical_path は "/services/u-next.html" のように先頭スラ付き。"""
    canonical_url = f'{SITE_URL}{canonical_path}' if canonical_path else SITE_URL

    # GA_ID が設定されていれば gtag タグを生成
    ga_block = ""
    if GA_ID:
        ga_block = (
            f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>\n'
            f"  <script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}"
            f"gtag('js',new Date());gtag('config','{GA_ID}');</script>"
        )

    # Search Console 所有権確認のメタタグ
    gsc_meta = (
        f'<meta name="google-site-verification" content="{escape(GSC_VERIFICATION)}">'
        if GSC_VERIFICATION else ""
    )

    return f"""<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(title)}</title>
  <meta name="description" content="{escape(description)}">
  {f'<meta name="keywords" content="{escape(keywords)}">' if keywords else ''}
  {gsc_meta}
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{escape(title)}">
  <meta property="og:description" content="{escape(description)}">
  <meta property="og:url" content="{canonical_url}">
  <meta property="og:site_name" content="{SITE_NAME}">
  <meta name="twitter:card" content="summary_large_image">
  {ga_block}
  <link rel="stylesheet" href="{extra_css}">
  {json_ld}
</head>"""


def site_header(*, css_prefix: str = "") -> str:
    """共通ヘッダー。css_prefix はトップなら ""、配下ページなら "../" を渡す。"""
    return f"""<header class="site-header">
  <a href="{css_prefix}index.html" class="site-logo"><span class="site-logo-icon">📘</span><span>{SITE_NAME}</span></a>
  <nav class="site-nav">
    <a href="{css_prefix}index.html#ranking">ランキング</a>
    <a href="{css_prefix}index.html#use-cases">目的別</a>
    <a href="{css_prefix}index.html#how-to-choose">選び方</a>
    <a href="{css_prefix}index.html#faq">FAQ</a>
  </nav>
</header>"""


def pr_disclosure(*, css_prefix: str = "") -> str:
    """ファーストビュー用のPR表記バッジ（景表法ステマ規制対応・必須）。
    全ページのヘッダー直下またはヒーロー直下に配置する。"""
    return f"""<div class="pr-disclosure" role="region" aria-label="広告表記">
  <span class="pr-badge">PR</span>
  <span class="pr-text">本ページはアフィリエイト広告を含みます。編集部の独自審査に基づき選定しています。<a href="{css_prefix}about.html">編集方針</a></span>
</div>"""


def site_footer(*, css_prefix: str = "") -> str:
    return f"""<footer class="site-footer">
  <div class="site-footer-inner">
    <p class="site-footer-brand">📘 {SITE_NAME}</p>
    <p class="site-footer-tag">{SUBSCRIPT}</p>
    <ul class="site-footer-links">
      <li><a href="{css_prefix}index.html">トップ</a></li>
      <li><a href="{css_prefix}about.html">当サイトについて</a></li>
      <li><a href="{css_prefix}about.html#editorial-policy">編集方針</a></li>
      <li><a href="{css_prefix}about.html#disclosure">広告表記</a></li>
    </ul>
    <p class="site-footer-disclaimer">※本サイトはアフィリエイト広告を含みます。掲載情報は最新月の代表値で、料金・作品数の確定値は各公式サイトをご確認ください。</p>
  </div>
</footer>
<script src="{css_prefix}assets/common.js"></script>"""


# --------------------------------------------------------------------
# パンくず
# --------------------------------------------------------------------
def breadcrumb(items: list[tuple[str, str]]) -> str:
    """items: [(label, href), ...]。最後の項目はリンクなし。"""
    parts = []
    for i, (label, href) in enumerate(items):
        if i == len(items) - 1 or not href:
            parts.append(f'<span class="breadcrumb-current">{escape(label)}</span>')
        else:
            parts.append(f'<a href="{href}">{escape(label)}</a>')
    return f'<nav class="breadcrumb">{" / ".join(parts)}</nav>'


# --------------------------------------------------------------------
# 目次（H2見出しリストから生成）
# --------------------------------------------------------------------
def toc(sections: list[str]) -> str:
    if not sections:
        return ""
    items = "\n      ".join(
        f'<li><a href="#sec-{i}">{escape(h)}</a></li>'
        for i, h in enumerate(sections)
    )
    return f"""<aside class="toc">
  <p class="toc-title">📑 目次</p>
  <ol class="toc-list">
      {items}
  </ol>
</aside>"""


# --------------------------------------------------------------------
# 「この記事でわかること」ボックス
# --------------------------------------------------------------------
def takeaways_box(items: list[str]) -> str:
    if not items:
        return ""
    lis = "\n      ".join(f'<li>{escape(s)}</li>' for s in items)
    return f"""<aside class="takeaways">
  <p class="takeaways-title">✅ この記事でわかること</p>
  <ul>
      {lis}
  </ul>
</aside>"""


# --------------------------------------------------------------------
# 記事メタ（更新日・著者・カテゴリ）
# --------------------------------------------------------------------
def article_meta(*, category: str, published_at: str, updated_at: str, author: str) -> str:
    return f"""<div class="article-meta">
  <span class="meta-cat">{escape(category)}</span>
  <span class="meta-date">📅 公開: {escape(published_at)}</span>
  <span class="meta-date meta-updated">🔄 更新: {escape(updated_at)}</span>
  <span class="meta-author">✍ {escape(author)}</span>
</div>"""


# --------------------------------------------------------------------
# FAQ ブロック
# --------------------------------------------------------------------
def faq_block(faqs: list[dict], heading: str = "よくある質問") -> str:
    if not faqs:
        return ""
    items = "\n  ".join(
        f"""<details class="faq-item">
    <summary>{escape(f['q'])}</summary>
    <div class="faq-answer">{escape(f['a'])}</div>
  </details>"""
        for f in faqs
    )
    return f"""<section class="faq-section">
  <h2 id="faq-section">{escape(heading)}</h2>
  {items}
</section>"""


# --------------------------------------------------------------------
# CTA バナー（クイズ診断への誘導）
# --------------------------------------------------------------------
def cta_banner(css_prefix: str = "../") -> str:
    return f"""<aside class="cta-banner">
  <p class="cta-banner-title">🎯 あなたに最適なサブスクは？</p>
  <p class="cta-banner-desc">3問の診断クイズで、編集部が10サービスから1本を提案します。</p>
  <a href="{css_prefix}index.html#quiz" class="cta-banner-btn">無料で診断する</a>
</aside>"""


# --------------------------------------------------------------------
# 編集部ボックス（E-E-A-T訴求）
# --------------------------------------------------------------------
def editor_box() -> str:
    return f"""<aside class="editor-box">
  <p class="editor-name">✍ {escape(EDITOR['name'])}</p>
  <p class="editor-role">{escape(EDITOR['role'])}</p>
  <p class="editor-bio">{escape(EDITOR['bio'])}</p>
  <ul class="editor-stats">
    <li><strong>{EDITOR['experience_years']}</strong> 年</li>
    <li><strong>{EDITOR['reviewed_services']}</strong> 社レビュー済</li>
    <li><strong>毎月</strong> 情報更新</li>
  </ul>
</aside>"""


# --------------------------------------------------------------------
# スコアバー
# --------------------------------------------------------------------
def score_bars(scores: dict, axes: list[dict]) -> str:
    """scores: {"value":4.0, "library":5.0, ...}, axes: SCORE_AXES"""
    rows = []
    for ax in axes:
        v = scores.get(ax["key"], 0)
        pct = int(v / 5.0 * 100)
        rows.append(
            f'<li class="score-row">'
            f'<span class="score-label">{escape(ax["label"])}</span>'
            f'<span class="score-bar"><span class="score-fill" style="width:{pct}%;"></span></span>'
            f'<span class="score-num">{v:.1f}</span>'
            f'</li>'
        )
    return f'<ul class="score-list">{"".join(rows)}</ul>'


# --------------------------------------------------------------------
# 比較表（VODのリストを受けて軸を並べる）
# --------------------------------------------------------------------
def comparison_table(vods: list[dict], axes: list[dict], *, link_prefix: str = "services/") -> str:
    if not vods:
        return ""
    head_row = "<tr><th>サービス</th>" + "".join(
        f'<th>{escape(ax["label"])}</th>' for ax in axes
    ) + "</tr>"

    body_rows = []
    for v in vods:
        cells = [f'<td><a href="{link_prefix}{v["id"]}.html">{v.get("icon","")} {escape(v["name"])}</a></td>']
        for ax in axes:
            val = v.get(ax["key"], "")
            if ax["key"] == "free_trial_days":
                val = f'{val}日' if val else 'なし'
            elif ax["key"] == "simultaneous_streams":
                val = f'{val}台'
            cells.append(f'<td>{escape(str(val))}</td>')
        body_rows.append("<tr>" + "".join(cells) + "</tr>")

    return f"""<div class="compare-table-wrap">
  <table class="compare-table">
    <thead>{head_row}</thead>
    <tbody>{''.join(body_rows)}</tbody>
  </table>
</div>"""


# --------------------------------------------------------------------
# pricing_plans を表で表示
# --------------------------------------------------------------------
def pricing_table(plans: list[dict]) -> str:
    if not plans:
        return ""
    rows = "".join(
        f'<tr><td>{escape(p["name"])}</td><td>{escape(p["fee"])}</td><td>{escape(p.get("note",""))}</td></tr>'
        for p in plans
    )
    return f"""<div class="pricing-table-wrap">
  <table class="pricing-table">
    <thead><tr><th>プラン</th><th>料金</th><th>備考</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>"""


# --------------------------------------------------------------------
# Pros / Cons の2カラム
# --------------------------------------------------------------------
def pros_cons(pros: list[str], cons: list[str]) -> str:
    p = "".join(f'<li>{escape(s)}</li>' for s in pros)
    c = "".join(f'<li>{escape(s)}</li>' for s in cons)
    return f"""<div class="pros-cons">
  <div class="pros-box">
    <h3>👍 メリット</h3>
    <ul class="pros-list">{p}</ul>
  </div>
  <div class="cons-box">
    <h3>👎 デメリット</h3>
    <ul class="cons-list">{c}</ul>
  </div>
</div>"""


# --------------------------------------------------------------------
# ステップリスト（登録手順・解約手順）
# --------------------------------------------------------------------
def step_list(steps: list[dict], *, title: str = "") -> str:
    items = "\n  ".join(
        f"""<li class="step-item">
    <span class="step-num">{i+1}</span>
    <div class="step-body">
      <p class="step-title">{escape(s['title'])}</p>
      <p class="step-desc">{escape(s['desc'])}</p>
    </div>
  </li>"""
        for i, s in enumerate(steps)
    )
    title_html = f'<h3 class="step-title-heading">{escape(title)}</h3>' if title else ''
    return f"""<div class="step-list-wrap">
  {title_html}
  <ol class="step-list">
  {items}
  </ol>
</div>"""


# --------------------------------------------------------------------
# 関連サービスカード
# --------------------------------------------------------------------
def related_service_cards(vods: list[dict], *, link_prefix: str = "../services/") -> str:
    if not vods:
        return ""
    cards = "".join(
        f"""<a class="related-card" href="{link_prefix}{v['id']}.html">
    <span class="related-icon">{v.get('icon','')}</span>
    <strong>{escape(v['name'])}</strong>
    <span class="related-fee">月額 {escape(v['monthly_fee'])}</span>
    <span class="related-tag">{escape(v.get('difficulty',''))}</span>
  </a>"""
        for v in vods
    )
    return f"""<section class="related">
  <h2>関連サービス</h2>
  <div class="related-cards">{cards}</div>
</section>"""


# --------------------------------------------------------------------
# JSON-LD ジェネレータ
# --------------------------------------------------------------------
def json_ld_breadcrumb(items: list[tuple[str, str]]) -> dict:
    """items: [(name, full_url), ...]"""
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": url}
            for i, (name, url) in enumerate(items)
        ],
    }


def json_ld_article(*, title: str, description: str, url: str,
                    published_at: str, updated_at: str, author: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "url": url,
        "datePublished": published_at,
        "dateModified": updated_at,
        "author": {"@type": "Organization", "name": author},
        "publisher": {"@type": "Organization", "name": SITE_NAME, "url": SITE_URL},
    }


def json_ld_person(editor: dict) -> dict:
    """編集者プロフィールをschema.org Person形式で出力（E-E-A-T訴求用）"""
    return {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": editor["name"],
        "jobTitle": editor.get("jobTitle", "編集"),
        "description": editor.get("bio", ""),
        "knowsAbout": editor.get("knowsAbout", []),
        "worksFor": {
            "@type": "Organization",
            "name": SITE_NAME,
            "url": SITE_URL,
        },
    }


def json_ld_faq(faqs: list[dict]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f["q"],
             "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
            for f in faqs
        ],
    }


def json_ld_howto_signup(vod: dict, url: str) -> dict:
    """登録手順のHowTo schema（リッチリザルト獲得用）"""
    name = vod["name"]
    trial = vod.get("free_trial_days", 0)
    return {
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": f"{name}の登録方法（4ステップ）",
        "description": f"{name}に新規登録し" + (f"{trial}日間の無料体験を始める" if trial else "サービス利用を開始する") + "までの手順",
        "totalTime": "PT5M",
        "estimatedCost": {
            "@type": "MonetaryAmount",
            "currency": "JPY",
            "value": "".join(c for c in str(vod.get("monthly_fee", "0")) if c.isdigit()) or "0",
        },
        "step": [
            {"@type": "HowToStep", "position": 1, "name": "公式サイトにアクセス",
             "text": f"{name}の公式サイトを開き、「{('無料体験を始める' if trial else '今すぐ登録')}」ボタンをタップ。", "url": vod.get("official_url", url)},
            {"@type": "HowToStep", "position": 2, "name": "メールアドレス登録",
             "text": "メールアドレスを入力し、ログイン用のパスワードを設定する。"},
            {"@type": "HowToStep", "position": 3, "name": "支払い方法の登録",
             "text": "クレジットカード/キャリア決済/Apple ID/Google Playのいずれかを選択し、必要情報を入力。" + (f"無料体験中は課金されません。" if trial else "")},
            {"@type": "HowToStep", "position": 4, "name": "視聴開始",
             "text": f"登録完了後、すぐに{name}の視聴・利用が開始可能。スマホアプリの併用もおすすめ。"},
        ],
    }


def json_ld_howto_cancel(vod: dict, url: str) -> dict:
    """解約手順のHowTo schema"""
    name = vod["name"]
    return {
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": f"{name}の解約方法（4ステップ）",
        "description": f"{name}を公式サイトから解約する手順。違約金なし・24時間いつでも可能。",
        "totalTime": "PT3M",
        "step": [
            {"@type": "HowToStep", "position": 1, "name": "公式サイトにログイン",
             "text": f"{name}の公式サイト（PC/スマホブラウザ）にログイン。", "url": vod.get("official_url", url)},
            {"@type": "HowToStep", "position": 2, "name": "アカウント設定を開く",
             "text": "マイページ → アカウント設定 → 契約情報（または視聴プラン）に進む。"},
            {"@type": "HowToStep", "position": 3, "name": "解約を選択",
             "text": "「解約する」「プランを解約」ボタンをタップ。アンケートが表示される場合は任意で回答。"},
            {"@type": "HowToStep", "position": 4, "name": "解約完了の確認",
             "text": "解約完了メールが届いたら手続き終了。日割り返金は基本的にありません。"},
        ],
    }


def json_ld_product(vod: dict, url: str) -> dict:
    """個別VODページ用の Product/SoftwareApplication 型JSON-LD"""
    scores = vod.get("recommend_score", {})
    avg = sum(scores.values()) / len(scores) if scores else 0
    return {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": vod["name"],
        "description": vod.get("tagline", ""),
        "url": url,
        "brand": {"@type": "Brand", "name": vod["name"]},
        "offers": {
            "@type": "Offer",
            "price": "".join(c for c in str(vod["monthly_fee"]) if c.isdigit()) or "0",
            "priceCurrency": "JPY",
            "url": vod.get("official_url", url),
        },
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": f"{avg:.1f}",
            "bestRating": "5",
            "worstRating": "1",
            "ratingCount": "1",
            "reviewCount": "1",
        } if scores else None,
    }


# --------------------------------------------------------------------
# 3つの特集ピラーカード（card版踏襲）
# --------------------------------------------------------------------
def pillar_card_block(features: list[dict]) -> str:
    cards = []
    for f in features:
        cards.append(f"""<a class="pillar-card" href="{f['link']}" style="--pillar-color:{f['color']};--pillar-bg:{f['bg_tint']}">
      <span class="pillar-icon">{f['icon']}</span>
      <strong class="pillar-title">{escape(f['title'])}</strong>
      <span class="pillar-desc">{escape(f['description'])}</span>
      <span class="pillar-cta">完全ガイドを見る →</span>
    </a>""")
    return f"""<section class="zone zone-pillar">
  <div class="zone-inner">
    <div class="zone-header">
      <h2>📚 完全ガイド：3つの特集</h2>
      <p>用途別にVOD・サブスクを横断比較できる総合ガイド</p>
    </div>
    <div class="pillar-grid">{''.join(cards)}</div>
  </div>
</section>"""


# --------------------------------------------------------------------
# 初心者向けクイックスタート4枚
# --------------------------------------------------------------------
def quick_start_block(cards: list[dict]) -> str:
    items = []
    for c in cards:
        items.append(f"""<a class="quickstart-card" href="{c['link']}" style="--qs-accent:{c['accent']}">
      <span class="quickstart-icon" style="background:{c['accent']}1a;color:{c['accent']}">{c['icon']}</span>
      <span class="quickstart-text">
        <strong>{escape(c['title'])}</strong>
        <em>{escape(c['subtitle'])}</em>
      </span>
    </a>""")
    return f"""<section class="zone zone-quickstart">
  <div class="zone-inner">
    <div class="zone-header">
      <h2>🚀 初めてサブスクを選ぶ方へ</h2>
      <p>まずは4つの記事で基本を押さえる</p>
    </div>
    <div class="quickstart-grid">{''.join(items)}</div>
  </div>
</section>"""


# --------------------------------------------------------------------
# コンパクトなTOP5スペック表（card版風）
# --------------------------------------------------------------------
def compact_vod_table(vods: list[dict], *, link_prefix: str = "services/") -> str:
    rows = []
    for i, v in enumerate(vods, 1):
        scores = v.get("recommend_score", {})
        avg = sum(scores.values()) / len(scores) if scores else 0
        rows.append(f"""<a class="compact-vod-card" href="{link_prefix}{v['id']}.html">
      <span class="compact-rank">{i}位</span>
      <span class="compact-icon">{v.get('icon','')}</span>
      <div class="compact-body">
        <strong class="compact-name">{escape(v['name'])}</strong>
        <span class="compact-tag">{escape(v.get('difficulty',''))}</span>
        <div class="compact-specs">
          <span><em>月額</em>{escape(v['monthly_fee'])}</span>
          <span><em>無料体験</em>{f"{v['free_trial_days']}日" if v['free_trial_days'] else "なし"}</span>
          <span><em>同時視聴</em>{v.get('simultaneous_streams','-')}台</span>
          <span><em>スコア</em>⭐{avg:.1f}</span>
        </div>
      </div>
      <span class="compact-cta">詳細 →</span>
    </a>""")
    return f'<div class="compact-vod-list">{"".join(rows)}</div>'


# --------------------------------------------------------------------
# 記事カードグリッド（画像付・card版踏襲）
# --------------------------------------------------------------------
def article_card_grid(articles: list[dict], categories: dict, *, link_prefix: str = "articles/") -> str:
    # カテゴリごとの色（CSSで定義済みのクラス名）
    cat_color_class = {
        "guide": "blue",
        "compare": "purple",
        "attribute": "green",
        "purpose": "orange",
        "service-detail": "red",
    }
    cards = []
    for a in articles:
        img = a.get("image_url") or ""
        cat_label = categories.get(a["category_slug"], a["category_slug"])
        cat_class = cat_color_class.get(a["category_slug"], "")
        # サマリの最初の100字
        summary = (a.get("summary") or a.get("description") or "")[:80]
        # CLS改善：width/height を明示
        img_tag = (
            f'<img class="article-card-img" src="{img}" alt="{escape(a["title"])}" '
            f'width="600" height="338" loading="lazy">'
        ) if img else '<div class="article-card-img article-card-noimg"></div>'
        cards.append(f"""<a class="article-card" href="{link_prefix}{a['slug']}.html">
      <div class="article-card-img-wrap">
        {img_tag}
        <span class="article-cat {cat_class}">{escape(cat_label)}</span>
      </div>
      <div class="article-card-body">
        <strong class="article-card-title">{escape(a['title'])}</strong>
        <span class="article-card-summary">{escape(summary)}…</span>
        <span class="article-card-meta">📅 {escape(a.get('updated_at',''))}</span>
      </div>
    </a>""")
    return f"""<section class="zone zone-articles">
  <div class="zone-inner">
    <div class="zone-header">
      <h2>📰 全{len(articles)}記事一覧</h2>
      <p>カテゴリ別に整理した解説記事</p>
    </div>
    <div class="article-card-grid">{''.join(cards)}</div>
  </div>
</section>"""


# --------------------------------------------------------------------
# A8バナーブロック（提携中プログラムの公式バナー埋め込み枠）
# --------------------------------------------------------------------
def a8_banner_block(*, vod: dict | None = None, label: str = "おすすめのサブスク") -> str:
    """提携中の公式バナーを埋め込む枠。vod.affiliate_url と icon を使う。"""
    if not vod or not vod.get("affiliate_url"):
        return ""
    return f"""<aside class="a8-banner-section">
  <div class="a8-banner-label">{escape(label)}</div>
  <a class="a8-banner-card" href="{vod['affiliate_url']}" rel="sponsored noopener" target="_blank">
    <span class="a8-banner-icon">{vod.get('icon','')}</span>
    <div class="a8-banner-body">
      <strong>{escape(vod['name'])}</strong>
      <span>{escape(vod.get('tagline',''))}</span>
      <em>月額 {escape(vod['monthly_fee'])} {f"・{vod['free_trial_days']}日無料体験" if vod.get('free_trial_days') else ""}</em>
    </div>
    <span class="a8-banner-cta">▶ 公式サイトへ</span>
  </a>
</aside>"""


# --------------------------------------------------------------------
# 申込前チェックリスト（個別ページ用）
# --------------------------------------------------------------------
def signup_checklist_block(vod: dict) -> str:
    items = [
        "クレジットカードが手元にある（無料体験でも登録時に必要）",
        f"解約期限（{vod.get('free_trial_days','')}日後）をスマホのカレンダーに登録した" if vod.get('free_trial_days') else "解約方法を確認した",
        "視聴したいデバイスでアプリが対応しているか確認した",
        "Wi-Fi環境または十分なモバイルデータ容量がある",
    ]
    lis = "\n      ".join(f'<li><label><input type="checkbox" disabled> {escape(it)}</label></li>' for it in items)
    return f"""<section class="vod-section signup-checklist">
  <h2>📝 申込前チェックリスト</h2>
  <p class="section-lead">下記すべてOKなら、安心して申し込めます。</p>
  <ul class="checklist">
      {lis}
  </ul>
</section>"""


# --------------------------------------------------------------------
# 関連記事画像カードグリッド
# --------------------------------------------------------------------
def related_articles_grid(articles: list[dict], categories: dict, *, link_prefix: str = "../articles/") -> str:
    if not articles:
        return ""
    cat_color_class = {
        "guide": "blue", "compare": "purple", "attribute": "green",
        "purpose": "orange", "service-detail": "red",
    }
    cards = []
    for a in articles[:4]:
        img = a.get("image_url") or ""
        cat_label = categories.get(a["category_slug"], a["category_slug"])
        cat_class = cat_color_class.get(a["category_slug"], "")
        img_tag = (
            f'<img class="article-card-img" src="{img}" alt="{escape(a["title"])}" '
            f'width="600" height="338" loading="lazy">'
        ) if img else '<div class="article-card-img article-card-noimg"></div>'
        cards.append(f"""<a class="article-card article-card-sm" href="{link_prefix}{a['slug']}.html">
      <div class="article-card-img-wrap">
        {img_tag}
        <span class="article-cat {cat_class}">{escape(cat_label)}</span>
      </div>
      <div class="article-card-body">
        <strong class="article-card-title">{escape(a['title'])}</strong>
      </div>
    </a>""")
    return f"""<section class="related related-articles">
  <h2>📖 関連記事</h2>
  <div class="article-card-grid related-grid">{''.join(cards)}</div>
</section>"""


# --------------------------------------------------------------------
# 編集部CTAブロック（記事ページ末尾用・card版踏襲）
# --------------------------------------------------------------------
def editor_cta_block(*, css_prefix: str = "../") -> str:
    return f"""<aside class="editor-cta">
  <div class="editor-cta-icon">✍</div>
  <div class="editor-cta-body">
    <strong>{escape(EDITOR['name'])}より</strong>
    <p>14社を実契約してきた編集部が、3問の質問に答えるだけで「あなたに最適な1本」を提案します。迷ったらまず診断クイズを試してみてください。</p>
    <a href="{css_prefix}index.html#quiz" class="editor-cta-btn">🎯 無料で診断する（1分）</a>
  </div>
</aside>"""


# --------------------------------------------------------------------
# スティッキーサイドバー目次（PC用・記事ページ用）
# --------------------------------------------------------------------
def toc_sticky(sections: list[str]) -> str:
    if not sections:
        return ""
    items = "\n      ".join(
        f'<li><a href="#sec-{i}">{escape(h)}</a></li>'
        for i, h in enumerate(sections)
    )
    return f"""<aside class="toc-sticky">
  <p class="toc-title">📑 目次</p>
  <ol>
      {items}
  </ol>
</aside>"""


# --------------------------------------------------------------------
# 記事サイドバー（card版踏襲）：TOC + 診断CTA + 人気記事 + おすすめVOD
# --------------------------------------------------------------------
def article_sidebar(*, sections: list[str], popular_articles: list[dict],
                    vod_picks: list[dict], css_prefix: str = "../") -> str:
    """記事ページの右カラム。stickyにして縦長記事に追従させる。"""
    # 1) TOC
    toc_items = "".join(
        f'<li><a href="#sec-{i}">{escape(h)}</a></li>'
        for i, h in enumerate(sections)
    )
    toc_block = f"""<div class="sidebar-widget sidebar-toc">
  <p class="sidebar-widget-title">📑 目次</p>
  <ul class="sidebar-toc-list">{toc_items}</ul>
</div>""" if sections else ""

    # 2) 診断CTA
    cta_block = f"""<div class="sidebar-widget sidebar-cta">
  <p class="sidebar-cta-title">🎯 サブスク選びに迷ったら</p>
  <p class="sidebar-cta-desc">3問の質問に答えるだけで、あなたに最適な1本を提案します。</p>
  <a class="sidebar-cta-btn" href="{css_prefix}index.html#quiz">無料診断スタート</a>
</div>"""

    # 3) 人気記事TOP5
    popular_lis = "".join(
        f'<li><span class="popular-num">{i+1}</span>'
        f'<a href="{css_prefix}articles/{a["slug"]}.html">{escape(a["title"])}</a></li>'
        for i, a in enumerate(popular_articles)
    ) if popular_articles else ""
    popular_block = f"""<div class="sidebar-widget sidebar-popular">
  <p class="sidebar-widget-title">🔥 人気記事TOP5</p>
  <ul class="sidebar-popular-list">{popular_lis}</ul>
</div>""" if popular_articles else ""

    # 4) おすすめVOD3社（提携中の公式リンクへ）
    vod_lis = []
    for pick in vod_picks:
        v = pick["vod"]
        tag = pick.get("tag", "")
        href = v.get("affiliate_url") or f'{css_prefix}services/{v["id"]}.html'
        rel = ' rel="sponsored noopener" target="_blank"' if v.get("affiliate_url") else ""
        scores = v.get("recommend_score", {})
        avg = sum(scores.values()) / len(scores) if scores else 0
        vod_lis.append(
            f'<a class="sidebar-vod-pick" href="{href}"{rel}>'
            f'<span class="sidebar-vod-tag">{escape(tag)}</span>'
            f'<span class="sidebar-vod-row">'
            f'<span class="sidebar-vod-icon">{v.get("icon","")}</span>'
            f'<span class="sidebar-vod-body">'
            f'<strong>{escape(v["name"])}</strong>'
            f'<em>月額 {escape(v["monthly_fee"])} ・⭐{avg:.1f}</em>'
            f'</span></span></a>'
        )
    vod_block = f"""<div class="sidebar-widget sidebar-vods">
  <p class="sidebar-widget-title">🎬 編集部おすすめVOD</p>
  <div class="sidebar-vod-list">{''.join(vod_lis)}</div>
</div>""" if vod_picks else ""

    return f"""<aside class="article-sidebar">
  {toc_block}
  {cta_block}
  {vod_block}
  {popular_block}
</aside>"""


def render_json_ld(*objs) -> str:
    """複数のJSON-LDオブジェクトを <script> タグで連結。Noneは無視。"""
    blocks = []
    for o in objs:
        if not o:
            continue
        # None値を除去
        cleaned = {k: v for k, v in o.items() if v is not None}
        blocks.append(
            '<script type="application/ld+json">'
            + json.dumps(cleaned, ensure_ascii=False)
            + "</script>"
        )
    return "\n  ".join(blocks)
