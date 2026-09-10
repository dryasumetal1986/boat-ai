import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timedelta, timezone

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


# =========================
# Session State
# =========================

defaults = {
    "prediction": None,
    "backtest": None,
    "bt_page": 1,
    "scroll_request": False,
    "scroll_token": 0,
}

for key, value in defaults.items():

    if key not in st.session_state:
        st.session_state[key] = value


# =========================
# タイトル
# =========================

st.title(
    "🚤 やっちゃんの競艇AI予想PRO"
)

st.caption(
    "AI予想 × 実オッズ × 期待値分析"
)


# =========================
# 選択
# =========================

venue = st.selectbox(
    "開催場",
    list(VENUES.keys()),
)

race_no = st.selectbox(
    "レース",
    range(1, 13),
    format_func=lambda x:
        f"{x}R",
)


# =========================
# AI予想
# =========================

if st.button(
    "🚀 AI予想開始",
    use_container_width=True,
):

    date_str = today_jst().isoformat()

    with st.status(
        "🤖 AI予想を開始しています…",
        expanded=True,
    ) as status:

        st.write(
            "📡 レース情報を取得中…"
        )

        race = get_race(
            date_str,
            venue,
            race_no,
        )

        if not race:

            status.update(
                label=(
                    "❌ レース情報を取得できませんでした"
                ),
                state="error",
            )

            st.error(
                "当日のレース情報を取得できませんでした。"
            )

        elif len(
            race.get("boats", [])
        ) != 6:

            status.update(
                label=(
                    "❌ 6艇のデータを取得できませんでした"
                ),
                state="error",
            )

            st.error(
                "6艇の選手データを取得できませんでした。"
            )

        else:

            st.write(
                "🤖 6艇のAI評価を計算中…"
            )

            pred = predict_race(
                race
            )

            st.write(
                "💰 公式3連単オッズを取得中…"
            )

            odds = get_trifecta_odds(
                date_str,
                race["venue_id"],
                race_no,
            )

            st.write(
                f"📊 オッズ "
                f"{len(odds)}/120通りを確認中…"
            )

            st.write(
                "📈 的中率・期待値を計算中…"
            )

            candidates = value_candidates(
                pred,
                odds,
                min_prob=0.006,
                limit=8,
            )

            st.session_state.prediction = {
                "race": race,
                "pred": pred,
                "odds": odds,
                "candidates":
                    candidates,
            }

            status.update(
                label="✅ AI予想が完了しました！",
                state="complete",
                expanded=False,
            )


# =========================
# AI結果
# =========================

result = st.session_state.prediction


if result:

    race = result["race"]
    pred = result["pred"]
    odds = result["odds"]
    candidates = result["candidates"]

    y, m, d = race["date"].split("-")

    st.subheader(
        f"{y}年{m}月{d}日 "
        f"{race['venue']} "
        f"{race['race_no']}R"
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

    stars = "⭐" * max(
        1,
        round(
            pred["confidence"] / 20
        ),
    )

    st.write(
        f"AI信頼度 {stars} "
        f"（{pred['confidence']:.1f}%）"
    )

    # -------------------------
    # 本命軸の最有力3連単
    # -------------------------

    a, b, c = pred[
        "main_best_combo"
    ]

    st.markdown(
        "### 🎯 本命軸の最有力三連単"
    )

    st.write(
        f"**{a}-{b}-{c}**　"
        f"AI確率 "
        f"{pred['main_best_combo_prob'] * 100:.2f}%"
    )

    # -------------------------
    # EV候補
    # -------------------------

    st.markdown(
        "### 💰 期待値の高い三連単"
    )

    st.caption(
        "公式BOATRACEの3連単実オッズを使用"
    )

    st.caption(
        "的中率を最優先し、"
        "期待値を補助評価しています。"
    )

    if len(odds) < 120:

        st.warning(
            f"公式オッズ取得 "
            f"{len(odds)}/120通り"
        )

    else:

        st.success(
            "公式オッズ 120/120通り取得"
        )

    if candidates:

        for item in candidates:

            x, y, z = item["combo"]

            st.write(
                f"🔥 **{x}-{y}-{z}**　"
                f"オッズ "
                f"{item['odds']:.1f}倍　"
                f"AI確率 "
                f"{item['prob'] * 100:.2f}%　"
                f"EV "
                f"**+{item['ev'] * 100:.1f}%**"
            )

            st.caption(
                f"市場確率 "
                f"{item['market_prob'] * 100:.2f}% / "
                f"AIとの差 "
                f"+{item['edge'] * 100:.2f}pt"
            )

    else:

        st.info(
            "条件を満たすプラス期待値の買い目はありません。"
        )

    # -------------------------
    # 6艇
    # -------------------------

    st.markdown(
        "### 🚤 6艇AI評価"
    )

    for no in pred["ranking"]:

        probability = (
            pred["first_probs"][no]
        )

        score = pred["scores"][no]

        name = next(
            (
                b["name"]
                for b in race["boats"]
                if b["boat"] == no
            ),
            f"{no}号艇",
        )

        st.write(
            f"**{no}号艇 {name}**　"
            f"1着AI確率 "
            f"**{probability * 100:.1f}%**　"
            f"AIスコア {score:.2f}"
        )

    st.markdown(
        "### 📊 AI確率ランキング"
    )

    for rank, no in enumerate(
        pred["ranking"],
        1,
    ):

        p = pred["first_probs"][no]

        st.write(
            f"{rank}. {no}号艇　"
            f"{p * 100:.1f}%"
        )


st.divider()


# =========================
# バックテスト
# =========================

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
    format_func=lambda x:
        f"{x}レース",
)


