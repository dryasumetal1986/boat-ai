import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timedelta, timezone

from data import VENUES, get_race, get_trifecta_odds
from ai import predict_race, value_candidates
from backtest import run_backtest, TARGET_RACES

st.set_page_config(
    page_title="やっちゃんの競艇AI予想PRO",
    page_icon="🚤",
    layout="centered",
)

JST = timezone(timedelta(hours=9))


def today_jst():
    return datetime.now(JST).date()


def scroll_to_results():
    components.html(
        """
        <script>
        (function () {
            let count = 0;
            const max_count = 30;

            function go() {
                try {
                    const doc = window.parent.document;
                    const target = doc.getElementById(
                        "backtest-results-anchor"
                    );

                    if (target) {
                        target.scrollIntoView({
                            behavior: "smooth",
                            block: "start"
                        });
                        return;
                    }
                } catch (e) {}

                count += 1;

                if (count < max_count) {
                    setTimeout(go, 100);
                }
            }

            setTimeout(go, 100);
        })();
        </script>
        """,
        height=1,
    )


# -----------------------------
# Session State
# -----------------------------

defaults = {
    "prediction": None,
    "backtest": None,
    "bt_page": 1,
    "scroll_request": False,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# -----------------------------
# Header
# -----------------------------

st.title("🚤 やっちゃんの競艇AI予想PRO")
st.caption("AI予想 × 実オッズ × 期待値分析")


# -----------------------------
# Race Selection
# -----------------------------

venue = st.selectbox(
    "開催場",
    list(VENUES.keys()),
)

race_no = st.selectbox(
    "レース",
    range(1, 13),
    format_func=lambda x: f"{x}R",
)


# -----------------------------
# AI Prediction
# -----------------------------

if st.button(
    "🚀 AI予想開始",
    use_container_width=True,
):
    ds = today_jst().isoformat()

    with st.spinner("🔄 AI予想を計算中…"):
        race = get_race(
            ds,
            venue,
            race_no,
        )

        if race:
            pred = predict_race(race)

            odds = get_trifecta_odds(
                ds,
                race["venue_id"],
                race_no,
            )

            candidates = value_candidates(
                pred,
                odds,
            )

            st.session_state.prediction = {
                "race": race,
                "pred": pred,
                "odds": odds,
                "candidates": candidates,
            }

        else:
            st.session_state.prediction = None

            st.error(
                "当日のレース情報を取得できませんでした。"
            )


# -----------------------------
# Prediction Result
# -----------------------------

x = st.session_state.prediction

if x:
    race = x["race"]
    pred = x["pred"]
    odds = x["odds"]

    y, m, d = race["date"].split("-")

    st.subheader(
        f"{y}年{m}月{d}日 {venue} {race_no}R"
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

    stars = max(
        1,
        min(
            5,
            round(pred["confidence"] / 20),
        ),
    )

    st.write(
        f"AI信頼度 {'⭐' * stars}"
        f"（{pred['confidence']:.1f}%）"
    )

    # -------------------------
    # Best Trifecta
    # -------------------------

    st.markdown(
        "### 💰 期待値の高い三連単"
    )

    st.caption(
        "公式BOATRACEの3連単実オッズを使用。"
        "的中率を最優先し、期待値を補助評価しています。"
    )

    best = max(
        pred["joint"],
        key=pred["joint"].get,
    )

    st.markdown(
        "**🎯 本命軸の最有力三連単**  \n"
        f"**{best[0]}-{best[1]}-{best[2]}**"
        f"　AI確率 {pred['joint'][best] * 100:.2f}%"
    )

    # -------------------------
    # Odds Status
    # -------------------------

    if len(odds) < 120:
        st.warning(
            f"公式オッズ {len(odds)}/120通り取得"
        )
        st.caption(
            "公式オッズを120通りすべて取得できていません。"
        )
    else:
        st.caption(
            "公式オッズ 120/120通り取得"
        )

    # -------------------------
    # Value Candidates
    # -------------------------

    if x["candidates"]:
        for q in x["candidates"]:
            a, b, c = q["combo"]

            st.write(
                f"🔥 **{a}-{b}-{c}**　"
                f"オッズ {q['odds']:.1f}倍　"
                f"AI確率 {q['prob'] * 100:.2f}%　"
                f"EV **+{q['ev'] * 100:.1f}%**"
            )

            st.caption(
                f"市場確率 {q['market_prob'] * 100:.2f}% / "
                f"AIとの差 +{q['edge'] * 100:.2f}pt"
            )

    else:
        st.info(
            "条件を満たすプラス期待値の買い目はありません。"
        )

    # -------------------------
    # Boat Evaluation
    # -------------------------

    st.markdown("### 🚤 6艇AI評価")

    for boat in pred["ranking"]:
        p = pred["first_probs"][boat]
        score = pred["scores"][boat]

        name = next(
            (
                b["name"]
                for b in race["boats"]
                if b["boat"] == boat
            ),
            f"{boat}号艇",
        )

        st.write(
            f"**{boat}号艇 {name}**　"
            f"1着AI確率 **{p * 100:.1f}%**　"
            f"AIスコア {score:.2f}"
        )

    # -------------------------
    # Probability Ranking
    # -------------------------

    st.markdown("### 📊 AI確率ランキング")

    for i, boat in enumerate(
        pred["ranking"],
        1,
    ):
        st.write(
            f"{i}. {boat}号艇　"
            f"{pred['first_probs'][boat] * 100:.1f}%"
        )


# -----------------------------
# Backtest
# -----------------------------

st.divider()

st.subheader("📊 AI予想バックテスト")

st.caption(
    "全国24場。現在日は除外し、"
    "前日から2026年1月1日まで遡って検証。"
)

target = st.selectbox(
    "検証レース数",
    TARGET_RACES,
    format_func=lambda x: f"{x}レース",
)


# -----------------------------
# Backtest Start
# -----------------------------

if st.button(
    "🔍 バックテスト開始",
    use_container_width=True,
):
    with st.spinner(
        "🔄 全国24場を遡って検証中…"
    ):
        result = run_backtest(
            target,
            today_jst(),
        )

    st.session_state.backtest = result
    st.session_state.bt_page = 1


# -----------------------------
# Backtest Result
# -----------------------------

bt = st.session_state.backtest

if bt:
    st.write(
        f"**検証レース数：{bt['count']}レース**"
    )

    st.write(
        f"**回収率 {bt['recovery']:.1f}%**"
    )

    st.write(
        f"**本命1着率 {bt['main_win_rate']:.1f}%**"
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
        f"**投資 {bt['investment']:,.0f}円**"
    )

    st.write(
        f"**払戻 {bt['return']:,.0f}円**"
    )

    # -------------------------
    # Scroll Anchor
    # -------------------------

    st.markdown(
        '<div id="backtest-results-anchor"></div>',
        unsafe_allow_html=True,
    )

    st.subheader("📋 検証結果")

    rows = bt["rows"]

    per_page = 10

    pages = max(
        1,
        (len(rows) + per_page - 1) // per_page,
    )

    page = min(
        max(
            1,
            st.session_state.bt_page,
        ),
        pages,
    )

    start = (
        page - 1
    ) * per_page

    end = page * per_page

    page_rows = rows[start:end]

    # -------------------------
    # Result List
    # -------------------------

    for r in page_rows:
        a, b, c = r["actual"]

        if r["exact_hit"]:
            exact_text = "✅ 3連単的中"
        else:
            exact_text = "❌ 不的中"

        if r["box_hit"]:
            box_text = "　/　AI3艇BOX的中"
        else:
            box_text = ""

        st.markdown(
            f"**{r['date']}　"
            f"{r['venue']} {r['race_no']}R**  \n"
            f"AI：🎯{r['main']}号艇　"
            f"🔥{r['counter']}号艇　"
            f"💥{r['hole']}号艇  \n"
            f"結果：🏁 **{a}-{b}-{c}**　"
            f"{exact_text}{box_text}"
        )

    # -------------------------
    # Page Navigation
    # -------------------------

    c1, c2, c3 = st.columns(
        [1, 2, 1]
    )

    with c1:
        if page > 1:
            if st.button(
                "◀ 前へ",
                use_container_width=True,
            ):
                st.session_state.bt_page = (
                    page - 1
                )

                st.session_state.scroll_request = True

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
            unsafe_allow_html=True,
        )

    with c3:
        if page < pages:
            if st.button(
                "次へ ▶",
                use_container_width=True,
            ):
                st.session_state.bt_page = (
                    page + 1
                )

                st.session_state.scroll_request = True

                st.rerun()

    # -------------------------
    # One-time Scroll
    # -------------------------

    if st.session_state.scroll_request:
        st.session_state.scroll_request = False
        scroll_to_results()
