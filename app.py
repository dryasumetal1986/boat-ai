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
    "選手データ＋展示タイム＋展示ST＋展示進入＋天候＋過去14日＋3連単オッズ"
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

    # =========================
    # レース取得
    # =========================

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


    # =========================
    # 出走データ
    # =========================

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


    # =========================
    # 展示データを枠番号へ変換
    # =========================

    preview_map = {}

    if isinstance(
        preview_data,
        dict,
    ):

        preview_items = preview_data.values()

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


    # =========================
    # 天候
    # =========================

    result_data = race.get(
        "result",
        {}
    )

    if not isinstance(
        result_data,
        dict,
    ):

        result_data = {}


    wind_speed = result_data.get(
        "wind_speed",
        0,
    )

    wind_direction = result_data.get(
        "wind_direction_number",
        0,
    )

    wave_height = result_data.get(
        "wave_height",
        0,
    )

    air_temperature = result_data.get(
        "air_temperature",
        0,
    )

    water_temperature = result_data.get(
        "water_temperature",
        0,
    )


    # =========================
    # 数値変換
    # =========================

    def num(value):

        try:

            return float(
                value or 0
            )

        except Exception:

            return 0.0


    wind_speed = num(
        wind_speed
    )

    wave_height = num(
        wave_height
    )

    air_temperature = num(
        air_temperature
    )

    water_temperature = num(
        water_temperature
    )


    # =========================
    # 天候表示
    # =========================

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

        direction_text = direction_names.get(
            int(wind_direction),
            "不明",
        )

    except Exception:

        direction_text = "不明"


    # =========================
    # 天候表示
    # =========================

    st.subheader(
        "🌤️ レース直前情報"
    )

    w1, w2, w3, w4, w5, w6 = st.columns(6)

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


    # =========================
    # 選手データ
    # =========================

    rows = []


    for lane in range(1, 7):

        racer = racers_data.get(
            str(lane),
            {},
        )

        preview = preview_map.get(
            str(lane),
            {},
        )


        if not racer:

            continue


        # -------------------------
        # 展示タイム
        # -------------------------

        exhibition = num(
            preview.get(
                "exhibition_time",
                0,
            )
        )


        # -------------------------
        # 展示ST
        # -------------------------

        exhibition_st = num(
            preview.get(
                "start_timing",
                0,
            )
        )


        # -------------------------
        # 展示進入
        # -------------------------

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


        # -------------------------
        # 選手情報
        # -------------------------

        rows.append({

            "枠": lane,

            "展示進入": exhibition_course,

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

            "全国勝率": num(
                racer.get(
                    "national_win_rate",
                    0,
                )
            ),

            "全国2連率": num(
                racer.get(
                    "national_top_2_percent",
                    0,
                )
            ),

            "当地勝率": num(
                racer.get(
                    "local_win_rate",
                    0,
                )
            ),

            "モーター2連率": num(
                racer.get(
                    "motor_top_2_percent",
                    0,
                )
            ),

            "平均ST": num(
                racer.get(
                    "average_start_timing",
                    0,
                )
            ),

            "展示ST": exhibition_st,

            "展示タイム": exhibition,
        })


    df = pd.DataFrame(
        rows
    )


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
    ).reset_index(
        drop=True
    )


    # =========================
    # 出走表
    # =========================

    st.subheader(
        f"🤖 {name} {rno}R AI評価"
    )


    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )


    # =========================
    # 展示確認
    # =========================

    st.subheader(
        "🔎 展示データ確認"
    )


    exhibition_view = df[
        [
            "枠",
            "展示進入",
            "選手名",
            "展示ST",
            "展示タイム",
        ]
    ].copy()


    st.dataframe(
        exhibition_view,
        use_container_width=True,
        hide_index=True,
    )


    # =========================
    # AI順位
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


        # =========================
        # オッズ
        # =========================

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


        if odds:

            tri["オッズ"] = (
                tri["3連単"].map(odds)
            )

        else:

            tri["オッズ"] = None


        # =========================
        # 最終AI
        # =========================

        tri["最終AI"] = tri[
            "AIスコア"
        ]


        for idx in tri.index:

            odd = tri.loc[
                idx,
                "オッズ",
            ]

            if pd.notna(odd):

                try:

                    odd = float(odd)

                    odds_bonus = (
                        math.log(
                            max(
                                odd,
                                1,
                            )
                        )
                        * 2.0
                    )

                    tri.loc[
                        idx,
                        "最終AI",
                    ] += odds_bonus

                except Exception:

                    pass


        # =========================
        # 信頼度
        # =========================

        min_score = tri[
            "最終AI"
        ].min()

        max_score = tri[
            "最終AI"
        ].max()


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


        # =========================
        # 穴度
        # =========================

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


        # =========================
        # 並び替え
        # =========================

        tri = tri.sort_values(
            "最終AI",
            ascending=False,
        ).reset_index(
            drop=True
        )


        # =========================
        # TOP
        # =========================

        top = tri.iloc[0]

        second = tri.iloc[1]

        third = tri.iloc[2]


        hole_candidates = tri[
            tri["オッズ"].notna()
        ].sort_values(
            "オッズ",
            ascending=False,
        )


        if len(hole_candidates) > 0:

            hole = (
                hole_candidates.iloc[0]
            )

        else:

            hole = tri.iloc[-1]


        # =========================
        # 120通り
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


        top10 = tri.head(
            10
        ).copy()


        st.dataframe(
            top10[
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


        st.caption(
            "展示ST・展示進入・天候データを取得しています。"
        )


else:

    st.info(
        "開催日・競艇場・レースを選んで"
        "「AI予想を実行」を押してください。"
                            )
