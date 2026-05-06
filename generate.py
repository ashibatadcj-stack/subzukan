"""
サブスク図鑑 ページ生成スクリプト（リッチ版）
- docs/index.html  トップ：10項目フルセット
- docs/articles/<slug>.html  記事
"""
import json
from pathlib import Path
from html import escape

from dotenv import load_dotenv

from vods_data import VODS, QUIZ_QUESTIONS, COMPARE_AXES, SCORE_AXES
from articles_data import ARTICLES, CATEGORIES
from content_data import (
    EDITOR, EDITORS_DETAIL, SITE_ABOUT,
    HOW_TO_CHOOSE, USE_CASES,
    THREE_SECOND_PICKS, TAG_CLOUD, BASIC_KNOWLEDGE,
    NEWS_ITEMS, TOP_FAQS_GROUPED,
)
import templates as T

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

DOCS_DIR = BASE_DIR / "docs"
ARTICLES_DIR = DOCS_DIR / "articles"

VODS_BY_ID = {v["id"]: v for v in VODS}


def fee_int(v: dict) -> int:
    s = "".join(c for c in str(v.get("monthly_fee", "0")) if c.isdigit())
    return int(s) if s else 999999


def avg_score(scores: dict) -> float:
    return sum(scores.values()) / len(scores) if scores else 0


# ====================================================================
# トップページ
# ====================================================================
def render_index() -> str:
    canonical_path = "/"
    page_url = T.SITE_URL + "/"

    # FAQの平坦リスト（JSON-LD用）
    flat_faqs = [item for g in TOP_FAQS_GROUPED for item in g["items"]]

    json_ld = T.render_json_ld(
        T.json_ld_breadcrumb([("トップ", page_url)]),
        T.json_ld_faq(flat_faqs),
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": T.SITE_NAME,
            "url": T.SITE_URL,
            "description": "国内主要サブスクを実契約レビューで紹介する図鑑型メディア",
        },
        {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": "主要VOD10社",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": i + 1,
                    "url": f"{T.SITE_URL}/services/{v['id']}.html",
                    "name": v["name"],
                }
                for i, v in enumerate(VODS)
            ],
        },
    )

    head = T.head_block(
        title=f"【2026年最新】{T.SITE_NAME} | 国内VOD11社を実契約レビューで比較する図鑑",
        description="国内主要サブスク（VOD・動画配信サービス）を実契約レビュー＋比較表で紹介する図鑑型メディア。3問の診断クイズで最適な1本が見つかります。",
        keywords="サブスク,VOD,動画配信,比較,診断,おすすめ,U-NEXT,Hulu,DAZN,dアニメストア,Lemino,ABEMA",
        canonical_path=canonical_path,
        json_ld=json_ld,
        extra_css="assets/common.css",
    )

    sections = [
        _render_hero(),
        _render_three_second_picks(),
        _render_quiz(),
        _render_vod_profiles(),
        _render_ranking_tabs(),
        _render_compare_table(),
        _render_use_cases(),
        _render_tag_cloud(),
        _render_how_to_choose(),
        _render_basic_knowledge(),
        _render_news(),
        _render_articles_grid(),
        _render_faq_grouped(),
        _render_editors_detail(),
        _render_about_block(),
    ]

    sticky_cta = """<aside class="sticky-cta" id="stickyCta" hidden>
  <a href="#quiz" class="sticky-cta-btn">🎯 無料診断する（3問・1分）</a>
</aside>"""

    body = f"""<body>
{T.site_header()}
{T.pr_disclosure()}
{sections[0]}
<main class="container container-wide">
  {''.join(sections[1:])}
</main>
{T.site_footer()}
{sticky_cta}
{_render_quiz_script()}
</body>"""

    return f"<!DOCTYPE html>\n<html lang=\"ja\">\n{head}\n{body}\n</html>"


# --------------------------------------------------------------------
# 1. ヒーロー（大型化＋VODロゴクラスター）
# --------------------------------------------------------------------
def _render_hero() -> str:
    logo_chips = "".join(
        f'<span class="logo-chip">{v.get("icon","")}<span>{escape(v["name"])}</span></span>'
        for v in VODS
    )
    return f"""<section class="hero hero-xl">
  <div class="hero-inner">
    <span class="hero-badge">📘 国内主要10社の実契約レビュー</span>
    <h1>あなたに最適なサブスクが<br><span class="hero-h1-em">3問でわかる</span><br>VOD図鑑</h1>
    <p class="hero-sub">月額・作品数・無料体験を実視聴ベースで整理。<br>編集部が10サービスから1本を提案します。</p>
    <div class="hero-stats">
      <div><strong>{len(VODS)}</strong><span>サービス比較</span></div>
      <div><strong>{len(ARTICLES)}</strong><span>解説記事</span></div>
      <div><strong>{EDITOR['experience_years']}</strong><span>年の運営</span></div>
      <div><strong>毎月</strong><span>料金チェック</span></div>
    </div>
    <a href="#quiz" class="hero-cta hero-cta-xl">🎯 無料で診断を始める</a>
    <p class="hero-cta-note">※ 1分・登録不要・スマホOK</p>
    <div class="hero-logos">
      <p class="hero-logos-title">取扱サービス</p>
      <div class="hero-logos-list">{logo_chips}</div>
    </div>
  </div>
</section>"""


