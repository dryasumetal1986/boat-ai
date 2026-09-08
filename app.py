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
    1: "桐生", 2: "戸田", 3: "江戸川", 4: "平和島",
    5: "多摩川", 6: "浜名湖", 7: "蒲郡", 8: "常滑",
    9: "津", 10: "三国", 11: "びわこ", 12: "住之江",
    13: "尼崎", 14: "鳴門", 15: "丸亀", 16: "児島",
    17: "宮島", 18: "徳山", 19: "下関", 20: "若松",
    21: "芦屋", 22: "福岡", 23: "唐津", 24: "大村"
}

TECHNIQUES = {
    1: "逃げ",
    2: "差し",
    3: "まくり",
    4: "まくり差し",
    5: "抜き",
    6: "恵まれ"
}


def num(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def racer_value(r, *keys):
    for key in keys:
        if key in r and r[key] not in (None, ""):
            return r[key]
    return 0


@st.cache_data(ttl=180)
def get_data(d):
    ymd = d.strftime("%Y%m%d")
    url = f"{API}/{d.year}/{ymd}.json"

    response = requests.get(url, timeout=15)
    response.raise_for_status()

    return response.json()


def get_race(data, stadium, race_no):
    return data["programs"]["stadiums"][str(stadium)]["races"][str(race_no)]


def make_table(race):
    rows = []

    racers = race.get("racers", [])
    previews = race.get("preview", {}).get("racers", [])

    preview_map = {}

    for preview in previews:
        number = str(
            racer_value(
                preview,
                "player_number",
                "racer_number"
            )
        )
        preview_map[number] = preview

    for i, racer in enumerate(racers, 1):
        number = str(
            racer_value(
                racer,
                "player_number",
                "racer_number"
            )
        )

        preview = preview_map.get(number, {})

        rows.append({
            "枠": i,
            "選手名": racer_value(
                racer,
                "player_name",
                "name"
            ),
            "選手番号": number,
            "級別": racer_value(
                racer,
                "rank",
                "class"
            ),
            "全国勝率": num(
                racer_value(
                    racer,
                    "national_win_rate",
                    "win_rate"
                )
            ),
            "全国2連率": num(
                racer_value(
                    racer,
                    "national_2rent_rate",
                    "national_second_rate"
                )
            ),
            "当地勝率": num(
                racer_value(
                    racer,
                    "local_win_rate",
                    "stadium_win_rate"
                )
            ),
            "モーター2連率": num(
                racer_value(
                    racer,
                    "motor_2rent_rate",
                    "motor_second_rate"
                )
            ),
            "平均ST": num(
                racer_value(
                    racer,
                    "average_start_timing",
                    "average_st"
                )
            ),
            "展示タイム": num(
                racer_value(
                    preview,
                    "exhibition_time",
                    "exhibition"
                )
            )
        })

    return pd.DataFrame(rows)


@st.cache_data(ttl=600)
def get_course_stats(target_date, days=30):
    stats = {}

    for n in range(1, days + 1):
        d = target_date - timedelta(days=n)

        try:
            data = get_data(d)

            stadiums = (
                data
                .get("programs", {})
                .get("stadiums", {})
            )

            for stadium_data in stadiums.values():

                for race in stadium_data.get("races", {}).values():

                    racers = (
                        race
                        .get("result", {})
                        .get("racers", [])
                    )

                    for racer in racers:

                        player = str(
                            racer_value(
                                racer,
                                "player_number",
                                "racer_number"
                            )
                        )

                        course = int(
                            num(
                                racer_value(
                                    racer,
                                    "course_number",
                                    "course"
                                ),
                                0
                            )
                        )

                        place = int(
                            num(
                                racer_value(
                                    racer,
                                    "place_number",
                                    "rank"
                                ),
                                99
                            )
                        )

                        if not player:
                            continue

                        if course < 1 or course > 6:
                            continue

                        key = (player, course)

                        if key not in stats:
                            stats[key] = [0, 0]

                        stats[key][0] += 1

                        if place == 1:
                            stats[key][1] += 1

        except Exception:
            continue

    return stats


@st.cache_data(ttl=600)
def get_technique_stats(target_date, days=30):
    stats = {}

    for n in range(1, days + 1):
        d = target_date - timedelta(days=n)

        try:
            data = get_data(d)

            stadiums = (
                data
                .get("programs", {})
                .get("stadiums", {})
            )

            for stadium_data in stadiums.values():

                for race in stadium_data.get("races", {}).values():

                    racers = (
                        race
                        .get("result", {})
                        .get("racers", [])
                    )

                    for racer in racers:

                        player = str(
                            racer_value(
                                racer,
                                "player_number",
                                "racer_number"
                            )
                        )

                        technique = int(
                            num(
                                racer_value(
                                    racer,
                                    "technique_number",
                                    "technique"
                                ),
                                0
                            )
                        )

                        if player and technique in TECHNIQUES:

                            if player not in stats:
                                stats[player] = {}

                            stats[player][technique] = (
                                stats[player].get(technique, 0) + 1
                            )

        except Exception:
            continue

    return stats


def add_stats(df, course_stats, technique_stats):

    first_rates = []
    starts = []
    best_techniques = []
    technique_counts = []

    for _, row in df.iterrows():

        player = str(row["選手番号"])
        course = int(row["枠"])

        result = course_stats.get(
            (player, course),
            [0, 0]
        )

        count = result[0]
        wins = result[1]

        if count > 0:
            first_rate = wins / count * 100
        else:
            first_rate = 0

        first_rates.append(first_rate)
        starts.append(count)

        techniques = technique_stats.get(player, {})

        if techniques:

            best_number = max(
                techniques,
                key=techniques.get
            )

            best_techniques.append(
                TECHNIQUES.get(best_number, "-")
            )

            technique_counts.append(
                techniques[best_number]
            )

        else:
            best_techniques.append("-")
            technique_counts.append(0)

    df["コース1着率"] = first_rates
    df["コース出走数"] = starts
    df["得意決まり手"] = best_techniques
    df["決まり手回数"] = technique_counts

    return df


def weather_info(race):

    weather = (
        race
        .get("preview", {})
        .get("weather", {})
    )

    if not isinstance(weather, dict):
        weather = {}

    return {
        "風速": num(
            racer_value(
                weather,
                "wind",
                "wind_speed"
            )
        ),
        "風向": racer_value(
            weather,
            "windDirect",
            "wind_direction",
            "wind_direction_number"
        ),
        "波高": num(
            racer_value(
                weather,
                "wave",
                "wave_height"
            )
        ),
        "気温": num(
            racer_value(
                weather,
                "temperature",
                "air_temperature"
            )
        )
    }


def calculate_score(row, weather):

    score = 0.0

    # 全国成績
    score += row["全国勝率"] * 10
    score += row["全国2連率"] * 0.25

    # 当地成績
    score += row["当地勝率"] * 5

    # モーター
    score += row["モーター2連率"] * 0.12

    # ST
    st_value = row["平均ST"]

    if st_value <= 0.12:
        score += 12
    elif st_value <= 0.15:
        score += 8
    elif st_value <= 0.18:
        score += 4
    elif st_value >= 0.22:
        score -= 4

    # コース
    lane_bonus = {
        1: 20,
        2: 8,
        3: 6,
        4: 7,
        5: 2,
        6: 0
    }

    lane = int(row["枠"])

    score += lane_bonus.get(lane, 0)

    # 選手×コース適性
    course_rate = row["コース1着率"]

    if course_rate >= 50:
        score += 12
    elif course_rate >= 40:
        score += 9
    elif course_rate >= 30:
        score += 6
    elif course_rate >= 20:
        score += 3
    elif course_rate > 0:
        score += 1

    # 決まり手
    technique = row["得意決まり手"]

    if lane == 1 and technique == "逃げ":
        score += 5

    elif lane in (2, 3) and technique in (
        "差し",
        "まくり"
    ):
        score += 4

    elif lane in (3, 4) and technique == "まくり差し":
        score += 4

    # 展示タイム
    exhibition = row["展示タイム"]

    if exhibition > 0:

        if exhibition <= 6.70:
            score += 6
        elif exhibition <= 6.75:
            score += 4
        elif exhibition <= 6.80:
            score += 2
        elif exhibition >= 6.90:
            score -= 2

    # 風
    wind = weather["風速"]

    if wind >= 5:

        if lane == 1:
            score -= 1

        if lane in (2, 3, 4):
            score += 1

    # 波
    wave = weather["波高"]

    if wave >= 4:

        if lane in (1, 2):
            score -= 1

        if lane in (3, 4):
            score += 1

    return round(score, 2)


def actual_order(race):

    result = (
        race
        .get("result", {})
        .get("racers", [])
    )

    values = []

    for racer in result:

        place = int(
            num(
                racer_value(
                    racer,
                    "place_number",
                    "rank"
                ),
                99
            )
        )

        course = int(
            num(
                racer_value(
                    racer,
                    "course_number",
                    "course"
                ),
                0
            )
        )

        if 1 <= place <= 6 and 1 <= course <= 6:
            values.append((place, course))

    values.sort()

    return [
        course
        for _, course in values[:3]
    ]


@st.cache_data(ttl=900)
def backtest(target_date, days=7):

    total = 0
    hit_first = 0
    hit_top3 = 0

    for n in range(1, days + 1):

        d = target_date - timedelta(days=n)

        try:

            data = get_data(d)

            stadiums = (
                data
                .get("programs", {})
                .get("stadiums", {})
            )

            for stadium_data in stadiums.values():

                for race in stadium_data.get(
                    "races",
                    {}
                ).values():

                    df = make_table(race)

                    if len(df) != 6:
                        continue

                    course_stats = get_course_stats(
                        d,
                        14
                    )

                    technique_stats = get_technique_stats(
                        d,
                        14
                    )

                    df = add_stats(
                        df,
                        course_stats,
                        technique_stats
                    )

                    weather = weather_info(race)

                    df["AI1着評価"] = df.apply(
                        lambda row: calculate_score(
                            row,
                            weather
                        ),
                        axis=1
                    )

                    prediction = (
                        df
                        .sort_values(
                            "AI1着評価",
                            ascending=False
                        )["枠"]
                        .astype(int)
                        .tolist()
                    )

                    actual = actual_order(race)

                    if len(actual) < 3:
                        continue

                    total += 1

                    if prediction[0] == actual[0]:
                        hit_first += 1

                    if set(prediction[:3]) == set(actual[:3]):
                        hit_top3 += 1

        except Exception:
            continue

    return total, hit_first, hit_top3


# --------------------------------------------------
# 画面
# --------------------------------------------------

st.title("🚤 やっちゃんの競艇AI予想 PRO")

st.caption(
    "会場・コース適性＋決まり手＋展示タイム＋風・波を加味した安定版"
)

col1, col2, col3 = st.columns(3)

with col1:
    target_date = st.date_input(
        "開催日",
        value=date.today()
    )

with col2:
    stadium = st.selectbox(
        "競艇場",
        list(STADIUMS.keys()),
        format_func=lambda x:
            f"{x} {STADIUMS[x]}"
    )

with col3:
    race_no = st.selectbox(
        "レース",
        list(range(1, 13)),
        format_func=lambda x:
            f"{x}R"
    )


if st.button(
    "🚀 AI予想を実行",
    type="primary",
    use_container_width=True
):

    try:

        data = get_data(target_date)

        race = get_race(
            data,
            stadium,
            race_no
        )

        df = make_table(race)

        if len(df) != 6:

            st.error(
                "6艇分のデータを取得できませんでした。"
            )

            st.stop()

        with st.spinner(
            "過去データを集計中..."
        ):

            course_stats = get_course_stats(
                target_date,
                30
            )

            technique_stats = get_technique_stats(
                target_date,
                30
            )

        df = add_stats(
            df,
            course_stats,
            technique_stats
        )

        weather = weather_info(race)

        df["AI1着評価"] = df.apply(
            lambda row:
                calculate_score(
                    row,
                    weather
                ),
            axis=1
        )

        df = (
            df
            .sort_values(
                "AI1着評価",
                ascending=False
            )
            .reset_index(drop=True)
        )

        st.subheader(
            f"🎯 {STADIUMS[stadium]} {race_no}R AI予想"
        )

        w1, w2, w3, w4 = st.columns(4)

        with w1:
            st.metric(
                "風速",
                f'{weather["風速"]:.1f} m'
            )

        with w2:
            st.metric(
                "波高",
                f'{weather["波高"]:.1f} cm'
            )

        with w3:
            st.metric(
                "AI本命",
                f'{int(df.iloc[0]["枠"])}号艇'
            )

        with w4:
            st.metric(
                "2番手",
                f'{int(df.iloc[1]["枠"])}号艇'
            )

        display_columns = [
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
            "コース1着率",
            "コース出走数",
            "得意決まり手",
            "AI1着評価"
        ]

        st.dataframe(
            df[display_columns],
            use_container_width=True,
            hide_index=True
        )

        top3 = (
            df
            .head(3)["枠"]
            .astype(int)
            .tolist()
        )

        st.success(
            f"🥇 本命 {top3[0]}号艇　"
            f"🥈 対抗 {top3[1]}号艇　"
            f"🥉 穴 {top3[2]}号艇"
        )

        combinations = [
            f"{top3[0]}-{top3[1]}-{top3[2]}",
            f"{top3[0]}-{top3[2]}-{top3[1]}",
            f"{top3[1]}-{top3[0]}-{top3[2]}"
        ]

        st.write("### 🎟️ 推奨3連単")

        for combination in combinations:
            st.write(
                f"・**{combination}**"
            )

        st.info(
            "※AI評価は過去統計・選手成績・展示タイム・"
            "天候などを組み合わせた参考値です。"
            "舟券購入は自己責任でお願いします。"
        )

    except Exception as e:

        st.error(
            f"予想処理でエラーが発生しました: {e}"
        )

        st.exception(e)


st.divider()

st.subheader("📊 簡易バックテスト")

if st.button("過去7日でバックテスト"):

    try:

        with st.spinner(
            "バックテスト中..."
        ):

            total, hit_first, hit_top3 = backtest(
                target_date,
                7
            )

        if total == 0:

            st.warning(
                "検証できるレースデータがありませんでした。"
            )

        else:

            a, b, c = st.columns(3)

            with a:
                st.metric(
                    "検証レース",
                    total
                )

            with b:
                st.metric(
                    "1着的中率",
                    f"{hit_first / total * 100:.1f}%"
                )

            with c:
                st.metric(
                    "3艇一致率",
                    f"{hit_top3 / total * 100:.1f}%"
                )

    except Exception as e:

        st.error(
            f"バックテストでエラーが発生しました: {e}"
        )

        st.exception(e)


st.caption(
    "やっちゃんの競艇AI予想 PRO"
)
