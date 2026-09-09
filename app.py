import html

import pandas as pd
import streamlit as st

from ai import tri_ai
from backtest import render_backtest
from data import (
    STADIUM_NAMES,
    available_races,
    available_stadiums,
    get_data,
    get_race,
    get_race_rows,
    jst_today,
    stadium_name,
)


st.set_page_config(
    page_title="やっちゃんの競艇AI予想PRO",
    page_icon="🚤",
    layout="wide",
)


# =========================
# CSS
# =========================

st.markdown(
    """
<style>
.block-container {
    max-width: 1100px;
    padding-top: 1.2rem;
    padding-bottom: 3rem;
}

.app-title {
    font-size: 2rem;
    font-weight: 800;
    margin-bottom: 0.2rem;
}

.app-subtitle {
    color: #777;
    margin-bottom: 1.5rem;
}

.race-header {
    border-radius: 16px;
    padding: 16px 20px;
    margin: 12px 0 18px 0;
    border: 1px solid rgba(128,128,128,.25);
}

.pick-card {
    border-radius: 16px;
    padding: 18px;
    margin-bottom: 12px;
    border: 1px solid rgba(128,128,128,.25);
}

.boat-card {
    border-radius: 14px;
    padding: 14px;
    margin-bottom: 10px;
    border: 1px solid rgba(128,128,128,.25);
}

.boat-number {
    font-size: 1.3rem;
    font-weight: 800;
}

.boat-name {
    font-size: 1.05rem;
    font-weight: 700;
    margin-top: 4px;
}

.boat-detail {
    font-size: .82rem;
    opacity: .75;
    margin-top: 6px;
}

.rank-card {
    border-radius: 12px;
    padding: 12px 16px;
    margin: 7px 0;
    border: 1px solid rgba(128,128,128,.25);
}

.ai-confidence {
    font-size: 1.2rem;
    font-weight: 800;
    margin: 12px 0;
}
</style>
""",
    unsafe_allow_html=True,
)


# =========================
# Helper
# =========================

def safe_name(value):
    return html.escape(
        str(value)
    )


def boat_name(df, boat):
    if df.empty:
        return f"{boat}号艇"

    rows = df[
        df["枠"].apply(
            lambda x: int(float(x))
        )
        == int(boat)
    ]

    if rows.empty:
        return f"{boat}号艇"

    return str(
        rows.iloc[0].get(
            "選手名",
            f"{boat}号艇",
        )
    )


def confidence_stars(stars):
    stars = max(
        1,
        min(5, int(stars)),
    )

    return (
        "★" * stars
        + "☆" * (5 - stars)
    )


# =========================
# Title
# =========================

st.markdown(
    '<div class="app-title">🚤 やっちゃんの競艇AI予想PRO</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="app-subtitle">BOAT RACE公式公開データ × AIスコアリング</div>',
    unsafe_allow_html=True,
)


# =========================
# Date data
# =========================

today = jst_today()

raw = get_data(today)

if raw is None:
    st.warning(
        "⚠️ 本日のレースデータを取得できませんでした"
    )

    st.info(
        "APIから本日のデータを取得できていません。"
        "少し時間を置いて再読み込みしてください。"
    )

    # バックテストは表示
    render_backtest()

    st.stop()


# =========================
# Selectors
# =========================

stadiums = available_stadiums(
    raw
)

if not stadiums:
    st.warning(
        "本日の開催場データがありません。"
    )

    render_backtest()

    st.stop()


stadium_labels = {
    number: (
        f"{number} {stadium_name(number)}"
    )
    for number in stadiums
}

selected_stadium = st.selectbox(
    "📍 開催場",
    stadiums,
    format_func=lambda x: stadium_labels[x],
    key="selected_stadium",
)


races = available_races(
    raw,
    selected_stadium,
)

if not races:
    st.warning(
        "この開催場のレースデータがありません。"
    )

    render_backtest()

    st.stop()


