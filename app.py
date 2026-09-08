import streamlit as st
import requests
import pandas as pd
from datetime import date, timedelta
from collections import defaultdict


# =========================================================
# 設定
# =========================================================

st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO++",
    page_icon="🚤",
    layout="wide"
)


# =========================================================
# API
# =========================================================
# 現在公開されている旧API群を利用。
# 将来的には boatraceopenapi/api への移行を推奨。

PROGRAM_API = "https://boatraceopenapi.github.io/programs/v3"
RESULT_API = "https://boatraceopenapi.github.io/results/v3"
PREVIEW_API = "https://boatraceopenapi.github.io/previews/v3"


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


TECHNIQUES = {
    1: "逃げ",
    2: "差し",
    3: "まくり",
    4: "まくり差し",
    5: "抜き",
    6: "恵まれ"
}


# =========================================================
# 基本関数
# =========================================================

def num(x):

    try:
        return float(x)

    except:
        return 0.0


def safe_int(x):

    try:
        return int(x)

    except:
        return 0


def get_url(base, d):

    return (
        base
        + "/"
        + d.strftime("%Y")
        + "/"
        + d.strftime("%Y%m%d")
        + ".json"
    )


# =========================================================
# API取得
# =========================================================

@st.cache_data(ttl=180)
def get_program_data(d):

    url = get_url(
        PROGRAM_API,
        d
    )

    r = requests.get(
        url,
        timeout=20
    )

    r.raise_for_status()

    return r.json()


@st.cache_data(ttl=180)
def get_result_data(d):

    url = get_url(
        RESULT_API,
        d
    )

    r = requests.get(
        url,
        timeout=20
    )

    r.raise_for_status()

    return r.json()


@st.cache_data(ttl=180)
def get_preview_data(d):

    url = get_url(
        PREVIEW_API,
        d
    )

    r = requests.get(
        url,
        timeout=20
    )

    r.raise_for_status()

    return r.json()


# =========================================================
# JSONから会場取得
# =========================================================

def get_stadiums(data):

    return (
        data
        .get("programs", {})
        .get("stadiums", {})
    )


def get_result_stadiums(data):

    return (
        data
        .get("results", {})
        .get("stadiums", {})
    )


# =========================================================
# レース取得
# =========================================================

def get_race(
    data,
    stadium_no,
    race_no
):

    stadiums = get_stadiums(
        data
    )

    stadium = stadiums.get(
        str(stadium_no)
    )

    if not stadium:
        return None

    races = stadium.get(
        "races",
        {}
    )

    return races.get(
        str(race_no)
    )


def get_result_race(
    data,
    stadium_no,
    race_no
):

    stadiums = get_result_stadiums(
        data
    )

    stadium = stadiums.get(
        str(stadium_no)
    )

    if not stadium:
        return None

    races = stadium.get(
        "races",
        {}
    )

    return races.get(
        str(race_no)
    )


# =========================================================
# 再帰的に天候データを探す
# =========================================================

def recursive_find(
    obj,
    keys
):

    if isinstance(obj, dict):

        for key in keys:

            if key in obj:
                return obj[key]

        for value in obj.values():

            found = recursive_find(
                value,
                keys
            )

            if found is not None:
                return found

    elif isinstance(obj, list):

        for value in obj:

            found = recursive_find(
                value,
                keys
            )

            if found is not None:
                return found

    return None


def extract_weather(race):

    if not race:
        return {
            "天候": "",
            "風速": 0,
            "風向": "",
            "波高": 0
        }

    weather = recursive_find(
        race,
        [
            "weather",
            "before_weather"
        ]
    )

    wind = recursive_find(
        race,
        [
            "wind",
            "before_wind",
            "wind_speed"
        ]
    )

    wind_direction = recursive_find(
        race,
        [
            "windDirect",
            "before_windDirect",
            "wind_direction"
        ]
    )

    wave = recursive_find(
        race,
        [
            "wave",
            "before_wave",
            "wave_height"
        ]
    )

    return {

        "天候": (
            str(weather)
            if weather is not None
            else ""
        ),

        "風速": num(wind),

        "風向": (
            str(wind_direction)
            if wind_direction is not None
            else ""
        ),

        "波高": num(wave)
    }


# =========================================================
# 出走表
# =========================================================

