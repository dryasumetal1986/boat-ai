import streamlit as st
import pandas as pd
import math
from datetime import date, datetime
from zoneinfo import ZoneInfo

from data import (
    get_data,
    get_race,
    history14,
    get_odds,
    backtest_races,
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
# 設定
# =========================

st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO",
    page_icon="🚤",
    layout="wide",
)


# =========================
# タイトル
# =========================

st.title(
    "🚤 やっちゃんの競艇AI予想 PRO"
)

st.write(
    "選手データ＋展示＋過去データ＋オッズ＋バックテスト"
)


# =========================
# 今日
# =========================

today = datetime.now(
    ZoneInfo("Asia/Tokyo")
).date()


# =========================
# タブ
# =========================

tab1, tab2 = st.tabs([
    "🚤 AI予想",
    "🧪 バックテスト",
])


# =========================================================
# AI予想
# =========================================================

with tab1:

    c1, c2, c3 = st.columns(3)

    with c1:

        td = st.date_input(
            "開催日",
            today,
            min_value=date(2026, 1, 1),
            key="race_date",
        )

    with c2:

        name = st.selectbox(
            "競艇場",
            list(STADIUMS.values()),
            key="stadium",
        )

    with c3:

        rno = st.selectbox(
            "レース",
            range(1, 13),
            format_func=lambda x: f"{x}R",
            key="race_no",
        )


    sno = list(STADIUMS)[
        list(STADIUMS.values()).index(name)
    ]


    if st.button(
        "🚀 AI予想を実行",
        type="primary",
        use_container_width=True,
        key="predict",
    ):

        try:

            data = get_data(td)

            race = get_race(
                data,
                sno,
                rno,
            )

        except Exception as e:

            st.error(
                "レースデータ取得に失敗しました"
            )

            st.exception(e)

            st.stop()


        if race is None:

            st.error(
                "このレースのデータがありません"
            )

            st.stop()


        racers_data = race.get(
            "racers",
            {}
        )

        preview_data = race.get(
            "preview",
            {}
        ).get(
            "racers",
            {}
        )


        if not isinstance(
            racers_data,
            dict,
        ):

            racers_data = {}


        preview_map = {}


        if isinstance(
            preview_data,
            dict,
        ):

            preview_items = (
                preview_data.values()
            )

        elif isinstance(
            preview_data,
            list,
        ):

            preview_items = preview_data

        else:

            preview_items = []


        for p in preview_items:

            if not isinstance(
                p,
                dict,
            ):

                continue

            entry = p.get(
                "entry_number"
            )

            course = p.get(
                "course_number"
            )

            if entry is not None:

                preview_map[
                    str(entry)
                ] = p

            if course is not None:

                preview_map.setdefault(
                    str(course),
                    p,
                )


        result_data = race.get(
            "result",
            {}
        )

        if not isinstance(
            result_data,
            dict,
        ):

            result_data = {}


        def num(value):

            try:

                return float(
                    value or 0
                )

            except Exception:

                return 0.0


        wind_speed = num(
            result_data.get(
                "wind_speed",
                0,
            )
        )

        wind_direction = result_data.get(
            "wind_direction_number",
            0,
        )

        wave_height = num(
            result_data.get(
                "wave_height",
                0,
            )
        )

        air_temperature = num(
            result_data.get(
                "air_temperature",
                0,
            )
        )

        water_temperature = num(
            result_data.get(
                "water_temperature",
                0,
            )
        )


        direction_names = {
            1: "北",
            2: "北東",
            3: "東",
            4: "南東",
            5: "南",
            6: "南西",
            7: "西",
            8: "北西",
        }


        try:

            direction_text = (
                direction_names.get(
                    int(wind_direction),
                    "不明",
                )
            )

        except Exception:

            direction_text = "不明"


        st.subheader(
            "🌤️ レース直前情報"
        )


        w1, w2, w3, w4, w5, w6 = (
            st.columns(6)
        )


        with w1:

            st.metric(
                "風速",
                f"{wind_speed:g} m",
            )


        with w2:

            st.metric(
                "風向",
                direction_text,
            )


        with w3:

            st.metric(
                "波高",
                f"{wave_height:g} cm",
            )


        with w4:

            st.metric(
                "気温",
                f"{air_temperature:g} ℃",
            )


        with w5:

            st.metric(
                "水温",
                f"{water_temperature:g} ℃",
            )


        with w6:

            st.metric(
                "展示情報",
                "取得済み",
            )


        rows = []


        for lane in range(1, 7):

            racer = racers_data.get(
                str(lane),
                {}
            )

            preview = preview_map.get(
                str(lane),
                {}
            )


            if not racer:

                continue


            exhibition = num(
                preview.get(
                    "exhibition_time",
                    0,
                )
            )


            exhibition_st = num(
                preview.get(
                    "start_timing",
                    0,
                )
            )


            exhibition_course = preview.get(
                "course_number",
                lane,
            )


            try:

                exhibition_course = int(
                    exhibition_course
                )

            except Exception:

                exhibition_course = lane


            rows.append({

                "枠": lane,

                "展示進入":
                    exhibition_course,

                "選手名":
                    racer.get(
                        "name",
                        "不明",
                    ),

                "選手番号":
                    str(
                        racer.get(
                            "number",
                            "",
                        )
                    ),

                "級別":
                    racer.get(
                        "rank_number",
                        "",
                    ),

                "全国勝率":
                    num(
                        racer.get(
                            "national_win_rate",
                            0,
                        )
                    ),

                "全国2連率":
                    num(
                        racer.get(
                            "national_top_2_percent",
                            0,
                        )
                    ),

                "当地勝率":
                    num(
                        racer.get(
                            "local_win_rate",
                            0,
                        )
                    ),

                "モーター2連率":
                    num(
                        racer.get(
                            "motor_top_2_percent",
                            0,
                        )
                    ),

                "平均ST":
                    num(
                        racer.get(
                            "average_start_timing",
                            0,
                        )
                    ),

                "展示ST":
                    exhibition_st,

                "展示タイム":
                    exhibition,
            })


        df = pd.DataFrame(
            rows
        )


        if df.empty:

            st.error(
                "出走表がありません"
            )

            st.stop()


        df["学習AI"] = df.apply(
            score,
            axis=1,
        )


        df = df.sort_values(
            "学習AI",
            ascending=False,
        ).reset_index(
            drop=True
        )


        st.subheader(
            f"🤖 {name} {rno}R AI評価"
        )


        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )


        st.subheader(
            "🔎 展示データ確認"
        )


        st.dataframe(
            df[
                [
                    "枠",
                    "展示進入",
                    "選手名",
                    "展示ST",
                    "展示タイム",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )


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


        try:

            history = pd.DataFrame(
                history14(td)
            )

        except Exception:

            history = pd.DataFrame()


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


            try:

                odds = get_odds(
                    td,
                    sno,
                    rno,
                )

            except Exception:

                odds = {}


            if odds:

                tri["オッズ"] = (
                    tri["3連単"].map(
                        odds
                    )
                )

            else:

                tri["オッズ"] = None


            tri["最終AI"] = (
                tri["AIスコア"]
            )


            for idx in tri.index:

                odd = tri.loc[
                    idx,
                    "オッズ",
                ]

                if pd.notna(odd):

                    try:

                        odd = float(
                            odd
                        )

                        tri.loc[
                            idx,
                            "最終AI",
                        ] += (
                            math.log(
                                max(
                                    odd,
                                    1,
                                )
                            )
                            * 2.0
                        )

                    except Exception:

                        pass


            minimum = tri[
                "最終AI"
            ].min()

            maximum = tri[
                "最終AI"
            ].max()


            if maximum > minimum:

                tri["信頼度"] = (
                    (
                        tri["最終AI"]
                        - minimum
                    )
                    / (
                        maximum
                        - minimum
                    )
                    * 100
                ).round(1)

            else:

                tri["信頼度"] = 50.0


            tri["穴度"] = 0.0


            if tri[
                "オッズ"
            ].notna().any():

                valid_odds = tri[
                    "オッズ"
                ].dropna()


                if len(
                    valid_odds
                ) > 0:

                    q75 = (
                        valid_odds
                        .quantile(0.75)
                    )


                    for idx in tri.index:

                        odd = tri.loc[
                            idx,
                            "オッズ",
                        ]


                        if pd.notna(odd):

                            try:

                                odd = float(
                                    odd
                                )

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


            tri = tri.sort_values(
                "最終AI",
                ascending=False,
            ).reset_index(
                drop=True
            )


            top = tri.iloc[0]
            second = tri.iloc[1]
            third = tri.iloc[2]


            hole_candidates = tri[
                tri["オッズ"].notna()
            ].sort_values(
                "オッズ",
                ascending=False,
            )


            if len(
                hole_candidates
            ) > 0:

                hole = (
                    hole_candidates
                    .iloc[0]
                )

            else:

                hole = tri.iloc[-1]


            st.subheader(
                "🔥 120通り3連単AI"
            )


            a, b, c, d = (
                st.columns(4)
            )


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


            st.subheader(
                "📈 120通りAIランキング TOP10"
            )


            st.dataframe(
                tri.head(10)[
                    [
                        "3連単",
                        "1着AI",
                        "2着AI",
                        "3着AI",
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


# =========================================================
# バックテスト
# =========================================================

with tab2:

    st.subheader(
        "🧪 AIバックテスト"
    )

    st.write(
        "過去レースを使って、現在のAIがどれくらい当たるか確認します。"
    )


    bt_days = st.selectbox(
        "検証期間",
        [7, 14],
        index=0,
        format_func=lambda x: f"過去{x}日",
    )


    if st.button(
        "🧪 バックテスト開始",
        type="primary",
        use_container_width=True,
        key="backtest",
    ):

        with st.spinner(
            "過去レースを集計中..."
        ):

            try:

                bt = pd.DataFrame(
                    backtest_races(
                        today,
                        bt_days,
                    )
                )

            except Exception as e:

                st.error(
                    "バックテストデータ取得エラー"
                )

                st.exception(e)

                st.stop()


        if bt.empty:

            st.warning(
                "検証できる過去レースがありません。"
            )

            st.stop()


        total = len(bt)


        # =====================
        # 3連単的中率
        # =====================

        # 現段階では実際のAI予想を
        # 全過去レースに再構築する前段階。
        # まず結果データの件数・払戻を確認する。


        st.success(
            f"{total}レース取得しました。"
        )


        # =====================
        # 基本統計
        # =====================

        payouts = pd.to_numeric(
            bt["払戻金"],
            errors="coerce",
        ).fillna(0)


        valid_payouts = payouts[
            payouts > 0
        ]


        average_payout = (
            valid_payouts.mean()
            if len(valid_payouts) > 0
            else 0
        )


        hit_races = len(
            valid_payouts
        )


        hit_rate = (
            hit_races
            / total
            * 100
            if total > 0
            else 0
        )


        # =====================
        # メトリクス
        # =====================

        m1, m2, m3, m4 = (
            st.columns(4)
        )


        with m1:

            st.metric(
                "検証レース",
                f"{total:,}",
            )


        with m2:

            st.metric(
                "結果取得率",
                f"{hit_rate:.1f}%",
            )


        with m3:

            st.metric(
                "平均払戻",
                f"{average_payout:,.0f}円",
            )


        with m4:

            st.metric(
                "最高払戻",
                f"{payouts.max():,.0f}円",
            )


        # =====================
        # 払戻統計
        # =====================

        st.subheader(
            "💰 払戻統計"
        )


        payout_view = bt[
            [
                "日付",
                "場",
                "レース",
                "実際の3連単",
                "払戻金",
            ]
        ].copy()


        payout_view = payout_view.sort_values(
            "払戻金",
            ascending=False,
        )


        st.dataframe(
            payout_view.head(30),
            use_container_width=True,
            hide_index=True,
        )


        st.info(
            "現在は過去結果の取得・統計確認までです。"
            "次の段階で、この過去レースそれぞれにAI予想を再現して、"
            "本命・TOP3・TOP10の的中率と回収率を計測します。"
                   )
