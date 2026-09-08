import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# =========================================================
# 基本設定
# =========================================================

st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO++",
    page_icon="🚤",
    layout="wide"
)

st.title("🚤 やっちゃんの競艇AI予想 PRO++")
st.caption("場・コース・決まり手・展示・風波・バックテスト対応版")

# 元々動いていたAPIをそのまま使用
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


# =========================================================
# 共通関数
# =========================================================

def num(x, default=0.0):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except:
        return default


def safe_int(x, default=0):
    try:
        if x is None or x == "":
            return default
        return int(float(x))
    except:
        return default


def ymd(d):
    return d.strftime("%Y%m%d")


# =========================================================
# API取得
# =========================================================

@st.cache_data(ttl=180)
def get_data(d):
    """
    元コードと同じAPI構造。
    エラー時はNoneを返してアプリを落とさない。
    """
    year = d.strftime("%Y")
    url = f"{API}/{year}/{ymd(d)}.json"

    try:
        r = requests.get(url, timeout=15)

        if r.status_code != 200:
            return None

        return r.json()

    except Exception:
        return None


def get_race(data, stadium, race_no):
    try:
        return data["programs"]["stadiums"][str(stadium)]["races"][str(race_no)]
    except:
        return None


# =========================================================
# 再帰的に値を探す
# 風・波などがAPI内に存在する場合だけ取得
# =========================================================

def find_key(obj, keys):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() in keys:
                return v

        for v in obj.values():
            result = find_key(v, keys)
            if result is not None:
                return result

    elif isinstance(obj, list):
        for v in obj:
            result = find_key(v, keys)
            if result is not None:
                return result

    return None


def extract_weather(race):
    """
    APIの構造が多少違っても落ちないようにする。
    データが無ければ0。
    """

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
# コース別成績
# =========================================================

@st.cache_data(ttl=600)
def get_course_stats(target_date, days=60):

    stats = {}

    for i in range(1, days + 1):

        d = target_date - timedelta(days=i)
        data = get_data(d)

        if not data:
            continue

        try:
            stadiums = data["programs"]["stadiums"]
        except:
            continue

        for stadium_no, stadium_data in stadiums.items():

            races = stadium_data.get("races", {})

            for race in races.values():

                result = race.get("result", {})
                racers = result.get("racers", [])

                for racer in racers:

                    player_no = str(
                        racer.get("player_number")
                        or racer.get("racer_number")
                        or ""
                    )

                    course = safe_int(
                        racer.get("course_number")
                        or racer.get("course")
                    )

                    place = safe_int(
                        racer.get("place_number")
                        or racer.get("rank")
                    )

                    if not player_no or course <= 0:
                        continue

                    key = (player_no, course)

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
# 場×コース成績
# =========================================================

@st.cache_data(ttl=600)
def get_stadium_course_stats(target_date, days=60):

    stats = {}

    for i in range(1, days + 1):

        d = target_date - timedelta(days=i)
        data = get_data(d)

        if not data:
            continue

        try:
            stadiums = data["programs"]["stadiums"]
        except:
            continue

        for stadium_no, stadium_data in stadiums.items():

            races = stadium_data.get("races", {})

            for race in races.values():

                result = race.get("result", {})
                racers = result.get("racers", [])

                for racer in racers:

                    course = safe_int(
                        racer.get("course_number")
                        or racer.get("course")
                    )

                    place = safe_int(
                        racer.get("place_number")
                        or racer.get("rank")
                    )

                    if course <= 0:
                        continue

                    key = (str(stadium_no), course)

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
# 決まり手統計
# =========================================================

@st.cache_data(ttl=600)
def get_technique_stats(target_date, days=60):

    stats = {}

    for i in range(1, days + 1):

        d = target_date - timedelta(days=i)
        data = get_data(d)

        if not data:
            continue

        try:
            stadiums = data["programs"]["stadiums"]
        except:
            continue

        for stadium_data in stadiums.values():

            for race in stadium_data.get("races", {}).values():

                result = race.get("result", {})
                racers = result.get("racers", [])

                for racer in racers:

                    player_no = str(
                        racer.get("player_number")
                        or racer.get("racer_number")
                        or ""
                    )

                    technique = safe_int(
                        racer.get("technique_number")
                        or racer.get("technique")
                    )

                    if not player_no or technique <= 0:
                        continue

                    key = (player_no, technique)

                    stats[key] = stats.get(key, 0) + 1

    return stats


# =========================================================
# 場×決まり手
# =========================================================