if st.button(
    "🔍 バックテスト開始",
    use_container_width=True,
):

    with st.status(
        "📊 バックテストを開始しています…",
        expanded=True,
    ) as status:

        st.write(
            "📡 全国24場のデータを検索中…"
        )

        st.write(
            "📅 前日から過去へ遡ってレースを確認中…"
        )

        st.write(
            f"🤖 {target}レースをAI予想中…"
        )

        st.write(
            "📈 的中率・回収率を集計中…"
        )

        bt_result = run_backtest(
            target,
            today_jst(),
        )

        st.session_state.backtest = (
            bt_result
        )

        st.session_state.bt_page = 1

        st.session_state.scroll_request = False

        status.update(
            label=(
                f"✅ バックテスト完了！ "
                f"{bt_result['count']}レースを検証"
            ),
            state="complete",
            expanded=False,
        )


# =========================
# バックテスト結果
# =========================

bt = st.session_state.backtest


if bt:

    st.write(
        f"**検証レース数：{bt['count']}レース**"
    )

    st.write(
        f"**回収率 {bt['recovery']:.1f}%**"
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
        f"**投資 {bt['investment']:,.0f}円**"
    )

    st.write(
        f"**払戻 {bt['return']:,.0f}円**"
    )

    # =====================
    # 結果位置
    # =====================

    st.markdown(
        """
        <div
            id="backtest-results-anchor"
            style="
                height:1px;
                margin:0;
                padding:0;
            ">
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader(
        "📋 検証結果"
    )

    rows = bt["rows"]

    per_page = 10

    total_pages = max(
        1,
        (
            len(rows)
            + per_page
            - 1
        ) // per_page,
    )

    page = min(
        max(
            1,
            st.session_state.bt_page,
        ),
        total_pages,
    )

    start = (
        page - 1
    ) * per_page

    page_rows = rows[
        start:start + per_page
    ]

    for row in page_rows:

        a, b, c = row["actual"]

        result_text = (
            "✅ 3連単的中"
            if row["exact_hit"]
            else "❌ 不的中"
        )

        box_text = (
            "　/　AI3艇BOX的中"
            if row["box_hit"]
            else ""
        )

        p = row.get(
            "predicted_combo"
        )

        if p:
            predicted = (
                f"予想："
                f"{p[0]}-{p[1]}-{p[2]} "
            )
        else:
            predicted = ""

        st.markdown(
            f"**{row['date']}　"
            f"{row['venue']} "
            f"{row['race_no']}R**  \n"
            f"AI：🎯{row['main']}号艇　"
            f"🔥{row['counter']}号艇　"
            f"💥{row['hole']}号艇  \n"
            f"{predicted}"
            f"結果：🏁 **{a}-{b}-{c}**　"
            f"{result_text}"
            f"{box_text}"
        )

    st.write("")

    # =====================
    # ページボタン
    # =====================

    col1, col2, col3 = st.columns(
        [1, 2, 1]
    )

    with col1:

        if page > 1:

            if st.button(
                "◀ 前へ",
                use_container_width=True,
                key="bt_prev",
            ):

                st.session_state.bt_page = (
                    page - 1
                )

                st.session_state.scroll_request = True

                st.session_state.scroll_token += 1

                st.rerun()

    with col2:

        st.markdown(
            f"""
            <div style="
                text-align:center;
                padding-top:8px;
                font-weight:bold;
            ">
                {page} / {total_pages}ページ
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:

        if page < total_pages:

            if st.button(
                "次へ ▶",
                use_container_width=True,
                key="bt_next",
            ):

                st.session_state.bt_page = (
                    page + 1
                )

                st.session_state.scroll_request = True

                st.session_state.scroll_token += 1

                st.rerun()

    # =====================
    # ページ変更後スクロール
    # =====================

    if st.session_state.scroll_request:

        token = (
            st.session_state.scroll_token
        )

        st.session_state.scroll_request = False

        components.html(
            f"""
            <script>
            (() => {{

                const token = "{token}";

                function scrollResult() {{

                    try {{

                        const doc =
                            window.parent.document;

                        const target =
                            doc.getElementById(
                                "backtest-results-anchor"
                            );

                        if (!target) {{
                            return;
                        }}

                        const active =
                            doc.activeElement;

                        if (
                            active &&
                            active.blur
                        ) {{
                            active.blur();
                        }}

                        target.scrollIntoView({{
                            behavior: "smooth",
                            block: "start"
                        }});

                    }} catch(e) {{}}
                }}

                setTimeout(
                    scrollResult,
                    100
                );

                setTimeout(
                    scrollResult,
                    300
                );

                setTimeout(
                    scrollResult,
                    700
                );

                setTimeout(
                    scrollResult,
                    1200
                );

                setTimeout(
                    scrollResult,
                    1800
                );

            }})();
            </script>
            """,
            height=1,
    )
