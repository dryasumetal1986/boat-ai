# app.py
# 🚤 やっちゃんの競艇AI予想PRO

from datetime import date

import pandas as pd
import streamlit as st

from data import (
    get_data,
    get_race,
    get_race_rows,
    history14,
    available_stadiums,
    available_races,
    api_status,
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

.main-title {
    font-size: 32px;
    font-weight: 800;
    margin-bottom: 5px;
}

.sub-title {
    color: #777;
    margin-bottom: 20px;
}

.card {
    padding: 18px;
    border-radius: 15px;
    border: 1px solid #ddd;
    margin-bottom: 12px;
}

.main-card {
    border: 3px solid #ff4b4b;
}

.counter-card {
    border: 3px solid #ff9800;
}

.hole-card {
    border: 3px solid #8e44ad;
}

.big-number {
    font-size: 30px;
    font-weight: 800;
}

.small-text {
    color: #666;
    font-size: 13px;
}

.boat-row {
    padding: 10px;
    margin: 5px 0;
    border-radius: 10px;
    background: #f7f7f7;
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
# 日付
# =========================================================

target_date = date.today()


# =========================================================
# API取得
# =========================================================

with st.spinner("📡 本日のレースデータを取得中..."):

    raw = get_data(target_date)


# =========================================================
# API取得失敗
# =========================================================

if raw is None:

    st.error(
        "⚠️ 本日のレースデータを取得できませんでした"
    )

    st.write(
        "APIから本日のデータを取得できていません。"
    )

    st.write(
        "下のAPI状態を確認してください。"
    )

    status = api_status(target_date)

    st.json(status)

    st.stop()


# =========================================================
# 開催場取得
# =========================================================

stadiums = available_stadiums(raw)


if not stadiums:

    st.error(
        "⚠️ APIには接続できましたが、開催場データがありません。"
    )

    st.json(
        {
            "programs": list(
                raw.get("programs", {}).keys()
            )
        }
    )

    st.stop()


# =========================================================
# 開催場選択
# =========================================================

st.subheader("📍 開催場")

stadium_number = st.selectbox(
    "開催場",
    stadiums,
    format_func=lambda x: f"{x}号場",
)


# =========================================================
# レース選択
# =========================================================

races = available_races(
    raw,
    stadium_number,
)


if not races:

    st.warning(
        "⚠️ この開催場のレースデータがありません。"
    )

    st.stop()


race_number = st.selectbox(
    "レース",
    races,
    format_func=lambda x: f"{x}R",
)


# =========================================================
# レース取得
# =========================================================

race = get_race(
    raw,
    stadium_number,
    race_number,
)


if race is None:

    st.error(
        "⚠️ 選択したレースのデータを取得できませんでした。"
    )

    st.stop()


# =========================================================
# 選手データ
# =========================================================

rows = get_race_rows(
    race,
    stadium_number,
)


if len(rows) < 6:

    st.warning(
        f"⚠️ 選手データが6艇揃っていません。現在 {len(rows)}艇です。"
    )

    st.stop()


df = pd.DataFrame(rows)


# =========================================================
# レースヘッダー
# =========================================================

st.divider()

st.markdown(
    f"""
### 🏁 {target_date.strftime("%Y-%m-%d")}  
## 📍 {stadium_number}号場　{race_number}R
""",
)


# =========================================================
# AI解析
# =========================================================

with st.spinner("🤖 AIがレースを解析中..."):

    hist = history14(
        stadium_number,
        race_number,
        target_date,
    )

    prediction = tri_ai(
        df,
        hist,
        stadium_number,
    )


# =========================================================
# AI自信度
# =========================================================

confidence = prediction.get(
    "confidence",
    0.0,
)

stars = "★" * int(
    round(confidence * 5)
)

stars += "☆" * (
    5 - int(round(confidence * 5))
)


# =========================================================
# 本命・対抗・穴
# =========================================================

main = prediction["main"]
counter = prediction["counter"]
hole = prediction["hole"]


st.subheader("🎯 AI予想")


col1, col2, col3 = st.columns(3)


with col1:

    st.markdown(
        f"""
<div class="card main-card">
<div>🎯 本命</div>
<div class="big-number">{main}号艇</div>
</div>
""",
        unsafe_allow_html=True,
    )


with col2:

    st.markdown(
        f"""
<div class="card counter-card">
<div>🔥 対抗</div>
<div class="big-number">{counter}号艇</div>
</div>
""",
        unsafe_allow_html=True,
    )


with col3:

    st.markdown(
        f"""
<div class="card hole-card">
<div>💥 穴</div>
<div class="big-number">{hole}号艇</div>
</div>
""",
        unsafe_allow_html=True,
    )


st.markdown(
    f"### 🤖 AI自信度　{stars}"
)


# =========================================================
# 6艇表示
# =========================================================

st.subheader("🚤 出走艇")


for _, row in df.iterrows():

    boat = int(row["枠"])
    name = row["選手名"]

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
<div class="boat-row">
<b>{boat}号艇</b>　
{name}
　
{mark}
</div>
""",
        unsafe_allow_html=True,
    )


# =========================================================
# AI確率
# =========================================================

st.subheader("📊 AI予測確率")


boat_probs = prediction.get(
    "boat_probs",
    {},
)


if boat_probs:

    prob_df = pd.DataFrame(
        [
            {
                "艇番": int(k),
                "AI予測": round(float(v) * 100, 1),
            }
            for k, v in boat_probs.items()
        ]
    )

    prob_df = prob_df.sort_values(
        "AI予測",
        ascending=False,
    )

    st.bar_chart(
        prob_df.set_index("艇番")
    )


# =========================================================
# バックテスト
# =========================================================

st.divider()

render_backtest()
