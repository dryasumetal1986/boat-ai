import streamlit as st
import pandas as pd
from datetime import date, datetime
from zoneinfo import ZoneInfo

from data import (
    get_data,
    get_race,
    history14,
    get_odds,
    odds_url,
)

from ai import score, tri_ai


# =========================
# 競艇場
# =========================

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


# =========================
# Streamlit設定
# =========================

st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO",
    page_icon="🚤",
    layout="wide",
)


# =========================
# タイトル
# =========================

st.title("🚤 やっちゃんの競艇AI予想 PRO")

st.write(
    "展示タイム＋選手データ＋過去14日データ＋3連単オッズで予想"
)


# =========================
# 今日
# =========================

today = datetime.now(
    ZoneInfo("Asia/Tokyo")
).date()


# =========================
# 入力
# =========================

c1, c2, c3 = st.columns(3)


with c1:
    td = st.date_input(
        "開催日",
        today,
        min_value=date(2026, 1, 1),
    )


with c2:
    name = st.selectbox(
        "競艇場",
        list(STADIUMS.values()),
    )


with c3:
    rno = st.selectbox(
        "レース",
        range(1, 13),
        format_func=lambda x: f"{x}R",
    )


sno = list(STADIUMS)[
    list(STADIUMS.values()).index(name)
]


# =========================
# AI実行
# =========================