# --------------------------------------------------------------------
# 2. 3秒で結論（4タイプ即決バナー）
# --------------------------------------------------------------------
def _render_three_second_picks() -> str:
    cards = []
    for p in THREE_SECOND_PICKS:
        v = VODS_BY_ID.get(p["vod_id"])
        if not v:
            continue
        cards.append(f"""<a class="pick-card" href="services/{v['id']}.html">
      <span class="pick-label">{escape(p['label'])}</span>
      <div class="pick-vod">
        <span class="pick-icon">{v.get('icon','')}</span>
        <div>
          <strong>{escape(v['name'])}</strong>
          <span class="pick-headline">{escape(p['headline'])}</span>
        </div>
      </div>
      <p class="pick-reason">{escape(p['reason'])}</p>
      <div class="pick-meta">
        <span>月額 {escape(v['monthly_fee'])}</span>
        <span>{f"{v['free_trial_days']}日無料" if v['free_trial_days'] else '体験なし'}</span>
      </div>
      <span class="pick-cta">▶ 詳細を見る</span>
    </a>""")
    return f"""<section class="top-section three-sec-section" id="three-sec">
  <h2>⚡ 3秒で結論：あなたのタイプ別TOP1</h2>
  <p class="section-lead">迷っている時間はもったいない。タイプ別に編集部の最有力候補を即提示します。</p>
  <div class="pick-grid">{''.join(cards)}</div>
</section>"""


# --------------------------------------------------------------------
# 3. クイズ
# --------------------------------------------------------------------
def _render_quiz() -> str:
    return f"""<section class="quiz-card" id="quiz">
  <span class="quiz-eyebrow">🎯 編集部が提案</span>
  <h2 class="quiz-heading">3問の質問でぴったりの1本が見つかります</h2>
  <div class="step-indicator">質問 <span id="stepNum">1</span> / {len(QUIZ_QUESTIONS)}</div>
  <div class="progress-bar"><div class="progress-fill" id="progressFill" style="width: {int(100 / len(QUIZ_QUESTIONS))}%;"></div></div>
  <h3 class="question" id="questionText"></h3>
  <div class="options" id="options"></div>
</section>
<section class="result-section" id="result"></section>"""


# --------------------------------------------------------------------
# 4. 大型VODプロフィールカード
# --------------------------------------------------------------------
def _render_vod_profiles() -> str:
    sorted_vods = sorted(VODS, key=lambda v: -avg_score(v.get("recommend_score", {})))
    cards = []
    for i, v in enumerate(sorted_vods, 1):
        avg = avg_score(v.get("recommend_score", {}))
        feats = "".join(f'<li>{escape(s)}</li>' for s in v.get("features", [])[:3])
        cards.append(f"""<article class="profile-card">
      <div class="profile-rank">No.{i}</div>
      <div class="profile-head">
        <span class="profile-icon">{v.get('icon','')}</span>
        <div class="profile-head-text">
          <span class="profile-tag">{escape(v.get('difficulty',''))}</span>
          <h3>{escape(v['name'])}</h3>
          <p class="profile-tagline">{escape(v.get('tagline',''))}</p>
        </div>
        <div class="profile-score">
          <span class="profile-score-num">{avg:.1f}</span>
          <span class="profile-score-max">/5.0</span>
        </div>
      </div>
      <div class="profile-meta">
        <div><span>月額</span><strong>{escape(v['monthly_fee'])}</strong></div>
        <div><span>無料体験</span><strong>{f"{v['free_trial_days']}日" if v['free_trial_days'] else 'なし'}</strong></div>
        <div><span>同時視聴</span><strong>{v.get('simultaneous_streams','-')}台</strong></div>
        <div><span>画質</span><strong>{escape(v.get('quality','-').split(' / ')[0])}</strong></div>
      </div>
      <ul class="profile-features">{feats}</ul>
      <div class="profile-actions">
        <a href="services/{v['id']}.html" class="profile-btn profile-btn-primary">▶ {escape(v['name'])}の詳細</a>
      </div>
    </article>""")
    return f"""<section class="top-section profile-section" id="profiles">
  <h2>🏆 主要10サービスを総合スコア順に紹介</h2>
  <p class="section-lead">編集部が実際に契約してチェックした評価軸（コスパ・作品数・独占度・UI・サポート）の合算スコア順。</p>
  <div class="profile-grid">{''.join(cards)}</div>
</section>"""


