import html

import pandas as pd
import streamlit as st

import data
from ai import tri_ai
from backtest import render_backtest


st.set_page_config(
    page_title="やっちゃんの競艇AI予想PRO",
    page_icon="🚤",
    layout="centered",
)


st.markdown("""
<style>
.main-title{
    font-size:28px;
    font-weight:800;
    text-align:center;
    margin-bottom:4px;
}
.sub-title{
    text-align:center;
    color:#777;
    margin-bottom:20px;
}
.race-header{
    font-size:22px;
    font-weight:800;
    margin:12px 0;
}
.pick-card{
    padding:14px;
    border-radius:12px;
    margin:6px 0;
    border:1px solid #ddd;
}
.boat-card{
    padding:10px;
    border:1px solid #ddd;
    border-radius:10px;
    margin:5px 0;
}
.boat-number{
    font-size:22px;
    font-weight:800;
}
.boat-name{
    font-weight:700;
}
.small-text{
    font-size:13px;
    color:#777;
}
</style>
""", unsafe_allow_html=True)


st.markdown(
    '<div class="main-title">🚤 やっちゃんの競艇AI予想PRO</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="sub-title">AI予想 × 実オッズ × 期待値分析</div>',
    unsafe_allow_html=True
)


if "prediction_target" not in st.session_state:
    st.session_state["prediction_target"] = None

if "prediction" not in st.session_state:
    st.session_state["prediction"] = None


today = data.jst_today()
raw = data.get_data(today)

if raw is None:
    st.error("本日のレースデータを取得できませんでした。")
    render_backtest()
    st.stop()


stadiums = data.available_stadiums(raw)

if not stadiums:
    st.error("開催場を取得できませんでした。")
    render_backtest()
    st.stop()


stadium_options = {
    data.stadium_name(s): s
    for s in stadiums
}

selected_stadium_name = st.selectbox(
    "開催場",
    list(stadium_options.keys()),
)

selected_stadium = stadium_options[
    selected_stadium_name
]

race_numbers = data.available_races(
    raw,
    selected_stadium
)

if not race_numbers:
    st.error("レース情報がありません。")
    render_backtest()
    st.stop()


race_labels = [
    f"{r}R"
    for r in race_numbers
]

selected_race_label = st.selectbox(
    "レース",
    race_labels
)

selected_race = int(
    selected_race_label.replace("R", "")
)


if st.button(
    "🚀 AI予想開始",
    use_container_width=True
):
    race = data.get_race(
        raw,
        selected_stadium,
        selected_race
    )

    rows = data.get_race_rows(race)

    if rows.empty:
        st.error("出走表を取得できませんでした。")
        st.stop()

    with st.spinner("AI予想と実オッズを取得中..."):
        history = data.history14(
            selected_stadium,
            selected_race,
            race.get("date", today)
        )

        odds = data.get_trifecta_odds(
            race.get("date", today),
            selected_stadium,
            selected_race
        )

        prediction = tri_ai(
            rows,
            history,
            selected_stadium,
            odds=odds
        )

    st.session_state["prediction_target"] = (
        selected_stadium,
        selected_race
    )

    st.session_state["prediction"] = prediction

    st.rerun()


prediction = st.session_state.get(
    "prediction"
)

target = st.session_state.get(
    "prediction_target"
)


if prediction and target:
    stadium_number, race_number = target

    st.markdown(
        f'<div class="race-header">'
        f'{today:%Y年%m月%d日} '
        f'{data.stadium_name(stadium_number)} '
        f'{race_number}R'
        f'</div>',
        unsafe_allow_html=True
    )

    main = prediction["main"]
    counter = prediction["counter"]
    hole = prediction["hole"]

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            f'<div class="pick-card">🎯 本命<br>'
            f'<b>{main}号艇</b></div>',
            unsafe_allow_html=True
        )

    with c2:
        st.markdown(
            f'<div class="pick-card">🔥 対抗<br>'
            f'<b>{counter}号艇</b></div>',
            unsafe_allow_html=True
        )

    with c3:
        st.markdown(
            f'<div class="pick-card">💥 穴<br>'
            f'<b>{hole}号艇</b></div>',
            unsafe_allow_html=True
        )

    stars = "⭐" * prediction["stars"]

    st.write(
        f"AI信頼度 **{stars}** "
        f"（{prediction['confidence_percent']:.1f}%）"
    )


    # -----------------------------------------------------
    # 実オッズ × AI確率 = EV
    # -----------------------------------------------------

    st.divider()
    st.subheader("💰 期待値の高い三連単")

    candidates = prediction.get(
        "trifecta_candidates",
        []
    )

    if prediction.get("odds_available"):

        st.caption(
            "公式BOATRACEの3連単実オッズを取得して計算"
        )

        positive = [
            x for x in candidates
            if x["EV"] is not None
            and x["EV"] > 0
        ]

        show = (
            positive[:8]
            if positive
            else candidates[:8]
        )

        if not positive:
            st.info(
                "現在のオッズではプラス期待値の買い目はありません。"
                "AI確率が高い順に表示します。"
            )

        for i, x in enumerate(show, 1):
            ev = x["EV率"]
            odd = x["オッズ"]
            prob = x["AI確率"]

            if ev >= 20:
                mark = "🔥"
            elif ev >= 0:
                mark = "💡"
            else:
                mark = "⚠️"

            st.markdown(
                f"**{i}. {mark} {x['買い目']}**  "
                f"オッズ **{odd:.1f}倍**  "
                f"AI確率 **{prob:.2f}%**  "
                f"EV **{ev:+.1f}%**"
            )

    else:
        st.warning(
            "実オッズを取得できませんでした。"
            "AI予想は表示していますが、EVは未計算です。"
        )


    # -----------------------------------------------------
    # 6艇
    # -----------------------------------------------------

    st.divider()
    st.subheader("🚤 6艇AI評価")

    result_data = prediction["data"]

    for _, row in result_data.iterrows():
        boat = int(row["枠"])
        name = html.escape(
            str(row.get("選手名", f"{boat}号艇"))
        )

        prob = prediction["boat_probs"].get(
            boat,
            0
        ) * 100

        score = prediction["scores"].get(
            boat,
            0
        )

        st.markdown(
            f'<div class="boat-card">'
            f'<span class="boat-number">{boat}号艇</span> '
            f'<span class="boat-name">{name}</span><br>'
            f'<span class="small-text">'
            f'AI確率 {prob:.1f}%　'
            f'AIスコア {score:.2f}'
            f'</span>'
            f'</div>',
            unsafe_allow_html=True
        )


    # -----------------------------------------------------
    # 確率ランキング
    # -----------------------------------------------------

    st.divider()
    st.subheader("📊 AI確率ランキング")

    ranking_df = pd.DataFrame(
        prediction["ranking_result"]
    )

    if not ranking_df.empty:
        st.bar_chart(
            ranking_df.set_index("艇")["確率"]
        )

        st.dataframe(
            ranking_df,
            use_container_width=True,
            hide_index=True
        )


    with st.expander("🔎 詳細データ"):
        st.dataframe(
            prediction["data"],
            use_container_width=True,
            hide_index=True
        )

    if st.button(
        "🔄 予想をリセット",
        use_container_width=True
    ):
        st.session_state["prediction"] = None
        st.session_state["prediction_target"] = None
        st.rerun()


render_backtest()