def make_table(race):

    racers = race.get(
        "racers",
        {}
    )

    preview = (
        race
        .get("preview", {})
        .get("racers", {})
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

    return pd.DataFrame(
        rows
    )


# =========================================================
# 過去日
# =========================================================

def past_dates(
    target_date,
    days
):

    result = []

    for i in range(
        1,
        days + 1
    ):

        d = target_date - timedelta(
            days=i
        )

        if d < date(2026, 1, 1):
            break

        result.append(d)

    return result


# =========================================================
# 選手×コース
# =========================================================

@st.cache_data(ttl=900)
def build_player_course_stats(
    target_date,
    days=90
):

    stats = defaultdict(
        lambda: {
            "出走": 0,
            "1着": 0,
            "2着": 0,
            "3着": 0
        }
    )

    for d in past_dates(
        target_date,
        days
    ):

        try:
            data = get_result_data(d)

        except:
            continue

        stadiums = get_result_stadiums(
            data
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

                racers = result.get(
                    "racers",
                    {}
                )

                for racer in racers.values():

                    player = str(
                        racer.get(
                            "number",
                            ""
                        )
                    )

                    course = safe_int(
                        racer.get(
                            "course_number"
                        )
                    )

                    place = safe_int(
                        racer.get(
                            "place_number"
                        )
                    )

                    if (
                        not player
                        or course < 1
                        or course > 6
                    ):
                        continue

                    key = (
                        player,
                        course
                    )

                    stats[key][
                        "出走"
                    ] += 1

                    if place == 1:
                        stats[key]["1着"] += 1

                    elif place == 2:
                        stats[key]["2着"] += 1

                    elif place == 3:
                        stats[key]["3着"] += 1

    return dict(stats)


# =========================================================
# 会場×コース
# =========================================================

@st.cache_data(ttl=900)
def build_stadium_course_stats(
    target_date,
    stadium_no,
    days=90
):

    stats = defaultdict(
        lambda: {
            "出走": 0,
            "1着": 0,
            "2着": 0,
            "3着": 0
        }
    )

    for d in past_dates(
        target_date,
        days
    ):

        try:
            data = get_result_data(d)

        except:
            continue

        stadiums = get_result_stadiums(
            data
        )

        stadium = stadiums.get(
            str(stadium_no)
        )

        if not stadium:
            continue

        races = stadium.get(
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
                {}
            )

            for racer in racers.values():

                course = safe_int(
                    racer.get(
                        "course_number"
                    )
                )

                place = safe_int(
                    racer.get(
                        "place_number"
                    )
                )

                if course < 1 or course > 6:
                    continue

                stats[course][
                    "出走"
                ] += 1

                if place == 1:
                    stats[course]["1着"] += 1

                elif place == 2:
                    stats[course]["2着"] += 1

                elif place == 3:
                    stats[course]["3着"] += 1

    return dict(stats)


# =========================================================
# 会場×決まり手
# =========================================================

@st.cache_data(ttl=900)
def build_stadium_technique_stats(
    target_date,
    stadium_no,
    days=90
):

    stats = defaultdict(int)

    for d in past_dates(
        target_date,
        days
    ):

        try:
            data = get_result_data(d)

        except:
            continue

        stadiums = get_result_stadiums(
            data
        )

        stadium = stadiums.get(
            str(stadium_no)
        )

        if not stadium:
            continue

        races = stadium.get(
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
                {}
            )

            for racer in racers.values():

                technique = safe_int(
                    racer.get(
                        "technique_number"
                    )
                )

                if technique in TECHNIQUES:

                    stats[
                        TECHNIQUES[
                            technique
                        ]
                    ] += 1

    return dict(stats)


# =========================================================
# 決まり手×選手
# =========================================================

@st.cache_data(ttl=900)
def build_player_technique_stats(
    target_date,
    days=90
):

    stats = defaultdict(int)

    for d in past_dates(
        target_date,
        days
    ):

        try:
            data = get_result_data(d)

        except:
            continue

        stadiums = get_result_stadiums(
            data
        )

        for stadium in stadiums.values():

            for race in stadium.get(
                "races",
                {}
            ).values():

                racers = (
                    race
                    .get("result", {})
                    .get("racers", {})
                )

                for racer in racers.values():

                    player = str(
                        racer.get(
                            "number",
                            ""
                        )
                    )

                    technique = safe_int(
                        racer.get(
                            "technique_number"
                        )
                    )

                    if (
                        player
                        and technique in TECHNIQUES
                    ):

                        stats[
                            (
                                player,
                                technique
                            )
                        ] += 1

    return dict(stats)


# =========================================================
# 天候×コース
# =========================================================

@st.cache_data(ttl=900)
def build_weather_course_stats(
    target_date,
    stadium_no,
    days=90
):

    stats = defaultdict(
        lambda: {
            "出走": 0,
            "1着": 0
        }
    )

    for d in past_dates(
        target_date,
        days
    ):

        try:
            data = get_result_data(d)

        except:
            continue

        stadiums = get_result_stadiums(
            data
        )

        stadium = stadiums.get(
            str(stadium_no)
        )

        if not stadium:
            continue

        for race in stadium.get(
            "races",
            {}
        ).values():

            weather = extract_weather(
                race
            )

            wind = weather[
                "風速"
            ]

            wave = weather[
                "波高"
            ]

            # 風・波の条件をグループ化
            if wind >= 5:
                condition = "強風"

            elif wind >= 3:
                condition = "中風"

            elif wind > 0:
                condition = "弱風"

            else:
                condition = "無風"

            if wave >= 5:
                condition += "_高波"

            elif wave >= 3:
                condition += "_中波"

            else:
                condition += "_低波"

            racers = (
                race
                .get("result", {})
                .get("racers", {})
            )

            for racer in racers.values():

                course = safe_int(
                    racer.get(
                        "course_number"
                    )
                )

                place = safe_int(
                    racer.get(
                        "place_number"
                    )
                )

                if course < 1 or course > 6:
                    continue

                key = (
                    condition,
                    course
                )

                stats[key][
                    "出走"
                ] += 1

                if place == 1:
                    stats[key][
                        "1着"
                    ] += 1

    return dict(stats)


# =========================================================
# 統計追加
# =========================================================

def add_player_course(
    df,
    stats
):

    win_rates = []
    second_rates = []
    counts = []

    for _, row in df.iterrows():

        key = (
            str(row["選手番号"]),
            int(row["枠"])
        )

        item = stats.get(
            key,
            {}
        )

        n = item.get(
            "出走",
            0
        )

        win = item.get(
            "1着",
            0
        )

        second = item.get(
            "2着",
            0
        )

        win_rate = (
            win / n * 100
            if n
            else 0
        )

        second_rate = (
            (win + second)
            / n
            * 100
            if n
            else 0
        )

        win_rates.append(
            round(
                win_rate,
                1
            )
        )

        second_rates.append(
            round(
                second_rate,
                1
            )
        )

        counts.append(
            n
        )

    df[
        "選手コース1着率"
    ] = win_rates

    df[
        "選手コース2連率"
    ] = second_rates

    df[
        "選手コース出走数"
    ] = counts

    return df


def add_stadium_course(
    df,
    stats
):

    win_rates = []
    second_rates = []
    counts = []

    for _, row in df.iterrows():

        item = stats.get(
            int(row["枠"]),
            {}
        )

        n = item.get(
            "出走",
            0
        )

        win = item.get(
            "1着",
            0
        )

        second = item.get(
            "2着",
            0
        )

        win_rate = (
            win / n * 100
            if n
            else 0
        )

        second_rate = (
            (win + second)
            / n
            * 100
            if n
            else 0
        )

        win_rates.append(
            round(
                win_rate,
                1
            )
        )

        second_rates.append(
            round(
                second_rate,
                1
            )
        )

        counts.append(
            n
        )

    df[
        "会場コース1着率"
    ] = win_rates

    df[
        "会場コース2連率"
    ] = second_rates

    df[
        "会場コース出走数"
    ] = counts

    return df


# =========================================================
# 得意決まり手
# =========================================================

def add_technique(
    df,
    stats
):

    names = []
    counts = []

    for _, row in df.iterrows():

        player = str(
            row["選手番号"]
        )

        best_name = "なし"
        best_count = 0

        for number, name in TECHNIQUES.items():

            count = stats.get(
                (
                    player,
                    number
                ),
                0
            )

            if count > best_count:

                best_count = count
                best_name = name

        names.append(
            best_name
        )

        counts.append(
            best_count
        )

    df[
        "得意決まり手"
    ] = names

    df[
        "決まり手回数"
    ] = counts

    return df


# =========================================================
# 天候補正
# =======================================
