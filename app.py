import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# =========================================================
# ページ設定
# =========================================================

st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO++",
    page_icon="🚤",
    layout="wide"
)

st.title("🚤 やっちゃんの競艇AI予想 PRO++")
st.caption("場・コース・決まり手・展示・風・波・バックテスト対応")


# =========================================================
# API
# =========================================================

API = "https://boatraceopenapi.github.io/api/v1"


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
# 決まり手
# =========================================================

TECHNIQUES = {
    1: "逃げ",
    2: "差し",
    3: "まくり",
    4: "まくり差し",
    5: "抜き",
    6: "恵まれ"
}


# =========================================================
# 数値変換
# =========================================================

def num(x, default=0.0):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default


def safe_int(x, default=0):
    try:
        if x is None or x == "":
            return default
        return int(float(x))
    except Exception:
        return default


def ymd(d):
    return d.strftime("%Y%m%d")


# =========================================================
# APIデータ取得
# =========================================================

@st.cache_data(ttl=180)
def get_data(d):

    year = d.strftime("%Y")
    url = f"{API}/{year}/{ymd(d)}.json"

    try:
        response = requests.get(
            url,
            timeout=15
        )

        if response.status_code != 200:
            return None

        return response.json()

    except Exception:
        return None


# =========================================================
# レース取得
# =========================================================

def get_race(data, stadium, race_no):

    try:
        return data[
            "programs"
        ][
            "stadiums"
        ][
            str(stadium)
        ][
            "races"
        ][
            str(race_no)
        ]

    except Exception:
        return None


# =========================================================
# 再帰検索
# =========================================================

def find_key(obj, keys):

    if isinstance(obj, dict):

        for key, value in obj.items():

            if str(key).lower() in keys:
                return value

        for value in obj.values():

            result = find_key(
                value,
                keys
            )

            if result is not None:
                return result

    elif isinstance(obj, list):

        for value in obj:

            result = find_key(
                value,
                keys
            )

            if result is not None:
                return result

    return None


# =========================================================
# 天候情報
# =========================================================

def extract_weather(race):

    if not race:
        return {
            "wind": 0.0,
            "wave": 0.0,
            "wind_direction": 0
        }

    wind = find_key(
        race,
        {
            "wind",
            "before_wind",
            "wind_speed"
        }
    )

    wave = find_key(
        race,
        {
            "wave",
            "before_wave",
            "wave_height"
        }
    )

    direction = find_key(
        race,
        {
            "winddirect",
            "before_winddirect",
            "wind_direction"
        }
    )

    return {
        "wind": num(wind),
        "wave": num(wave),
        "wind_direction": safe_int(direction)
    }


# =========================================================
# 選手×コース統計
# =========================================================

@st.cache_data(ttl=600)
def get_course_stats(
    target_date,
    days=60
):

    stats = {}

    for i in range(1, days + 1):

        d = target_date - timedelta(days=i)

        data = get_data(d)

        if not data:
            continue

        try:
            stadiums = data[
                "programs"
            ][
                "stadiums"
            ]
        except Exception:
            continue

        for stadium_data in stadiums.values():

            races = stadium_data.get(
                "races",
                {}
            )

            for race in races.values():

                result = race.get(
                    "result",
                    {}
                )

                racers = result.get(
                    "racers",
                    []
                )

                for racer in racers:

                    player_no = str(
                        racer.get(
                            "player_number"
                        )
                        or racer.get(
                            "racer_number"
                        )
                        or ""
                    )

                    course = safe_int(
                        racer.get(
                            "course_number"
                        )
                        or racer.get(
                            "course"
                        )
                    )

                    place = safe_int(
                        racer.get(
                            "place_number"
                        )
                        or racer.get(
                            "rank"
                        )
                    )

                    if not player_no:
                        continue

                    if course <= 0:
                        continue

                    key = (
                        player_no,
                        course
                    )

                    if key not in stats:

                        stats[key] = {
                            "starts": 0,
                            "wins": 0
                        }

                    stats[key]["starts"] += 1

                    if place == 1:
                        stats[key]["wins"] += 1

    return stats


# =========================================================
# 場×コース統計
# =========================================================