# --------------------------------------------------------------------
# 5. ランキングタブ切替（5系統）
# --------------------------------------------------------------------
def _render_ranking_tabs() -> str:
    def cards_html(vods, value_key, value_label_fn):
        items = []
        for i, v in enumerate(vods[:5], 1):
            items.append(
                f'<a class="rank-card" href="services/{v["id"]}.html">'
                f'<span class="rank-no">{i}位</span>'
                f'<span class="rank-icon">{v.get("icon","")}</span>'
                f'<span class="rank-body"><strong>{escape(v["name"])}</strong>'
                f'<span class="rank-tag">{escape(v.get("difficulty",""))}</span></span>'
                f'<span class="rank-fee">{escape(value_label_fn(v))}</span>'
                f'</a>'
            )
        return f'<div class="ranking-list">{"".join(items)}</div>'

    overall = sorted(VODS, key=lambda v: -avg_score(v.get("recommend_score", {})))
    cheap = sorted(VODS, key=fee_int)
    trial = sorted(VODS, key=lambda v: -v.get("free_trial_days", 0))
    library = sorted(VODS, key=lambda v: -(v.get("recommend_score", {}).get("library", 0)))
    exclusive = sorted(VODS, key=lambda v: -(v.get("recommend_score", {}).get("exclusive", 0)))

    tabs = [
        ("overall", "🏆 総合", cards_html(overall, "score", lambda v: f'⭐ {avg_score(v.get("recommend_score", {})):.1f}')),
        ("cheap", "💴 料金が安い順", cards_html(cheap, "fee", lambda v: v["monthly_fee"])),
        ("trial", "🎁 無料体験が長い順", cards_html(trial, "trial", lambda v: f'{v["free_trial_days"]}日間' if v["free_trial_days"] else "なし")),
        ("library", "📚 作品数が多い順", cards_html(library, "library", lambda v: f'⭐ {v.get("recommend_score", {}).get("library", 0):.1f}')),
        ("exclusive", "🎬 独占度が高い順", cards_html(exclusive, "exclusive", lambda v: f'⭐ {v.get("recommend_score", {}).get("exclusive", 0):.1f}')),
    ]

    btns = "".join(
        f'<button class="rank-tab-btn{(" active" if i==0 else "")}" data-rank-tab="{tid}">{escape(label)}</button>'
        for i, (tid, label, _) in enumerate(tabs)
    )
    panels = "".join(
        f'<div class="rank-tab-panel{(" active" if i==0 else "")}" data-rank-panel="{tid}">{html}</div>'
        for i, (tid, _, html) in enumerate(tabs)
    )

    return f"""<section class="top-section" id="ranking">
  <h2>📊 ランキング（5系統で切替）</h2>
  <p class="section-lead">観点別のTOP5。タブをタップして切り替えてください。</p>
  <div class="rank-tabs" role="tablist">{btns}</div>
  <div class="rank-tab-panels">{panels}</div>
</section>"""


# --------------------------------------------------------------------
# 6. 総合比較表
# --------------------------------------------------------------------
def _render_compare_table() -> str:
    sorted_vods = sorted(VODS, key=fee_int)
    return f"""<section class="top-section" id="compare-table">
  <h2>📊 主要VOD10社 総合比較表</h2>
  <p class="section-lead">月額が安い順で並べた一覧。サービス名をタップで個別ページへ。</p>
  {T.comparison_table(sorted_vods, COMPARE_AXES, link_prefix='services/')}
</section>"""


# --------------------------------------------------------------------
# 7. 目的別カード（既存）
# --------------------------------------------------------------------
def _render_use_cases() -> str:
    cards = []
    for uc in USE_CASES:
        primary = VODS_BY_ID.get(uc["primary"])
        if not primary:
            continue
        alts = ", ".join(VODS_BY_ID[a]["name"] for a in uc["alt"] if a in VODS_BY_ID)
        cards.append(f"""<div class="usecase-card">
      <span class="usecase-icon">{uc['icon']}</span>
      <h3>{escape(uc['title'])}</h3>
      <p class="usecase-reason">{escape(uc['reason'])}</p>
      <a href="services/{primary['id']}.html" class="usecase-primary">
        {primary.get('icon','')} <strong>{escape(primary['name'])}</strong> を見る
      </a>
      <p class="usecase-alt">他候補: {escape(alts)}</p>
    </div>""")
    return f"""<section class="top-section" id="use-cases">
  <h2>🎯 目的別おすすめ</h2>
  <p class="section-lead">観たいジャンル・使い方から逆引きできる目的別カード。</p>
  <div class="usecase-grid">{''.join(cards)}</div>
</section>"""


# --------------------------------------------------------------------
# 8. タグクラウド（ジャンル × 属性 × 予算）
# --------------------------------------------------------------------
def _render_tag_cloud() -> str:
    blocks = []
    for group, items in TAG_CLOUD.items():
        chips = "".join(
            f'<a class="tag-chip" href="services/{t["vod_id"]}.html">'
            f'<span class="tag-label">{escape(t["label"])}</span>'
            f'<span class="tag-arrow">→</span>'
            f'</a>'
            for t in items
        )
        blocks.append(f'<div class="tag-block"><h3>{escape(group)}</h3><div class="tag-chips">{chips}</div></div>')
    return f"""<section class="top-section" id="tags">
  <h2>🔖 ジャンル・属性・予算で逆引き</h2>
  <p class="section-lead">あなたのキーワードからおすすめVODに直接ジャンプできます。</p>
  {''.join(blocks)}
</section>"""


# --------------------------------------------------------------------
# 9. 選び方ガイド（既存4ステップ）
# --------------------------------------------------------------------
def _render_how_to_choose() -> str:
    steps = "".join(
        f"""<div class="howto-step">
      <span class="howto-num">{s['step']}</span>
      <div>
        <h3>{escape(s['title'])}</h3>
        <p>{escape(s['body'])}</p>
        <p class="howto-tip">💡 {escape(s['tip'])}</p>
      </div>
    </div>"""
        for s in HOW_TO_CHOOSE
    )
    return f"""<section class="top-section" id="how-to-choose">
  <h2>🧭 サブスクの選び方ガイド</h2>
  <p class="section-lead">編集部が10社契約してたどり着いた、失敗しない4ステップ。</p>
  <div class="howto-list">{steps}</div>
</section>"""


# --------------------------------------------------------------------
# 10. VOD基礎知識
# --------------------------------------------------------------------
def _render_basic_knowledge() -> str:
    items = "".join(
        f"""<div class="basic-card">
      <span class="basic-icon">{k['icon']}</span>
      <h3>{escape(k['title'])}</h3>
      <p>{escape(k['body'])}</p>
    </div>"""
        for k in BASIC_KNOWLEDGE
    )
    return f"""<section class="top-section" id="basics">
  <h2>📘 はじめて使う方へ — VODの基礎知識</h2>
  <p class="section-lead">仕組み・料金・無料体験・解約のしやすさまでを6項目で整理。</p>
  <div class="basic-grid">{items}</div>
</section>"""


