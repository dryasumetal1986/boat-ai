# app.py
# 🚤 やっちゃんの競艇AI予想PRO
# 完全版

from datetime import date

import pandas as pd
import streamlit as st

from data import (
    STADIUM_NAMES,
    get_data,
    get_race,
    get_race_rows,
    history14,
    available_stadiums,
    available_races,
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
    initial_sidebar_state="collapsed",
)


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
<style>

html, body, [class*="css"] {
    font-family: sans-serif;
}

/* タイトル */

.main-title {
    font-size: 30px;
    font-weight: 900;
    margin-bottom: 2px;
}

.sub-title {
    font-size: 14px;
    color: #777;
    margin-bottom: 18px;
}


/* レース情報 */

.race-header {
    background: linear-gradient(
        135deg,
        #111827,
        #1f2937
    );
    color: white;
    padding: 18px;
    border-radius: 16px;
    margin: 15px 0;
}

.race-date {
    font-size: 14px;
    opacity: 0.8;
}

.race-title {
    font-size: 25px;
    font-weight: 900;
}


/* 予想カード */

.pred-card {
    padding: 20px;
    border-radius: 16px;
    color: white;
    min-height: 135px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.15);
}

.pred-label {
    font-size: 15px;
    font-weight: 700;
}

.pred-boat {
    font-size: 32px;
    font-weight: 900;
    margin-top: 8px;
}


/* 本命 */

.main-card {
    background: linear-gradient(
        135deg,
        #dc2626,
        #991b1b
    );
}


/* 対抗 */

.counter-card {
    background: linear-gradient(
        135deg,
        #f59e0b,
        #b45309
    );
}


/* 穴 */

.hole-card {
    background: linear-gradient(
        135deg,
        #7c3aed,
        #4c1d95
    );
}


/* 出走艇 */

.boat-card {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 13px 15px;
    margin: 7px 0;
    border-radius: 12px;
    background: #1f2937;
    color: #ffffff;
    border: 1px solid #374151;
    box-shadow: 0 2px 7px rgba(0,0,0,0.18);
}

.boat-number {
    font-size: 20px;
    font-weight: 900;
    min-width: 45px;
}

.boat-name {
    font-size: 16px;
    font-weight: 700;
    flex: 1;
}

.boat-mark {
    font-size: 13px;
    font-weight: 800;
}


/* バックテスト */

.backtest-box {
    padding: 18px;
    border-radius: 16px;
    background: #111827;
    color: white;
    margin-top: 15px;
}

.metric-card {
    padding: 16px;
    border-radius: 14px;
    background: #f3f4f6;
    color: #111827;
    text-align: center;
}

.metric-title {
    font-size: 13px;
    color: #6b7280;
}

.metric-value {
    font-size: 25px;
    font-weight: 900;
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
    '<div class="sub-title">AI × 展示 × 選手成績 × モーター解析</div>',
    unsafe_allow_html=True,
)


# =========================================================
# 今日のデータ
# =========================================================

target_date = date.today()

with st.spinner("📡 本日のレースデータを取得中..."):
    raw = get_data(target_date)


if raw is None:

    st.error(
        "⚠️ 本日のレースデータを取得できませんでした。"
    )

    st.info(
        "APIに接続できない、または本日のデータがまだ公開されていない可能性があります。"
    )

    st.stop()


# =========================================================
# 開催場
# =========================================================

stadiums = available_stadiums(raw)

if not stadiums:

    st.error(
        "⚠️ 本日の開催場データがありません。"
    )

    st.stop()


st.subheader("📍 開催場")

stadium_number = st.selectbox(
    "開催場を選択",
    stadiums,
    format_func=lambda x: STADIUM_NAMES.get(
        x,
        f"{x}場"
    ),
)


# =========================================================
# レース
# =========================================================

races = available_races(
    raw,
    stadium_number,
)

if not races:

    st.warning(
        "⚠️ 選択した開催場にレースデータがありません。"
    )

    st.stop()


st.subheader("🏁 レース")

race_number = st.selectbox(
    "レースを選択",
    races,
    format_func=lambda x: f"{x}R",
)


# =========================================================
# レースヘッダー
# =========================================================

venue_name = STADIUM_NAMES.get(
    stadium_number,
    f"{stadium_number}場",
)

st.markdown(
    f"""
<div class="race-header">
    <div class="race-date">
        🗓 {target_date.strftime("%Y-%m-%d")}
    </div>
    <div class="race-title">
        📍 {venue_name}　{race_number}R
    </div>
</div>
""",
    unsafe_allow_html=True,
)


# =========================================================
# レース存在確認
# =========================================================

race = get_race(
    raw,
    stadium_number,
    race_number,
)