@st.cache_data(ttl=600)
def get_stadium_technique_stats(target_date, days=60):

    stats = {}

    for i in range(1, days + 1):

        d = target_date - timedelta(days=i)
        data = get_data(d)

        if not data:
            continue

        try:
            stadiums = data["programs"]["stadiums"]
        except:
            continue

        for stadium_no, stadium_data in stadiums.items():

            for race in stadium_data.get("races", {}).values():

                result = race.get("result", {})
                racers = result.get("racers", [])

                for racer in racers:

                    technique = safe_int(
                        racer.get("technique_number")
                        or racer.get("technique")
                    )

                    place = safe_int(
                        racer.get("place_number")
                        or racer.get("rank")
                    )

                    if technique <= 0:
                        continue

                    key = (str(stadium_no), technique)

                    if key not in stats:
                        stats[key] = {
                            "count": 0,
                            "wins": 0
                        }

                    stats[key]["count"] += 1

                    if place == 1:
                        stats[key]["wins"] += 1

    return stats


# =========================================================
# レース表作成
# =========================================================

def make_table(race):

    racers = race.get("racers", [])
    previews = race.get("preview", {}).get("racers", [])

    preview_map = {}

    for p in previews:

        number = str(
            p.get("player_number")
            or p.get("racer_number")
            or ""
        )

        if number:
            preview_map[number] = p

    rows = []

    for r in racers:

        player_no = str(
            r.get("player_number")
            or r.get("racer_number")
            or ""
        )

        p = preview_map.get(player_no, {})

        row = {
            "枠": safe_int(
                r.get("course_number")
                or r.get("course")
            ),
            "選手名": (
                r.get("name")
                or r.get("racer_name")
                or "不明"
            ),
            "選手番号": player_no,
            "級別": r.get("class", ""),
            "全国勝率": num(
                r.get("national_win_rate")
                or r.get("win_rate")
            ),
            "全国2連率": num(
                r.get("national_2_rate")
                or r.get("second_rate")
            ),
            "当地勝率": num(
                r.get("local_win_rate")
            ),
            "モーター2連率": num(
                r.get("motor_2_rate")
                or r.get("motor_second_rate")
            ),
            "平均ST": num(
                r.get("average_st")
                or r.get("st")
            ),
            "展示タイム": num(
                p.get("exhibition_time")
                or p.get("exhibition")
                or r.get("exhibition_time")
            )
        }

        rows.append(row)

    return pd.DataFrame(rows)


# =========================================================
# コース成績追加
# =========================================================

def add_course_stats(df, stats):

    df = df.copy()

    rates = []
    starts = []

    for _, row in df.iterrows():

        key = (
            str(row["選手番号"]),
            int(row["枠"])
        )

        s = stats.get(key, {})

        n = s.get("starts", 0)
        w = s.get("wins", 0)

        starts.append(n)

        if n > 0:
            rates.append(w / n * 100)
        else:
            rates.append(0)

    df["コース1着率"] = rates
    df["コース出走数"] = starts

    return df


# =========================================================
# 場×コース成績追加
# =========================================================

def add_stadium_course_stats(df, stats, stadium):

    df = df.copy()

    rates = []

    for _, row in df.iterrows():

        key = (
            str(stadium),
            int(row["枠"])
        )

        s = stats.get(key, {})

        starts = s.get("starts", 0)
        wins = s.get("wins", 0)

        if starts > 0:
            rates.append(wins / starts * 100)
        else:
            rates.append(0)

    df["場×コース1着率"] = rates

    return df


# =========================================================
# 決まり手追加
# =========================================================

def add_technique_stats(df, stats):

    df = df.copy()

    best_names = []
    best_counts = []

    for _, row in df.iterrows():

        player_no = str(row["選手番号"])

        candidates = []

        for technique_no, technique_name in TECHNIQUES.items():

            count = stats.get(
                (player_no, technique_no),
                0
            )

            candidates.append(
                (count, technique_name)
            )

        candidates.sort(reverse=True)

        best_counts.append(candidates[0][0])
        best_names.append(candidates[0][1])

    df["得意決まり手"] = best_names
    df["決まり手回数"] = best_counts

    return df


# =========================================================
# 風・波による補正
# 控えめな補正にして過学習を防止
# =========================================================

def weather_bonus(row, wind, wave):

    bonus = 0

    lane = safe_int(row["枠"])

    # データが無い場合は完全に無補正
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
# 決まり手ボーナス
# =========================================================

def technique_bonus(row):

    lane = safe_int(row["枠"])
    tech = row["得意決まり手"]

    bonus = 0

    if lane == 1 and tech == "逃げ":
        bonus += 4

    elif lane == 2 and tech == "差し":
        bonus += 3

    elif lane == 3 and tech in ["まくり", "まくり差し"]:
        bonus += 3

    elif lane == 4 and tech in ["まくり", "まくり差し"]:
        bonus += 3

    elif lane in [5, 6] and tech == "まくり差し":
        bonus += 2

    return bonus