# --------------------------------------------------------------------
# 11. 更新情報・最新トピック
# --------------------------------------------------------------------
def _render_news() -> str:
    items = "".join(
        f"""<article class="news-item">
      <div class="news-meta">
        <span class="news-date">📅 {escape(n['date'])}</span>
        <span class="news-cat">{escape(n['category'])}</span>
      </div>
      <h3>{escape(n['title'])}</h3>
      <p>{escape(n['body'])}</p>
    </article>"""
        for n in NEWS_ITEMS
    )
    return f"""<section class="top-section" id="news">
  <h2>📰 最新トピック・編集部ノート</h2>
  <p class="section-lead">料金改定・新作配信・サービス改善など、2026年の最新動向を編集部がチェック。</p>
  <div class="news-list">{items}</div>
</section>"""


# --------------------------------------------------------------------
# 12. 記事カテゴリ一覧
# --------------------------------------------------------------------
def _render_articles_grid() -> str:
    cat_blocks = []
    for slug, label in CATEGORIES.items():
        items = [a for a in ARTICLES if a["category_slug"] == slug]
        if not items:
            continue
        lis = "".join(
            f'<li><a href="articles/{a["slug"]}.html">{escape(a["title"])}</a></li>'
            for a in items
        )
        cat_blocks.append(
            f'<div class="cat-block"><h3>{escape(label)}</h3><ul>{lis}</ul></div>'
        )
    return f"""<section class="top-section" id="articles">
  <h2>📰 カテゴリ別記事</h2>
  <p class="section-lead">{len(ARTICLES)}本の解説記事をカテゴリ別に整理しています。</p>
  <div class="cat-grid">{''.join(cat_blocks)}</div>
</section>"""


# --------------------------------------------------------------------
# 13. FAQ拡充版（5カテゴリ15問）
# --------------------------------------------------------------------
def _render_faq_grouped() -> str:
    blocks = []
    for g in TOP_FAQS_GROUPED:
        items = "".join(
            f"""<details class="faq-item">
        <summary>{escape(f['q'])}</summary>
        <div class="faq-answer">{escape(f['a'])}</div>
      </details>"""
            for f in g["items"]
        )
        blocks.append(f'<div class="faq-group"><h3>{escape(g["category"])}</h3>{items}</div>')
    return f"""<section class="top-section faq-section" id="faq">
  <h2>❓ サブスクのよくある質問（5カテゴリ15問）</h2>
  <p class="section-lead">編集部に問い合わせの多い質問を5カテゴリで整理しています。</p>
  {''.join(blocks)}
</section>"""


# --------------------------------------------------------------------
# 14. 編集部詳細プロフィール
# --------------------------------------------------------------------
def _render_editors_detail() -> str:
    cards = []
    for e in EDITORS_DETAIL:
        subs = "".join(f'<span class="editor-sub-pill">{escape(s)}</span>' for s in e["subscribed"])
        cards.append(f"""<article class="editor-card">
      <span class="editor-card-icon">{e['icon']}</span>
      <h3>{escape(e['name'])}</h3>
      <p class="editor-card-role">{escape(e['role'])}</p>
      <p class="editor-card-bio">{escape(e['bio'])}</p>
      <p class="editor-card-subs-label">契約中:</p>
      <div class="editor-card-subs">{subs}</div>
    </article>""")
    return f"""<section class="top-section editors-section" id="editor">
  <h2>✍ 編集部メンバー</h2>
  <p class="section-lead">VOD領域に専門知識を持つ3名で、毎月の最新情報を更新しています。</p>
  <div class="editors-grid">{''.join(cards)}</div>
  {T.editor_box()}
</section>"""


# --------------------------------------------------------------------
# 15. 当サイトについて
# --------------------------------------------------------------------
def _render_about_block() -> str:
    return f"""<section class="top-section" id="about">
  <h2>📘 当サイトについて</h2>
  <p class="section-lead">{escape(SITE_ABOUT['tagline'])}</p>
  <ul class="principles-list">
    {''.join(f'<li>{escape(p)}</li>' for p in SITE_ABOUT['principles'])}
  </ul>
</section>"""