if st.button(
    "🚀 AI予想を実行",
    type="primary",
    use_container_width=True,
):

    # -------------------------
    # レースデータ
    # -------------------------

    try:
        data = get_data(td)

        race = get_race(
            data,
            sno,
            rno,
        )

    except Exception as e:

        st.error("レースデータ取得に失敗しました")

        st.exception(e)

        st.stop()


    if race is None:

        st.error(
            "このレースのデータがありません"
        )

        st.stop()


    # -------------------------
    # 出走選手
    # -------------------------

    rows = []

    racers_data = race.get(
        "racers",
        {},
    )

    preview_data = race.get(
        "preview",
        {},
    ).get(
        "racers",
        {},
    )


    if not isinstance(
        racers_data,
        dict,
    ):
        racers_data = {}


    if not isinstance(
        preview_data,
        dict,
    ):
        preview_data = {}


    for lane in range(1, 7):

        racer = racers_data.get(
            str(lane),
            {},
        )

        preview = preview_data.get(
            str(lane),
            {},
        )


        if not racer:
            continue


        exhibition = preview.get(
            "exhibition_time",
            0,
        )


        try:
            exhibition = float(
                exhibition or 0
            )

        except Exception:
            exhibition = 0


        rows.append(
            {
                "枠": lane,

                "選手名": racer.get(
                    "name",
                    "不明",
                ),

                "選手番号": str(
                    racer.get(
                        "number",
                        "",
                    )
                ),

                "級別": racer.get(
                    "rank_number",
                    "",
                ),

                "全国勝率": float(
                    racer.get(
                        "national_win_rate",
                        0,
                    )
                    or 0
                ),

                "全国2連率": float(
                    racer.get(
                        "national_top_2_percent",
                        0,
                    )
                    or 0
                ),

                "当地勝率": float(
                    racer.get(
                        "local_win_rate",
                        0,
                    )
                    or 0
                ),

                "モーター2連率": float(
                    racer.get(
                        "motor_top_2_percent",
                        0,
                    )
                    or 0
                ),

                "平均ST": float(
                    racer.get(
                        "average_start_timing",
                        0,
                    )
                    or 0
                ),

                "展示タイム": exhibition,
            }
        )


    df = pd.DataFrame(rows)


    if df.empty:

        st.error(
            "出走表がありません"
        )

        st.stop()


    # =========================
    # 選手AI
    # =========================

    df["学習AI"] = df.apply(
        score,
        axis=1,
    )


    df = df.sort_values(
        "学習AI",
        ascending=False,
    ).reset_index(drop=True)


    st.subheader(
        f"🤖 {name} {rno}R AI評価"
    )


    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )


    # =========================
    # 選手ランキング
    # =========================

    st.subheader(
        "🏆 AI順位"
    )


    labels = [
        "🥇 本命",
        "🥈 対抗",
        "🥉 穴",
    ]


    for i, row in df.head(3).iterrows():

        st.write(
            f"{labels[i]} "
            f"{int(row['枠'])}号艇 "
            f"{row['選手名']} "
            f"AI {row['学習AI']}"
        )


    # =========================
    # 過去14日
    # =========================

    try:

        history = pd.DataFrame(
            history14(td)
        )

    except Exception as e:

        st.warning(
            "過去14日データの取得に失敗しました"
        )

        history = pd.DataFrame()


    # =========================
    # 3連単AI
    # =========================

    if len(df) >= 3:

        try:

            tri = tri_ai(
                df,
                history,
            )

        except Exception as e:

            st.error(
                "3連単AI計算でエラーが発生しました"
            )

            st.exception(e)

            st.stop()


        # -------------------------
        # オッズ取得
        # -------------------------

        try:

            odds = get_odds(
                td,
                sno,
                rno,
            )

        except Exception as e:

            st.warning(
                "3連単オッズを取得できませんでした"
            )

            odds = {}


        # -------------------------
        # オッズをAIランキングに追加
        # -------------------------

        if odds:

            tri["オッズ"] = tri["3連単"].map(
                odds
            )

        else:

            tri["オッズ"] = None


        # -------------------------
        # 最終AIスコア
        # -------------------------

        tri["最終AI"] = tri["AIスコア"]


        for idx in tri.index:

            odd = tri.loc[
                idx,
                "オッズ",
            ]

            if pd.notna(odd):

                try:

                    odd = float(odd)

                    # 人気過ぎる買い目だけに偏らないよう
                    # オッズを弱めに評価
                    import math

                    odds_bonus = (
                        math.log(max(odd, 1))
                        * 2.0
                    )

                    tri.loc[
                        idx,
                        "最終AI",
                    ] += odds_bonus

                except Exception:
                    pass


        # -------------------------
        # 信頼度
        # -------------------------

        min_score = tri["最終AI"].min()
        max_score = tri["最終AI"].max()


        if max_score > min_score:

            tri["信頼度"] = (
                (
                    tri["最終AI"]
                    - min_score
                )
                / (
                    max_score
                    - min_score
                )
                * 100
            ).round(1)

        else:

            tri["信頼度"] = 50.0


        # -------------------------
        # 穴度
        # -------------------------

        tri["穴度"] = 0.0


        if tri["オッズ"].notna().any():

            valid_odds = tri[
                "オッズ"
            ].dropna()


            if len(valid_odds) > 0:

                q75 = valid_odds.quantile(
                    0.75
                )


                for idx in tri.index:

                    odd = tri.loc[
                        idx,
                        "オッズ",
                    ]


                    if pd.notna(odd):

                        try:

                            odd = float(odd)

                            if q75 > 0:

                                hole = (
                                    odd
                                    / q75
                                    * 100
                                )

                                tri.loc[
                                    idx,
                                    "穴度",
                                ] = round(
                                    min(
                                        hole,
                                        100,
                                    ),
                                    1,
                                )

                        except Exception:
                            pass


        # -------------------------
        # 並び替え
        # -------------------------

        tri = tri.sort_values(
            "最終AI",
            ascending=False,
        ).reset_index(drop=True)


        # -------------------------
        # TOP
        # -------------------------

        top = tri.iloc[0]

        second = tri.iloc[1]

        third = tri.iloc[2]


        # 穴はオッズ上位から選択
        hole_candidates = tri[
            tri["オッズ"].notna()
        ].sort_values(
            "オッズ",
            ascending=False,
        )


        if len(hole_candidates) > 0:

            hole = hole_candidates.iloc[0]

        else:

            hole = tri.iloc[-1]


        # =========================
        # 3連単AI表示
        # =========================

        st.subheader(
            "🔥 120通り3連単AI"
        )


        a, b, c, d = st.columns(4)


        with a:

            st.metric(
                "🥇 AI本線",
                top["3連単"],
                f"信頼度 {top['信頼度']}%",
            )


        with b:

            st.metric(
                "🥈 AI対抗",
                second["3連単"],
                f"信頼度 {second['信頼度']}%",
            )


        with c:

            st.metric(
                "🎯 AI押さえ",
                third["3連単"],
                f"信頼度 {third['信頼度']}%",
            )


        with d:

            st.metric(
                "💥 AI穴",
                hole["3連単"],
                f"穴度 {hole['穴度']}%",
            )


        # =========================
        # TOP10
        # =========================

        st.subheader(
            "📈 120通りAIランキング TOP10"
        )


        top10 = tri.head(10).copy()


        st.dataframe(
            top10[
                [
                    "3連単",
                    "AIスコア",
                    "オッズ",
                    "最終AI",
                    "信頼度",
                    "穴度",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )


        # =========================
        # 上位4点
        # =========================

        st.subheader(
            "📊 上位4点"
        )


        st.write(
            f"🥇 本線：{top['3連単']} "
            f"（信頼度 {top['信頼度']}% / "
            f"オッズ {top['オッズ']}）"
        )


        st.write(
            f"🥈 対抗：{second['3連単']} "
            f"（信頼度 {second['信頼度']}% / "
            f"オッズ {second['オッズ']}）"
        )


        st.write(
            f"🎯 押さえ：{third['3連単']} "
            f"（信頼度 {third['信頼度']}% / "
            f"オッズ {third['オッズ']}）"
        )


        st.write(
            f"💥 穴：{hole['3連単']} "
            f"（穴度 {hole['穴度']}% / "
            f"オッズ {hole['オッズ']}）"
        )


        # =========================
        # オッズ取得先
        # =========================

        st.caption(
            "直前3連単オッズを取得してAI評価に反映しています。"
        )

else:

    st.info(
        "開催日・競艇場・レースを選んで"
        "「AI予想を実行」を押してください。"
                    )