# =========================================================
# AIスコア
# =========================================================

def calculate_score(row, stadium, wind=0, wave=0):

    score = 0

    # 基本能力
    score += num(row["全国勝率"]) * 10
    score += num(row["全国2連率"]) * 0.25
    score += num(row["当地勝率"]) * 5
    score += num(row["モーター2連率"]) * 0.12

    # ST
    st_value = num(row["平均ST"])

    if st_value > 0:

        if st_value <= 0.12:
            score += 12
        elif st_value <= 0.15:
            score += 8
        elif st_value <= 0.18:
            score += 4
        elif st_value >= 0.22:
            score -= 4

    # コース
    lane = safe_int(row["枠"])

    lane_bonus = {
        1: 20,
        2: 8,
        3: 6,
        4: 7,
        5: 2,
        6: 0
    }

    score += lane_bonus.get(lane, 0)

    # 選手×コース
    course_rate = num(row["コース1着率"])

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

    # 場×コース
    stadium_rate = num(row["場×コース1着率"])

    if stadium_rate >= 50:
        score += 7
    elif stadium_rate >= 40:
        score += 5
    elif stadium_rate >= 30:
        score += 3
    elif stadium_rate > 0:
        score += 1

    # 決まり手
    score += technique_bonus(row)

    # 展示
    exhibition = num(row["展示タイム"])

    if exhibition > 0:

        if exhibition <= 6.70:
            score += 6
        elif exhibition <= 6.75:
            score += 4
        elif exhibition <= 6.80:
            score += 2
        elif exhibition >= 6.90:
            score -= 2

    # 風波
    score += weather_bonus(
        row,
        wind,
        wave
    )

    return round(score, 2)


# =========================================================
# 実際の着順を取得
# =========================================================

def get_actual_order(race):

    result = race.get("result", {})
    racers = result.get("racers", [])

    order = []

    for r in racers:

        place = safe_int(
            r.get("place_number")
            or r.get("rank")
        )

        course = safe_int(
            r.get("course_number")
            or r.get("course")
        )

        if place > 0 and course > 0:
            order.append(
                (place, course)
            )

    order.sort()

    return [x[1] for x in order]


# =========================================================
# バックテスト
# =========================================================

@st.cache_data(ttl=1800)
def run_backtest(target_date, stadium, days=30):

    results = []

    # 各日について、その日より前のデータだけで予想
    for day_offset in range(1, days + 1):

        d = target_date - timedelta(days=day_offset)

        data = get_data(d)

        if not data:
            continue

        # 過去側の統計
        course_stats = get_course_stats(
            d,
            days=30
        )

        stadium_course_stats = get_stadium_course_stats(
            d,
            days=30
        )

        technique_stats = get_technique_stats(
            d,
            days=30
        )

        try:
            stadium_data = data["programs"]["stadiums"][
                str(stadium)
            ]
        except:
            continue

        for race_no, race in stadium_data.get(
            "races",
            {}
        ).items():

            try:
                race_no_int = int(race_no)
            except:
                continue

            df = make_table(race)

            if df.empty:
                continue

            actual = get_actual_order(race)

            if len(actual) < 3:
                continue

            df = add_course_stats(
                df,
                course_stats
            )

            df = add_stadium_course_stats(
                df,
                stadium_course_stats,
                stadium
            )

            df = add_technique_stats(
                df,
                technique_stats
            )

            weather = extract_weather(race)

            df["AIスコア"] = df.apply(
                lambda r: calculate_score(
                    r,
                    stadium,
                    weather["wind"],
                    weather["wave"]
                ),
                axis=1
            )

            df = df.sort_values(
                "AIスコア",
                ascending=False
            )

            prediction = df["枠"].tolist()

            top3 = prediction[:3]

            if len(top3) < 3:
                continue

            first_hit = top3[0] == actual[0]

            trifecta_hit = (
                top3[0] == actual[0]
                and top3[1] == actual[1]
                and top3[2] == actual[2]
            )

            exacta_hit = (
                top3[0] == actual[0]
                and top3[1] == actual[1]
            )

            results.append({
                "日付": d.strftime("%Y-%m-%d"),
                "レース": race_no_int,
                "AI1位": top3[0],
                "実際1着": actual[0],
                "1着的中": first_hit,
                "2連単的中": exacta_hit,
                "3連単的中": trifecta_hit
            })

    if not results:
        return pd.DataFrame()

    return pd.DataFrame(results)


# =========================================================
# UI
# =========================================================

st.sidebar.header("🎯 レース設定")

target_date = st.sidebar.