# --------------------------------------------------------------------
# クイズスクリプト（既存ロジック）
# --------------------------------------------------------------------
def _render_quiz_script() -> str:
    return f"""<script>
const VODS = {json.dumps(VODS, ensure_ascii=False)};
const QUESTIONS = {json.dumps(QUIZ_QUESTIONS, ensure_ascii=False)};
const answers = {{}};
let step = 0;

function renderStep() {{
  const q = QUESTIONS[step];
  document.getElementById('stepNum').textContent = step + 1;
  document.getElementById('progressFill').style.width = ((step + 1) / QUESTIONS.length * 100) + '%';
  document.getElementById('questionText').textContent = q.text;
  const opts = document.getElementById('options');
  opts.innerHTML = '';
  q.options.forEach(o => {{
    const btn = document.createElement('button');
    btn.className = 'option-btn';
    btn.textContent = o.label;
    btn.onclick = () => {{
      answers[q.id] = o.value;
      step++;
      if (step >= QUESTIONS.length) showResult();
      else renderStep();
    }};
    opts.appendChild(btn);
  }});
}}

function showResult() {{
  document.getElementById('quiz').style.display = 'none';
  const result = document.getElementById('result');
  const recommended = recommend(answers);
  result.style.display = 'block';
  result.innerHTML = '<h2>🎯 編集部が選んだあなた向けTOP3</h2>' + recommended.map((v, i) => `
    <div class="result-card">
      <div class="result-card-head">
        <span class="result-rank">${{i+1}}位</span>
        <span class="result-icon">${{v.icon || ''}}</span>
        <div>
          <span class="badge">${{v.difficulty}}</span>
          <h3>${{v.name}}</h3>
        </div>
      </div>
      <p class="result-tagline">${{v.tagline || ''}}</p>
      <p>月額: <strong>${{v.monthly_fee}}</strong> / 無料体験: <strong>${{v.free_trial_days || 0}}日</strong></p>
      <p>${{v.features.slice(0,2).join(' / ')}}</p>
      <a href="services/${{v.id}}.html" class="apply-btn">▶ 詳細を見る</a>
    </div>
  `).join('');
  document.getElementById('result').scrollIntoView({{behavior:'smooth'}});
}}

function recommend(a) {{
  const score = {{}};
  VODS.forEach(v => {{ score[v.id] = 0; }});
  const genreMap = {{
    drama_kr: ['韓国ドラマ', 'K-POP'],
    anime: ['アニメ'],
    sports: ['サッカー', '野球', 'F1', 'テニス', '格闘技'],
    movie: ['映画', '海外ドラマ'],
  }};
  const targetGenres = genreMap[a.genre] || [];
  VODS.forEach(v => {{
    targetGenres.forEach(g => {{ if (v.genres.includes(g)) score[v.id] += 3; }});
  }});
  VODS.forEach(v => {{
    const fee = parseInt(String(v.monthly_fee).replace(/[^0-9]/g, ''), 10);
    if (a.budget === 'low' && fee <= 600) score[v.id] += 2;
    if (a.budget === 'mid' && fee <= 1200) score[v.id] += 2;
    if (a.budget === 'high') score[v.id] += 1;
  }});
  VODS.forEach(v => {{
    if (a.device === 'tv' && v.devices.includes('テレビ')) score[v.id] += 1;
    if (a.device === 'share' && v.simultaneous_streams >= 4) score[v.id] += 2;
  }});
  return VODS
    .map(v => ({{...v, _score: score[v.id]}}))
    .sort((a, b) => b._score - a._score)
    .slice(0, 3);
}}

renderStep();
</script>"""


# ====================================================================
# 記事ページ（既存ロジック維持）
# ====================================================================
def render_article(article: dict) -> str:
    canonical_path = f"/articles/{article['slug']}.html"
    page_url = T.SITE_URL + canonical_path
    cat_label = CATEGORIES.get(article["category_slug"], article["category_slug"])

    crumbs_data = [
        ("トップ", T.SITE_URL + "/"),
        (cat_label, T.SITE_URL + f"/#{article['category_slug']}"),
        (article["title"], page_url),
    ]
    json_ld = T.render_json_ld(
        T.json_ld_breadcrumb(crumbs_data),
        T.json_ld_article(
            title=article["title"],
            description=article["description"],
            url=page_url,
            published_at=article.get("published_at", ""),
            updated_at=article.get("updated_at", ""),
            author=article.get("author", T.SITE_NAME),
        ),
        T.json_ld_faq(article.get("faqs", [])) if article.get("faqs") else None,
    )

    head = T.head_block(
        title=(
            f'{article["title"]} | {T.SITE_NAME}'
            if "2026" in article["title"]
            else f'【2026年最新】{article["title"]} | {T.SITE_NAME}'
        ),
        description=article["description"],
        keywords=article.get("keyword", ""),
        canonical_path=canonical_path,
        json_ld=json_ld,
        extra_css="../assets/common.css",
    )

    breadcrumb_html = T.breadcrumb([
        ("トップ", "../index.html"),
        (cat_label, f"../index.html#{article['category_slug']}"),
        (article["title"], ""),
    ])

    meta_html = T.article_meta(
        category=cat_label,
        published_at=article.get("published_at", ""),
        updated_at=article.get("updated_at", ""),
        author=article.get("author", ""),
    )

    takeaways_html = T.takeaways_box(article.get("key_takeaways", []))
    toc_html = T.toc(article.get("sections", []))
    body_html = render_article_body(article)
    faq_html = T.faq_block(article.get("faqs", []), "❓ よくある質問")
    cta_mid_html = T.cta_banner(css_prefix="../")
    related_vods = [VODS_BY_ID[s] for s in article.get("related_services", []) if s in VODS_BY_ID]
    related_html = T.related_service_cards(related_vods, link_prefix="../services/")

    body = f"""<body>
{T.site_header(css_prefix='../')}
{T.pr_disclosure(css_prefix='../')}
<main class="container">
  {breadcrumb_html}
  <article class="article-content">
    <span class="article-cat">{escape(cat_label)}</span>
    <h1>{escape(article['title'])}</h1>
    {meta_html}
    <p class="lead">{escape(article.get('summary', article['description']))}</p>
    {takeaways_html}
    {toc_html}
    {body_html}
    {cta_mid_html}
    {faq_html}
    {related_html}
    {T.editor_box()}
  </article>
</main>
{T.site_footer(css_prefix='../')}
</body>"""
    return f"<!DOCTYPE html>\n<html lang=\"ja\">\n{head}\n{body}\n</html>"


