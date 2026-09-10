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


# =========================
# Session State
# =========================

if "prediction" not in st.session_state:
    st.session_state.prediction = None

if "backtest" not in st.session_state:
    st.session_state.backtest = None

if "bt_page" not in st.session_state:
    st.session_state.bt_page = 1

if "scroll_results" not in st.session_state:
    st.session_state.scroll_results = False

if "scroll_token" not in st.session_state:
    st.session_state.scroll_token = 0


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
# 開催場
# =========================

venue = st.selectbox(
    "開催場",
    list(VENUES.keys()),
)


# =========================
# レース
# =========================

race_no = st.selectbox(
    "レース",
    range(1, 13),
    format_func=lambda x:
    f"{x}R",
)


# =========================
# AI予想開始
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
                    "❌ レース情報を"
                    "取得できませんでした"
                ),
                state="error",
                expanded=True,
            )

            st.error(
                "当日のレース情報を取得できませんでした。"
            )

        elif len(
            race.get("boats", [])
        ) != 6:

            status.update(
                label=(
                    "❌ 6艇のデータを"
                    "取得できませんでした"
                ),
                state="error",
                expanded=True,
            )

            st.error(
                "6艇の選手データを取得できませんでした。"
            )

        else:

            st.write(
                "🤖 6艇のAI評価を計算中…"
            )

            prediction = predict_race(
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
                prediction,
                odds,
                min_prob=0.0075,
                limit=8,
            )

            st.session_state.prediction = {
                "race": race,
                "pred": prediction,
                "odds": odds,
                "candidates": candidates,
            }

            status.update(
                label="✅ AI予想が完了しました！",
                state="complete",
                expanded=False,
            )


# =========================
# AI予想結果
# =========================

result = st.session_state.prediction


if result:

    race = result["race"]
    pred = result["pred"]
    odds = result["odds"]

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

    # =========================
    # 3連単
    # =========================

    st.markdown(
        "### 💰 期待値の高い三連単"
    )

    st.caption(
        "公式BOATRACEの3連単実オッズを使用"
    )

    st.caption(
        "的中率70%＋期待値30%。"
        "超高配当への偏りを補正しています。"
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

    candidates = result["candidates"]

    if candidates:

        for item in candidates:

            a, b, c = item["combo"]

            st.write(
                f"🔥 **{a}-{b}-{c}**　"
                f"オッズ {item['odds']:.1f}倍　"
                f"AI確率 "
                f"{item['prob'] * 100:.2f}%　"
                f"EV **+{item['ev'] * 100:.1f}%**"
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

    # =========================
    # 6艇AI評価
    # =========================

    st.markdown(
        "### 🚤 6艇AI評価"
    )

    for boat_no in pred["ranking"]:

        probability = (
            pred["first_probs"][boat_no]
        )

        score = pred["scores"][boat_no]

        boat_name = next(
            (
                boat["name"]
                for boat in race["boats"]
                if boat["boat"] == boat_no
            ),
            f"{boat_no}号艇",
        )

        st.write(
            f"**{boat_no}号艇 {boat_name}**　"
            f"1着AI確率 "
            f"**{probability * 100:.1f}%**　"
            f"AIスコア {score:.2f}"
        )

    # =========================
    # AI確率ランキング
    # =========================

    st.markdown(
        "### 📊 AI確率ランキング"
    )

    for rank, boat_no in enumerate(
        pred["ranking"],
        1,
    ):

        probability = (
            pred["first_probs"][boat_no]
        )

        st.write(
            f"{rank}. {boat_no}号艇　"
            f"{probability * 100:.1f}%"
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


# =========================
# バックテスト開始
# =========================

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

        backtest_result = run_backtest(
            target,
            today_jst(),
        )

        st.session_state.backtest = (
            backtest_result
        )

        st.session_state.bt_page = 1

        status.update(
            label=(
                f"✅ バックテスト完了！ "
                f"{backtest_result['count']}レースを検証"
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

    # =========================
    # 結果アンカー
    # =========================

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
        )
        // per_page,
    )

    page = min(
        max(
            1,
            st.session_state.bt_page,
        ),
        total_pages,
    )

    start = (
        (page - 1)
        * per_page
    )

    end = start + per_page

    page_rows = rows[start:end]

    for row in page_rows:

        a, b, c = row["actual"]

        if row["exact_hit"]:
            result_text = "✅ 3連単的中"
        else:
            result_text = "❌ 不的中"

        box_text = ""

        if row["box_hit"]:
            box_text = "　/　AI3艇BOX的中"

        predicted = row.get(
            "predicted_combo"
        )

        if predicted:
            p1, p2, p3 = predicted
            predicted_text = (
                f"予想：{p1}-{p2}-{p3}  "
            )
        else:
            predicted_text = ""

        st.markdown(
            f"**{row['date']}　"
            f"{row['venue']} "
            f"{row['race_no']}R**  \n"
            f"AI：🎯{row['main']}号艇　"
            f"🔥{row['counter']}号艇　"
            f"💥{row['hole']}号艇  \n"
            f"{predicted_text}"
            f"結果：🏁 **{a}-{b}-{c}**　"
            f"{result_text}"
            f"{box_text}"
        )

    st.write("")

    # =========================
    # ページ操作
    # =========================

    col1, col2, col3 = st.columns(
        [1, 2, 1]
    )

    with col1:

        if page > 1:

            if st.button(
                "◀ 前へ",
                use_container_width=True,
                key="backtest_prev",
            ):

                st.session_state.bt_page = (
                    page - 1
                )

                st.session_state.scroll_results = True

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
                key="backtest_next",
            ):

                st.session_state.bt_page = (
                    page + 1
                )

                st.session_state.scroll_results = True

                st.session_state.scroll_token += 1

                st.rerun()

    # =========================
    # ページ変更後スクロール
    #
    # ページ番号をHTMLに含めることで
    # 毎回別のiframeとして再描画させる
    # =========================

    if st.session_state.scroll_results:

        token = (
            st.session_state.scroll_token
        )

        st.session_state.scroll_results = False

        components.html(
            f"""
            <div id="scroll-token-{token}"></div>

            <script>
            (function() {{

                const token = "{token}";

                function go() {{

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

                        const rect =
                            target.getBoundingClientRect();

                        const top =
                            rect.top +
                            window.parent.scrollY -
                            12;

                        window.parent.scrollTo({{
                            top: top,
                            behavior: "smooth"
                        }});

                    }} catch(e) {{}}

                }}

                setTimeout(go, 150);
                setTimeout(go, 500);
                setTimeout(go, 1000);
                setTimeout(go, 1800);

            }})();
            </script>
            """,
            height=1,
)
