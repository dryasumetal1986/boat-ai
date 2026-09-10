import streamlit as st

from datetime import datetime
from zoneinfo import ZoneInfo

import ai
import backtest
import data


st.set_page_config(
    page_title="やっちゃんの競艇AI予想PRO",
    page_icon="🚤",
    layout="centered",
)


st.title(
    "🚤 やっちゃんの競艇AI予想PRO"
)

st.caption(
    "AI予想 × 実オッズ × 期待値分析"
)


# =========================
# JST
# =========================

JST = ZoneInfo(
    "Asia/Tokyo"
)

today_jst = datetime.now(
    JST
).strftime(
    "%Y%m%d"
)


# =========================
# Session
# =========================

if "prediction" not in st.session_state:
    st.session_state.prediction = None

if "backtest_result" not in st.session_state:
    st.session_state.backtest_result = None

if "backtest_page" not in st.session_state:
    st.session_state.backtest_page = 0


# =========================
# 入力
# =========================

stadium_names = list(
    data.STADIUMS.values()
)

stadium_name = st.selectbox(
    "開催場",
    stadium_names,
)

stadium_number = next(
    number
    for number, name
    in data.STADIUMS.items()
    if name == stadium_name
)

race_number = st.selectbox(
    "レース",
    list(range(1, 13)),
    format_func=lambda x:
    f"{x}R",
)


# =========================
# AI予想
# =========================

if st.button(
    "🚀 AI予想開始",
    type="primary",
    use_container_width=True,
):

    with st.spinner(
        "レースデータを取得中..."
    ):

        raw = data.get_data(
            today_jst
        )

    if not raw:

        st.error(
            "本日のレースデータを取得できませんでした。"
        )

        st.info(
            "APIの更新前・対象外の日付・"
            "一時的な通信エラーの可能性があります。"
        )

    else:

        race = data.get_race(
            raw,
            stadium_number,
            race_number,
        )

        if not race:

            st.error(
                "この会場・レースのデータを取得できませんでした。"
            )

        else:

            racers = data.get_race_racers(
                race
            )

            if len(racers) < 6:

                st.error(
                    "6艇分の選手データを取得できませんでした。"
                )

            else:

                with st.spinner(
                    "公式3連単オッズを取得中..."
                ):

                    odds = (
                        data.get_trifecta_odds(
                            today_jst,
                            stadium_number,
                            race_number,
                        )
                    )

                prediction = ai.tri_ai(
                    racers,
                    odds=odds,
                )

                st.session_state.prediction = {
                    "date": today_jst,
                    "stadium": stadium_name,
                    "stadium_number": (
                        stadium_number
                    ),
                    "race_number": (
                        race_number
                    ),
                    "race": race,
                    "racers": racers,
                    "prediction": prediction,
                }


# =========================
# 予想結果
# =========================

saved = st.session_state.prediction


if saved:

    target_date = saved[
        "date"
    ]

    display_date = (
        f"{target_date[:4]}年"
        f"{target_date[4:6]}月"
        f"{target_date[6:8]}日"
    )

    st.subheader(
        f"{display_date} "
        f"{saved['stadium']} "
        f"{saved['race_number']}R"
    )

    prediction = saved[
        "prediction"
    ]

    racers = saved[
        "racers"
    ]

    st.write(
        f"🎯 本命 "
        f"**{prediction['main']}号艇**"
    )

    st.write(
        f"🔥 対抗 "
        f"**{prediction['counter']}号艇**"
    )

    st.write(
        f"💥 穴 "
        f"**{prediction['hole']}号艇**"
    )

    stars = round(
        prediction["confidence"]
        * 5
    )

    stars = max(
        1,
        min(5, stars),
    )

    st.write(
        "AI信頼度 "
        + "⭐" * stars
        + f" "
        f"（{prediction['confidence'] * 100:.1f}%）"
    )

    st.divider()

    # =====================
    # 期待値
    # =====================

    st.subheader(
        "💰 期待値の高い三連単"
    )

    if prediction[
        "odds_available"
    ]:

        st.caption(
            "公式BOATRACEの3連単実オッズを取得して計算"
        )

        shown = 0

        for item in prediction[
            "trifecta_candidates"
        ]:

            if item["odds"] is None:
                continue

            shown += 1

            combo = "-".join(
                str(x)
                for x in item[
                    "combination"
                ]
            )

            probability = (
                item["probability"]
                * 100
            )

            odd = item[
                "odds"
            ]

            ev = item[
                "ev_rate"
            ]

            market = (
                item[
                    "market_probability"
                ]
                * 100
                if item[
                    "market_probability"
                ]
                is not None
                else 0
            )

            edge = (
                item["edge"]
                * 100
                if item["edge"]
                is not None
                else 0
            )

            icon = (
                "🔥"
                if ev > 0
                else "📉"
            )

            st.write(
                f"{shown}. {icon} "
                f"**{combo}** "
                f"オッズ **{odd:.1f}倍** "
                f"AI確率 **{probability:.2f}%** "
                f"EV **{ev:+.1f}%**"
            )

            st.caption(
                f"市場確率 {market:.2f}%"
                f" / "
                f"AIとの差 {edge:+.2f}pt"
            )

            if shown >= 8:
                break

    else:

        st.warning(
            "公式3連単オッズを取得できませんでした。"
        )

    st.divider()

    # =====================
    # 6艇
    # =====================

    st.subheader(
        "🚤 6艇AI評価"
    )

    for number in prediction[
        "ranking"
    ]:

        racer = next(
            (
                x
                for x in racers
                if x["number"] == number
            ),
            None,
        )

        if racer is None:
            continue

        probability = (
            prediction[
                "probabilities"
            ].get(
                number,
                0.0,
            )
            * 100
        )

        score = prediction[
            "scores"
        ].get(
            number,
            0.0,
        )

        st.write(
            f"**{number}号艇 "
            f"{racer['name']}**"
        )

        st.write(
            f"1着AI確率 "
            f"**{probability:.1f}%** "
            f"AIスコア "
            f"**{score:.2f}**"
        )

    st.divider()

    # =====================
    # ランキング
    # =====================

    st.subheader(
        "📊 AI確率ランキング"
    )

    probability_ranking = sorted(
        prediction[
            "probabilities"
        ].items(),
        key=lambda x: x[1],
        reverse=True,
    )

    for index, (
        number,
        probability,
    ) in enumerate(
        probability_ranking,
        start=1,
    ):

        st.write(
            f"{index}. "
            f"{number}号艇 "
            f"**{probability * 100:.1f}%**"
        )


