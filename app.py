import streamlit as st
import pandas as pd

from datetime import date, datetime
from zoneinfo import ZoneInfo

from data import (
    get_data,
    get_race,
    history14,
    get_odds,
    clear_odds_cache,
    odds_url,
)

from ai import (
    score,
    tri_ai,
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
    24: "大村",

}


# =========================================================
# Streamlit設定
# =========================================================

st.set_page_config(

    page_title="やっちゃんの競艇AI予想 PRO",

    page_icon="🚤",

    layout="wide",

)


# =========================================================
# タイトル
# =========================================================

st.title(
    "🚤 やっちゃんの競艇AI予想 PRO"
)

st.caption(
    "展示タイム＋選手データ＋過去14日＋購入前3連単オッズ"
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

col1, col2, col3 = st.columns(3)


with col1:

    td = st.date_input(

        "開催日",

        value=today,

        min_value=date(
            2026,
            1,
            1
        ),

    )


with col2:

    stadium_name = st.selectbox(

        "競艇場",

        list(
            STADIUMS.values()
        ),

    )


with col3:

    race_number = st.selectbox(

        "レース",

        range(1, 13),

        format_func=lambda x:
        f"{x}R",

    )


stadium_number = next(

    number

    for number, name
    in STADIUMS.items()

    if name == stadium_name

)


# =========================================================
# オッズ更新
# =========================================================

refresh_odds = st.button(
    "🔄 購入前オッズを更新"
)


if refresh_odds:

    clear_odds_cache()

    st.success(
        "オッズのキャッシュを更新しました。"
    )


# =========================================================
# AI予想
# =========================================================

run_ai = st.button(

    "🚀 AI予想を実行",

    type="primary",

    use_container_width=True,

)


if not run_ai:

    st.info(

        "開催日・競艇場・レースを選択して"
        "「AI予想を実行」を押してください。"

    )

    st.stop()


# =========================================================
# レースデータ取得
# =========================================================

with st.spinner(
    "レースデータを取得中..."
):

    try:

        data = get_data(
            td
        )

        race = get_race(
            data,
            stadium_number,
            race_number
        )

    except Exception as error:

        st.error(
            "レースデータの取得に失敗しました。"
        )

        st.code(
            str(error)
        )

        st.stop()


if race is None:

    st.error(
        "このレースのデータがありません。"
    )

    st.stop()


# =========================================================
# 選手データ
# =========================================================

rows = []


racers_data = race.get(
    "racers",
    {}
)


preview_data = (
    race
    .get("preview", {})
    .get("racers", {})
)


if not isinstance(
    racers_data,
    dict
):

    racers_data = {}


if not isinstance(
    preview_data,
    dict
):

    preview_data = {}


# =========================================================
# 6艇
# =========================================================

for lane in range(1, 7):

    racer = racers_data.get(
        str(lane),
        {}
    )

    preview = preview_data.get(
        str(lane),
        {}
    )


    if not racer:

        continue


    # -----------------------------------------
    # 展示タイム
    # -----------------------------------------

    exhibition = preview.get(
        "exhibition_time",
        0
    )


    try:

        exhibition = float(
            exhibition or 0
        )

    except (
        TypeError,
        ValueError
    ):

        exhibition = 0.0


    # -----------------------------------------
    # 各データ
    # -----------------------------------------

    rows.append({

        "枠": lane,

        "選手名": racer.get(
            "name",
            "不明"
        ),

        "選手番号": str(
            racer.get(
                "number",
                ""
            )
        ),

        "級別": racer.get(
            "rank_number",
            ""
        ),

        "全国勝率": float(
            racer.get(
                "national_win_rate",
                0
            ) or 0
        ),

        "全国2連率": float(
            racer.get(
                "national_top_2_percent",
                0
            ) or 0
        ),

        "当地勝率": float(
            racer.get(
                "local_win_rate",
                0
            ) or 0
        ),

        "モーター2連率": float(
            racer.get(
                "motor_top_2_percent",
                0
            ) or 0
        ),

        "平均ST": float(
            racer.get(
                "average_start_timing",
                0
            ) or 0
        ),

        "展示タイム": exhibition,

    })


# =========================================================
# DataFrame
# =========================================================

df = pd.DataFrame(
    rows
)


if df.empty:

    st.error(
        "出走表が取得できませんでした。"
    )

    st.stop()


# =========================================================
# AIスコア
# =========================================================

df["学習AI"] = df.apply(
    score,
    axis=1
)


df = df.sort_values(

    "学習AI",

    ascending=False,

).reset_index(
    drop=True
)


# =========================================================
# 選手AI評価
# =========================================================

st.subheader(
    f"🤖 {stadium_name} {race_number}R 選手AI評価"
)


st.dataframe(

    df[
        [
            "枠",
            "選手名",
            "選手番号",
            "級別",
            "全国勝率",
            "全国2連率",
            "当地勝率",
            "モーター2連率",
            "平均ST",
            "展示タイム",
            "学習AI",
        ]
    ],

    use_container_width=True,

    hide_index=True,

)


# =========================================================
# AI上位3艇
# =========================================================

st.subheader(
    "🏆 AI選手ランキング"
)


ranking_labels = [

    "🥇 本命",

    "🥈 対抗",

    "🥉 穴",

]


top_three = df.head(
    min(3, len(df))
)


for position, (_, row) in enumerate(
    top_three.iterrows()
):

    st.write(

        f"{ranking_labels[position]} "

        f"**{int(row['枠'])}号艇 "
        f"{row['選手名']}**　"

        f"AIスコア "
        f"**{row['学習AI']}**"

    )


# =========================================================
# 過去14日
# =========================================================

with st.spinner(
    "過去14日データを確認中..."
):

    history = pd.DataFrame(
        history14(td)
    )


# =========================================================
# オッズ取得
# =========================================================

st.subheader(
    "💰 購入前3連単オッズ"
)


with st.spinner(
    "BOATRACE公式サイトからオッズを取得中..."
):

    odds = get_odds(

        td,

        stadium_number,

        race_number,

    )


# =========================================================
# オッズ状態
# =========================================================

if len(odds) >= 100:

    st.success(

        f"3連単オッズを "
        f"**{len(odds)}通り** 取得しました。"

    )

elif len(odds) > 0:

    st.warning(

        f"3連単オッズを "
        f"{len(odds)}通り取得しました。"
        f"120通りすべて取得できていません。"

    )

else:

    st.error(

        "購入前オッズを取得できませんでした。"
        "AI予想のみ計算します。"

    )


# =========================================================
# 公式オッズページ
# =========================================================

st.caption(
    f"取得対象: {odds_url(td, stadium_number, race_number)}"
)


# =========================================================
# 3連単AI
# =========================================================

tri = tri_ai(

    df,

    history,

    odds,

)


if tri.empty:

    st.error(
        "3連単AIを計算できませんでした。"
    )

    st.stop()


# =========================================================
# AI TOP
# =========================================================

top = tri.iloc[0]

second = tri.iloc[1]

third = tri.iloc[2]


# 穴は「AI確率」ではなく
# 期待値を含めて低評価側から選ぶ
hole_candidates = tri.sort_values(

    [
        "穴度",
        "AI確率",
    ],

    ascending=[
        False,
        True,
    ],

)


hole = hole_candidates.iloc[0]


# =========================================================
# AI本線
# =========================================================

st.subheader(
    "🔥 AI本線"
)


c1, c2, c3, c4 = st.columns(4)


with c1:

    st.metric(

        "🥇 本線",

        top["3連単"],

        f"AI {top['AI確率']}%",

    )


with c2:

    st.metric(

        "🥈 対抗",

        second["3連単"],

        f"AI {second['AI確率']}%",

    )


with c3:

    st.metric(

        "🎯 押さえ",

        third["3連単"],

        f"AI {third['AI確率']}%",

    )


with c4:

    st.metric(

        "💥 穴候補",

        hole["3連単"],

        f"AI {hole['AI確率']}%",

    )


# =========================================================
# 本線詳細
# =========================================================

st.subheader(
    "📌 上位買い目詳細"
)


summary = pd.DataFrame({

    "区分": [
        "🥇 本線",
        "🥈 対抗",
        "🎯 押さえ",
        "💥 穴",
    ],

    "3連単": [
        top["3連単"],
        second["3連単"],
        third["3連単"],
        hole["3連単"],
    ],

    "AI確率": [
        top["AI確率"],
        second["AI確率"],
        third["AI確率"],
        hole["AI確率"],
    ],

    "オッズ": [
        top["オッズ"],
        second["オッズ"],
        third["オッズ"],
        hole["オッズ"],
    ],

    "市場確率": [
        top["市場確率"],
        second["市場確率"],
        third["市場確率"],
        hole["市場確率"],
    ],

    "AI乖離": [
        top["AI乖離"],
        second["AI乖離"],
        third["AI乖離"],
        hole["AI乖離"],
    ],

    "期待値倍率": [
        top["期待値倍率"],
        second["期待値倍率"],
        third["期待値倍率"],
        hole["期待値倍率"],
    ],

})


st.dataframe(

    summary,

    use_container_width=True,

    hide_index=True,

)


# =========================================================
# 期待値ランキング
# =========================================================

st.subheader(
    "💰 期待値ランキング TOP10"
)


ev_columns = [

    "3連単",

    "AI確率",

    "オッズ",

    "市場確率",

    "AI乖離",

    "期待値倍率",

]


ev_view = tri[
    ev_columns
].head(10)


st.dataframe(

    ev_view,

    use_container_width=True,

    hide_index=True,

)


# =========================================================
# AIランキング
# =========================================================

st.subheader(
    "📈 3連単120通り AIランキング"
)


ranking_columns = [

    "3連単",

    "AIスコア",

    "AI確率",

    "オッズ",

    "市場確率",

    "AI乖離",

    "期待値倍率",

    "信頼度",

    "穴度",

]


st.dataframe(

    tri[
        ranking_columns
    ],

    use_container_width=True,

    hide_index=True,

)


# =========================================================
# 買い目候補
# =========================================================

st.subheader(
    "🎯 最終候補"
)


def display_bet(
    label,
    row
):

    odds_text = (

        f"{row['オッズ']:.1f}倍"

        if pd.notna(
            row["オッズ"]
        )

        else "取得なし"

    )


    ev_text = (

        f"{row['期待値倍率']:.2f}倍"

        if pd.notna(
            row["期待値倍率"]
        )

        else "計算不可"

    )


    st.write(

        f"{label} "

        f"**{row['3連単']}**　"

        f"AI確率 "
        f"**{row['AI確率']:.2f}%**　"

        f"オッズ "
        f"**{odds_text}**　"

        f"期待値 "
        f"**{ev_text}**"

    )


display_bet(
    "🥇 本線：",
    top
)


display_bet(
    "🥈 対抗：",
    second
)


display_bet(
    "🎯 押さえ：",
    third
)


display_bet(
    "💥 穴：",
    hole
)


# =========================================================
# 注意表示
# =========================================================

st.divider()

st.caption(

    "※ オッズは取得時点の公開情報です。"
    "レース締切まで変動する可能性があります。"
    "期待値倍率はAI確率が正しく校正されていることを前提とした"
    "理論値であり、的中・利益を保証するものではありません。"

)