@st.cache_data(ttl=600)
def get_stadium_course_stats(
    target_date,
    days=60
):

    stats = {}

    for i in range(1, days + 1):

        d = target_date - timedelta(days=i)

        data = get_data(d)

        if not data:
            continue

        try:
            stadiums = data[
                "programs"
            ][
                "stadiums"
            ]
        except Exception:
            continue

        for stadium_no, stadium_data in stadiums.items():

            races = stadium_data.get(
                "races",
                {}
            )

            for race in races.values():

                result = race.get(
                    "result",
                    {}
                )

                racers = result.get(
                    "racers",
                    []
                )

                for racer in racers:

                    course = safe_int(
                        racer.get(
                            "course_number"
                        )
                        or racer.get(
                            "course"
                        )
                    )

                    place = safe_int(
                        racer.get(
                            "place_number"
                        )
                        or racer.get(
                            "rank"
                        )
                    )

                    if course <= 0:
                        continue

                    key = (
                        str(stadium_no),
                        course
                    )

                    if key not in stats:

                        stats[key] = {
                            "starts": 0,
                            "wins": 0
                        }

                    stats[key]["starts"] += 1

                    if place == 1:
                        stats[key]["wins"] += 1

    return stats


# =========================================================
# 選手×決まり手
# =========================================================

@st.cache_data(ttl=600)
def get_technique_stats(
    target_date,
    days=60
):

    stats = {}

    for i in range(1, days + 1):

        d = target_date - timedelta(days=i)

        data = get_data(d)

        if not data:
            continue

        try:
            stadiums = data[
                "programs"
            ][
                "stadiums"
            ]
        except Exception:
            continue

        for stadium_data in stadiums.values():

            for race in stadium_data.get(
                "races",
                {}
            ).values():

                result = race.get(
                    "result",
                    {}
                )

                racers = result.get(
                    "racers",
                    []
                )

                for racer in racers:

                    player_no = str(
                        racer.get(
                            "player_number"
                        )
                        or racer.get(
                            "racer_number"
                        )
                        or ""
                    )

                    technique = safe_int(
                        racer.get(
                            "technique_number"
                        )
                        or racer.get(
                            "technique"
                        )
                    )

                    if not player_no:
                        continue

                    if technique <= 0:
                        continue

                    key = (
                        player_no,
                        technique
                    )

                    stats[key] = (
                        stats.get(key, 0) + 1
                    )

    return stats


# =========================================================
# レース表作成
# =========================================================

def make_table(race):

    racers = race.get(
        "racers",
        []
    )

    preview = race.get(
        "preview",
        {}
    )

    previews = preview.get(
        "racers",
        []
    )

    preview_map = {}

    for p in previews:

        number = str(
            p.get(
                "player_number"
            )
            or p.get(
                "racer_number"
            )
            or ""
        )

        if number:
            preview_map[number] = p

    rows = []

    for racer in racers:

        player_no = str(
            racer.get(
                "player_number"
            )
            or racer.get(
                "racer_number"
            )
            or ""
        )

        p = preview_map.get(
            player_no,
            {}
        )

        row = {

            "枠": safe_int(
                racer.get(
                    "course_number"
                )
                or racer.get(
                    "course"
                )
            ),

            "選手名": (
                racer.get("name")
                or racer.get("racer_name")
                or "不明"
            ),

            "選手番号": player_no,

            "級別": (
                racer.get("class")
                or ""
            ),

            "全国勝率": num(
                racer.get(
                    "national_win_rate"
                )
                or racer.get(
                    "win_rate"
                )
            ),

            "全国2連率": num(
                racer.get(
                    "national_2_rate"
                )
                or racer.get(
                    "second_rate"
                )
            ),

            "当地勝率": num(
                racer.get(
                    "local_win_rate"
                )
            ),

            "モーター2連率": num(
                racer.get(
                    "motor_2_rate"
                )
                or racer.get(
                    "motor_second_rate"
                )
            ),

            "平均ST": num(
                racer.get(
                    "average_st"
                )
                or racer.get(
                    "st"
                )
            ),

            "展示タイム": num(
                p.get(
                    "exhibition_time"
                )
                or p.get(
                    "exhibition"
                )
                or racer.get(
                    "exhibition_time"
                )
            )
        }

        rows.append(row)

    return pd.DataFrame(rows)


# =========================================================
# コース統計追加
# =========================================================

def add_course_stats(
    df,
    stats
):

    df = df.copy()

    rates = []
    starts = []

    for _, row in df.iterrows():

        key = (
            str(row["選手番号"]),
            int(row["枠"])
        )

        item = stats.get(
            key,
            {}
        )

        start_count = item.get(
            "starts",
            0
        )

        win_count = item.get(
            "wins",
            0
        )

        starts.append(
            start_count
        )

        if start_count > 0:

            rates.append(
                win_count
                / start_count
                * 100
            )

        else:
            rates.append(0)

    df["コース1着率"] = rates
    df["コース出走数"] = starts

    return df


