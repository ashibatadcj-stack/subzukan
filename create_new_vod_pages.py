"""個別VODサービスページを vods_data.py から一括生成（リッチ版）

各ページに含まれる要素:
- パンくず
- ヒーロー（アイコン・タグライン・推奨スコア・無料体験バッジ）
- スコアバー（5軸）
- スペック表（拡張版）
- 料金プラン詳細
- メリット・デメリット2カラム
- 独自の強み（USP）
- 取扱ジャンル・対応デバイス
- 登録手順 / 解約手順
- 同カテゴリの他社比較表
- FAQ
- 関連サービス
- CTAバナー（記事中盤・末尾）
- JSON-LD（Product / FAQ / Breadcrumb）
"""
from pathlib import Path
from html import escape

from vods_data import VODS, SCORE_AXES
from content_data import SIGNUP_STEPS_TEMPLATE, CANCEL_STEPS_TEMPLATE, SERVICE_FAQ_TEMPLATES
import templates as T

BASE_DIR = Path(__file__).parent
SERVICES_DIR = BASE_DIR / 'docs' / 'services'

SITE_NAME = T.SITE_NAME


def _list(items: list[str], css_class: str = "") -> str:
    cls = f' class="{css_class}"' if css_class else ''
    return f'<ul{cls}>' + "".join(f'<li>{escape(s)}</li>' for s in items) + '</ul>'


def _avg_score(scores: dict) -> float:
    return sum(scores.values()) / len(scores) if scores else 0


def _trial_badge(days: int) -> str:
    if not days:
        return '<span class="trial-badge trial-none">無料体験なし</span>'
    return f'<span class="trial-badge">🎁 無料体験 {days}日間</span>'


def _other_vods(target: dict, n: int = 3) -> list[dict]:
    """同じ難易度（カテゴリ）から比較用に他のVODをピックアップ"""
    same = [v for v in VODS if v["id"] != target["id"] and v.get("difficulty") == target.get("difficulty")]
    if len(same) >= n:
        return same[:n]
    # 不足分は全体から月額が近い順で補う
    others = [v for v in VODS if v["id"] != target["id"] and v not in same]
    def fee_int(v):
        s = "".join(c for c in str(v.get("monthly_fee","")) if c.isdigit())
        return int(s) if s else 0
    target_fee = fee_int(target)
    others.sort(key=lambda v: abs(fee_int(v) - target_fee))
    return (same + others)[:n]


def _faqs_for_service(vod: dict) -> list[dict]:
    """共通FAQテンプレに名前と無料体験日数を差し込む"""
    trial = f'{vod["free_trial_days"]}日間' if vod["free_trial_days"] else '体験なし'
    return [
        {"q": f["q"].format(name=vod["name"]),
         "a": f["a"].format(name=vod["name"], trial=trial)}
        for f in SERVICE_FAQ_TEMPLATES
    ]


def _cta_html(vod: dict, position: str = "main") -> str:
    if vod.get("affiliate_url"):
        return (
            f'<a href="{vod["affiliate_url"]}" '
            f'class="apply-btn apply-btn-{position}" '
            f'rel="sponsored noopener" target="_blank">'
            f'▶ {escape(vod["name"])}を無料体験する</a>'
        )
    return (
        f'<div class="apply-btn-placeholder">'
        f'※ A8参加申請が通り次第、{escape(vod["name"])}のアフィリエイトリンクを設置します</div>'
    )


