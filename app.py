import streamlit as st
from datetime import datetime
import pandas as pd

from data import (
    STADIUMS,
    get_race,
    race_to_df,
    get_result,
    get_official_odds,
)
from ai import predict
from backtest import run_backtest


st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO",
    page_icon="🚤",
    layout="wide",
)

st.title("🚤 やっちゃんの競艇AI予想PRO")
st.caption("AI的中率重視 × 実データ × 3連単3点")


# ---------------------------------------------------------
# 入力
# ---------------------------------------------------------
today = datetime.now()

date = st.date_input(
    "開催日",
    value=today
)

stadium = st.selectbox(
    "開催場",
    list(STADIUMS.values()),
    index=list(STADIUMS.values()).index("大村")
)

race_no = st.number_input(
    "レース",
    min_value=1,
    max_value=12,
    value=7,
    step=1
)

date_str = date.strftime("%Y%m%d")


# ---------------------------------------------------------
# 予想
# ---------------------------------------------------------
if st.button("🎯 AI予想を実行", use_container_width=True):

    race = get_race(date_str, stadium, race_no)

    if not race:
        st.error(
            "レースデータを取得できませんでした。"
            "開催日・開催場・レース番号を確認してください。"
        )
        st.stop()

    df = race_to_df(race)

    if len(df) != 6:
        st.error("6艇分のデータを取得できませんでした。")
        st.stop()

    with st.spinner("AIが120通りの3連単を分析中..."):
        result = predict(df)

    tickets = result["tickets"]
    ranking = result["ranking"]

    st.success(
        f"{date.strftime('%Y年%m月%d日')} {stadium} {race_no}R"
    )

    # -----------------------------------------------------
    # AI軸
    # -----------------------------------------------------
    best = ranking[0]

    c1, c2 = st.columns(2)

    with c1:
        st.metric(
            "🎯 AI最有力軸",
            f"{best['boat']}号艇"
        )

    with c2:
        st.metric(
            "AI信頼度",
            f"⭐ {result['confidence']:.1f}%"
        )

    # -----------------------------------------------------
    # 3点
    # -----------------------------------------------------
    st.subheader("🎯 AIが選んだ3連単3点")

    labels = [
        ("◎ 本線", tickets["main"]),
        ("○ 対抗", tickets["counter"]),
        ("▲ 穴", tickets["hole"]),
    ]

    try:
        odds = get_official_odds(
            date_str,
            next(
                k for k, v in STADIUMS.items()
                if v == stadium
            ),
            race_no
        )
    except Exception:
        odds = {}

    for label, ticket in labels:
        combo = ticket["combo"]
        prob = ticket["prob"]
        odd = odds.get(combo)

        odd_text = (
            f"{odd:.1f}倍"
            if odd is not None
            else "オッズ取得なし"
        )

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

    # -----------------------------------------------------
    # 6艇評価
    # -----------------------------------------------------
    st.subheader("📊 6艇AI評価")

    rank_df = pd.DataFrame({
        "艇番": [x["boat"] for x in ranking],
        "選手": [x["name"] for x in ranking],
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
        use_container_width=True
    )

    # -----------------------------------------------------
    # 実際の3連単結果
    # -----------------------------------------------------
    actual = get_result(race)

    if actual:
        st.subheader("🏁 結果")

        st.write(
            f"**{actual[0]}-{actual[1]}-{actual[2]}**"
        )

        if actual == tuple(tickets["main"]["combo"]):
            st.success("◎ 本線的中！")
        elif actual == tuple(tickets["counter"]["combo"]):
            st.success("○ 対抗的中！")
        elif actual == tuple(tickets["hole"]["combo"]):
            st.success("▲ 穴的中！")
        else:
            st.info("3点の的中なし")


# ---------------------------------------------------------
# バックテスト
# ---------------------------------------------------------
st.divider()
st.header("📈 バックテスト")

bt_date = st.date_input(
    "バックテスト日",
    value=date,
    key="bt_date"
)

bt_count = st.number_input(
    "検証レース数",
    min_value=10,
    max_value=1000,
    value=100,
    step=10
)

bt_stadium = st.selectbox(
    "バックテスト開催場",
    list(STADIUMS.values()),
    index=list(STADIUMS.values()).index("びわこ"),
    key="bt_stadium"
)

if st.button(
    "🚀 バックテスト開始",
    use_container_width=True
):

    races = []

    # 同一開催場のレースを順番に取得
    for r in range(1, 13):
        races.append({
            "stadium": bt_stadium,
            "race_no": r,
        })

    # 100/300/500などを超える場合は複数日分
    # まずは指定日を中心に実行
    if bt_count > 12:
        st.info(
            "現在のバックテストは1開催場×1日を基本単位にしています。"
            "指定数を超える場合は取得できるレースまで検証します。"
        )

    races = races[:min(int(bt_count), 12)]

    progress = st.progress(0)

    result = run_backtest(
        bt_date.strftime("%Y%m%d"),
        races,
        progress_callback=progress.progress
    )

    progress.progress(1.0)

    stats = result["stats"]

    if not stats:
        st.error("バックテストできるデータがありません。")
        st.stop()

    # -----------------------------------------------------
    # 成績
    # -----------------------------------------------------
    st.subheader("📊 バックテスト成績")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "3点合計的中率",
        f"{stats['three_bet_hit_rate'] * 100:.1f}%"
    )

    c2.metric(
        "本線的中率",
        f"{stats['main_hit_rate'] * 100:.1f}%"
    )

    c3.metric(
        "対抗的中率",
        f"{stats['counter_hit_rate'] * 100:.1f}%"
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "穴的中率",
        f"{stats['hole_hit_rate'] * 100:.1f}%"
    )

    c2.metric(
        "AI軸1着率",
        f"{stats['first_hit_rate'] * 100:.1f}%"
    )

    c3.metric(
        "AI軸3連対率",
        f"{stats['top3_hit_rate'] * 100:.1f}%"
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "AI上位3艇BOX的中率",
        f"{stats['box_hit_rate'] * 100:.1f}%"
    )

    c2.metric(
        "投資",
        f"{stats['investment']:,}円"
    )

    c3.metric(
        "払戻",
        f"{stats['payout']:,}円"
    )

    st.metric(
        "回収率",
        f"{stats['return_rate'] * 100:.1f}%"
    )

    # -----------------------------------------------------
    # 各レース
    # -----------------------------------------------------
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
        False: "❌"
    })

    show = show[
        [
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
        use_container_width=True
        )
