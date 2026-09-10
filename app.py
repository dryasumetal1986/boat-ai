import streamlit as st
import streamlit.components.v1 as components

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from data import (
    VENUES,
    get_race,
    get_trifecta_odds,
)

from ai import (
    predict_race,
    value_candidates,
)

from backtest import (
    run_backtest,
    TARGET_RACES,
)


st.set_page_config(
    page_title="やっちゃんの競艇AI予想PRO",
    page_icon="🚤",
    layout="centered",
)


JST = timezone(
    timedelta(hours=9)
)


def today_jst():
    return datetime.now(JST).date()


def request_scroll():
    st.session_state.scroll_request = True


# =========================================================
# タイトル
# =========================================================

st.title(
    "🚤 やっちゃんの競艇AI予想PRO"
)

st.caption(
    "AI予想 × 実オッズ × 期待値分析"
)


# =========================================================
# 開催場・レース
# =========================================================

venue = st.selectbox(
    "開催場",
    list(VENUES.keys())
)

race_no = st.selectbox(
    "レース",
    range(1, 13),
    format_func=lambda x: f"{x}R"
)


# =========================================================
# Session State
# =========================================================

if "prediction" not in st.session_state:
    st.session_state.prediction = None

if "backtest" not in st.session_state:
    st.session_state.backtest = None

if "bt_page" not in st.session_state:
    st.session_state.bt_page = 1

if "scroll_request" not in st.session_state:
    st.session_state.scroll_request = False


# =========================================================
# AI予想開始
# =========================================================

if st.button(
    "🚀 AI予想開始",
    use_container_width=True
):

    ds = today_jst().isoformat()

    race = get_race(
        ds,
        venue,
        race_no
    )

    if not race:

        st.error(
            "当日のレース情報を取得できませんでした。"
        )

    else:

        pred = predict_race(
            race
        )

        odds = get_trifecta_odds(
            ds,
            race["venue_id"],
            race_no
        )

        candidates = value_candidates(
            pred,
            odds
        )

        st.session_state.prediction = {
            "race": race,
            "pred": pred,
            "odds": odds,
            "candidates": candidates,
        }


# =========================================================
# AI予想結果
# =========================================================

x = st.session_state.prediction


if x:

    race = x["race"]
    pred = x["pred"]
    odds = x["odds"]

    y, m, d = race["date"].split("-")

    st.subheader(
        f"{y}年{m}月{d}日 "
        f"{venue} {race_no}R"
    )

    st.write(
        f"🎯 **本命 {pred['main']}号艇**"
    )

    st.write(
        f"🔥 **対抗 {pred['counter']}号艇**"
    )

    st.write(
        f"💥 **穴 {pred['hole']}号艇**"
    )

    stars = (
        "⭐"
        * max(
            1,
            round(
                pred["confidence"]
                / 20
            )
        )
    )

    st.write(
        f"AI信頼度 {stars}"
        f"（{pred['confidence']:.1f}%）"
    )

    # -----------------------------------------------------
    # 本命軸
    # -----------------------------------------------------

    main_combo = max(
        pred["joint"],
        key=pred["joint"].get
    )

    a, b, c = main_combo

    st.markdown(
        "### 🎯 本命軸の最有力三連単"
    )

    st.write(
        f"**{a}-{b}-{c}**　"
        f"AI確率 "
        f"**{pred['joint'][main_combo] * 100:.2f}%**"
    )

    # -----------------------------------------------------
    # EV候補
    # -----------------------------------------------------

    st.markdown(
        "### 💰 期待値の高い三連単"
    )

    st.caption(
        "公式BOATRACEの3連単実オッズを使用。"
        "的中率を最優先し、期待値を補助評価しています。"
    )

    st.caption(
        f"公式オッズ "
        f"{len(odds)}/120通り取得"
    )

    if len(odds) < 120:

        st.warning(
            "公式オッズを120通りすべて取得できていません。"
        )

    candidates = x["candidates"]

    if candidates:

        for q in candidates:

            a, b, c = q["combo"]

            st.write(
                f"🔥 **{a}-{b}-{c}**　"
                f"オッズ {q['odds']:.1f}倍　"
                f"AI確率 "
                f"{q['prob'] * 100:.2f}%　"
                f"EV **+{q['ev'] * 100:.1f}%**"
            )

            st.caption(
                f"市場確率 "
                f"{q['market_prob'] * 100:.2f}% / "
                f"AIとの差 "
                f"{q['edge'] * 100:+.2f}pt"
            )

    else:

        st.info(
            "条件を満たすプラス期待値の買い目はありません。"
        )

    # -----------------------------------------------------
    # 6艇評価
    # -----------------------------------------------------

    st.markdown(
        "### 🚤 6艇AI評価"
    )

    for boat in pred["ranking"]:

        p = pred["first_probs"][boat]
        score = pred["scores"][boat]

        name = next(
            (
                b["name"]
                for b in race["boats"]
                if b["boat"] == boat
            ),
            f"{boat}号艇"
        )

        st.write(
            f"**{boat}号艇 {name}**　"
            f"1着AI確率 "
            f"**{p * 100:.1f}%**　"
            f"AIスコア {score:.2f}"
        )

    # -----------------------------------------------------
    # AI確率ランキング
    # -----------------------------------------------------

    st.markdown(
        "### 📊 AI確率ランキング"
    )

    for i, boat in enumerate(
        pred["ranking"],
        1
    ):

        st.write(
            f"{i}. {boat}号艇　"
            f"{pred['first_probs'][boat] * 100:.1f}%"
        )