# =========================================================
# 場×コース統計追加
# =========================================================

def add_stadium_course_stats(
    df,
    stats,
    stadium
):

    df = df.copy()

    rates = []

    for _, row in df.iterrows():

        key = (
            str(stadium),
            int(row["枠"])
        )

        item = stats.get(
            key,
            {}
        )

        starts = item.get(
            "starts",
            0
        )

        wins = item.get(
            "wins",
            0
        )

        if starts > 0:

            rates.append(
                wins
                / starts
                * 100
            )

        else:
            rates.append(0)

    df["場×コース1着率"] = rates

    return df


# =========================================================
# 決まり手統計追加
# =========================================================

def add_technique_stats(
    df,
    stats
):

    df = df.copy()

    best_names = []
    best_counts = []

    for _, row in df.iterrows():

        player_no = str(
            row["選手番号"]
        )

        candidates = []

        for technique_no, technique_name in TECHNIQUES.items():

            count = stats.get(
                (
                    player_no,
                    technique_no
                ),
                0
            )

            candidates.append(
                (
                    count,
                    technique_name
                )
            )

        candidates.sort(
            reverse=True
        )

        best_counts.append(
            candidates[0][0]
        )

        best_names.append(
            candidates[0][1]
        )

    df["得意決まり手"] = best_names
    df["決まり手回数"] = best_counts

    return df


# =========================================================
# 決まり手ボーナス
# =========================================================

def technique_bonus(row):

    lane = safe_int(
        row["枠"]
    )

    technique = row[
        "得意決まり手"
    ]

    bonus = 0

    if lane == 1:

        if technique == "逃げ":
            bonus += 4

    elif lane == 2:

        if technique == "差し":
            bonus += 3

    elif lane == 3:

        if technique in [
            "まくり",
            "まくり差し"
        ]:
            bonus += 3

    elif lane == 4:

        if technique in [
            "まくり",
            "まくり差し"
        ]:
            bonus += 3

    elif lane in [5, 6]:

        if technique == "まくり差し":
            bonus += 2

    return bonus


# =========================================================
# 風・波ボーナス
# =========================================================

def weather_bonus(
    row,
    wind,
    wave
):

    bonus = 0

    lane = safe_int(
        row["枠"]
    )

    # 天候データが無い場合
    if wind == 0 and wave == 0:
        return 0

    # 強風
    if wind >= 5:

        if lane == 1:
            bonus -= 1

        elif lane in [2, 3, 4]:
            bonus += 1

    # 高波
    if wave >= 5:

        if lane == 1:
            bonus -= 1

        elif lane in [2, 3]:
            bonus += 1

    return bonus


# =========================================================
# AIスコア
# =========================================================

def calculate_score(
    row,
    stadium,
    wind=0,
    wave=0
):

    score = 0

    # -----------------------------------------
    # 全国成績
    # -----------------------------------------

    score += (
        num(row["全国勝率"])
        * 10
    )

    score += (
        num(row["全国2連率"])
        * 0.25
    )

    # -----------------------------------------
    # 当地成績
    # -----------------------------------------

    score += (
        num(row["当地勝率"])
        * 5
    )

    # -----------------------------------------
    # モーター
    # -----------------------------------------

    score += (
        num(row["モーター2連率"])
        * 0.12
    )

    # -----------------------------------------
    # ST
    # -----------------------------------------

    st_value = num(
        row["平均ST"]
    )

    if st_value > 0:

        if st_value <= 0.12:
            score += 12

        elif st_value <= 0.15:
            score += 8

        elif st_value <= 0.18:
            score += 4

        elif st_value >= 0.22:
            score -= 4

    # -----------------------------------------
    # 枠
    # -----------------------------------------

    lane = safe_int(
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

    score += lane_bonus.get(
        lane,
        0
    )

    # -----------------------------------------
    # 選手×コース
    # -----------------------------------------

    course_rate = num(
        row["コース1着率"]
    )

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

    # -----------------------------------------
    # 場×コース
    # -----------------------------------------

    stadium_rate = num(
        row["場×コース1着率"]
    )

    if stadium_rate >= 50:
        score += 7

    elif stadium_rate >= 40:
        score += 5

    elif stadium_rate >= 30:
        score += 3

    elif stadium_rate > 0:
        score += 1

    # -----------------------------------------
    # 決まり手
    # -----------------------------------------

    score += technique_bonus(
        row
    )

    # -----------------------------------------
    # 展示タイム
    # -----------------------------------------

    exhibition = num(
        row["展示タイム"]
    )

    if exhibition > 0:

        if exhibition <= 6
