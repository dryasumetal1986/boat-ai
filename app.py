import streamlit as st
import pandas as pd
from datetime import date

import data

from ai import (
    score,
    tri_ai,
)


# =========================================================
# ページ設定
# =========================================================

st.set_page_config(
    page_title="競艇AI予想",
    page_icon="🚤",
    layout="wide",
)


# =========================================================
# 場コード
# =========================================================

STADIUMS = {
    1: "桐生",
    2: "戸田",
    3: "江戸川",
    4: "平和島",
    5: "多摩川",
    6: "浜名湖",
    7: "蒲郡",
    8: "常滑",
    9: "津",
    10: "三国",
    11: "びわこ",
    12: "住之江",
    13: "尼崎",
    14: "鳴門",
    15: "丸亀",
    16: "児島",
    17: "宮島",
    18: "徳山",
    19: "下関",
    20: "若松",
    21: "芦屋",
    22: "福岡",
    23: "唐津",
    24: "大村",
}


# =========================================================
# タイトル
# =========================================================

st.title("🚤 競艇AI予想")

st.caption(
    "過去データをRandomForestで学習して3連単を予測します"
)


# =========================================================
# 条件入力
# =========================================================

col1, col2, col3 = st.columns(3)

with col1:

    td = st.date_input(
        "開催日",
        value=date.today()
    )

with col2:

    stadium_name = st.selectbox(
        "競艇場",
        list(STADIUMS.values())
    )

    sno = next(
        k
        for k, v in STADIUMS.items()
        if v == stadium_name
    )

with col3:

    rno = st.selectbox(
        "レース",
        list(range(1, 13))
    )


# =========================================================
# AI予想ボタン
# =========================================================

