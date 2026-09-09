import streamlit as st
import pandas as pd

from datetime import date, datetime
from zoneinfo import ZoneInfo

from data import (
    get_data,
    get_race,
    history14,
    get_odds
)

from ai import (
    score,
    tri_ai
)


# =========================================================
# 競艇場
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
    24: "大村"

}


# =========================================================
# Streamlit設定
# =========================================================

st.set_page_config(

    page_title="やっちゃんの競艇AI予想 PRO",

    page_icon="🚤",

    layout="wide"

)


st.title(
    "🚤 やっちゃんの競艇AI予想 PRO"
)

st.caption(
    "展示タイム＋選手データ＋過去14日＋3連単オッズでAI評価"
)


# =========================================================
# 今日
# =========================================================

today = datetime.now(
    ZoneInfo("Asia/Tokyo")
).date()


# =========================================================
# 入力
# =========================================================

c1, c2, c3 = st.columns(3)


with c1:

    td = st.date_input(

        "開催日",

        today,

        min_value=date(
            2026,
            1,
            1
        )

    )


with c2:

    name = st.selectbox(

        "競艇場",

        list(
            STADIUMS.values()
        )

    )


with c3:

    rno = st.selectbox(

        "レース",

        range(1, 13),

        format_func=lambda x:
        f"{x}R"

    )


sno = list(
    STADIUMS
)[
    list(
        STADIUMS.values()
    ).index(name)
]


# =========================================================
# オッズ更新ボタン
# =========================================================

refresh = st.button(
    "🔄 オッズを更新"
)


if refresh:

    get_odds.clear()

    st.success(
        "オッズ取得キャッシュを更新しました"
    )


# =========================================================
# AI予想
# =========================================================

