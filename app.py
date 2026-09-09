import html

import pandas as pd
import streamlit as st

import data
from ai import tri_ai
from backtest import render_backtest


st.set_page_config(
    page_title="やっちゃんの競艇AI予想PRO",
    page_icon="🚤",
    layout="wide",
)


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
    <style>
    .main-title {
        font-size: 34px;
        font-weight: 800;
        margin-bottom: 4px;
    }

    .sub-title {
        color: #888;
        margin-bottom: 20px;
    }

    .race-header {
        padding: 16px;
        border-radius: 14px;
        margin: 15px 0;
        background: rgba(120, 120, 120, 0.10);
        border: 1px solid rgba(120, 120, 120, 0.20);
    }

    .pick-card {
        padding: 14px;
        border-radius: 12px;
        margin-bottom: 8px;
        text-align: center;
        font-weight: 700;
        border: 1px solid rgba(120, 120, 120, 0.20);
    }

    .boat-card {
        padding: 12px;
        border-radius: 12px;
        margin-bottom: 8px;
        border: 1px solid rgba(120, 120, 120, 0.20);
    }

    .boat-number {
        font-size: 24px;
        font-weight: 800;
    }

    .boat-name {
        font-size: 16px;
        font-weight: 700;
    }

    .small-text {
        font-size: 13px;
        color: #888;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# タイトル
# =========================================================

st.markdown(
    '<div class="main-title">🚤 やっちゃんの競艇AI予想PRO</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="sub-title">全国24場対応・展示データ＋選手データ＋過去成績AI予想</div>',
    unsafe_allow_html=True,
)


# =========================================================
# セッション初期化
# =========================================================

if "prediction_target" not in st.session_state:
    st.session_state.prediction_target = None

if "prediction_result" not in st.session_state:
    st.session_state.prediction_result = None

if "prediction_race" not in st.session_state:
    st.session_state.prediction_race = None


# =========================================================
# 開催日
# =========================================================

today = data.jst_today()


# =========================================================
# 開催データ取得
# =========================================================

raw = data.get_data(today)


if not raw:
    st.error(
        "本日の競艇データを取得できませんでした。"
    )

    st.info(
        "時間を置いて再読み込みしてください。"
    )

    render_backtest()
    st.stop()


# =========================================================
# 場選択
# =========================================================

stadiums = data.available_stadiums(raw)


if not stadiums:
    st.error(
        "開催場データを取得できませんでした。"
    )

    render_backtest()
    st.stop()


stadium_options = [
    (
        stadium_number,
        data.stadium_name(stadium_number),
    )
    for stadium_number in stadiums
]


selected_stadium = st.selectbox(
    "🏟️ 開催場",
    stadium_options,
    format_func=lambda x: x[1],
    key="selected_stadium",
)


stadium_number = int(
    selected_stadium[0]
)

stadium_display_name = (
    data.stadium_name(stadium_number)
)


# =========================================================
# レース選択
# =========================================================

races = data.available_races(
    raw,
    stadium_number,
)


if not races:
    st.warning(
        f"{stadium_display_name}の開催レースがありません。"
    )

    render_backtest()
    st.stop()


race_options = [
    int(race_number)
    for race_number in races
]


selected_race = st.selectbox(
    "🏁 レース",
    race_options,
    format_func=lambda x: f"{x}R",
    key="selected_race",
)


race_number = int(
    selected_race
)


# =========================================================
# AI予想開始
# =========================================================

if st.button(
    "🚀 AI予想開始",
    use_container_width=True,
    key="start_prediction",
):

    race = data.get_race(
        raw,
        stadium_number,
        race_number,
    )

    if not race:
        st.error(
            "レースデータを取得できませんでした。"
        )

    else:
        rows = data.get_race_rows(race)

        if rows.empty:
            st.error(
                "選手データを取得できませんでした。"
            )

        else:
            with st.spinner(
                "🤖 AIが過去データと展示データを分析中..."
            ):

                history = data.history14(
                    stadium_number,
                    race_number,
                    today,
                )

                try:
                    prediction = tri_ai(
                        rows,
                        history,
                        stadium_number,
                    )

                    st.session_state.prediction_target = (
                        today,
                        stadium_number,
                        race_number,
                    )

                    st.session_state.prediction_result = (
                        prediction
                    )

                    st.session_state.prediction_race = (
                        race
                    )

                    st.rerun()

                except Exception as e:
                    st.error(
                        "AI予想の計算中にエラーが発生しました。"
                    )

                    st.exception(e)


# =========================================================
# 予想結果
# =========================================================

prediction_target = (
    st.session_state.prediction_target
)

prediction = (
    st.session_state.prediction_result
)

prediction_race = (
    st.session_state.prediction_race
)


if (
    prediction_target is not None
    and prediction is not None
    and prediction_race is not None
):

    (
        prediction_date,
        prediction_stadium,
        prediction_race_number,
    ) = prediction_target


    prediction_rows = prediction.get(
        "data",
        pd.DataFrame(),
    )


    # -----------------------------------------------------
    # レースヘッダー
    # -----------------------------------------------------

    safe_date = html.escape(
        str(prediction_date)
    )

    safe_stadium = html.escape(
        data.stadium_name(
            prediction_stadium
        )
    )

    header_html = (
        '<div class="race-header">'
        f'<div><b>{safe_date}</b></div>'
        f'<div style="font-size:24px; font-weight:800;">'
        f'{safe_stadium} {prediction_race_number}R'
        f'</div>'
        '</div>'
    )

    st.markdown(
        header_html,
        unsafe_allow_html=True,
    )


    # -----------------------------------------------------
    # 本命・対抗・穴
    # -----------------------------------------------------

    main = int(
        prediction.get("main", 1)
    )

    counter = int(
        prediction.get("counter", 2)
    )

    hole = int(
        prediction.get("hole", 3)
    )


    col1, col2, col3 = st.columns(3)


    with col1:

        st.markdown(
            f"""
            <div class="pick-card">
                🎯 本命<br>
                <span style="font-size:28px;">
                    {main}号艇
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )


    with col2:

        st.markdown(
            f"""
            <div class="pick-card">
                🔥 対抗<br>
                <span style="font-size:28px;">
                    {counter}号艇
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )


    with col3:

        st.markdown(
            f"""
            <div class="pick-card">
                💥 穴<br>
                <span style="font-size:28px;">
                    {hole}号艇
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )


    # -----------------------------------------------------
    # AI自信度
    # -----------------------------------------------------

    stars = int(
        prediction.get(
            "stars",
            3,
        )
    )

    stars = max(
        1,
        min(
            stars,
            5,
        ),
    )

    confidence_percent = float(
        prediction.get(
            "confidence_percent",
            0,
        )
    )


    st.markdown(
        f"### 🤖 AI自信度 {'★' * stars}{'☆' * (5 - stars)}"
    )

    if confidence_percent > 0:

        st.caption(
            f"AI信頼度 {confidence_percent:.1f}%"
        )


    # =====================================================
    # 6艇表示
    # =====================================================

    st.markdown(
        "### 🚤 出走選手"
    )


    display_rows = prediction_rows.copy()


    if not display_rows.empty:

        if "枠" in display_rows.columns:

            display_rows = display_rows.sort_values(
                "枠"
            )


        for _, row in display_rows.iterrows():

            try:
                boat_number = int(
                    row.get("枠", 0)
                )
            except Exception:
                continue


            if boat_number < 1 or boat_number > 6:
                continue


            player_name = str(
                row.get(
                    "選手名",
                    "選手情報なし",
                )
            )


            exhibition_time = row.get(
                "展示タイム",
                None,
            )

            exhibition_st = row.get(
                "展示ST",
                None,
            )

            exhibition_course = row.get(
                "展示進入",
                None,
            )

            score = prediction.get(
                "scores",
                {},
            ).get(
                boat_number,
                0,
            )

            probability = prediction.get(
                "boat_probs",
                {},
            ).get(
                boat_number,
                0,
            )


            if isinstance(
                probability,
                (int, float),
            ):
                probability_text = (
                    f"{float(probability) * 100:.1f}%"
                    if float(probability) <= 1
                    else f"{float(probability):.1f}%"
                )
            else:
                probability_text = "—"


            safe_name = html.escape(
                player_name
            )


            boat_html = (
                '<div class="boat-card">'
                f'<span class="boat-number">'
                f'{boat_number}号艇'
                f'</span>　'
                f'<span class="boat-name">'
                f'{safe_name}'
                f'</span>'
                '<br>'
                f'<span class="small-text">'
                f'展示進入: {exhibition_course}　'
                f'展示ST: {exhibition_st}　'
                f'展示タイム: {exhibition_time}'
                f'</span>'
                '<br>'
                f'<span class="small-text">'
                f'AIスコア: {float(score):.2f}　'
                f'予測確率: {probability_text}'
                f'</span>'
                '</div>'
            )


            st.markdown(
                boat_html,
                unsafe_allow_html=True,
            )


    # =====================================================
    # 確率グラフ
    # =====================================================

    st.markdown(
        "### 📊 AI予測確率"
    )


    boat_probs = prediction.get(
        "boat_probs",
        {},
    )


    if boat_probs:

        chart_data = pd.DataFrame(
            {
                "艇番": [
                    f"{int(k)}号艇"
                    for k in boat_probs.keys()
                ],
                "確率": [
                    float(v) * 100
                    if float(v) <= 1
                    else float(v)
                    for v in boat_probs.values()
                ],
            }
        )


        if not chart_data.empty:

            chart_data = chart_data.set_index(
                "艇番"
            )

            st.bar_chart(
                chart_data,
                use_container_width=True,
            )


    # =====================================================
    # AIランキング
    # =====================================================

    st.markdown(
        "### 🏆 AIランキング"
    )


    ranking = prediction.get(
        "ranking",
        [],
    )


    if ranking:

        for index, boat in enumerate(
            ranking,
            start=1,
        ):

            try:
                boat_number = int(boat)
            except Exception:
                continue


            medal = {
                1: "🥇",
                2: "🥈",
                3: "🥉",
            }.get(
                index,
                f"{index}位",
            )


            player_name = ""


            if not prediction_rows.empty:

                matched = prediction_rows[
                    prediction_rows["枠"]
                    == boat_number
                ]

                if not matched.empty:

                    player_name = str(
                        matched.iloc[0].get(
                            "選手名",
                            "",
                        )
                    )


            if player_name:

                st.write(
                    f"{medal} {boat_number}号艇 "
                    f"{player_name}"
                )

            else:

                st.write(
                    f"{medal} {boat_number}号艇"
                )


    # =====================================================
    # データ詳細
    # =====================================================

    with st.expander(
        "📋 AI分析に使用したデータを見る"
    ):

        if not prediction_rows.empty:

            st.dataframe(
                prediction_rows,
                use_container_width=True,
            )

        else:

            st.info(
                "表示できるデータがありません。"
            )


    # =====================================================
    # 別レースを再予想
    # =====================================================

    if st.button(
        "🔄 別のレースを予想する",
        use_container_width=True,
        key="reset_prediction",
    ):

        st.session_state.prediction_target = None
        st.session_state.prediction_result = None
        st.session_state.prediction_race = None

        st.rerun()


# =========================================================
# バックテスト
# =========================================================

render_backtest()
