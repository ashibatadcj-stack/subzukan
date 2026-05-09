"""
GA4 + Search Console データから Markdown レポートを生成
"""
from __future__ import annotations
from datetime import date, timedelta
from pathlib import Path


def _fmt_seconds(s: float) -> str:
    s = int(s)
    if s < 60:
        return f"{s}秒"
    return f"{s // 60}分{s % 60}秒"


def _table(headers: list[str], rows: list[list[str]]) -> str:
    """Markdownテーブルを生成"""
    sep = "|" + "|".join([" --- " for _ in headers]) + "|"
    head = "| " + " | ".join(headers) + " |"
    body = "\n".join(["| " + " | ".join(map(str, r)) + " |" for r in rows])
    return f"{head}\n{sep}\n{body}"


def _shorten_path(p: str, n: int = 50) -> str:
    if len(p) > n:
        return p[: n - 1] + "…"
    return p


def render(ga4: dict[str, list[dict]], gsc: dict[str, list[dict]],
           days: int) -> str:
    """ga4 / gsc データからMarkdownレポート文字列を生成"""
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=days - 1)

    out: list[str] = []
    out.append(f"# サイト分析レポート（直近{days}日: {start} 〜 {end}）")
    out.append(f"\n生成日: {date.today().isoformat()}\n")

    # ────────────────────────────────────────────────
    # サマリー
    # ────────────────────────────────────────────────
    out.append("## 📊 サマリー\n")

    daily = ga4.get("daily_pageviews", [])
    total_pv = sum(r.get("screenPageViews", 0) for r in daily)
    total_sessions = sum(r.get("sessions", 0) for r in daily)
    total_users = sum(r.get("totalUsers", 0) for r in daily)
    avg_pv = total_pv / max(len(daily), 1)

    gsc_daily = gsc.get("daily", [])
    total_clicks = sum(r.get("clicks", 0) for r in gsc_daily)
    total_impressions = sum(r.get("impressions", 0) for r in gsc_daily)
    avg_position = (sum(r.get("position", 0) for r in gsc_daily) / len(gsc_daily)) if gsc_daily else 0
    overall_ctr = (total_clicks / total_impressions * 100) if total_impressions else 0

    out.append(_table(
        ["指標", "数値"],
        [
            ["合計PV", f"{total_pv:,}"],
            ["合計セッション", f"{total_sessions:,}"],
            ["合計ユニークユーザー", f"{total_users:,}"],
            ["1日平均PV", f"{avg_pv:.1f}"],
            ["検索クリック数", f"{total_clicks:,}"],
            ["検索表示回数", f"{total_impressions:,}"],
            ["平均CTR", f"{overall_ctr:.2f}%"],
            ["平均検索順位", f"{avg_position:.1f}位"],
        ],
    ))
    out.append("")

    # ────────────────────────────────────────────────
    # 人気ページ TOP10
    # ────────────────────────────────────────────────
    out.append("## 🔥 人気ページ TOP10（GA4 PV順）\n")
    top_pages = ga4.get("top_pages", [])[:10]
    rows = []
    for i, p in enumerate(top_pages, 1):
        path = _shorten_path(p.get("pagePath", ""))
        pv = p.get("screenPageViews", 0)
        sess = p.get("sessions", 0)
        eng = p.get("userEngagementDuration", 0)
        avg_eng = (eng / sess) if sess else 0
        bounce = p.get("bounceRate", 0)
        rows.append([i, path, f"{pv:,}", f"{sess:,}", _fmt_seconds(avg_eng), f"{bounce*100:.1f}%"])
    out.append(_table(
        ["#", "パス", "PV", "セッション", "平均滞在", "直帰率"],
        rows,
    ) if rows else "_データなし_")
    out.append("")

    # ────────────────────────────────────────────────
    # 流入チャネル
    # ────────────────────────────────────────────────
    out.append("## 🌐 流入チャネル\n")
    sources = ga4.get("traffic_sources", [])
    total = sum(s.get("sessions", 0) for s in sources) or 1
    rows = []
    for s in sources:
        ch = s.get("sessionDefaultChannelGroup", "(unknown)")
        sess = s.get("sessions", 0)
        users = s.get("totalUsers", 0)
        share = sess / total * 100
        rows.append([ch, f"{sess:,}", f"{users:,}", f"{share:.1f}%"])
    out.append(_table(
        ["チャネル", "セッション", "ユーザー", "シェア"],
        rows,
    ) if rows else "_データなし_")
    out.append("")

    # ────────────────────────────────────────────────
    # デバイス
    # ────────────────────────────────────────────────
    out.append("## 📱 デバイス\n")
    devices = ga4.get("device", [])
    rows = []
    for d in devices:
        cat = d.get("deviceCategory", "(unknown)")
        sess = d.get("sessions", 0)
        users = d.get("totalUsers", 0)
        bounce = d.get("bounceRate", 0)
        rows.append([cat, f"{sess:,}", f"{users:,}", f"{bounce*100:.1f}%"])
    out.append(_table(
        ["デバイス", "セッション", "ユーザー", "直帰率"],
        rows,
    ) if rows else "_データなし_")
    out.append("")

    # ────────────────────────────────────────────────
    # 検索クエリ TOP20（Search Console）
    # ────────────────────────────────────────────────
    out.append("## 🔍 検索クエリ TOP20（Search Console）\n")
    queries = gsc.get("top_queries", [])[:20]
    rows = []
    for i, q in enumerate(queries, 1):
        rows.append([
            i,
            q.get("query", ""),
            f"{q.get('clicks', 0):,}",
            f"{q.get('impressions', 0):,}",
            f"{q.get('ctr', 0):.2f}%",
            f"{q.get('position', 0):.1f}位",
        ])
    out.append(_table(
        ["#", "クエリ", "クリック", "表示回数", "CTR", "順位"],
        rows,
    ) if rows else "_データなし_")
    out.append("")

    # ────────────────────────────────────────────────
    # 検索流入ページ TOP15
    # ────────────────────────────────────────────────
    out.append("## 🎯 検索流入ページ TOP15\n")
    pages = gsc.get("top_pages", [])[:15]
    rows = []
    for i, p in enumerate(pages, 1):
        path = _shorten_path(p.get("page", "").replace("https://cardshindan.com", ""))
        rows.append([
            i,
            path,
            f"{p.get('clicks', 0):,}",
            f"{p.get('impressions', 0):,}",
            f"{p.get('ctr', 0):.2f}%",
            f"{p.get('position', 0):.1f}位",
        ])
    out.append(_table(
        ["#", "パス", "クリック", "表示回数", "CTR", "順位"],
        rows,
    ) if rows else "_データなし_")
    out.append("")

    # ────────────────────────────────────────────────
    # 🩺 本日の状況診断（サイトのライフサイクル段階・統計的妥当性）
    # ────────────────────────────────────────────────
    out.append("## 🩺 本日の状況診断\n")

    # サイトライフサイクル判定
    if total_clicks == 0 and total_impressions < 100:
        lifecycle = "🟢 立ち上げ期（インデックス進行中）"
        lifecycle_note = (
            "Search Consoleにデータがまだ蓄積されていない段階。"
            "検索流入の本格化までは通常1〜4週間かかる。"
            "**この段階での主要KPIは「PV増」ではなく「インデックス完了URL数の増加」**。"
        )
    elif total_clicks < 50:
        lifecycle = "🟡 成長初期（流入が立ち上がり始めた）"
        lifecycle_note = (
            "検索流入が発生し始めた段階。"
            "個別クエリのCTR・順位を見て、勝てるキーワードを特定するのが重要。"
        )
    elif total_clicks < 500:
        lifecycle = "🟠 成長期（最適化フェーズ）"
        lifecycle_note = (
            "本格的な流入が発生中。CTR・滞在時間・回遊率の改善で成果を伸ばせる段階。"
        )
    else:
        lifecycle = "🟣 成熟期"
        lifecycle_note = "継続的なコンテンツ拡充とCV率改善が中心。"

    out.append(f"**サイト段階**: {lifecycle}\n")
    out.append(f"{lifecycle_note}\n")

    # 統計的妥当性の警告
    warnings = []
    if total_sessions < 20:
        warnings.append(
            f"⚠ **統計的有意性の注意**: 直近{days}日のセッション数が {total_sessions} と少ないため、"
            f"個別ページの直帰率・滞在時間の数値はノイズが大きい。"
            f"50セッション以上溜まるまでは個別ページ単位の改善判断は保留が推奨。"
        )

    direct_share = next((s.get("sessions", 0) / total * 100 for s in sources
                          if s.get("sessionDefaultChannelGroup", "") == "Direct"), 0)
    if direct_share > 70:
        warnings.append(
            f"ℹ️ **Direct流入が {direct_share:.0f}%**: 開発者・クローラ・テスト訪問が中心。"
            f"一般ユーザーの流入はOrganic Searchが本格化してから増加する。"
        )

    if not gsc.get("top_queries"):
        warnings.append(
            f"ℹ️ **Search Console クエリデータ未蓄積**: GA4のOrganic Searchが計上されていても、"
            f"Search Consoleへの反映には2〜7日のラグがある。クエリ別分析は数日後に。"
        )

    for w in warnings:
        out.append(f"- {w}")
    out.append("")

    # ────────────────────────────────────────────────
    # 🎯 直近の打ち手評価（4分類でROIを判断）
    # ────────────────────────────────────────────────
    out.append("## 🎯 直近の打ち手評価（ROI観点）\n")
    out.append("以下の各施策を「**本当に必要か・効果はあるか**」の4分類で評価:\n")
    out.append("| 判定 | 意味 | 行動 |")
    out.append("| --- | --- | --- |")
    out.append("| 🟢 やる | 即時着手で効果が期待できる | 今日アクション実行 |")
    out.append("| 🔵 様子見（能動的） | 既存施策の効果検証 or データ蓄積待ち。**動かないことに価値がある** | 期日まで観察に徹する |")
    out.append("| 🟡 検討 | 効果はあり得るが優先度中位 | 状況次第で判断 |")
    out.append("| 🔴 やらない | 現段階でROIが低い・効果計測不能 | 今日は手を出さない |")
    out.append("")

    # 施策候補リスト（ライフサイクルごとに評価が変わる）
    # 各 action: name / verdict / reason / expected /
    #           wait_until (🔵時に観察期日) / decision_criteria (🔵時に判断条件)
    actions = []

    # アクション1: GSCインデックス申請
    if total_clicks < 100:
        actions.append({
            "name": "GSCで未インデックスURLの登録リクエスト",
            "verdict": "🟢 やる",
            "reason": (
                "立ち上げ期では最大の即効施策。"
                "コンテンツが優良でもインデックスされなければ流入ゼロのため、"
                "他のあらゆる施策の前提条件。1日10〜20URLの手動申請が現実解。"
            ),
            "expected": "数日でインデックス進行 → 1〜2週間で検索流入が本格化",
        })

    # アクション2: 既存施策の効果観察（能動的様子見）
    if total_clicks < 100:
        actions.append({
            "name": "既存施策の効果観察（インデックス進捗・GA4推移）",
            "verdict": "🔵 様子見",
            "reason": (
                "GSC申請・コンテンツ追加・IndexNow通知などの既存施策の効果を測るタイミング。"
                "短期間で次々と新施策を追加すると **何が効いたか分からなくなる** ため、"
                "意図的に手を止めて観察に徹することが、次の打ち手を正しく選ぶ前提条件になる。"
            ),
            "expected": "インデックス完了URL数の増加、Organic Searchの本格化",
            "wait_until": "3〜4日後",
            "decision_criteria": (
                "`python inspect_all_urls.py` でインデックス済URLが20件以上に増えていれば、"
                "コンテンツ最適化フェーズに移行。10件未満ならインデックス促進をさらに継続。"
            ),
        })

    # アクション3: Search Console データ蓄積待ち（能動的様子見）
    if not gsc.get("top_queries"):
        actions.append({
            "name": "Search Console クエリデータの蓄積待ち",
            "verdict": "🔵 様子見",
            "reason": (
                "GA4でOrganic Searchが計上されてもSearch Console側の反映には2〜7日のラグがある。"
                "クエリ別CTR・順位データが揃うまでは、タイトル・description最適化は判断不能。"
                "**焦って先回りすると的外れな修正になる**ため、データを待つことが正解。"
            ),
            "expected": "どのキーワードで何位なのかが見える → 戦略的なタイトル/見出し最適化が可能に",
            "wait_until": "1週間後（5/15-16頃）",
            "decision_criteria": (
                "Search Console > 検索パフォーマンス でクエリが10件以上表示されたら本格分析開始。"
                "表示回数が伸びている＋低CTRのクエリがあれば、その記事のタイトル改善を最優先。"
            ),
        })

    # アクション4: 新規記事追加
    actions.append({
        "name": "新規記事の量産",
        "verdict": "🔴 やらない" if total_clicks < 50 else "🟡 検討",
        "reason": (
            "既存記事が未インデックス or 評価データが揃っていない段階で書き足しても、"
            "Googleからの評価は積み上がらない。**先にインデックス・評価データを揃え、"
            "勝てるキーワードを把握してから書く**のが効率的。"
        ) if total_clicks < 50 else (
            "Search Consoleデータでニーズの高いキーワードが判明してから、ターゲットを絞って書くのが効率的。"
        ),
        "expected": "立ち上げ期の量産は効果限定的（インプレッション増加のみ）",
    })

    # アクション5: タイトル・description最適化
    if total_impressions > 100:
        low_ctr = [q for q in queries if q.get("impressions", 0) >= 50 and q.get("ctr", 0) < 2.0]
        if low_ctr:
            actions.append({
                "name": f"低CTR（<2%）クエリ {len(low_ctr)}件のタイトル/description最適化",
                "verdict": "🟢 やる",
                "reason": (
                    f"既に表示回数50以上ある＝順位は出ているのにクリックされていない状態。"
                    f"タイトル改善でCTRが2倍になればクリック数も2倍になる即効施策。"
                    f"例: 「{low_ctr[0]['query']}」（表示{low_ctr[0]['impressions']:,}・CTR {low_ctr[0]['ctr']:.2f}%）"
                ),
                "expected": "CTR改善（理想3〜5%）でクリック数が2〜3倍に",
            })

    # アクション6: 11-20位の記事の補強
    if total_impressions > 100:
        near_top = [q for q in queries if 11 <= q.get("position", 0) <= 20 and q.get("impressions", 0) >= 30]
        if near_top:
            actions.append({
                "name": f"11〜20位クエリ {len(near_top)}件の対象記事を補強（内部リンク・見出し・字数）",
                "verdict": "🟢 やる",
                "reason": (
                    "あと一押しで1ページ目（10位以内）に入れる位置。"
                    "1ページ目に入るとCTRが3〜10倍に跳ねるため、コスパが極めて高い。"
                ),
                "expected": "順位2〜5上昇 → CTR大幅増 → 流入数倍化",
            })

    # アクション7: 直帰率改善
    landings = ga4.get("landing_pages", [])
    high_bounce = [l for l in landings if l.get("bounceRate", 0) > 0.7 and l.get("sessions", 0) >= 30]
    if high_bounce:
        actions.append({
            "name": f"直帰率70%超のランディング {len(high_bounce)}件の改善",
            "verdict": "🟡 検討",
            "reason": (
                "30セッション以上集まっているので統計的には参考になる。"
                "ただしVOD/サブスク系比較記事は「結論だけ見て離脱」が自然なため、"
                "高直帰率＝悪ではない。**滞在時間と合わせて判断**する必要あり。"
            ),
            "expected": "回遊率改善は副次的指標。一次KPIは検索流入数",
        })
    elif any(l.get("bounceRate", 0) > 0.7 for l in landings):
        actions.append({
            "name": "直帰率70%超のランディング改善",
            "verdict": "🔴 やらない",
            "reason": (
                "セッション30未満では統計ノイズが大きい。"
                "「3PV中3直帰」で100%になっても改善判断には不十分。"
                "サンプルが揃ってから検討。"
            ),
            "expected": "現時点では効果計測不能",
        })

    # アクション8: 技術SEO（CWV / WebP / OGP等）
    actions.append({
        "name": "技術SEO（CWV・OGP・schema等）の細部最適化",
        "verdict": "🔴 やらない",
        "reason": (
            "基本のArticle/FAQ/HowTo/Product schema、OGP、WebPは既に実装済み。"
            "細部の最適化はCV率に劇的影響しないため、**コンテンツ・インデックスを優先**。"
            "順位が中位（10〜30位）に集中してきたら手を入れる価値が出る。"
        ),
        "expected": "現段階では順位への寄与が小さい",
    })

    # アクション9: SNS発信・被リンク獲得
    actions.append({
        "name": "SNS発信・被リンク獲得",
        "verdict": "🟡 検討" if total_clicks > 0 else "🔴 やらない",
        "reason": (
            "サイトコンテンツがインデックスされていない段階では、誘導した先で評価が積み上がりにくい。"
            "インデックスが揃ってから外部流入を増やすのが効率的。"
        ) if total_clicks == 0 else (
            "X（旧Twitter）アカウント運用で記事をシェア → 直接流入＋被リンク確保。"
            "アフィリエイトサイトとしては中長期で必要な施策。"
        ),
        "expected": "中長期的な権威性UP・直接流入経路の確保",
    })

    # 描画
    for i, a in enumerate(actions, 1):
        out.append(f"### {i}. {a['name']}")
        out.append(f"**判定**: {a['verdict']}\n")
        out.append(f"**理由**: {a['reason']}\n")
        out.append(f"**期待効果**: {a['expected']}\n")
        if "wait_until" in a:
            out.append(f"**観察期日**: {a['wait_until']}\n")
            out.append(f"**判断条件**: {a['decision_criteria']}\n")

    # ────────────────────────────────────────────────
    # 🎯 今日のネクストアクション（🟢着手 + 🔵様子見を統合）
    # ────────────────────────────────────────────────
    out.append("## 🎯 今日のネクストアクション\n")

    # 🟢 能動的アクション
    todo_active = [a for a in actions if "🟢" in a["verdict"]]
    out.append("### 🟢 着手するもの\n")
    if todo_active:
        for i, a in enumerate(todo_active, 1):
            out.append(f"{i}. **{a['name']}**")
            out.append(f"   - 期待効果: {a['expected']}")
    else:
        out.append("_該当なし_")
    out.append("")

    # 🔵 能動的様子見
    todo_observe = [a for a in actions if "🔵" in a["verdict"]]
    out.append("### 🔵 能動的に様子見（何もしないことが正解）\n")
    if todo_observe:
        out.append("以下の項目は**意図的に手を止めて観察に徹する**のが今日のベストアクション。")
        out.append("動くことよりも、データが揃うのを待つことに価値がある。\n")
        for i, a in enumerate(todo_observe, 1):
            out.append(f"{i}. **{a['name']}**")
            out.append(f"   - 観察期日: {a.get('wait_until', '-')}")
            out.append(f"   - 判断条件: {a.get('decision_criteria', '-')}")
    else:
        out.append("_該当なし_")
    out.append("")

    # ────────────────────────────────────────────────
    # ❌ 今やらない方が良いこと
    # ────────────────────────────────────────────────
    out.append("## ❌ 今やらない方が良いこと（ROI低）\n")
    skip = [a for a in actions if "🔴" in a["verdict"]]
    if skip:
        for i, a in enumerate(skip, 1):
            short_reason = a["reason"][:80] + ("…" if len(a["reason"]) > 80 else "")
            out.append(f"{i}. **{a['name']}** — {short_reason}")
    else:
        out.append("_該当なし_")
    out.append("")

    # ────────────────────────────────────────────────
    # 📅 次の判断ポイント（🔵様子見の期日を集約）
    # ────────────────────────────────────────────────
    out.append("## 📅 次の判断ポイント\n")
    if todo_observe:
        out.append("能動的様子見の期日が来たら、以下の判断条件で次のアクションを決定:\n")
        for a in todo_observe:
            out.append(f"- **{a.get('wait_until', '-')}**: {a['name']}")
            out.append(f"  - 判断条件: {a.get('decision_criteria', '-')}")
    else:
        # フォールバック（🔵がない場合）
        if total_clicks == 0:
            out.append("- **3〜4日後**: `python inspect_all_urls.py` でインデックス進捗確認")
            out.append("- **1週間後**: Search Consoleにクエリデータが反映されたら本格分析開始")
        elif total_clicks < 50:
            out.append("- **明日**: 流入クエリの内訳を確認し、勝てそうなキーワードを特定")
            out.append("- **1週間後**: CTR・順位データから記事タイトル最適化候補を抽出")
        else:
            out.append("- **毎日**: 流入クエリの変化を観察、新規キーワードを発掘")
            out.append("- **週次**: 順位変動の大きい記事の補強")
    out.append("")

    out.append("---")
    out.append(f"\n_GA4プロパティ_: `{__import__('os').environ.get('GA4_PROPERTY_ID', '?')}`")
    out.append(f"_Search Consoleサイト_: `{__import__('os').environ.get('GSC_SITE_URL', '?')}`")

    return "\n".join(out)


def save_report(content: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"report-{date.today().isoformat()}.md"
    path.write_text(content, encoding="utf-8")
    return path
