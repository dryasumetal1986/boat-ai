import streamlit as st
import requests
import pandas as pd
from datetime import date

st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO",
    page_icon="🚤"
)

API = "https://boatraceopenapi.github.io/api/v1"

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


def num(x):
    try:
        return float(x)
    except:
        return 0


@st.cache_data(ttl=180)
def get_data(d):

    ymd = d.strftime("%Y%m%d")
    year = d.strftime("%Y")

    url = API + "/" + year + "/" + ymd + ".json"

    r = requests.get(
        url,
        timeout=20
    )

    r.raise_for_status()

    return r.json()


def get_race(data, stadium, race_no):

    stadiums = data.get(
        "programs",
        {}
    ).get(
        "stadiums",
        {}
    )

    s = stadiums.get(
        str(stadium)
    )

    if not s:
        return None

    races = s.get(
        "races",
        {}
    )

    return races.get(
        str(race_no)
    )


def make_table(race):

    racers = race.get(
        "racers",
        {}
    )

    preview = race.get(
        "preview",
        {}
    ).get(
        "racers",
        {}
    )

    rows = []

    for lane in range(1, 7):

        r = racers.get(
            str(lane),
            {}
        )

        p = preview.get(
            str(lane),
            {}
        )

        if not r:
            continue

        rows.append({
            "枠": lane,
            "選手名": r.get(
                "name",
                "不明"
            ),
            "級別": r.get(
                "rank_number",
                ""
            ),
            "全国勝率": num(
                r.get(
                    "national_win_rate"
                )
            ),
            "全国2連率": num(
                r.get(
                    "national_top_2_percent"
                )
            ),
            "当地勝率": num(
                r.get(
                    "local_win_rate"
                )
            ),
            "モーター2連率": num(
                r.get(
                    "motor_top_2_percent"
                )
            ),
            "平均ST": num(
                r.get(
                    "average_start_timing"
                )
            ),
            "展示タイム": num(
                p.get(
                    "exhibition_time"
                )
            )
        })

    return pd.DataFrame(rows)


def score(row):

    s = 0

    s += row["全国勝率"] * 10
    s += row["全国2連率"] * 0.25
    s += row["当地勝率"] * 5
    s += row["モーター2連率"] * 0.12

    lane = int(row["枠"])

    bonus = {
        1: 20,
        2: 8,
        3: 6,
        4: 7,
        5: 2,
        6: 0
    }

    s += bonus.get(
        lane,
        0
    )

    st_time = row["平均ST"]

    if st_time > 0:

        if st_time <= 0.12:
            s += 12

        elif st_time <= 0.15:
            s += 8

        elif st_time <= 0.18:
            s += 4

        elif st_time >= 0.22:
            s -= 4

    return s


st.title(
    "🚤 やっちゃんの競艇AI予想 PRO"
)

st.write(
    "全国24場対応の競艇予想支援アプリ"
)

st.warning(
    "非公式APIを利用しています。"
)

st.subheader(
    "レースを選択"
)

c1, c2, c3 = st.columns(3)

with c1:

    target_date = st.date_input(
        "開催日",
        value=date.today(),
        min_value=date(2026, 1, 1)
    )

with c2:

    stadium_name = st.selectbox(
        "競艇場",
        list(STADIUMS.values())
    )

with c3:

    race_no = st.selectbox(
        "レース",
        list(range(1, 13)),
        format_func=lambda x:
        str(x) + "R"
    )


stadium_no = 1

for n, name in STADIUMS.items():

    if name == stadium_name:
        stadium_no = n


if st.button(
    "🚀 AI予想を実行",
    type="primary"
):

    try:

        with st.spinner(
            "データ取得中..."
        ):

            data = get_data(
                target_date
            )

    except Exception as e:

        st.error(
            "データ取得に失敗しました"
        )

        st.code(str(e))

        st.stop()


    race = get_race(
        data,
        stadium_no,
        race_no
    )


    if race is None:

        st.error(
            "このレースのデータがありません"
        )

        st.stop()


    df = make_table(race)


    if df.empty:

        st.error(
            "出走表がありません"
        )

        st.stop()


    df["AIスコア"] = df.apply(
        score,
        axis=1
    )


    maximum = df["AIスコア"].max()


    if maximum > 0:

        df["AI1着評価"] = (
            df["AIスコア"]
            / maximum
            * 100
        ).round(1)

    else:

        df["AI1着評価"] = 0


    df = df.sort_values(
        "AI1着評価",
        ascending=False
    )

    df = df.reset_index(
        drop=True
    )


    st.subheader(
        stadium_name
        + " "
        + str(race_no)
        + "R"
    )


    st.subheader(
        "📋 AI評価"
    )


    columns = [
        "枠",
        "選手名",
        "級別",
        "全国勝率",
        "全国2連率",
        "当地勝率",
        "モーター2連率",
        "平均ST",
        "展示タイム",
        "AI1着評価"
    ]


    st.dataframe(
        df[columns],
        use_container_width=True,
        hide_index=True
    )


    top = df.iloc[0]


    st.success(
        "本命 "
        + str(int(top["枠"]))
        + "号艇 "
        + str(top["選手名"])
        + " AI評価 "
        + str(top["AI1着評価"])
    )


    if len(df) >= 2:

        second = df.iloc[1]

        st.info(
            "対抗 "
            + str(int(second["枠"]))
            + "号艇 "
            + str(second["選手名"])
        )


    if len(df) >= 3:

        third = df.iloc[2]

        st.info(
            "穴 "
            + str(int(third["枠"]))
            + "号艇 "
            + str(third["選手名"])
        )


    if len(df) >= 3:

        a = int(df.iloc[0]["枠"])
        b = int(df.iloc[1]["枠"])
        c = int(df.iloc[2]["枠"])

        st.subheader(
            "🎯 推奨3連単"
        )

        st.write(
            "本線 "
            + str(a)
            + "-"
            + str(b)
            + "-"
            + str(c)
        )

        st.write(
            "押さえ "
            + str(a)
            + "-"
            + str(c)
            + "-"
            + str(b)
        )

        st.write(
            "穴 "
            + str(b)
            + "-"
            + str(a)
            + "-"
            + str(c)
        )


else:

    st.info(
        "競艇場とレースを選んでください"
    )
