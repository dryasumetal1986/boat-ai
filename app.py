import streamlit as st
import pandas as pd

from data import (
    STADIUM_NAMES,
    get_data,
    get_race,
    get_race_rows,
    history14,
    available_stadiums,
    available_races,
    jst_today,
)

from ai import tri_ai
from backtest import render_backtest


# =========================================================
# ページ設定
# =========================================================

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

.stApp {
    background: linear-gradient(
        180deg,
        #0b1020 0%,
        #080d18 100%
    );
    color: #ffffff;
}

.block-container {
    max-width: 1100px;
    padding-top: 1.5rem;
    padding-bottom: 4rem;
}

.app-title {
    font-size: 2.1rem;
    font-weight: 900;
    color: #ffffff;
    margin-bottom: 4px;
}

.app-subtitle {
    color: #aeb8c9;
    font-size: 0.95rem;
    margin-bottom: 24px;
}

.section-title {
    font-size: 1.25rem;
    font-weight: 900;
    color: #ffffff;
    margin-top: 18px;
    margin-bottom: 10px;
}

.race-header {
    background: #141d30;
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 18px;
    padding: 18px;
    margin: 12px 0 18px 0;
}

.race-date {
    color: #aeb8c9;
    font-size: 0.95rem;
}

.race-title {
    color: #ffffff;
    font-size: 1.55rem;
    font-weight: 900;
    margin-top: 5px;
}

.prediction-card {
    background: #141d30;
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 18px;
    padding: 18px;
    min-height: 145px;
    margin-bottom: 12px;
}

.pred-label {
    color: #aeb8c9;
    font-size: 0.95rem;
    font-weight: 800;
}

.pred-boat {
    color: #ffffff;
    font-size: 2rem;
    font-weight: 900;
    margin-top: 8px;
}

.pred-small {
    color: #8793a8;
    font-size: 0.8rem;
    margin-top: 4px;
}

.confidence-card {
    background: #141d30;
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 16px;
    padding: 15px;
    text-align: center;
    margin: 10px 0 20px 0;
}

.confidence-label {
    color: #aeb8c9;
    font-size: 0.9rem;
}

.confidence-stars {
    color: #ffffff;
    font-size: 1.55rem;
    font-weight: 900;
    letter-spacing: 3px;
    margin-top: 4px;
}

.boat-card {
    background: #172238;
    border: 1px solid rgba(255,255,255,0.11);
    border-radius: 16px;
    padding: 15px;
    min-height: 135px;
    margin-bottom: 12px;
}

.boat-number {
    color: #9eabc0;
    font-size: 0.85rem;
    font-weight: 800;
}

.boat-name {
    color: #ffffff;
    font-size: 1.05rem;
    font-weight: 900;
    margin-top: 7px;
    min-height: 30px;
}

.boat-mark {
    color: #ffffff;
    font-size: 0.85rem;
    font-weight: 900;
    margin-top: 10px;
    min-height: 22px;
}

.ranking-card {
    background: #141d30;
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 14px;
    padding: 13px 16px;
    margin-bottom: 8px;
}

.ranking-number {
    color: #ffffff;
    font-weight: 900;
}

.ranking-boat {
    color: #ffffff;
    font-weight: 800;
    margin-left: 10px;
}

.ranking-prob {
    color: #d6deeb;
    font-weight: 800;
    float: right;
}

</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# HTML表示
# =========================================================

def show_html(html_text):
    """
    Streamlit 1.49.1 の st.html を使用。
    HTMLタグが文字として表示されるのを防ぐ。
    """
    st.html(html_text)


# =========================================================
# セッション状態
# =========================================================

if "prediction_cache" not in st.session_state:
    st.session_state.prediction_cache = {}


# =========================================================
# タイトル
# =========================================================

show_html(
    """
<div class="app-title">🚤 やっちゃんの競艇AI予想PRO</div>
<div class="app-subtitle">AI × 展示 × 選手成績 × モーター解析</div>
"""
)


# =========================================================
# 日付
# =========================================================

try:
    target_date = jst_today()
except Exception:
    from datetime import date
    target_date = date.today()


# =========================================================
# APIデータ
# =========================================================

raw = get_data(target_date)

if raw is None:
    st.error("⚠️ 本日のレースデータを取得できませんでした。")
    st.info(
        "APIから本日のデータを取得できていません。"
        "少し時間を置いて再読み込みしてください。"
    )
    st.stop()


# =========================================================
# 開催場
# =========================================================

st.markdown(
    '<div class="section-title">📍 開催場</div>',
    unsafe_allow_html=True,
)

stadium_numbers = available_stadiums(raw)

if not stadium_numbers:
    st.warning("⚠️ 開催場データがありません。")
    st.stop()