def render_article_body(article: dict) -> str:
    sections = article.get("sections", [])
    cat = article["category_slug"]
    parts = []
    inserted_compare_table = False
    inserted_ranking = False

    for i, h2 in enumerate(sections):
        parts.append(f'<h2 id="sec-{i}">{escape(h2)}</h2>')
        if h2 in ("よくある質問", "FAQ"):
            parts.append('<p>下部の「❓ よくある質問」セクションをご覧ください。</p>')
            continue
        body_para = _generate_section_body(article, h2, i)
        parts.append(body_para)

        if cat == "compare" and not inserted_compare_table and i == 0:
            ids = article.get("compare_service_ids") or article.get("related_services", [])
            vods = [VODS_BY_ID[s] for s in ids if s in VODS_BY_ID]
            if vods:
                parts.append(T.comparison_table(
                    vods,
                    [
                        {"key": "monthly_fee", "label": "月額"},
                        {"key": "free_trial_days", "label": "無料体験"},
                        {"key": "content_count", "label": "作品数"},
                        {"key": "simultaneous_streams", "label": "同時視聴"},
                        {"key": "quality", "label": "画質"},
                    ],
                    link_prefix="../services/",
                ))
                inserted_compare_table = True

        if cat in ("attribute", "purpose") and not inserted_ranking and any(
            kw in h2 for kw in ("ランキング", "TOP", "おすすめ", "比較")
        ):
            ids = article.get("ranking_service_ids") or article.get("related_services", [])
            vods = [VODS_BY_ID[s] for s in ids if s in VODS_BY_ID]
            if vods:
                cards = []
                for j, v in enumerate(vods, 1):
                    cards.append(
                        f'<a class="rank-card" href="../services/{v["id"]}.html">'
                        f'<span class="rank-no">{j}位</span>'
                        f'<span class="rank-icon">{v.get("icon","")}</span>'
                        f'<span class="rank-body"><strong>{escape(v["name"])}</strong>'
                        f'<span class="rank-tag">{escape(v.get("tagline",""))}</span></span>'
                        f'<span class="rank-fee">{escape(v["monthly_fee"])}</span>'
                        f'</a>'
                    )
                parts.append(f'<div class="ranking-list">{"".join(cards)}</div>')
                inserted_ranking = True

    return "\n".join(parts)


