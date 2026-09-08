import streamlit as st
import requests
import pandas as pd
from datetime import date

st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO",
    page_icon="🚤",
    layout="wide",
)

API_BASE = "https://boatraceopenapi.github.io/api/v1"

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


def get_number(value, default=0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


@st.cache_data(ttl=180)
def get_data(target_date):
    ymd = target_date.strftime("%Y%m%d")
    year = target_date.strftime("%Y")

    url = f"{API_BASE}/{year}/{ymd}.json"

    response = requests.get(
        url,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0"},
    )

    response.raise_for_status()

    return response.json()


def get_race(data, stadium_number, race_number):
    programs = data.get("programs", {})
    stadiums = programs.get("stadiums", {})

    stadium = stadiums.get(str(stadium_number))

    if not stadium:
        return None

    races = stadium.get("races", {})

    return races.get(str(race_number))


def get_course_bonus(course):
    bonuses = {
        1: 18,
        2: 7,
        3: 6,
        4: 7,
        5: 3,
        6: 0,
    }

    return bonuses.get(course, 0)


def make_table(race):
    racers = race.get("racers", {})
    preview = race.get("preview", {}).get("racers", {})

    rows = []

    for lane in range(1, 7):

        racer = racers.get(str(lane), {})
        info = preview.get(str(lane), {})

        if not racer:
            continue

        rows.append(
            {
                "枠": lane,
                "選手名": racer.get(
                    "name",
                    "不明",
                ),
                "級別": racer.get(
                    "rank_number",
                    "",
                ),
                "全国勝率": get_number(
                    racer.get(
                        "national_win_rate"
                    )
                ),
                "全国2連率": get_number(
                    racer.get(
                        "national_top_2_percent"
                    )
                ),
                "当地勝率": get_number(
                    racer.get(
                        "local_win_rate"
                    )
                ),
                "モーター2連率": get_number(
                    racer.get(
                        "motor_top_2_percent"
                    )
                ),
                "平均ST": get_number(
                    racer.get(
                        "average_start_timing"
                    )
                ),
                "展示タイム": get_number(
                    info.get(
                        "exhibition_time"
                    )
                ),
                "コース適性": get_course_bonus(
                    lane
                ),
            }
        )

    return pd.DataFrame(rows)


def calculate_score(row):

    score = 0.0

    score += row["全国勝率"] * 10

    score += (
        row["全国2連率"] * 0.25
    )

    score += (
        row["当地勝率"] * 5
    )

    score += (
        row["モーター2連率"] * 0.12
    )

    st_time = row["平均ST"]

    if st_time > 0:

        if st_time <= 0.12:
            score += 12

        elif st_time <= 0.15:
            score += 8

        elif st_time <= 0.18:
            score += 4

        elif st_time >= 0.22:
            score -= 4

    score += row["コース適性"]

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

    return score


st.title(
    "🚤 やっちゃんの競艇AI予想 PRO"
)

st.write(
    "全国24場対応の競艇予想支援アプリです。"
)

st.warning(
    "⚠️ 非公式APIを利用しています。"
    "最新情報は必ず公式BOATRACEで確認してください。"
)

st.subheader("📅 レースを選択")

col1, col2, col3 = st.columns(3)

with col1:

    target_date = st.date_input(
        "開催日",
        value=date.today(),
        min_value=date(2026, 1, 1),
    )

with col2:

    stadium_name = st.selectbox(
        "競艇場",
        list(STADIUMS.values()),
    )

with col3:

    race_number = st.selectbox(
        "レース",
        list(range(1, 13)),
        format_func=lambda x:
        f"{