stadium_options = []

for number in stadium_numbers:
    number = int(number)

    stadium_name = STADIUM_NAMES.get(
        number,
        f"{number}号場",
    )

    stadium_options.append(
        (number, stadium_name)
    )


stadium_names = [
    item[1]
    for item in stadium_options
]


selected_stadium_name = st.selectbox(
    "開催場を選択",
    stadium_names,
)


selected_stadium = next(
    number
    for number, name in stadium_options
    if name == selected_stadium_name
)


# =========================================================
# レース
# =========================================================

st.markdown(
    '<div class="section-title">🏁 レース</div>',
    unsafe_allow_html=True,
)

race_numbers = available_races(
    raw,
    selected_stadium,
)

if not race_numbers:
    st.warning(
        f"⚠️ {selected_stadium_name}のレースデータがありません。"
    )
    st.stop()


race_labels = [
    f"{int(number)}R"
    for number in race_numbers
]


selected_race_label = st.selectbox(
    "レースを選択",
    race_labels,
)


selected_race = int(
    selected_race_label.replace("R", "")
)


# =========================================================
# レースキー
# =========================================================

race_key = (
    f"{target_date.isoformat()}_"
    f"{selected_stadium}_"
    f"{selected_race}"
)


prediction = st.session_state.prediction_cache.get(
    race_key
)


# =========================================================
# AI予想
# =========================================================

st.markdown(
    '<div class="section-title">🤖 AI予想</div>',
    unsafe_allow_html=True,
)


# =========================================================
# 予想前
# =========================================================

if prediction is None:

    st.info(
        "👆 「AI予想開始」を押すと、"
        "展示・選手成績・モーターなどを解析します。"
    )

    if st.button(
        "🚀 AI予想開始",
        type="primary",
        use_container_width=True,
        key="ai_predict_button",
    ):

        race = get_race(
            raw,
            selected_stadium,
            selected_race,
        )

        if race is None:
            st.error(
                "⚠️ レースデータを取得できませんでした。"
            )
            st.stop()


        with st.spinner(
            "🤖 AIがレースを解析しています..."
        ):

            race_df = get_race_rows(
                race
            )

            if (
                race_df is None
                or race_df.empty
            ):
                st.error(
                    "⚠️ 出走艇データを取得できませんでした。"
                )
                st.stop()


            # -----------------------------------------
            # 過去データ
            # -----------------------------------------

            try:
                hist = history14(
                    selected_stadium,
                    selected_race,
                    target_date,
                )

            except TypeError:

                try:
                    hist = history14(
                        selected_stadium,
                        selected_race,
                    )

                except Exception:
                    hist = pd.DataFrame()

            except Exception:
                hist = pd.DataFrame()


            # -----------------------------------------
            # AI
            # -----------------------------------------

            prediction = tri_ai(
                race_df,
                hist,
                selected_stadium,
            )


            st.session_state.prediction_cache[
                race_key
            ] = prediction


        st.rerun()


# =========================================================
# 予想結果
# =========================================================