# =========================
# バックテスト
# =========================

st.divider()

st.subheader(
    "📊 AI予想バックテスト"
)

st.caption(
    "全国24場を対象に、"
    "2026年1月1日まで遡って検証"
)

count = st.selectbox(
    "検証レース数",
    [100, 300, 500, 1000],
    index=0,
)


if st.button(
    "🔍 バックテスト開始",
    use_container_width=True,
):

    st.session_state.backtest_result = None
    st.session_state.backtest_page = 0

    progress = st.progress(
        0
    )

    status = st.empty()

    try:

        result = backtest.run_backtest(
            today_jst,
            count,
            progress_callback=lambda value: (
                progress.progress(
                    min(
                        1.0,
                        max(
                            0.0,
                            value,
                        ),
                    )
                )
            ),
        )

        progress.empty()
        status.empty()

        st.session_state.backtest_result = (
            result
        )

    except Exception as e:

        progress.empty()

        st.error(
            "バックテスト中にエラーが発生しました。"
        )

        st.exception(e)


# =========================
# バックテスト結果
# =========================

result = (
    st.session_state.backtest_result
)


if result:

    st.write(
        f"**検証レース数："
        f"{result['total']}レース**"
    )

    col1, col2 = st.columns(
        2
    )

    with col1:

        st.metric(
            "回収率",
            f"{result['recovery']:.1f}%",
        )

        st.metric(
            "本命1着率",
            f"{result['main_win_rate']:.1f}%",
        )

        st.metric(
            "本命3連対率",
            f"{result['main_top3_rate']:.1f}%",
        )

    with col2:

        st.metric(
            "AI買い的中率",
            f"{result['buy_hit_rate']:.1f}%",
        )

        st.metric(
            "AI上位3艇全艇3連対率",
            f"{result['top3_all_top3_rate']:.1f}%",
        )

        st.metric(
            "3連単完全的中率",
            f"{result['trifecta_hit_rate']:.1f}%",
        )

    st.write(
        f"投資 "
        f"**{result['investment']:,}円**"
    )

    st.write(
        f"払戻 "
        f"**{result['payout']:,}円**"
    )

    st.divider()

    st.subheader(
        "📋 検証結果"
    )

    rows = result[
        "results"
    ]

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

    page = st.session_state.backtest_page

    page = max(
        0,
        min(
            page,
            total_pages - 1,
        ),
    )

    start = (
        page * per_page
    )

    end = (
        start + per_page
    )

    for item in rows[
        start:end
    ]:

        actual = "-".join(
            str(x)
            for x in item[
                "actual"
            ]
        )

        st.write(
            f"{item['date'][:4]}-"
            f"{item['date'][4:6]}-"
            f"{item['date'][6:8]} "
            f"{item['stadium']}"
            f"{item['race']}R "
            f"main{item['main']} "
            f"counter{item['counter']} "
            f"hole{item['hole']} "
            f"actual {actual}"
        )

    st.caption(
        f"{page + 1} / "
        f"{total_pages}ページ"
    )

    st.divider()

    col1, col2 = st.columns(
        2
    )

    with col1:

        if st.button(
            "◀ 前へ",
            disabled=page <= 0,
            use_container_width=True,
        ):

            st.session_state.backtest_page = (
                page - 1
            )

            st.rerun()

    with col2:

        if st.button(
            "次へ ▶",
            disabled=(
                page
                >= total_pages - 1
            ),
            use_container_width=True,
        ):

            st.session_state.backtest_page = (
                page + 1
            )

            st.rerun()