# =========================================================
# 区切り
# =========================================================

st.divider()


# =========================================================
# バックテスト
# =========================================================

st.subheader(
    "📊 AI予想バックテスト"
)

st.caption(
    "全国24場。現在日は除外し、"
    "前日から2026年1月1日まで遡って検証。"
)


target = st.selectbox(
    "検証レース数",
    TARGET_RACES,
    format_func=lambda x: f"{x}レース"
)


# =========================================================
# バックテスト開始
# =========================================================

if st.button(
    "🔍 バックテスト開始",
    use_container_width=True
):

    with st.spinner(
        "全国24場を遡って検証中…"
    ):

        st.session_state.backtest = (
            run_backtest(
                target,
                today_jst()
            )
        )

    st.session_state.bt_page = 1

    st.session_state.scroll_request = False


# =========================================================
# バックテスト結果
# =========================================================

bt = st.session_state.backtest


if bt:

    st.write(
        f"**検証レース数："
        f"{bt['count']}レース**"
    )

    st.write(
        f"**回収率 "
        f"{bt['recovery']:.1f}%**"
    )

    st.write(
        f"**本命1着率 "
        f"{bt['main_win_rate']:.1f}%**"
    )

    st.write(
        f"**本命3連対率 "
        f"{bt['main_top3_rate']:.1f}%**"
    )

    st.write(
        f"**AI上位3艇全艇3連対率 "
        f"{bt['top3_all_top3_rate']:.1f}%**"
    )

    st.write(
        f"**AI選出3艇BOX的中率 "
        f"{bt['box_hit_rate']:.1f}%**"
    )

    st.write(
        f"**3連単完全的中率 "
        f"{bt['exact_hit_rate']:.1f}%**"
    )

    st.write(
        f"**投資 "
        f"{bt['investment']:,.0f}円**"
    )

    st.write(
        f"**払戻 "
        f"{bt['return']:,.0f}円**"
    )

    # =====================================================
    # スクロール用アンカー
    # =====================================================

    st.markdown(
        '<div id="backtest-results-anchor"></div>',
        unsafe_allow_html=True
    )

    st.subheader(
        "📋 検証結果"
    )

    rows = bt["rows"]

    per_page = 10

    pages = max(
        1,
        (
            len(rows)
            + per_page
            - 1
        )
        // per_page
    )

    page = min(
        max(
            1,
            st.session_state.bt_page
        ),
        pages
    )

    start = (
        page - 1
    ) * per_page

    current_rows = rows[
        start:start + per_page
    ]

    # =====================================================
    # 検証結果10件
    # =====================================================

    for r in current_rows:

        a, b, c = r["actual"]

        exact = (
            "✅ 3連単的中"
            if r["exact_hit"]
            else "❌ 不的中"
        )

        box = (
            "　/　AI3艇BOX的中"
            if r["box_hit"]
            else ""
        )

        st.markdown(
            f"**{r['date']}　"
            f"{r['venue']} "
            f"{r['race_no']}R**  \n"
            f"AI：🎯{r['main']}号艇　"
            f"🔥{r['counter']}号艇　"
            f"💥{r['hole']}号艇  \n"
            f"予想："
            f"{r['main']}-"
            f"{r['counter']}-"
            f"{r['hole']}  \n"
            f"結果：🏁 **{a}-{b}-{c}**　"
            f"{exact}{box}"
        )

    # =====================================================
    # ページ切替
    # =====================================================

    c1, c2, c3 = st.columns(
        [1, 2, 1]
    )

    with c1:

        if page > 1:

            if st.button(
                "◀ 前へ",
                use_container_width=True
            ):

                st.session_state.bt_page = (
                    page - 1
                )

                request_scroll()

                st.rerun()

    with c2:

        st.markdown(
            f"""
            <div style="
                text-align:center;
                padding-top:8px;
                font-weight:bold;
            ">
                {page} / {pages}ページ
            </div>
            """,
            unsafe_allow_html=True
        )

    with c3:

        if page < pages:

            if st.button(
                "次へ ▶",
                use_container_width=True
            ):

                st.session_state.bt_page = (
                    page + 1
                )

                request_scroll()

                st.rerun()


# =========================================================
# ページ切替後の自動スクロール
# =========================================================
#
# 常時監視しない。
# ページ切替が発生したときだけ実行。
#
# DOMにアンカーが現れるまで最大25回確認。
# 見つかったら1回だけスクロールして終了。
# =========================================================

if st.session_state.scroll_request:

    st.session_state.scroll_request = False

    components.html(
        """
        <script>
        (function () {

            let attempts = 0;
            const maxAttempts = 25;

            function scrollToResults() {

                try {

                    const doc =
                        window.parent.document;

                    const target =
                        doc.getElementById(
                            "backtest-results-anchor"
                        );

                    if (target) {

                        target.scrollIntoView({
                            behavior: "smooth",
                            block: "start"
                        });

                        return;
                    }

                } catch (e) {
                    // 再描画中は一時的に取得できない場合あり
                }

                attempts += 1;

                if (attempts < maxAttempts) {

                    setTimeout(
                        scrollToResults,
                        100
                    );
                }
            }

            setTimeout(
                scrollToResults,
                100
            );

        })();
        </script>
        """,
        height=1
    )
