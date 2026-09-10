import streamlit as st

from datetime import datetime
from zoneinfo import ZoneInfo

import ai
import backtest
import data


# =========================================================
# 基本設定
# =========================================================

st.set_page_config(
    page_title="🚤 やっちゃんの競艇AI予想PRO",
    page_icon="🚤",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }

    h1 {
        font-size: 1.8rem !important;
    }

    h2 {
        font-size: 1.35rem !important;
    }

    h3 {
        font-size: 1.15rem !important;
    }

    .metric-card {
        border: 1px solid rgba(128,128,128,0.25);
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 10px;
        text-align: center;
    }

    .boat-card {
        border: 1px solid rgba(128,128,128,0.25);
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 8px;
    }

    .result-card {
        border: 1px solid rgba(128,128,128,0.22);
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 10px;
    }

    .small-text {
        font-size: 0.82rem;
        opacity: 0.75;
    }

    .big-number {
        font-size: 1.5rem;
        font-weight: 700;
    }

    @media (max-width: 640px) {

        .block-container {
            padding-left: 0.7rem;
            padding-right: 0.7rem;
            padding-top: 0.7rem;
        }

        h1 {
            font-size: 1.45rem !important;
        }

        h2 {
            font-size: 1.2rem !important;
        }

        .metric-card {
            padding: 10px;
        }

    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# Session State
# =========================================================

if "prediction" not in st.session_state:
    st.session_state.prediction = None

if "prediction_meta" not in st.session_state:
    st.session_state.prediction_meta = None

if "backtest_result" not in st.session_state:
    st.session_state.backtest_result = None

if "backtest_page" not in st.session_state:
    st.session_state.backtest_page = 0

if "backtest_page_size" not in st.session_state:
    st.session_state.backtest_page_size = 10

if "scroll_to_backtest" not in st.session_state:
    st.session_state.scroll_to_backtest = False


# =========================================================
# 日付
# =========================================================

JST = ZoneInfo(
    "Asia/Tokyo"
)

now_jst = datetime.now(JST)

today_jst = now_jst.strftime(
    "%Y%m%d"
)

today_display = now_jst.strftime(
    "%Y/%m/%d"
)


# =========================================================
# タイトル
# =========================================================

st.title(
    "🚤 やっちゃんの競艇AI予想PRO"
)

st.caption(
    f"AI予想・公式3連単オッズ・EV分析・バックテスト | {today_display}"
)


# =========================================================
# レース選択
# =========================================================

st.subheader(
    "🎯 レース選択"
)

raw_today = data.get_data(
    today_jst
)

race_rows = data.get_race_rows(
    raw_today
)

stadium_options = [
    (
        row["stadium_number"],
        row["stadium"],
    )
    for row in race_rows
]

# 重複除去
stadium_options = list(
    dict.fromkeys(
        stadium_options
    )
)

if not stadium_options:

    st.warning(
        "本日のレースデータを取得できませんでした。"
    )

    st.stop()


col1, col2 = st.columns(
    2
)

with col1:

    stadium_label = st.selectbox(
        "競艇場",
        options=[
            f"{number}: {name}"
            for number, name
            in stadium_options
        ],
    )

stadium_number = int(
    stadium_label.split(":")[0]
)

stadium_name = data.get_stadium_name(
    stadium_number
)

stadium_races = [
    row["race_number"]
    for row in race_rows
    if row["stadium_number"]
    == stadium_number
]

stadium_races.sort()


with col2:

    race_number = st.selectbox(
        "レース",
        options=stadium_races,
        format_func=lambda x: f"{x}R",
    )


# =========================================================
# AI予想ボタン
# =========================================================

if st.button(
    "🤖 AI予想を実行",
    type="primary",
    use_container_width=True,
):

    with st.spinner(
        "レース情報・公式オッズを取得してAI分析中..."
    ):

        race = data.get_race(
            raw_today,
            stadium_number,
            race_number,
        )

        racers = data.get_race_racers(
            race
        )

        odds = data.get_trifecta_odds(
            today_jst,
            stadium_number,
            race_number,
        )

        prediction = ai.tri_ai(
            racers,
            odds=odds,
        )

        st.session_state.prediction = (
            prediction
        )

        st.session_state.prediction_meta = {
            "stadium_number": stadium_number,
            "stadium_name": stadium_name,
            "race_number": race_number,
        }


# =========================================================
# AI予想表示
# =========================================================

prediction = st.session_state.prediction
prediction_meta = (
    st.session_state.prediction_meta
)

if prediction:

    st.divider()

    st.subheader(
        "🤖 AI予想"
    )

    main = prediction.get(
        "main"
    )

    counter = prediction.get(
        "counter"
    )

    hole = prediction.get(
        "hole"
    )

    confidence = prediction.get(
        "confidence",
        0.55,
    )

    confidence_percent = (
        confidence * 100
    )

    stars = (
        "⭐"
        * max(
            1,
            min(
                5,
                int(
                    round(
                        confidence_percent
                        / 20
                    )
                ),
            ),
        )
    )

    if prediction_meta:

        st.caption(
            f"📍 {prediction_meta['stadium_name']} "
            f"{prediction_meta['race_number']}R"
        )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            f"""
            <div class="boat-card">
                <div>🔥 本命</div>
                <div class="big-number">
                    {main}号艇
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div class="boat-card">
                <div>⚡ 対抗</div>
                <div class="big-number">
                    {counter}号艇
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f"""
            <div class="boat-card">
                <div>💥 穴</div>
                <div class="big-number">
                    {hole}号艇
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write(
        f"AI信頼度 {stars} "
        f"（{confidence_percent:.1f}%）"
    )


    # =====================================================
    # 6艇1着確率
    # =====================================================

    st.subheader(
        "📊 6艇1着確率"
    )

    probabilities = prediction.get(
        "probabilities",
        {},
    )

    ranking = prediction.get(
        "ranking",
        [],
    )

    for boat in ranking:

        probability = probabilities.get(
            boat,
            0.0,
        )

        st.progress(
            min(
                1.0,
                probability,
            ),
            text=(
                f"{boat}号艇　"
                f"{probability * 100:.3f}%"
            ),
        )


    # =====================================================
    # 3連単EV
    # =====================================================

    st.divider()

    st.subheader(
        "💰 3連単EV分析"
    )

    candidates = prediction.get(
        "trifecta_candidates",
        [],
    )

    odds_available = prediction.get(
        "odds_available",
        False,
    )

    if not odds_available:

        st.warning(
            "公式3連単オッズを取得できませんでした。"
        )

    else:

        st.success(
            f"公式3連単オッズ取得済み："
            f"{len(prediction.get('odds', {}))}/120通り"
        )

        st.caption(
            "EV = AI確率 × 公式オッズ − 1"
            "｜市場確率 = 1 ÷ 公式オッズ"
        )

        for item in candidates[:8]:

            combo = item[
                "combination"
            ]

            odd = item[
                "odds"
            ]

            probability = item[
                "probability"
            ]

            market_probability = item[
                "market_probability"
            ]

            ev_rate = item[
                "ev_rate"
            ]

            edge = item[
                "edge"
            ]

            combo_text = "-".join(
                str(x)
                for x in combo
            )

            if odd is None:
                continue

            if ev_rate is None:
                ev_text = "—"
            else:
                ev_text = (
                    f"{ev_rate:+.1f}%"
                )

            if edge is None:
                edge_text = "—"
            else:
                edge_text = (
                    f"{edge * 100:+.3f}%"
                )

            market_text = (
                f"{market_probability * 100:.3f}%"
                if market_probability
                is not None
                else "—"
            )

            st.markdown(
                f"""
                <div class="result-card">
                    <b>🎯 {combo_text}</b><br>
                    オッズ：<b>{odd:g}倍</b><br>
                    AI確率：
                    <b>{probability * 100:.3f}%</b><br>
                    市場確率：
                    {market_text}<br>
                    EV：
                    <b>{ev_text}</b><br>
                    Edge：
                    {edge_text}
                </div>
                """,
                unsafe_allow_html=True,
            )


    # =====================================================
    # AI検証指標
    # =====================================================

    st.divider()

    st.subheader(
        "📈 AI評価"
    )

    st.caption(
        "バックテストと同じ判定基準で表示します。"
    )

    top3 = ranking[:3]

    top3_text = (
        "・".join(
            f"{x}号艇"
            for x in top3
        )
    )

    st.markdown(
        f"""
        <div class="metric-card">
            <div class="small-text">
                AI上位3艇
            </div>
            <div class="big-number">
                {top3_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# バックテスト
# =========================================================

st.divider()

st.markdown(
    '<div id="backtest-results-anchor"></div>',
    unsafe_allow_html=True,
)

st.subheader(
    "📋 検証結果"
)

st.caption(
    "当日を除外し、前日までの完了レースを "
    "2026/01/01まで遡って検証します。"
)

count = st.selectbox(
    "検証レース数",
    options=[
        100,
        300,
        500,
        1000,
    ],
    index=0,
)

if st.button(
    "🔎 バックテスト開始",
    use_container_width=True,
):

    st.session_state.backtest_result = None
    st.session_state.backtest_page = 0

    progress = st.progress(
        0.0,
        text="検証データを取得中..."
    )

    def update_progress(value):
        progress.progress(
            float(value),
            text=(
                f"検証中... "
                f"{value * 100:.0f}%"
            ),
        )

    result = backtest.run_backtest(
        today_jst,
        count,
        progress_callback=update_progress,
    )

    progress.progress(
        1.0,
        text="検証完了"
    )

    st.session_state.backtest_result = (
        result
    )

    st.session_state.backtest_page = 0

    st.session_state.scroll_to_backtest = True

    st.rerun()


# =========================================================
# バックテスト結果
# =========================================================

result = st.session_state.backtest_result

if result:

    total = result.get(
        "total",
        0,
    )

    if total == 0:

        st.warning(
            "検証可能な完了レースがありませんでした。"
        )

    else:

        # -------------------------------------------------
        # 指標
        # -------------------------------------------------

        col1, col2 = st.columns(2)

        with col1:

            st.metric(
                "本命1着率",
                f"{result['main_win_rate']:.1f}%",
            )

        with col2:

            st.metric(
                "本命3連対率",
                f"{result['main_top3_rate']:.1f}%",
            )

        col3, col4 = st.columns(2)

        with col3:

            st.metric(
                "AI上位3艇 全艇3連対率",
                f"{result['top3_all_top3_rate']:.1f}%",
            )

        with col4:

            st.metric(
                "AI3連単完全的中率",
                f"{result['trifecta_hit_rate']:.1f}%",
            )

        col5, col6 = st.columns(2)

        with col5:

            st.metric(
                "回収率",
                f"{result['recovery']:.1f}%",
            )

        with col6:

            st.metric(
                "検証レース数",
                f"{total}R",
            )

        st.write("")

        col7, col8 = st.columns(2)

        with col7:

            st.metric(
                "投資額",
                f"{result['investment']:,}円",
            )

        with col8:

            st.metric(
                "払戻",
                f"{result['payout']:,}円",
            )


        # -------------------------------------------------
        # 検証条件
        # -------------------------------------------------

        st.caption(
            f"1レース {backtest.BET_AMOUNT}円投資 "
            f"｜ AI本命・対抗・穴の3連単1点"
            f"｜ 当日除外"
            f"｜ 前日から2026/01/01まで"
        )


        # -------------------------------------------------
        # ページング
        # -------------------------------------------------

        results = result.get(
            "results",
            [],
        )

        page_size = (
            st.session_state.backtest_page_size
        )

        total_pages = max(
            1,
            (
                len(results)
                + page_size
                - 1
            )
            // page_size,
        )

        current_page = min(
            st.session_state.backtest_page,
            total_pages - 1,
        )

        st.session_state.backtest_page = (
            current_page
        )

        start = (
            current_page
            * page_size
        )

        end = min(
            start + page_size,
            len(results),
        )

        page_results = results[
            start:end
        ]

        st.markdown(
            f"**{start + 1}～{end}件 / "
            f"{len(results)}件**"
        )

        # -------------------------------------------------
        # 検証レース一覧
        # -------------------------------------------------

        for item in page_results:

            date_text = item[
                "date"
            ]

            if len(date_text) == 8:
                date_text = (
                    f"{date_text[:4]}/"
                    f"{date_text[4:6]}/"
                    f"{date_text[6:8]}"
                )

            stadium = item[
                "stadium"
            ]

            race_number = item[
                "race"
            ]

            main = item[
                "main"
            ]

            counter = item[
                "counter"
            ]

            hole = item[
                "hole"
            ]

            actual = item[
                "actual"
            ]

            actual_text = "-".join(
                str(x)
                for x in actual
            )

            ai_top3_hit_count = item.get(
                "ai_top3_hit_count",
                0,
            )

            trifecta_hit = item.get(
                "trifecta_hit",
                False,
            )

            if trifecta_hit:
                trifecta_text = (
                    "🎯 3連単完全的中"
                )
            else:
                trifecta_text = (
                    "❌ 3連単不的中"
                )

            st.markdown(
                f"""
                <div class="result-card">

                    <b>
                        {date_text}
                        {stadium}
                        {race_number}R
                    </b>

                    <br><br>

                    🤖 AI：
                    <b>
                        🔥{main}号艇
                        ⚡{counter}号艇
                        💥{hole}号艇
                    </b>

                    <br>

                    🏁 結果：
                    <b>{actual_text}</b>

                    <br>

                    {trifecta_text}

                    <br>

                    📊 AI上位3艇：
                    <b>{ai_top3_hit_count}/3艇</b>
                    が3連対

                </div>
                """,
                unsafe_allow_html=True,
            )


        # -------------------------------------------------
        # ページ操作
        # -------------------------------------------------

        st.write("")

        prev_col, page_col, next_col = st.columns(
            [1, 1, 1]
        )

        with prev_col:

            if st.button(
                "◀ 前へ",
                disabled=current_page <= 0,
                use_container_width=True,
            ):

                st.session_state.backtest_page = (
                    current_page - 1
                )

                st.session_state.scroll_to_backtest = True

                st.rerun()

        with page_col:

            st.markdown(
                f"""
                <div style="
                    text-align:center;
                    padding-top:8px;
                ">
                    {current_page + 1}
                    / {total_pages}
                </div>
                """,
                unsafe_allow_html=True,
            )

        with next_col:

            if st.button(
                "次へ ▶",
                disabled=(
                    current_page
                    >= total_pages - 1
                ),
                use_container_width=True,
            ):

                st.session_state.backtest_page = (
                    current_page + 1
                )

                st.session_state.scroll_to_backtest = True

                st.rerun()


        # -------------------------------------------------
        # 自動スクロール
        # -------------------------------------------------

        if st.session_state.scroll_to_backtest:

            st.session_state.scroll_to_backtest = False

            st.components.v1.html(
                """
                <script>
                (function() {

                    function scrollToResults() {

                        try {

                            const parentDoc =
                                window.parent.document;

                            const target =
                                parentDoc.getElementById(
                                    "backtest-results-anchor"
                                );

                            if (target) {

                                target.scrollIntoView({
                                    behavior: "smooth",
                                    block: "start"
                                });

                                return true;
                            }

                        } catch (e) {}

                  
