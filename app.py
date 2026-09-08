import streamlit as st
import requests
import pandas as pd
from datetime import date, timedelta


st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO",
    page_icon="🚤",
    layout="wide"
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


TECHNIQUES = {
    1: "逃げ",
    2: "差し",
    3: "まくり",
    4: "まくり差し",
    5: "抜き",
    6: "恵まれ"
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


def get_course_stats(target_date):

    stats = {}

    for day in range(1, 15):

        d = target_date - timedelta(days=day)

        if d < date(2026, 1, 1):
            continue

        try:
            data = get_data(d)
        except:
            continue

        stadiums = data.get(
            "programs",
            {}
        ).get(
            "stadiums",
            {}
        )

        for stadium in stadiums.values():

            races = stadium.get(
                "races",
                {}
            )

            for race in races.values():

                result = race.get(
                    "result",
                    {}
                )

                result_racers = result.get(
                    "racers",
                    {}
                )

                if not result_racers:
                    continue

                for racer in result_racers.values():

                    player_number = str(
                        racer.get(
                            "number",
                            ""
                        )
                    )

                    course = racer.get(
                        "course_number"
                    )

                    place = racer.get(
                        "place_number"
                    )

                    if not player_number:
                        continue

                    try:
                        course = int(course)
                    except:
                        continue

                    if course < 1 or course > 6:
                        continue

                    key = (
                        player_number,
                        course
                    )

                    if key not in stats:

                        stats[key] = {
                            "出走": 0,
                            "1着": 0
                        }

                    stats[key]["出走"] += 1

                    try:
                        place = int(place)
                    except:
                        place = 0

                    if place == 1:
                        stats[key]["1着"] += 1

    return stats


def get_technique_stats(target_date):

    stats = {}

    for day in range(1, 15):

        d = target_date - timedelta(days=day)

        if d < date(2026, 1, 1):
            continue

        try:
            data = get_data(d)
        except:
            continue

        stadiums = data.get(
            "programs",
            {}
        ).get(
            "stadiums",
            {}
        )

        for stadium in stadiums.values():

            races = stadium.get(
                "races",
                {}
            )

            for race in races.values():

                result = race.get(
                    "result",
                    {}
                )

                technique = result.get(
                    "technique_number"
                )

                try:
                    technique = int(technique)
                except:
                    continue

                if technique not in TECHNIQUES:
                    continue

                result_racers = result.get(
                    "racers",
                    {}
                )

                if not result_racers:
                    continue

                winner = None

                for racer in result_racers.values():

                    try:
                        place = int(
                            racer.get(
                                "place_number"
                            )
                        )
                    except:
                        place = 0

                    if place == 1:
                        winner = racer
                        break

                if winner is None:
                    continue

                player_number = str(
                    winner.get(
                        "number",
                        ""
                    )
                )

                if not player_number:
                    continue

                key = (
                    player_number,
                    technique
                )

                if key not in stats:
                    stats[key] = 0

                stats[key] += 1

    return stats


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
            "選手番号": str(
                r.get(
                    "number",
                    ""
                )
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


def add_course_stats(df, stats):

    rates = []
    starts = []

    for _, row in df.iterrows():

        player = str(
            row["選手番号"]
        )

        course = int(
            row["枠"]
        )

        key = (
            player,
            course
        )

        item = stats.get(
            key,
            {}
        )

        start_count = item.get(
            "出走",
            0
        )

        win_count = item.get(
            "1着",
            0
        )

        if start_count > 0:

            rate = (
                win_count
                / start_count
                * 100
            )

        else:

            rate = 0

        rates.append(
            round(rate, 1)
        )

        starts.append(
            start_count
        )

    df["コース1着率"] = rates
    df["コース出走数"] = starts

    return df


def add_technique_stats(df, stats):

    technique_columns = {
        1: "逃げ回数",
        2: "差し回数",
        3: "まくり回数",
        4: "まくり差し回数",
        5: "抜き回数",
        6: "恵まれ回数"
    }

    for number, column in technique_columns.items():

        values = []

        for _, row in df.iterrows():

            player = str(
                row["選手番号"]
            )

            key = (
                player,
                number
            )

            values.append(
                stats.get(
                    key,
                    0
                )
            )

        df[column] = values


    best_names = []
    best_counts = []
    total_counts = []

    for _, row in df.iterrows():

        counts = {}

        for number, column in technique_columns.items():

            counts[number] = int(
                row[column]
            )

        total = sum(
            counts.values()
        )

        total_counts.append(
            total
        )

        if total == 0:

            best_names.append(
                "データなし"
            )

            best_counts.append(
                0
            )

        else:

            best_number = max(
                counts,
                key=counts.get
            )

            best_names.append(
                TECHNIQUES[best_number]
            )

            best_counts.append(
                counts[best_number]
            )

    df["決まり手合計"] = total_counts

    df["得意決まり手"] = best_names

    df["最多決まり手回数"] = best_counts

    return df


def technique_bonus(row):

    lane = int(
        row["枠"]
    )

    technique = row[
        "得意決まり手"
    ]

    bonus = 0

    if lane == 1 and technique == "逃げ":
        bonus = 8

    elif lane == 2 and technique == "差し":
        bonus = 8

    elif lane == 3 and technique == "まくり":
        bonus = 7

    elif lane == 3 and technique == "まくり差し":
        bonus = 7

    elif lane == 4 and technique == "まくり":
        bonus = 7

    elif lane == 4 and technique == "まくり差し":
        bonus = 7

    elif lane == 5 and technique == "まくり差し":
        bonus = 5

    elif lane == 6 and technique == "まくり差し":
        bonus = 4

    return bonus


def calculate_score(row):

    s = 0

    s += row["全国勝率"] * 10

    s += row["全国2連率"] * 0.25

    s += row["当地勝率"] * 5

    s += row["モーター2連率"] * 0.12

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

    lane = int(
        row["枠"]
    )

    lane_bonus = {
        1: 20,
        2: 8,
        3: 6,
        4: 7,
        5: 2,
        6: 0
    }

    s += lane_bonus.get(
        lane,
        0
    )

    course_rate = row[
        "コース1着率"
    ]

    if course_rate >= 50:
        s += 12

    elif course_rate >= 40:
        s += 9

    elif course_rate >= 30:
        s += 6

    elif course_rate >= 20:
        s += 3

    elif course_rate > 0:
        s += 1

    s += technique_bonus(
        row
    )

    exhibition = row[
        "展示タイム"
    ]

    if exhibition > 0:

        if exhibition <= 6.70:
            s += 6

        elif exhibition <= 6.75:
            s += 4

        elif exhibition <= 6.80:
            s += 2

        elif exhibition >= 6.90:
            s -= 2

    return s


st.title(
    "🚤 やっちゃんの競艇AI予想 PRO"
)


st.write(
    "全国24場対応の競艇予想支援アプリ"
)


st.warning(
    "非公式APIを利用しています。"
    "最新情報は必ず公式BOATRACEで確認してください。"
)


st.subheader(
    "📅 レースを選択"
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
        break


if st.button(
    "🚀 AI予想を実行",
    type="primary"
):

    try:

        with st.spinner(
            "🚤 レースデータ取得中..."
        ):

            data = get_data(
                target_date
            )

    except Exception as e:

        st.error(
            "データ取得に失敗しました"
        )

        st.code(
            str(e)
        )

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


    df = make_table(
        race
    )


    if df.empty:

        st.error(
            "出走表がありません"
        )

        st.stop()


    with st.spinner(
        "📊 過去14日分のデータを分析中..."
    ):

        course_stats = get_course_stats(
            target_date
        )

        technique_stats = get_technique_stats(
            target_date
        )


    df = add_course_stats(
        df,
        course_stats
    )


    df = add_technique_stats(
        df,
        technique_stats
    )


    df["決まり手補正"] = df.apply(
        technique_bonus,
        axis=1
    )


    df["AIスコア"] = df.apply(
        calculate_score,
        axis=1
    )


    maximum = df[
        "AIスコア"
    ].max()


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
        "当地勝率",
        "モーター2連率",
        "平均ST",
        "展示タイム",
        "コース1着率",
        "コース出走数",
        "逃げ回数",
        "差し回数",
        "まくり回数",
        "まくり差し回数",
        "抜き回数",
        "恵まれ回数",
        "決まり手合計",
        "得意決まり手",
        "最多決まり手回数",
        "決まり手補正",
        "AI1着評価"
    ]


    st.dataframe(
        df[columns],
        use_container_width=True,
        hide_index=True
    )


    st.subheader(
        "🏆 AI注目選手"
    )


    top = df.iloc[0]


    st.success(
        "本命 "
        + str(int(top["枠"]))
        + "号艇 "
        + str(top["選手名"])
        + "　コース1着率 "
        + str(top["コース1着率"])
        + "%"
        + "　得意決まり手 "
        + str(top["得意決まり手"])
        + "　"
        + str(int(top["最多決まり手回数"]))
        + "回"
        + "　AI評価 "
        + str(top["AI1着評価"])
    )


    if len(df) >= 2:

        second = df.iloc[1]

        st.info(
            "対抗 "
            + str(int(second["枠"]))
            + "号艇 "
            + str(second["選手名"])
            + "　得意決まり手 "
            + str(second["得意決まり手"])
            + "　"
            + str(int(second["最多決まり手回数"]))
            + "回"
        )


    if len(df) >= 3:

        third = df.iloc[2]

        st.info(
            "穴 "
            + str(int(third["枠"]))
            + "号艇 "
            + str(third["選手名"])
            + "　得意決まり手 "
            + str(third["得意決まり手"])
            + "　"
            + str(int(third["最多決まり手回数"]))
            + "回"
        )


    if len(df) >= 3:

        a = int(
            df.iloc[0]["枠"]
        )

        b = int(
            df.iloc[1]["枠"]
        )

        c = int(
            df.iloc[2]["枠"]
        )


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


    st.subheader(
        "🧠 AI分析項目"
    )


    st.write(
        "・全国勝率"
    )

    st.write(
        "・全国2連率"
    )

    st.write(
        "・当地勝率"
    )

    st.write(
        "・モーター2連率"
    )

    st.write(
        "・平均ST"
    )

    st.write(
        "・展示タイム"
    )

    st.write(
        "・選手別コース1着率"
    )

    st.write(
        "・逃げ / 差し / まくり / まくり差し / 抜き / 恵まれ"
    )

    st.write(
        "・選手別の過去14日間の決まり手回数"
    )


    st.divider()


    st.caption(
        "AI評価は独自計算による予想値です。"
        "的中や利益を保証するものではありません。"
    )


else:

    st.info(
        "競艇場とレースを選んでください"
        )