if prediction is not None:

    # -----------------------------------------------------
    # レース情報
    # -----------------------------------------------------

    show_html(
        f"""
<div class="race-header">
    <div class="race-date">
        🗓 {target_date.strftime("%Y-%m-%d")}
    </div>
    <div class="race-title">
        📍 {selected_stadium_name}　{selected_race}R
    </div>
</div>
"""
    )


    # -----------------------------------------------------
    # 本命・対抗・穴
    # -----------------------------------------------------

    main = int(
        prediction.get(
            "main",
            1,
        )
    )

    counter = int(
        prediction.get(
            "counter",
            2,
        )
    )

    hole = int(
        prediction.get(
            "hole",
            3,
        )
    )


    columns = st.columns(3)


    with columns[0]:

        show_html(
            f"""
<div class="prediction-card">
    <div class="pred-label">🎯 本命</div>
    <div class="pred-boat">{main}号艇</div>
    <div class="pred-small">AI最上位評価</div>
</div>
"""
        )


    with columns[1]:

        show_html(
            f"""
<div class="prediction-card">
    <div class="pred-label">🔥 対抗</div>
    <div class="pred-boat">{counter}号艇</div>
    <div class="pred-small">AI第2位評価</div>
</div>
"""
        )


    with columns[2]:

        show_html(
            f"""
<div class="prediction-card">
    <div class="pred-label">💥 穴</div>
    <div class="pred-boat">{hole}号艇</div>
    <div class="pred-small">AI穴候補</div>
</div>
"""
        )


    # -----------------------------------------------------
    # 自信度
    # -----------------------------------------------------

    confidence = float(
        prediction.get(
            "confidence",
            0.5,
        )
    )

    stars = int(
        prediction.get(
            "stars",
            3,
        )
    )

    stars = max(
        1,
        min(5, stars),
    )

    star_text = (
        "★" * stars
        + "☆" * (5 - stars)
    )

    confidence_percent = round(
        confidence * 100,
        1,
    )


    show_html(
        f"""
<div class="confidence-card">
    <div class="confidence-label">
        🤖 AI自信度　{confidence_percent}%
    </div>
    <div class="confidence-stars">
        {star_text}
    </div>
</div>
"""
    )


    # -----------------------------------------------------
    # 出走艇
    # -----------------------------------------------------

    st.markdown(
        '<div class="section-title">🚤 出走艇</div>',
        unsafe_allow_html=True,
    )


    race_df = prediction.get(
        "data"
    )


    if (
        race_df is None
        or not isinstance(
            race_df,
            pd.DataFrame,
        )
        or race_df.empty
    ):

        race = get_race(
            raw,
            selected_stadium,
            selected_race,
        )

        race_df = get_race_rows(
            race
        )


    for row_start in range(0, 6, 3):

        cols = st.columns(3)

        for index, col in enumerate(cols):

            boat_number = (
                row_start + index + 1
            )

            with col:

                if (
                    isinstance(
                        race_df,
                        pd.DataFrame,
                    )
                    and len(race_df) >= boat_number
                ):

                    try:
                        row = race_df.iloc[
                            boat_number - 1
                        ]

                        boat_name = str(
                            row.get(
                                "選手名",
                                f"{boat_number}号艇",
                            )
                        )

                    except Exception:

                        boat_name = (
                            f"{boat_number}号艇"
                        )

                else:

                    boat_name = (
                        f"{boat_number}号艇"
                    )


                marks = []

                if boat_number == main:
                    marks.append("🎯 本命")

                if boat_number == counter:
                    marks.append("🔥 対抗")

                if boat_number == hole:
                    marks.append("💥 穴")

                mark_text = " ".join(
                    marks
                )


                show_html(
                    f"""
<div class="boat-card">
    <div class="boat-number">
        {boat_number}号艇
    </div>
    <div class="boat-name">
        {boat_name}
    </div>
    <div class="boat-mark">
        {mark_text}
    </div>
</div>
"""
                )


    # -----------------------------------------------------
    # AI予測確率
    # -----------------------------------------------------

    st.markdown(
        '<div class="section-title">📊 AI予測確率</div>',
        unsafe_allow_html=True,
    )


    boat_probs = prediction.get(
        "boat_probs",
        {},
    )


    probability_data = []

    for boat in range(1, 7):

        probability = float(
            boat_probs.get(
                boat,
                0.0,
            )
        )

        probability_data.append(
            {
                "艇": f"{boat}号艇",
                "AI確率": probability,
            }
        )


    probability_df = pd.DataFrame(
        probability_data
    )


    st.bar_chart(
        probability_df.set_index("艇"),
        y="AI確率",
        height=330,
    )


    # -----------------------------------------------------
    # AIランキング
    # -----------------------------------------------------

    st.markdown(
        '<div class="section-title">🏆 AI総合ランキング</div>',
        unsafe_allow_html=True,
    )


    ranking = prediction.get(
        "ranking",
        [],
    )


    if not ranking:

        ranking = [
            1,
            2,
            3,
            4,
            5,
            6,
        ]


    for rank, boat in enumerate(
        ranking,
        start=1,
    ):

        boat = int(boat)

        probability = float(
            boat_probs.get(
                boat,
                0.0,
            )
        )


        show_html(
            f"""
<div class="ranking-card">
    <span class="ranking-number">
        {rank}位
    </span>
    <span class="ranking-boat">
        {boat}号艇
    </span>
    <span class="ranking-prob">
        {probability * 100:.1f}%
    </span>
</div>
"""
        )


    # -----------------------------------------------------
    # 予想データ
    # -----------------------------------------------------

    st.markdown(
        '<div class="section-title">📋 予想データ</div>',
        unsafe_allow_html=True,
    )


    if (
        isinstance(
            race_df,
            pd.DataFrame,
        )
        and not race_df.empty
    ):

        display_columns = [
            "枠",
            "選手名",
            "展示進入",
            "全国勝率",
            "全国2連率",
            "全国3連率",
            "当地勝率",
            "当地2連率",
            "モーター2連率",
            "平均ST",
            "展示ST",
            "展示タイム",
        ]


        available_columns = [
            column
            for column in display_columns
            if column in race_df.columns
        ]


        if available_columns:

            display_df = race_df[
                available_columns
            ].copy()


            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
            )


    # -----------------------------------------------------
    # バックテスト
    # -----------------------------------------------------

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    render_backtest()
