import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from data import (
    STADIUMS,
    get_race,
    race_to_df,
    get_result,
    get_official_odds,
)
from ai import predict
from backtest import run_backtest


# =========================================================
# 設定
# =========================================================
st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO",
    page_icon="🚤",
    layout="wide",
)

st.title("🚤 やっちゃんの競艇AI予想PRO")
st.caption(
    "AI的中率重視 × 実データ × 3連単3点"
)


# =========================================================
# 通常予想
# =========================================================
st.header("🎯 AI予想")

today = datetime.now().date()

date = st.date_input(
    "開催日",
    value=today,
    key="prediction_date",
)

stadium_options = [
    "選択してください"
] + list(STADIUMS.values())

stadium = st.selectbox(
    "開催場",
    stadium_options,
    index=0,
    key="prediction_stadium",
)

race_options = [
    "選択してください"
] + list(range(1, 13))

race_no = st.selectbox(
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
        st.warning("開催場を選択してください。")
        st.stop()

    if race_no == "選択してください":
        st.warning("レースを選択してください。")
        st.stop()

    date_str = date.strftime("%Y%m%d")

    race = get_race(
        date_str,
        stadium,
        int(race_no),
    )

    if not race:
        st.error(
            "レースデータを取得できませんでした。"
        )
        st.stop()

    df = race_to_df(race)

    if len(df) != 6:
        st.error(
            "6艇分のデータを取得できませんでした。"
        )
        st.stop()

    with st.spinner(
        "AIが120通りの3連単を分析中..."
    ):
        prediction = predict(df)

    tickets = prediction["tickets"]
    ranking = prediction["ranking"]

    st.success(
        f"{date.strftime('%Y年%m月%d日')} "
        f"{stadium} {int(race_no)}R"
    )

    # =====================================================
    # AI軸
    # =====================================================
    best = ranking[0]

    c1, c2 = st.columns(2)

    with c1:
        st.metric(
            "🎯 AI最有力軸",
            f"{best['boat']}号艇",
        )

    with c2:
        st.metric(
            "AI信頼度",
            f"⭐ {prediction['confidence']:.1f}%",
        )

    # =====================================================
    # 3連単3点
    # =====================================================
    st.subheader(
        "🎯 AIが選んだ3連単3点"
    )

    jcd = next(
        code
        for code, name in STADIUMS.items()
        if name == stadium
    )

    odds = get_official_odds(
        date_str,
        jcd,
        int(race_no),
    )

    ticket_list = [
        ("◎ 本線", tickets["main"]),
        ("○ 対抗", tickets["counter"]),
        ("▲ 穴", tickets["hole"]),
    ]

    for label, ticket in ticket_list:

        combo = ticket["combo"]
        prob = ticket["prob"]

        odd = odds.get(combo)

        if odd is None:
            odd_text = "オッズ取得なし"
        else:
            odd_text = f"{odd:.1f}倍"

        st.markdown(
            f"### {label}　"
            f"**{combo[0]}-{combo[1]}-{combo[2]}**"
        )

        st.write(
            f"AI確率 **{prob * 100:.2f}%**　"
            f"公式オッズ **{odd_text}**"
        )

    st.caption(
        f"公式オッズ {len(odds)}/120通り取得"
    )

    # =====================================================
    # 6艇評価
    # =====================================================
    st.subheader("📊 6艇AI評価")

    rank_df = pd.DataFrame({
        "順位": range(1, 7),

        "艇番": [
            x["boat"]
            for x in ranking
        ],

        "選手": [
            x["name"]
            for x in ranking
        ],

        "1着AI確率": [
            f"{x['prob'] * 100:.1f}%"
            for x in ranking
        ],

        "AIスコア": [
            f"{x['score']:.2f}"
            for x in ranking
        ],
    })

    st.dataframe(
        rank_df,
        hide_index=True,
        use_container_width=True,
    )

    # =====================================================
    # 結果
    # =====================================================
    actual = get_result(race)

    if actual:

        st.subheader("🏁 結果")

        st.write(
            f"**{actual[0]}-{actual[1]}-{actual[2]}**"
        )

        actual = tuple(actual)

        if actual == tuple(
            tickets["main"]["combo"]
        ):
            st.success(
                "🎯 ◎ 本線的中！"
            )

        elif actual == tuple(
            tickets["counter"]["combo"]
        ):
            st.success(
                "🎯 ○ 対抗的中！"
            )

        elif actual == tuple(
            tickets["hole"]["combo"]
        ):
            st.success(
                "💥 ▲ 穴的中！"
            )

        else:
            st.info(
                "今回は3点の的中なし"
            )


# =========================================================
# バックテスト
# =========================================================
st.divider()

st.header("📈 バックテスト")

yesterday = today - timedelta(days=1)

bt_date = st.date_input(
    "バックテスト日",
    value=yesterday,
    max_value=yesterday,
    key="backtest_date",
)

count_options = list(
    range(100, 1001, 100)
)

bt_count = st.selectbox(
    "検証レース数",
    count_options,
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

    start_date = bt_date.strftime(
        "%Y%m%d"
    )

    progress = st.progress(0)

    status = st.empty()

    status.info(
        f"{bt_count}レースを集計しています..."
    )

    result = run_backtest(
        start_date,
        int(bt_count),
        progress_callback=progress.progress,
    )

    progress.progress(1.0)

    stats = result["stats"]

    if not stats:
        status.error(
            "検証できる過去レースがありませんでした。"
        )
        st.stop()

    status.success(
        f"{stats['races']}レースの検証が完了しました。"
    )

    # =====================================================
    # 成績
    # =====================================================
    st.subheader("📊 バックテスト成績")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "3点合計的中率",
        f"{stats['three_bet_hit_rate'] * 100:.1f}%",
    )

    c2.metric(
        "本線的中率",
        f"{stats['main_hit_rate'] * 100:.1f}%",
    )

    c3.metric(
        "対抗的中率",
        f"{stats['counter_hit_rate'] * 100:.1f}%",
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "穴的中率",
        f"{stats['hole_hit_rate'] * 100:.1f}%",
    )

    c2.metric(
        "AI軸1着率",
        f"{stats['first_hit_rate'] * 100:.1f}%",
    )

    c3.metric(
        "AI軸3連対率",
        f"{stats['top3_hit_rate'] * 100:.1f}%",
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "AI上位3艇BOX的中率",
        f"{stats['box_hit_rate'] * 100:.1f}%",
    )

    c2.metric(
        "投資",
        f"{stats['investment']:,}円",
    )

    c3.metric(
        "払戻",
        f"{stats['payout']:,}円",
    )

    st.metric(
        "回収率",
        f"{stats['return_rate'] * 100:.1f}%",
    )

    # =====================================================
    # レース別
    # =====================================================
    records = result["records"]

    st.subheader("🔎 レース別結果")

    show = records.copy()

    show["本線"] = show["main"].apply(
        lambda x: "-".join(map(str, x))
    )

    show["対抗"] = show["counter"].apply(
        lambda x: "-".join(map(str, x))
    )

    show["穴"] = show["hole"].apply(
        lambda x: "-".join(map(str, x))
    )

    show["結果"] = show["result"].apply(
        lambda x: "-".join(map(str, x))
    )

    show["判定"] = show["hit3"].map({
        True: "🎯 的中",
        False: "❌",
    })

    show = show[
        [
            "date",
            "stadium",
            "race_no",
            "本線",
            "対抗",
            "穴",
            "結果",
            "判定",
            "payout",
        ]
    ]

    show.columns = [
        "日付",
        "開催場",
        "R",
        "本線",
        "対抗",
        "穴",
        "結果",
        "判定",
        "払戻",
    ]

    st.dataframe(
        show,
        hide_index=True,
        use_container_width=True,
    )