if race is None:

    st.error(
        "⚠️ このレースのデータを取得できませんでした。"
    )

    st.stop()


# =========================================================
# AI予想開始ボタン
# =========================================================

st.markdown(
    "### 🤖 AI予想"
)

predict_key = (
    f"predict_{target_date}_"
    f"{stadium_number}_"
    f"{race_number}"
)

if predict_key not in st.session_state:
    st.session_state[predict_key] = False


if st.button(
    "🚀 AI予想開始",
    type="primary",
    use_container_width=True,
):

    st.session_state[predict_key] = True


# =========================================================
# ボタンを押す前
# =========================================================

if not st.session_state[predict_key]:

    st.info(
        "👆 「AI予想開始」を押すと、展示・選手成績・モーターなどを解析します。"
    )

    st.divider()

    render_backtest()

    st.stop()


# =========================================================
# 選手データ
# =========================================================

rows = get_race_rows(
    race,
    stadium_number,
)

if len(rows) < 6:

    st.error(
        f"⚠️ 6艇分のデータを取得できませんでした。現在 {len(rows)}艇です。"
    )

    st.stop()


df = pd.DataFrame(rows)


# =========================================================
# 過去データ
# =========================================================

with st.spinner("📚 過去14日分のデータを解析中..."):

    hist = history14(
        stadium_number,
        race_number,
        target_date,
    )


# =========================================================
# AI
# =========================================================

with st.spinner("🤖 AIがレースを解析中..."):

    prediction = tri_ai(
        df,
        hist,
        stadium_number,
    )


# =========================================================
# AI予想表示
# =========================================================

main = prediction["main"]
counter = prediction["counter"]
hole = prediction["hole"]

confidence = prediction["confidence"]

star_count = int(
    round(
        confidence * 5
    )
)

star_count = max(
    1,
    min(
        5,
        star_count
    ),
)

stars = (
    "★" * star_count
    + "☆" * (5 - star_count)
)


col1, col2, col3 = st.columns(3)


with col1:

    st.markdown(
        f"""
<div class="pred-card main-card">
    <div class="pred-label">🎯 本命</div>
    <div class="pred-boat">{main}号艇</div>
</div>
""",
        unsafe_allow_html=True,
    )


with col2:

    st.markdown(
        f"""
<div class="pred-card counter-card">
    <div class="pred-label">🔥 対抗</div>
    <div class="pred-boat">{counter}号艇</div>
</div>
""",
        unsafe_allow_html=True,
    )


with col3:

    st.markdown(
        f"""
<div class="pred-card hole-card">
    <div class="pred-label">💥 穴</div>
    <div class="pred-boat">{hole}号艇</div>
</div>
""",
        unsafe_allow_html=True,
    )


st.markdown(
    f"### 🤖 AI自信度　{stars}"
)


# =========================================================
# 出走艇
# =========================================================

st.subheader("🚤 出走艇")


for _, row in df.iterrows():

    boat = int(row["枠"])
    name = str(row["選手名"])

    if boat == main:
        mark = "🎯 本命"

    elif boat == counter:
        mark = "🔥 対抗"

    elif boat == hole:
        mark = "💥 穴"

    else:
        mark = ""

    st.markdown(
        f"""
<div class="boat-card">
    <div class="boat-number">
        {boat}号艇
    </div>

    <div class="boat-name">
        {name}
    </div>

    <div class="boat-mark">
        {mark}
    </div>
</div>
""",
        unsafe_allow_html=True,
    )


# =========================================================
# AI予測確率
# =========================================================

st.subheader("📊 AI予測確率")

boat_probs = prediction.get(
    "boat_probs",
    {},
)

if boat_probs:

    probability_df = pd.DataFrame(
        [
            {
                "艇番": int(boat),
                "AI予測確率": round(
                    float(prob) * 100,
                    1,
                ),
            }
            for boat, prob in boat_probs.items()
        ]
    )

    probability_df = probability_df.sort_values(
        "艇番"
    )

    st.bar_chart(
        probability_df.set_index(
            "艇番"
        )
    )


# =========================================================
# AIランキング
# =========================================================

st.subheader("🏆 AI総合ランキング")

ranking = prediction.get(
    "ranking",
    [],
)

ranking_rows = []

for rank, boat in enumerate(
    ranking,
    start=1,
):

    probability = (
        boat_probs.get(
            boat,
            0,
        )
        * 100
    )

    ranking_rows.append(
        {
            "順位": rank,
            "艇番": f"{boat}号艇",
            "AI確率": f"{probability:.1f}%",
        }
    )

st.dataframe(
    pd.DataFrame(ranking_rows),
    use_container_width=True,
    hide_index=True,
)


# =========================================================
# バックテスト
# =========================================================

st.divider()

render_backtest()