selected_race = st.selectbox(
    "🏁 レース",
    races,
    format_func=lambda x: f"{x}R",
    key="selected_race",
)


# =========================
# Prediction button
# =========================

if st.button(
    "🚀 AI予想開始",
    use_container_width=True,
    type="primary",
    key="prediction_start",
):
    st.session_state[
        "prediction_target"
    ] = (
        today.isoformat(),
        int(selected_stadium),
        int(selected_race),
    )

    st.session_state[
        "prediction_result"
    ] = None

    st.rerun()


# =========================
# Prediction state
# =========================

target = st.session_state.get(
    "prediction_target"
)

prediction = st.session_state.get(
    "prediction_result"
)


# =========================
# Actually calculate
# =========================

if (
    target is not None
    and prediction is None
):
    target_date_text, target_stadium, target_race = target

    race = get_race(
        raw,
        target_stadium,
        target_race,
    )

    if race is None:
        st.error(
            "レースデータを取得できませんでした。"
        )
    else:
        df = get_race_rows(
            race
        )

        if df.empty:
            st.error(
                "選手データを取得できませんでした。"
            )
        else:
            with st.spinner(
                "🤖 AIがデータを分析しています..."
            ):
                # 現在レースより前の履歴
                from data import history14

                history = history14(
                    target_stadium,
                    target_race,
                    today,
                )

                try:
                    prediction = tri_ai(
                        df,
                        history,
                        target_stadium,
                    )

                    st.session_state[
                        "prediction_result"
                    ] = prediction

                    st.rerun()

                except Exception as e:
                    st.error(
                        "AI予想中にエラーが発生しました。"
                    )

                    st.exception(e)


# =========================
# Prediction display
# =========================