def _generate_section_body(article: dict, h2: str, idx: int) -> str:
    summary = article.get("summary", "")
    takeaways = article.get("key_takeaways", [])
    cat = article["category_slug"]
    related_ids = article.get("related_services", [])
    related_names = [VODS_BY_ID[s]["name"] for s in related_ids if s in VODS_BY_ID]

    if idx == 0:
        return (
            f"<p>{escape(summary)}</p>"
            f"<p>本記事の結論は冒頭の「この記事でわかること」にまとめています。"
            f"以降のセクションで詳細を順に確認してください。</p>"
        )

    if "選び方" in h2 or "ポイント" in h2 or ("比較" in h2 and idx <= 2):
        items = "".join(
            f"<li>{escape(t)}</li>" for t in takeaways[:3]
        ) if takeaways else "<li>料金</li><li>作品数</li><li>無料体験</li>"
        return (
            f"<p>{escape(h2)}を判断するうえで、編集部が重視している軸は以下の通りです。</p>"
            f"<ul>{items}</ul>"
            f"<p>これらを意識して比較すれば、{', '.join(related_names) if related_names else '主要VOD'}"
            f"のなかから最適な1本を選べます。</p>"
        )

    if "おすすめ" in h2 or "ランキング" in h2 or "TOP" in h2:
        return (
            f"<p>編集部が実契約してチェックした評価軸（コスパ・作品数・独占度・UI・サポート）"
            f"を総合した{escape(h2)}です。各サービス名をクリックすると個別ページで詳細スペックを確認できます。</p>"
        )

    if "結論" in h2 or "向いている" in h2 or "使い分け" in h2 or "あなたに" in h2:
        items = "".join(f"<li>{escape(t)}</li>" for t in takeaways) or "<li>各記事の判断軸を参照</li>"
        return (
            f"<p>本記事の結論を整理します。</p>"
            f"<ul>{items}</ul>"
            f"<p>迷ったらトップページの3問診断クイズを試すと、編集部が10サービスから1本を提案します。</p>"
        )

    if "申込" in h2 or "申し込み" in h2 or "登録" in h2 or "フロー" in h2 or "始め方" in h2:
        return (
            "<p>VODの登録は基本的に5分以内で完了します。共通の流れは以下の通りです。</p>"
            "<ol>"
            "<li>公式サイトにアクセスし「無料体験を始める」を選択</li>"
            "<li>メールアドレスとパスワードを設定</li>"
            "<li>支払い方法（クレジットカードが基本）を登録</li>"
            "<li>視聴開始。スマホアプリも入れておくと便利</li>"
            "</ol>"
            "<p>アプリ・テレビ・PCで同じアカウントが使えるため、登録は1回で済みます。</p>"
        )

    if "解約" in h2:
        return (
            "<p>VODの解約は公式サイトのアカウント設定から24時間いつでも可能です。"
            "電話手続きは不要で、所要時間は数分。違約金もかかりません。</p>"
            "<ol>"
            "<li>公式サイトにログイン</li>"
            "<li>アカウント設定 → 契約情報 → 解約</li>"
            "<li>アンケートに回答（任意）</li>"
            "<li>解約完了メールを確認</li>"
            "</ol>"
            "<p>日割り返金がない点には注意。月末ギリギリの解約だと損をするため、月初に解約日を決めておくのがお得です。</p>"
        )

    if "落とし穴" in h2 or "注意" in h2 or "デメリット" in h2:
        return (
            "<p>VODの利用で見落としがちな注意点をまとめます。</p>"
            "<ul>"
            "<li>無料体験の解約期日を1日でも過ぎると自動課金される</li>"
            "<li>日割り返金がないため月末解約は損をしやすい</li>"
            "<li>「見放題」と表記されていてもレンタル別料金の作品が混ざる</li>"
            "<li>ダウンロード視聴に対応していない作品もある</li>"
            "</ul>"
            "<p>これらは申込み前に把握しておけば回避できます。</p>"
        )

    if "視聴環境" in h2 or "デバイス" in h2 or "観るなら" in h2 or "観られる" in h2:
        return (
            "<p>VODをテレビで楽しむ最も汎用的な方法は Fire TV Stick。約5,000円で買えるドングルで、"
            "ほぼ全VODのアプリが揃います。Chromecast や Apple TV、対応スマートテレビでも視聴可能です。</p>"
            "<p>4K対応テレビなら U-NEXT・WOWOW・DAZNなどで4K作品を楽しめます。"
            "通信速度は最低25Mbps、推奨50Mbps以上を目安にしてください。</p>"
        )

    if "ジャンル" in h2 or "ラインナップ" in h2:
        if related_names:
            return (
                f"<p>{', '.join(related_names)}のジャンル別ラインナップには明確な強みがあります。"
                f"以下のテーブルで比較表を確認すると一目瞭然です。</p>"
                "<p>本セクション上部に並ぶ比較表もあわせてチェックしてください。</p>"
            )
        return "<p>ジャンル別の強みは比較表で確認できます。</p>"

    if "料金" in h2 and "コスパ" in h2:
        return (
            f"<p>料金面では、{', '.join(related_names) if related_names else '各VOD'}"
            f"でプラン構成と還元率に差があります。"
            f"単純な月額だけでなくポイント還元・無料体験・複数アカウント可否を含めた"
            f"トータルコストで比較するのが正解です。</p>"
        )

    if "強み" in h2 or "良い評判" in h2:
        return (
            "<p>編集部が実際に契約して感じた強みを整理します。"
            "ユーザーレビューでも一貫して評価されている代表的なポイントを示します。</p>"
            "<ul>"
            "<li>独占配信タイトルの豊富さ</li>"
            "<li>無料体験中でも全機能が使える</li>"
            "<li>解約手続きがWeb完結で簡単</li>"
            "</ul>"
        )

    if "悪い評判" in h2:
        return (
            "<p>一方で改善余地のあるポイントも素直に共有します。</p>"
            "<ul>"
            "<li>料金が他社より高めという声</li>"
            "<li>UIが直感的でない部分がある</li>"
            "<li>地域や通信環境による画質低下</li>"
            "</ul>"
            "<p>これらは契約前に把握しておけばギャップが減ります。</p>"
        )

    if "観るべき作品" in h2 or "豊富" in h2:
        return (
            "<p>無料体験を最大化したい方は、まず代表的な独占配信タイトルから観るのがおすすめ。"
            "解約日までに観たい作品リストを作っておくと時間を有効活用できます。</p>"
        )

    return (
        f"<p>本セクションでは「{escape(h2)}」のポイントを解説します。"
        f"具体的なサービス選定は本記事末尾の「関連サービス」または"
        f"トップページの3問診断クイズを参考にしてください。</p>"
    )