# --------------------------------------------------------------------
# ページ全体の組み立て
# --------------------------------------------------------------------
def render_page(vod: dict) -> str:
    name = vod["name"]
    avg = _avg_score(vod.get("recommend_score", {}))
    trial_days = vod["free_trial_days"]

    canonical_path = f"/services/{vod['id']}.html"
    page_url = f"{T.SITE_URL}{canonical_path}"

    # JSON-LD
    crumbs_data = [
        ("トップ", T.SITE_URL + "/"),
        ("サービス", T.SITE_URL + "/#ranking"),
        (name, page_url),
    ]
    faqs = _faqs_for_service(vod)
    json_ld = T.render_json_ld(
        T.json_ld_breadcrumb(crumbs_data),
        T.json_ld_product(vod, page_url),
        T.json_ld_faq(faqs),
    )

    head = T.head_block(
        title=(
            f"【2026年最新】{name}の評判・料金・作品数まとめ｜{trial_days}日無料体験 | {SITE_NAME}"
            if trial_days else
            f"【2026年最新】{name}の評判・料金・作品数まとめ | {SITE_NAME}"
        ),
        description=(
            f"{name}を実契約レビュー。月額{vod['monthly_fee']}・"
            f"{vod['content_count']}・{vod.get('tagline','')}など"
            f"料金プランから解約手順まで完全ガイド。"
        ),
        keywords=f"{name},評判,料金,作品数,無料体験,VOD,サブスク",
        canonical_path=canonical_path,
        json_ld=json_ld,
        extra_css="../assets/common.css",
    )

    breadcrumb_html = T.breadcrumb([
        ("トップ", "../index.html"),
        ("サービス", "../index.html#ranking"),
        (name, ""),
    ])

    # ヒーロー
    hero_html = f"""<section class="vod-hero">
  <div class="vod-hero-inner">
    <span class="vod-hero-icon">{vod.get('icon','')}</span>
    <div class="vod-hero-text">
      <p class="vod-hero-tag">{escape(vod.get('difficulty',''))}</p>
      <h1>{escape(name)}</h1>
      <p class="vod-hero-tagline">{escape(vod.get('tagline',''))}</p>
      <div class="vod-hero-meta">
        <span class="vod-hero-fee">月額 {escape(vod['monthly_fee'])}</span>
        {_trial_badge(trial_days)}
        <span class="vod-hero-score">⭐ 総合 {avg:.1f}/5.0</span>
      </div>
    </div>
  </div>
  {_cta_html(vod, 'hero')}
</section>"""

    # スコア
    score_html = f"""<section class="vod-section" id="score">
  <h2>編集部の評価スコア</h2>
  <p class="section-lead">編集部が実契約してチェックした5軸の評価です（5.0が満点）。</p>
  {T.score_bars(vod.get('recommend_score', {}), SCORE_AXES)}
</section>"""

    # スペック表
    spec_rows = [
        ("月額料金", vod["monthly_fee"]),
        ("無料体験", f'{trial_days}日間' if trial_days else 'なし'),
        ("作品数", vod["content_count"]),
        ("同時視聴可能数", f'{vod.get("simultaneous_streams","-")}台'),
        ("画質", vod.get("quality", "-")),
        ("ダウンロード", "対応" if vod.get("download") else "非対応"),
        ("字幕・吹替", vod.get("subtitles_dubbing", "-")),
        ("対応デバイス", "・".join(vod.get("devices", []))),
        ("支払い方法", "・".join(vod.get("payment_methods", []))),
        ("公式サイト", f'<a href="{vod.get("official_url","#")}" target="_blank" rel="noopener">{escape(vod.get("official_url","-"))}</a>' if vod.get("official_url") else "-"),
    ]
    spec_html = '<section class="vod-section" id="spec"><h2>📋 基本スペック</h2><table class="spec-table"><tbody>'
    for k, v in spec_rows:
        spec_html += f'<tr><th>{escape(k)}</th><td>{v if "<a " in str(v) else escape(str(v))}</td></tr>'
    spec_html += '</tbody></table></section>'

    # 料金プラン
    pricing_html = f"""<section class="vod-section" id="pricing">
  <h2>💴 料金プラン</h2>
  <p class="section-lead">{escape(name)}で選べる料金プラン一覧です。</p>
  {T.pricing_table(vod.get('pricing_plans', []))}
</section>"""

    # メリット・デメリット
    pros_cons_html = f"""<section class="vod-section" id="pros-cons">
  <h2>👍 メリット・👎 デメリット</h2>
  {T.pros_cons(vod.get('pros', []), vod.get('cons', []))}
</section>"""

    # 独自の強み
    usp_html = ""
    if vod.get("usp"):
        usp_items = "".join(
            f'<div class="usp-item"><span class="usp-num">{i+1}</span><p>{escape(s)}</p></div>'
            for i, s in enumerate(vod["usp"])
        )
        usp_html = f"""<section class="vod-section" id="usp">
  <h2>✨ {escape(name)}ならではの強み</h2>
  <div class="usp-grid">{usp_items}</div>
</section>"""

    # ターゲット
    target_html = f"""<section class="vod-section" id="target">
  <h2>🎯 こんな人におすすめ</h2>
  {_list(vod.get('target', []), 'check-list')}
</section>"""

    # ジャンル
    genre_html = f"""<section class="vod-section" id="genre">
  <h2>🎬 取扱ジャンル</h2>
  <ul class="genre-pills">{"".join(f'<li>{escape(g)}</li>' for g in vod.get('genres', []))}</ul>
</section>"""

    # 登録手順
    signup_html = f"""<section class="vod-section" id="signup">
  <h2>📝 登録方法（4ステップ）</h2>
  <p class="section-lead">公式サイトから5分で登録完了。{trial_days}日間の無料体験が始まります。</p>
  {T.step_list(SIGNUP_STEPS_TEMPLATE)}
  {_cta_html(vod, 'mid')}
</section>""" if trial_days else f"""<section class="vod-section" id="signup">
  <h2>📝 登録方法</h2>
  {T.step_list(SIGNUP_STEPS_TEMPLATE)}
  {_cta_html(vod, 'mid')}
</section>"""

    # 解約手順
    cancel_html = f"""<section class="vod-section" id="cancel">
  <h2>🚪 解約方法（4ステップ）</h2>
  <p class="section-lead">{escape(name)}は公式サイトから24時間いつでも解約できます。違約金はかかりません。</p>
  {T.step_list(CANCEL_STEPS_TEMPLATE)}
</section>"""

    # 他社比較
    others = _other_vods(vod, n=3)
    compare_html = f"""<section class="vod-section" id="compare">
  <h2>🔍 同ジャンル他社との比較</h2>
  <p class="section-lead">{escape(vod.get('difficulty',''))}カテゴリの代表サービスと並べた比較表です。</p>
  {T.comparison_table([vod] + others, [
    {'key': 'monthly_fee', 'label': '月額'},
    {'key': 'free_trial_days', 'label': '無料体験'},
    {'key': 'content_count', 'label': '作品数'},
    {'key': 'simultaneous_streams', 'label': '同時視聴'},
  ], link_prefix='')}
</section>"""

    # FAQ
    faq_html = f"""<section class="vod-section" id="faq">
  {T.faq_block(faqs, '❓ よくある質問')}
</section>"""

    # 関連
    related_html = T.related_service_cards(others, link_prefix='')

    # CTA末尾
    cta_end_html = f"""<section class="vod-section vod-cta-end">
  <h2>🎬 {escape(name)}を試してみる</h2>
  <p>{escape(vod.get('tagline',''))}</p>
  {_cta_html(vod, 'end')}
</section>"""

    body = f"""
<body>
{T.site_header(css_prefix='../')}
{T.pr_disclosure(css_prefix='../')}
<main class="container">
  {breadcrumb_html}
  {hero_html}
  <article class="vod-article">
    {score_html}
    {spec_html}
    {pricing_html}
    {pros_cons_html}
    {usp_html}
    {target_html}
    {genre_html}
    {signup_html}
    {cancel_html}
    {compare_html}
    {faq_html}
    {related_html}
    {cta_end_html}
    {T.editor_box()}
  </article>
</main>
{T.site_footer(css_prefix='../')}
</body>"""

    return f"<!DOCTYPE html>\n<html lang=\"ja\">\n{head}\n{body}\n</html>"


def main():
    SERVICES_DIR.mkdir(parents=True, exist_ok=True)
    created = 0
    for vod in VODS:
        out_path = SERVICES_DIR / f'{vod["id"]}.html'
        out_path.write_text(render_page(vod), encoding='utf-8')
        print(f'作成: {out_path.name}')
        created += 1
    print(f'\n=== 完了: {created}件作成 ===')


if __name__ == '__main__':
    main()