if (
    target is not None
    and prediction is not None
):
    target_date_text, target_stadium, target_race = target

    race = get_race(
        raw,
        target_stadium,
        target_race,
    )

    if race is not None:
        df = get_race_rows(
            race
        )
    else:
        df = prediction.get(
            "data",
            pd.DataFrame(),
        )

    # ---------------------
    # Race header
    # ---------------------

    st.markdown(
        f'<div class="race-header">'
        f'<div>🗓 {html.escape(str(target_date_text))}</div>'
        f'<div style="font-size:1.45rem;font-weight:800;margin-top:5px;">'
        f'📍 {html.escape(stadium_name(target_stadium))} '
        f'{target_race}R'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ---------------------
    # Picks
    # ---------------------

    main = int(
        prediction["main"]
    )

    counter = int(
        prediction["counter"]
    )

    hole = int(
        prediction["hole"]
    )

    main_name = boat_name(
        df,
        main,
    )

    counter_name = boat_name(
        df,
        counter,
    )

    hole_name = boat_name(
        df,
        hole,
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            f'<div class="pick-card">'
            f'<div style="font-size:1.1rem;font-weight:800;">🎯 本命</div>'
            f'<div style="font-size:1.6rem;font-weight:900;">'
            f'{main}号艇'
            f'</div>'
            f'<div>{safe_name(main_name)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f'<div class="pick-card">'
            f'<div style="font-size:1.1rem;font-weight:800;">🔥 対抗</div>'
            f'<div style="font-size:1.6rem;font-weight:900;">'
            f'{counter}号艇'
            f'</div>'
            f'<div>{safe_name(counter_name)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f'<div class="pick-card">'
            f'<div style="font-size:1.1rem;font-weight:800;">💥 穴</div>'
            f'<div style="font-size:1.6rem;font-weight:900;">'
            f'{hole}号艇'
            f'</div>'
            f'<div>{safe_name(hole_name)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ---------------------
    # Confidence
    # ---------------------

    stars = int(
        prediction.get(
            "stars",
            3,
        )
    )

    confidence_percent = float(
        prediction.get(
            "confidence_percent",
            0,
        )
    )

    st.markdown(
        f'<div class="ai-confidence">'
        f'🤖 AI自信度 '
        f'{confidence_stars(stars)} '
        f'<span style="font-size:.9rem;font-weight:500;">'
        f'({confidence_percent:.1f}%)'
        f'</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ---------------------
    # Boat cards
    # ---------------------

    st.markdown(
        "### 🚤 出走6艇"
    )

    boat_probs = prediction.get(
        "boat_probs",
        {},
    )

    for boat in range(1, 7):
        name = boat_name(
            df,
            boat,
        )

        row = df[
            df["枠"].apply(
                lambda x: int(
                    float(x)
                )
            )
            == boat
        ]

        if row.empty:
            exhibition_time = "-"
            exhibition_st = "-"
            win_rate = "-"
        else:
            item = row.iloc[0]

            exhibition_time = item.get(
                "展示タイム",
                "-",
            )

            exhibition_st = item.get(
                "展示ST",
                "-",
            )

            win_rate = item.get(
                "全国勝率",
                "-",
            )

        try:
            prob = float(
                boat_probs.get(
                    boat,
                    0,
                )
            ) * 100
        except Exception:
            prob = 0.0

        st.markdown(
            f'<div class="boat-card">'
            f'<div class="boat-number">'
            f'{boat}号艇'
            f'</div>'
            f'<div class="boat-name">'
            f'{safe_name(name)}'
            f'</div>'
            f'<div class="boat-detail">'
            f'全国勝率 {html.escape(str(win_rate))}　'
            f'展示ST {html.escape(str(exhibition_st))}　'
            f'展示タイム {html.escape(str(exhibition_time))}'
            f'</div>'
            f'<div class="boat-detail">'
            f'AI確率 {prob:.1f}%'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ---------------------
    # Probability chart
    # ---------------------

    st.markdown(
        "### 📈 AI勝率予測"
    )

    chart_df = pd.DataFrame(
        {
            "艇": [
                f"{boat}号艇"
                for boat in range(1, 7)
            ],
            "AI確率": [
                float(
                    boat_probs.get(
                        boat,
                        0,
                    )
                )
                * 100
                for boat in range(1, 7)
            ],
        }
    )

    chart_df = chart_df.set_index(
        "艇"
    )

    st.bar_chart(
        chart_df,
        height=350,
    )

    # ---------------------
    # Ranking
    # ---------------------

    st.markdown(
        "### 🏆 AIランキング"
    )

    ranking_result = prediction.get(
        "ranking_result",
        [],
    )

    if ranking_result:
        for item in ranking_result:
            rank = item["順位"]
            boat = item["艇"]
            name = item["選手名"]
            score = item["スコア"]
            prob = item["確率"]

            st.markdown(
                f'<div class="rank-card">'
                f'<b>{rank}位　{boat}号艇 '
                f'{safe_name(name)}</b>'
                f'<br>'
                f'<span style="opacity:.75;">'
                f'AIスコア {score:.2f}　'
                f'予測確率 {prob:.1f}%'
                f'</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info(
            "ランキングデータがありません。"
        )

    # ---------------------
    # Prediction data
    # ---------------------

    with st.expander(
        "🔎 AI計算データを見る"
    ):
        display_df = prediction.get(
            "data",
            pd.DataFrame(),
        )

        if isinstance(
            display_df,
            pd.DataFrame,
        ) and not display_df.empty:
            columns = [
                "枠",
                "選手名",
                "展示進入",
                "全国勝率",
                "全国2連率",
                "全国3連率",
                "当地勝率",
                "当地2連率",
                "当地3連率",
                "モーター2連率",
                "平均ST",
                "展示ST",
                "展示タイム",
                "_AIスコア",
                "_確率",
            ]

            columns = [
                col
                for col in columns
                if col in display_df.columns
            ]

            st.dataframe(
                display_df[columns],
                use_container_width=True,
            )

    if st.button(
        "🔄 このレースをもう一度予想",
        key="redo_prediction",
        use_container_width=True,
    ):
        st.session_state[
            "prediction_result"
        ] = None

        st.rerun()


# =========================
# Backtest
# =========================

render_backtest()
