import streamlit as st
from datetime import date, timedelta

from data import (
    STADIUMS,
    get_race,
    race_to_df,
    get_official_odds,
)

from ai import (
    predict,
    combo_text,
)

from backtest import (
    run_backtest,
)


st.set_page_config(
    page_title="やっちゃんの競艇AI予想PRO",
    page_icon="🚤",
    layout="wide",
)


st.title("🚤 やっちゃんの競艇AI予想PRO")
st.caption(
    "AI的中率重視 × 実データ × 3連単3点"
)


# =========================================================
# AI予想
# =========================================================

st.header("🎯 AI予想")

today = date.today()

target_date = st.date_input(
    "開催日",
    value=today,
    key="prediction_date",
)

stadium_names = [
    "選択してください"
] + list(STADIUMS.keys())

stadium = st.selectbox(
    "開催場",
    stadium_names,
    index=0,
    key="prediction_stadium",
)


race_options = [
    "選択してください"
]

if stadium != "選択してください":
    race_options += [
        str(i)
        for i in range(1, 13)
    ]

race_selected = st.selectbox(
    "レース",
    race_options,
    index=0,
    key="prediction_race",
)


if st.button(
    "🎯 AI予想を実行",
    use_container_width=True,
):
    if stadium == "選択してください":
        st.warning(
            "開催場を選択してください。"
        )

    elif race_selected == "選択してください":
        st.warning(
            "レースを選択してください。"
        )

    else:
        race_no = int(race_selected)

        race = get_race(
            target_date,
            stadium,
            race_no,
        )

        if not race:
            st.error(
                "レースデータを取得できませんでした。"
            )
        else:
            df = race_to_df(race)

            if df.empty or len(df) != 6:
                st.error(
                    "出走表データが正しく取得できませんでした。"
                )
            else:
                pred = predict(df)

                if not pred:
                    st.error(
                        "AI予想を作成できませんでした。"
                    )
                else:
                    st.success(
                        f"{target_date.strftime('%Y年%m月%d日')} "
                        f"{stadium} {race_no}R"
                    )

                    ranking = pred[
                        "ranking"
                    ]

                    axis = ranking[0]

                    st.subheader(
                        "🎯 AI最有力軸"
                    )

                    # ★必ず1～6号艇
                    st.markdown(
                        f"# {axis['boat']}号艇"
                    )

                    st.subheader(
                        "AI信頼度"
                    )

                    st.markdown(
                        f"# ⭐ {pred['confidence']:.1f}%"
                    )

                    st.subheader(
                        "🎯 AIが選んだ3連単3点"
                    )

                    odds = get_official_odds(
                        target_date,
                        stadium,
                        race_no,
                    )

                    for ticket in pred[
                        "tickets"
                    ]:
                        combo = tuple(
                            int(x)
                            for x in ticket[
                                "combo"
                            ]
                        )

                        combo_str = combo_text(
                            combo
                        )

                        official = odds.get(
                            combo
                        )

                        if official is None:
                            odds_text = (
                                "オッズ取得なし"
                            )
                        else:
                            odds_text = (
                                f"{official:.2f}倍"
                            )

                        st.markdown(
                            f"### "
                            f"{ticket['mark']}"
                            f"{ticket['label']}　"
                            f"**{combo_str}**"
                        )

                        st.write(
                            f"AI確率 "
                            f"{ticket['prob'] * 100:.2f}%"
                            f"　公式オッズ "
                            f"{odds_text}"
                        )

                    st.divider()

                    st.subheader(
                        "📊 6艇AI評価"
                    )

                    display_rows = []

                    for r in ranking:
                        display_rows.append({
                            "艇番": (
                                f"{r['boat']}号艇"
                            ),
                            "選手": r["name"],
                            "1着AI確率": (
                                f"{r['prob'] * 100:.1f}%"
                            ),
                            "AIスコア": (
                                f"{r['score']:.2f}"
                            ),
                        })

                    st.dataframe(
                        display_rows,
                        use_container_width=True,
                        hide_index=True,
                    )


# =========================================================
# バックテスト
# =========================================================

st.divider()

st.header("📈 バックテスト")

yesterday = today - timedelta(days=1)

backtest_date = st.date_input(
    "バックテスト日",
    value=yesterday,
    min_value=date(2026, 1, 1),
    max_value=yesterday,
    key="backtest_date",
)

count = st.selectbox(
    "検証レース数",
    [100, 200, 300, 500, 1000],
    index=0,
    key="backtest_count",
)

st.caption(
    "昨日を起点に、必要なレース数に達するまで"
    "過去へ自動的に遡ります。"
)

if st.button(
    "🚀 バックテスト開始",
    use_container_width=True,
):
    with st.spinner(
        "全24場の過去レースを解析しています..."
    ):
        result = run_backtest(
            backtest_date,
            count,
        )

    valid = result.get(
        "valid",
        0,
    )

    if valid == 0:
        st.error(
            "有効な結果データを取得できませんでした。"
        )

    else:
        stats = result["stats"]

        st.success(
            f"{valid}レースの検証が完了しました。"
        )

        st.subheader(
            "📊 バックテスト成績"
        )

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric(
                "3点合計的中率",
                f"{stats['total_hit_rate']:.1f}%",
            )

        with c2:
            st.metric(
                "本線的中率",
                f"{stats['main_hit_rate']:.1f}%",
            )

        with c3:
            st.metric(
                "対抗的中率",
                f"{stats['counter_hit_rate']:.1f}%",
            )

        c4, c5, c6 = st.columns(3)

        with c4:
            st.metric(
                "穴的中率",
                f"{stats['hole_hit_rate']:.1f}%",
            )

        with c5:
            st.metric(
                "AI軸1着率",
                f"{stats['axis_first_rate']:.1f}%",
            )

        with c6:
            st.metric(
                "AI軸3連対率",
                f"{stats['axis_top3_rate']:.1f}%",
            )

        c7, c8, c9 = st.columns(3)

        with c7:
            st.metric(
                "AI上位3艇BOX的中率",
                f"{stats['box_rate']:.1f}%",
            )

        with c8:
            st.metric(
                "投資",
                f"{stats['investment']:,}円",
            )

        with c9:
            st.metric(
                "払戻",
                f"{stats['payout']:,}円",
            )

        st.metric(
            "回収率",
            f"{stats['recovery']:.1f}%",
        )

        st.subheader(
            "🔎 レース別結果"
        )

        rows = result["rows"]

        if rows:
            st.dataframe(
                rows,
                use_container_width=True,
                hide_index=True,
            )