if st.button(
    "🚀 AI予想を実行",
    type="primary"
):

    # -----------------------------------------------------
    # レースデータ
    # -----------------------------------------------------

    try:

        data = get_data(td)

        race = get_race(
            data,
            sno,
            rno
        )

    except Exception as e:

        st.error(
            "データ取得に失敗しました"
        )

        st.code(
            str(e)
        )

        st.stop()


    if race is None:

        st.error(
            "このレースのデータがありません"
        )

        st.stop()


    # =====================================================
    # 選手データ
    # =====================================================

    rows = []

    rs = race.get(
        "racers",
        {}
    )

    preview = (
        race
        .get("preview", {})
        .get("racers", {})
    )


    if not isinstance(
        rs,
        dict
    ):
        rs = {}


    if not isinstance(
        preview,
        dict
    ):
        preview = {}


    for lane in range(1, 7):

        r = rs.get(
            str(lane),
            {}
        )

        p = preview.get(
            str(lane),
            {}
        )


        if not r:
            continue


        ex = p.get(
            "exhibition_time",
            0
        )


        try:

            ex = float(
                ex or 0
            )

        except Exception:

            ex = 0


        rows.append({

            "枠":
                lane,

            "選手名":
                r.get(
                    "name",
                    "不明"
                ),

            "選手番号":
                str(
                    r.get(
                        "number",
                        ""
                    )
                ),

            "級別":
                r.get(
                    "rank_number",
                    ""
                ),

            "全国勝率":
                float(
                    r.get(
                        "national_win_rate",
                        0
                    ) or 0
                ),

            "全国2連率":
                float(
                    r.get(
                        "national_top_2_percent",
                        0
                    ) or 0
                ),

            "当地勝率":
                float(
                    r.get(
                        "local_win_rate",
                        0
                    ) or 0
                ),

            "モーター2連率":
                float(
                    r.get(
                        "motor_top_2_percent",
                        0
                    ) or 0
                ),

            "平均ST":
                float(
                    r.get(
                        "average_start_timing",
                        0
                    ) or 0
                ),

            "展示タイム":
                ex

        })


    df = pd.DataFrame(
        rows
    )


    if df.empty:

        st.error(
            "出走表がありません"
        )

        st.stop()


    # =====================================================
    # 選手AI
    # =====================================================

    df["学習AI"] = df.apply(
        score,
        axis=1
    )


    df = df.sort_values(
        "学習AI",
        ascending=False
    ).reset_index(
        drop=True
    )


    # =====================================================
    # AI評価
    # =====================================================

    st.subheader(
        f"🤖 {name} {rno}R AI評価"
    )


    st.dataframe(

        df,

        use_container_width=True,

        hide_index=True

    )


    # =====================================================
    # AI順位
    # =====================================================

    st.subheader(
        "🏆 AI順位"
    )


    labels = [

        "🥇 本命",

        "🥈 対抗",

        "🥉 穴"

    ]


    for i, row in df.head(3).iterrows():

        st.write(

            f"{labels[i]} "

            f"{int(row['枠'])}号艇 "

            f"{row['選手名']}　"

            f"AI {row['学習AI']}"

        )


    # =====================================================
    # 過去14日
    # =====================================================

    history = pd.DataFrame(
        history14(td)
    )


    if len(df) < 3:

        st.warning(
            "3連単AIを計算するには3艇以上必要です"
        )

        st.stop()


    # =====================================================
    # オッズ取得
    # =====================================================

    with st.spinner(
        "購入前オッズを取得中..."
    ):

        odds = get_odds(
            td,
            sno,
            rno
        )


    if odds:

        st.success(
            f"購入前オッズ {len(odds)}通り取得"
        )

    else:

        st.warning(
            "購入前オッズを取得できませんでした。"
            "AI予想のみ表示します。"
        )


    # =====================================================
    # 3連単AI
    # =====================================================

    tri = tri_ai(

        df,

        history,

        odds

    )


    if tri.empty:

        st.error(
            "3連単AIの計算に失敗しました"
        )

        st.stop()


    # =====================================================
    # TOP
    # =====================================================

    top = tri.iloc[0]

    second = tri.iloc[1]

    third = tri.iloc[2]

    hole = tri.iloc[-1]


    # =====================================================
    # AI本線
    # =====================================================

    st.subheader(
        "🔥 AI本線"
    )


    a, b, c, d = st.columns(4)


    with a:

        st.metric(

            "🥇 AI本線",

            top["3連単"],

            f"AI確率 {top['AI確率']}%"

        )


    with b:

        st.metric(

            "🥈 AI対抗",

            second["3連単"],

            f"AI確率 {second['AI確率']}%"

        )


    with c:

        st.metric(

            "🎯 AI押さえ",

            third["3連単"],

            f"AI確率 {third['AI確率']}%"

        )


    with d:

        st.metric(

            "💥 AI穴",

            hole["3連単"],

            f"AI確率 {hole['AI確率']}%"

        )


    # =====================================================
    # オッズ表示
    # =====================================================

    st.subheader(
        "💰 購入前オッズ"
    )


    odds_cols = [

        "3連単",

        "AI確率",

        "オッズ",

        "市場確率",

        "AI乖離",

        "期待値倍率",

        "信頼度",

        "穴度"

    ]


    odds_view = tri[
        odds_cols
    ].copy()


    odds_view = odds_view.head(
        20
    )


    st.dataframe(

        odds_view,

        use_container_width=True,

        hide_index=True

    )


    # =====================================================
    # 期待値ランキング
    # =====================================================

    st.subheader(
        "💰 AI期待値ランキング TOP10"
    )


    ev_view = tri[
        [
            "3連単",
            "AI確率",
            "オッズ",
            "市場確率",
            "AI乖離",
            "期待値倍率"
        ]
    ].head(10)


    st.dataframe(

        ev_view,

        use_container_width=True,

        hide_index=True

    )


    # =====================================================
    # 120通り
    # =====================================================

    st.subheader(
        "📈 120通り3連単AIランキング"
    )


    st.dataframe(

        tri,

        use_container_width=True,

        hide_index=True

    )


    # =====================================================
    # 買い目まとめ
    # =====================================================

    st.subheader(
        "🎯 最終候補"
    )


    st.write(

        f"🥇 本線："
        f"{top['3連単']}　"
        f"AI {top['AI確率']}%　"
        f"オッズ {top['オッズ']}　"
        f"期待値 {top['期待値倍率']}倍"

    )


    st.write(

        f"🥈 対抗："
        f"{second['3連単']}　"
        f"AI {second['AI確率']}%　"
        f"オッズ {second['オッズ']}　"
        f"期待値 {second['期待値倍率']}倍"

    )


    st.write(

        f"🎯 押さえ："
        f"{third['3連単']}　"
        f"AI {third['AI確率']}%　"
        f"オッズ {third['オッズ']}　"
        f"期待値 {third['期待値倍率']}倍"

    )


    st.write(

        f"💥 穴："
        f"{hole['3連単']}　"
        f"AI {hole['AI確率']}%　"
        f"オッズ {hole['オッズ']}　"
        f"期待値 {hole['期待値倍率']}倍"

    )


else:

    st.info(

        "開催日・競艇場・レースを選んで"
        "「AI予想を実行」を押してください。"

        )
