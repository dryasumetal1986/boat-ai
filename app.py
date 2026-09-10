import streamlit as st

import ai
import backtest
import data


st.set_page_config(
    page_title="やっちゃんの競艇AI予想PRO",
    page_icon="🚤",
    layout="centered",
)


st.title("🚤 やっちゃんの競艇AI予想PRO")
st.caption("AI予想 × 実オッズ × 期待値分析")


# =========================
# 入力
# =========================

stadium_name_to_number = {
    name: number
    for number, name in data.STADIUMS.items()
}

stadium_name = st.selectbox(
    "開催場",
    list(stadium_name_to_number.keys()),
)

stadium_number = stadium_name_to_number[
    stadium_name
]

race_number = st.selectbox(
    "レース",
    list(range(1, 13)),
    format_func=lambda x: f"{x}R",
)


if "prediction" not in st.session_state:
    st.session_state.prediction = None

if "prediction_date" not in st.session_state:
    st.session_state.prediction_date = None

if "backtest_result" not in st.session_state:
    st.session_state.backtest_result = None

if "backtest_page" not in st.session_state:
    st.session_state.backtest_page = 0


# =========================
# AI予想
# =========================

if st.button(
    "🚀 AI予想開始",
    type="primary",
    use_container_width=True,
):
    today = st.session_state.get(
        "prediction_date"
    )

    if today is None:
        from datetime import datetime

        today = datetime.now().strftime(
            "%Y%m%d"
        )

    raw = data.get_data(today)

    race = data.get_race(
        raw,
        stadium_number,
        race_number,
    )

    if not race:
        st.error(
            "このレースのデータを取得できませんでした。"
        )
        st.stop()

    racers = data.get_race_racers(race)

    if len(racers) < 6:
        st.error(
            "6艇分の選手データを取得できませんでした。"
        )
        st.stop()

    odds = data.get_trifecta_odds(
        today,
        stadium_number,
        race_number,
    )

    prediction = ai.tri_ai(
        racers,
        odds=odds,
    )

    st.session_state.prediction = {
        "race": race,
        "racers": racers,
        "prediction": prediction,
        "date": today,
    }

    st.session_state.prediction_date = today


# =========================
# 予想表示
# =========================

saved = st.session_state.prediction

if saved:
    race = saved["race"]
    racers = saved["racers"]
    prediction = saved["prediction"]
    target_date = saved["date"]

    display_date = (
        f"{target_date[:4]}年"
        f"{target_date[4:6]}月"
        f"{target_date[6:8]}日"
    )

    st.subheader(
        f"{display_date} "
        f"{stadium_name} "
        f"{race_number}R"
    )

    st.write(
        f"🎯 本命 **{prediction['main']}号艇**"
    )

    st.write(
        f"🔥 対抗 **{prediction['counter']}号艇**"
    )

    st.write(
        f"💥 穴 **{prediction['hole']}号艇**"
    )

    stars = round(
        prediction["confidence"] * 5
    )

    stars = max(1, min(5, stars))

    st.write(
        "AI信頼度 "
        + "⭐" * stars
        + f" "
        f"（{prediction['confidence'] * 100:.1f}%）"
    )

    st.divider()

    # =========================
    # 期待値
    # =========================

    st.subheader(
        "💰 期待値の高い三連単"
    )

    if prediction["odds_available"]:
        st.caption(
            "公式BOATRACEの3連単実オッズを取得して計算"
        )

        shown = 0

        for item in prediction[
            "trifecta_candidates"
        ]:
            if item["odds"] is None:
                continue

            combo = "-".join(
                str(x)
                for x in item["combination"]
            )

            probability = (
                item["probability"] * 100
            )

            odds_value = item["odds"]

            ev_rate = item["ev_rate"]

            market_probability = (
                item["market_probability"]
                * 100
            )

            edge = (
                item["edge"] * 100
            )

            shown += 1

            icon = "🔥" if ev_rate > 0 else "📉"

            st.write(
                f"{shown}. {icon} **{combo}** "
                f"オッズ **{odds_value:.1f}倍** "
                f"AI確率 **{probability:.2f}%** "
                f"EV **{ev_rate:+.1f}%**"
            )

            st.caption(
                f"市場確率 {market_probability:.2f}% "
                f"/ AIとの差 {edge:+.2f}pt"
            )

            if shown >= 8:
                break

    else:
        st.warning(
            "公式3連単オッズを取得できませんでした。"
        )

    st.divider()

    # =========================
    # 6艇評価
    # =========================

    st.subheader("🚤 6艇AI評価")

    ranking = prediction["ranking"]

    for number in ranking:
        racer = next(
            (
                r
                for r in racers
                if r["number"] == number
            ),
            None,
        )

        if not racer:
            continue

        probability = (
            prediction["probabilities"]
            .get(number, 0)
            * 100
        )

        score = prediction["scores"].get(
            number,
            0,
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

    # =========================
    # AI確率ランキング
    # =========================

    st.subheader(
        "📊 AI確率ランキング"
    )

    ranking_by_probability = sorted(
        prediction["probabilities"].items(),
        key=lambda x: x[1],
        reverse=True,
    )

    for index, (
        number,
        probability,
    ) in enumerate(
        ranking_by_probability,
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
    "全国24場を対象に、2026年1月1日まで遡って検証"
)

count = st.selectbox(
    "検証レース数",
    [100, 300, 500, 1000],
    index=0,
    key="backtest_count",
)


if st.button(
    "🔍 バックテスト開始",
    use_container_width=True,
):
    progress = st.progress(0)

    result = backtest.run_backtest(
        st.session_state.prediction_date
        or __import__("datetime")
        .datetime.now()
        .strftime("%Y%m%d"),
        count,
        progress_callback=lambda x: progress.progress(
            x
        ),
    )

    progress.empty()

    st.session_state.backtest_result = result
    st.session_state.backtest_page = 0


result = st.session_state.backtest_result


if result:
    st.write(
        f"**検証レース数："
        f"{result['total']}レース**"
    )

    col1, col2 = st.columns(2)

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
        f"投資 **{result['investment']:,}円**"
    )

    st.write(
        f"払戻 **{result['payout']:,}円**"
    )

    st.divider()

    st.subheader("📋 検証結果")

    per_page = 10

    results = result["results"]

    total_pages = max(
        1,
        (
            len(results)
            + per_page
            - 1
        )
        // per_page,
    )

    page = st.session_state.backtest_page

    page = max(
        0,
        min(page, total_pages - 1),
    )

    start = page * per_page
    end = start + per_page

    for item in results[start:end]:
        actual = "-".join(
            str(x)
            for x in item["actual"]
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
        f"{page + 1} / {total_pages}ページ"
    )

    st.divider()

    col1, col2 = st.columns(2)

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
            disabled=page >= total_pages - 1,
            use_container_width=True,
        ):
            st.session_state.backtest_page = (
                page + 1
            )

            st.rerun()

    # ページ移動後に検証結果へ戻す
    st.markdown(
        """
        <script>
        window.parent.postMessage(
          {
            type: "streamlit:setComponentValue",
            value: "scroll"
          },
          "*"
        );
        window.scrollTo({
          top: document.body.scrollHeight,
          behavior: "smooth"
        });
        </script>
        """,
        unsafe_allow_html=True,
    )