if st.button(
    "🤖 AI予想を実行",
    type="primary",
    use_container_width=True
):

    # =====================================================
    # データ取得
    # =====================================================

    with st.spinner(
        "レースデータを取得しています..."
    ):

        try:

            all_data = data.get_data(
                td
            )

            race = data.get_race(
                all_data,
                sno,
                rno
            )

        except Exception as e:

            st.error(
                f"データ取得エラー: {e}"
            )

            st.stop()

    if race is None:

        st.error(
            "指定したレースのデータが見つかりません。"
        )

        st.stop()

    # =====================================================
    # 出走表
    # =====================================================

    race_racers = (
        race.get("racers")
        or race.get("entries")
        or []
    )

    if isinstance(
        race_racers,
        dict
    ):
        race_racers = list(
            race_racers.values()
        )

    # =====================================================
    # 展示データ
    # =====================================================

    preview = (
        race.get("preview")
        or []
    )

    if isinstance(
        preview,
        dict
    ):
        preview = list(
            preview.values()
        )

    preview_map = {}

    for p in preview:

        if not isinstance(
            p,
            dict
        ):
            continue

        number = (
            p.get("racerNumber")
            or p.get("playerNumber")
            or p.get("number")
        )

        try:
            number = int(
                float(number)
            )

        except Exception:
            continue

        preview_map[number] = p

    # =====================================================
    # 現在のレースをDataFrame化
    # =====================================================

    rows = []

    for idx, r in enumerate(
        race_racers
    ):

        if not isinstance(
            r,
            dict
        ):
            continue

        lane = (
            r.get("entryNumber")
            or r.get("boatNumber")
            or r.get("courseNumber")
            or idx + 1
        )

        try:
            lane = int(
                float(lane)
            )

        except Exception:
            lane = idx + 1

        number = (
            r.get("racerNumber")
            or r.get("playerNumber")
            or r.get("number")
        )

        try:
            number = int(
                float(number)
            )

        except Exception:
            number = 0

        p = preview_map.get(
            number,
            {}
        )

        # -----------------------------------------------
        # 値取得
        # -----------------------------------------------

        exhibition_course = (
            p.get("courseNumber")
            or p.get("entryNumber")
            or p.get("course")
            or lane
        )

        exhibition_st = (
            p.get("startTiming")
            or p.get("exhibitionST")
            or p.get("st")
            or 0
        )

        exhibition_time = (
            p.get("exhibitionTime")
            or p.get("time")
            or 0
        )

        nationwide_win = (
            r.get("nationwideWinRate")
            or r.get("nationalWinRate")
            or r.get("winRate")
            or 0
        )

        nationwide_2rate = (
            r.get("nationwide2Rate")
            or r.get("national2Rate")
            or r.get("secondRate")
            or 0
        )

        local_win = (
            r.get("localWinRate")
            or r.get("localRate")
            or 0
        )

        motor_2rate = (
            r.get("motor2Rate")
            or r.get("motorSecondRate")
            or 0
        )

        average_st = (
            r.get("averageST")
            or r.get("avgST")
            or r.get("averageStartTiming")
            or 0
        )

        name = (
            r.get("racerName")
            or r.get("name")
            or r.get("選手名")
            or "-"
        )

        grade = (
            r.get("class")
            or r.get("rank")
            or r.get("級別")
            or "-"
        )

        rows.append(
            {
                "枠": lane,
                "展示進入": exhibition_course,
                "選手名": name,
                "選手番号": number,
                "級別": grade,

                "全国勝率": nationwide_win,
                "全国2連率": nationwide_2rate,
                "当地勝率": local_win,
                "モーター2連率": motor_2rate,
                "平均ST": average_st,

                "展示ST": exhibition_st,
                "展示タイム": exhibition_time,

                "場": sno,
            }
        )

    df = pd.DataFrame(
        rows
    )

    if df.empty:

        st.error(
            "出走選手データが取得できませんでした。"
        )

        st.stop()

    # =====================================================
    # 数値列を数値化
    # =====================================================

    numeric_cols = [
        "枠",
        "展示進入",
        "選手番号",
        "全国勝率",
        "全国2連率",
        "当地勝率",
        "モーター2連率",
        "平均ST",
        "展示ST",
        "展示タイム",
        "場",
    ]

    for col in numeric_cols:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)

    # =====================================================
    # 学習AI
    # =====================================================

    df["学習AI"] = df.apply(
        score,
        axis=1
    )

    # =====================================================
    # 過去データ取得
    # =====================================================

    with st.spinner(
        "過去データを学習しています..."
    ):

        try:

            history = pd.DataFrame(
                data.history14(td)
            )

        except Exception as e:

            st.warning(
                f"過去データ取得に失敗したため、"
                f"簡易予測を使用します。\n{e}"
            )

            history = pd.DataFrame()

    # =====================================================
    # AI予測
    # =====================================================

    with st.spinner(
        "AIが3連単120通りを予測しています..."
    ):

        result = tri_ai(
            df,
            history
        )

    # =====================================================
    # 出走表
    # =====================================================

    st.subheader("🚤 出走表")

    display_df = df.sort_values(
        "学習AI",
        ascending=False
    ).copy()

    display_df["全国勝率"] = (
        display_df["全国勝率"]
        .round(2)
    )

    display_df["全国2連率"] = (
        display_df["全国2連率"]
        .round(2)
    )

    display_df["当地勝率"] = (
        display_df["当地勝率"]
        .round(2)
    )

    display_df["モーター2連率"] = (
        display_df["モーター2連率"]
        .round(2)
    )

    display_df["平均ST"] = (
        display_df["平均ST"]
        .round(3)
    )

    display_df["展示ST"] = (
        display_df["展示ST"]
        .round(3)
    )

    display_df["展示タイム"] = (
        display_df["展示タイム"]
        .round(2)
    )

    display_df["学習AI"] = (
        display_df["学習AI"]
        .round(2)
    )

    st.dataframe(
        display_df[
            [
                "枠",
                "展示進入",
                "選手名",
                "選手番号",
                "級別",
                "全国勝率",
                "全国2連率",
                "当地勝率",
                "モーター2連率",
                "平均ST",
                "展示ST",
                "展示タイム",
                "学習AI",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    # =====================================================
    # AI予想
    # =====================================================

    st.subheader(
        "🤖 AI 3連単予想"
    )

    if result.empty:

        st.error(
            "AI予測結果を作成できませんでした。"
        )

        st.stop()

    # =====================================================
    # 本命
    # =====================================================

    best = result.iloc[0]

    st.markdown(
        f"""
        ### 🥇 AI本命

        **{best["3連単"]}**

        AI確率：**{best["AI確率"]:.2f}%**

        信頼度：**{best["信頼度"]:.1f}%**
        """
    )

    # =====================================================
    # 2位・3位
    # =====================================================

    col1, col2, col3 = st.columns(3)

    for col, idx, title in [
        (col1, 0, "🥇 1位"),
        (col2, 1, "🥈 2位"),
        (col3, 2, "🥉 3位"),
    ]:

        if len(result) <= idx:
            continue

        row = result.iloc[idx]

        with col:

            st.metric(
                title,
                row["3連単"]
            )

            st.write(
                f"AI確率：**{row['AI確率']:.2f}%**"
            )

            st.write(
                f"信頼度：**{row['信頼度']:.1f}%**"
            )

    # =====================================================
    # 上位10
    # =====================================================

    st.subheader(
        "📊 AI予想ランキング"
    )

    st.dataframe(
        result.head(10),
        use_container_width=True,
        hide_index=True,
    )

    # =====================================================
    # 1着候補
    # =====================================================

    st.subheader(
        "🏆 各着順のAI評価"
    )

    place_df = df[
        [
            "枠",
            "選手名",
            "選手番号",
        ]
    ].copy()

    place_df = place_df.merge(
        result[
            [
                "1着",
                "1着AI",
                "2着AI",
                "3着AI",
            ]
        ].drop_duplicates(
            subset=["1着"]
        ),
        left_on="枠",
        right_on="1着",
        how="left",
    )

    # merge後の重複列を整理
    place_df = place_df.drop(
        columns=["1着"],
        errors="ignore"
    )

    st.dataframe(
        place_df,
        use_container_width=True,
        hide_index=True,
    )


# =========================================================
# 過去レース検証
# =========================================================

st.divider()

st.subheader(
    "📈 過去レース検証"
)

if st.button(
    "過去14日を確認",
    use_container_width=True
):

    with st.spinner(
        "過去レースを取得しています..."
    ):

        try:

            backtest = data.backtest_races(
                td,
                14
            )

        except Exception as e:

            st.error(
                f"取得エラー：{e}"
            )

            backtest = []

    if backtest:

        backtest_df = pd.DataFrame(
            backtest
        )

        st.dataframe(
            backtest_df,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "過去レースデータがありません。"
        )