# ====================================================================
# About / 運営者情報ページ
# ====================================================================
def render_about() -> str:
    canonical_path = "/about.html"
    page_url = T.SITE_URL + canonical_path

    person_lds = [T.json_ld_person(e) for e in EDITORS_DETAIL]
    json_ld = T.render_json_ld(
        T.json_ld_breadcrumb([
            ("トップ", T.SITE_URL + "/"),
            ("当サイトについて", page_url),
        ]),
        {
            "@context": "https://schema.org",
            "@type": "AboutPage",
            "name": f"{T.SITE_NAME}について",
            "url": page_url,
            "description": "サブスク図鑑の運営方針・編集ポリシー・編集メンバー・広告表記",
        },
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": T.SITE_NAME,
            "url": T.SITE_URL,
            "description": "国内主要サブスクを実契約レビューで紹介する図鑑型メディア",
            "sameAs": [],
        },
        *person_lds,
    )

    head = T.head_block(
        title=f"当サイトについて | {T.SITE_NAME}",
        description="サブスク図鑑の運営方針・編集ポリシー・広告表記・編集メンバーの紹介。実契約レビューと独立した編集を約束します。",
        canonical_path=canonical_path,
        json_ld=json_ld,
        extra_css="assets/common.css",
    )

    breadcrumb_html = T.breadcrumb([
        ("トップ", "index.html"),
        ("当サイトについて", ""),
    ])

    # 編集メンバー
    members_html = ""
    for e in EDITORS_DETAIL:
        subs = "".join(
            f'<span class="editor-sub-pill">{escape(s)}</span>' for s in e["subscribed"]
        )
        members_html += f"""<article class="editor-card">
      <span class="editor-card-icon">{e['icon']}</span>
      <h3>{escape(e['name'])}</h3>
      <p class="editor-card-role">{escape(e['role'])}</p>
      <p class="editor-card-bio">{escape(e['bio'])}</p>
      <p class="editor-card-subs-label">契約中:</p>
      <div class="editor-card-subs">{subs}</div>
    </article>"""

    body = f"""<body>
{T.site_header()}
{T.pr_disclosure()}
<main class="container">
  {breadcrumb_html}
  <article class="article-content about-page">
    <span class="article-cat">サイト情報</span>
    <h1>📘 サブスク図鑑について</h1>
    <p class="lead">サブスク図鑑は、国内主要VOD・サブスクを「実契約してレビューする」図鑑型メディアです。料金・作品数・無料体験を独立した立場で比較し、編集部の体験に基づく一次情報を提供します。</p>

    <section id="mission">
      <h2>🎯 ミッション</h2>
      <p>サブスクサービスは年々増加し、料金・特典・作品ラインナップは月単位で変動します。サブスク図鑑は、利用者が「自分に合った1社を最短で見つけられる」ことを目的に、編集部が全社を実際に契約・視聴して比較レビューを公開します。</p>
    </section>

    <section id="editorial-policy">
      <h2>✍ 編集方針</h2>
      <ul class="principles-list">
        <li>全サービスを実際に有料契約してレビューします</li>
        <li>料金・作品数の数値は最新月にチェックし更新します</li>
        <li>解約したくなる弱点・後悔ポイントも隠さず掲載します</li>
        <li>「ベスト」評価は編集部の評価軸（コスパ・作品数・独占度・UI・サポート）の合算で判定します</li>
        <li>掲載順位はアフィリエイト報酬の単価では決定しません</li>
      </ul>
    </section>

    <section id="disclosure">
      <h2>📋 広告表記・景表法対応</h2>
      <p>本サイトは <strong>アフィリエイト広告</strong> を含みます（景品表示法第5条第3号告示「ステルスマーケティング規制」に基づく明示）。</p>
      <ul class="check-list">
        <li>記事内で紹介する各VODサービスへのリンクは、提携先からの紹介料が発生する場合があります</li>
        <li>紹介料の有無は記事の評価・順位に影響しません</li>
        <li>アフィリエイトリンクには <code>rel="sponsored"</code> 属性を付与し、Googleのリンク品質ガイドラインに準拠しています</li>
        <li>各ページのファーストビュー（最上部）にPR表記を常時表示しています</li>
      </ul>
    </section>

    <section id="editor">
      <h2>👥 編集メンバー</h2>
      <p>VOD領域に専門知識を持つ3名で、毎月の最新情報を更新しています。</p>
      <div class="editors-grid">
        {members_html}
      </div>
    </section>

    <section id="review-method">
      <h2>🔬 レビュー方法</h2>
      <p>編集部のレビュープロセス：</p>
      <ol>
        <li><strong>実契約</strong>：全サービスを編集部の個人カードで有料契約</li>
        <li><strong>多端末で実視聴</strong>：スマホ・PC・テレビ（Fire TV）で視聴体験をチェック</li>
        <li><strong>5軸評価</strong>：コスパ／作品数／独占度／UI／サポートの5軸で1.0〜5.0で採点</li>
        <li><strong>長期モニタ</strong>：契約後も継続契約し、料金改定・新作配信・UI変更を月次でモニタリング</li>
        <li><strong>編集会議</strong>：月1回、3名の編集者で評価を持ち寄り合議</li>
      </ol>
    </section>

    <section id="update-policy">
      <h2>🔄 更新ポリシー</h2>
      <ul>
        <li><strong>月次</strong>：料金・作品数・キャンペーン情報を更新</li>
        <li><strong>都度</strong>：新規サービス追加・終了・大型機能変更があれば即時更新</li>
        <li><strong>年次</strong>：ランキング軸の見直し</li>
      </ul>
      <p>各記事の上部には「公開日」「更新日」を表示しています。</p>
    </section>

    <section id="contact">
      <h2>✉️ お問い合わせ</h2>
      <p>取材・記事監修・記載内容の訂正依頼などのお問い合わせは、現在準備中です。準備が整い次第、本ページに連絡先を記載します。</p>
      <p>（編集部の運営状況により、回答までお時間をいただく場合があります）</p>
    </section>

    <section class="cta-banner" id="quiz-cta">
      <p class="cta-banner-title">🎯 まずは3問の診断クイズから</p>
      <p class="cta-banner-desc">あなたに合うサブスクが10サービスから見つかります。</p>
      <a href="index.html#quiz" class="cta-banner-btn">無料で診断を始める</a>
    </section>

    {T.editor_box()}
  </article>
</main>
{T.site_footer()}
</body>"""
    return f"<!DOCTYPE html>\n<html lang=\"ja\">\n{head}\n{body}\n</html>"


# ====================================================================
# エントリーポイント
# ====================================================================
def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)

    print("--- index.html ---")
    out = DOCS_DIR / "index.html"
    out.write_text(render_index(), encoding="utf-8")
    print(f"作成: {out.relative_to(BASE_DIR)}")

    print("--- about.html ---")
    out = DOCS_DIR / "about.html"
    out.write_text(render_about(), encoding="utf-8")
    print(f"作成: {out.relative_to(BASE_DIR)}")

    print("--- 記事 ---")
    for a in ARTICLES:
        out = ARTICLES_DIR / f'{a["slug"]}.html'
        out.write_text(render_article(a), encoding="utf-8")
        print(f'作成: {out.relative_to(BASE_DIR)}')

    print("\n=== 完了 ===")


if __name__ == "__main__":
    main()
