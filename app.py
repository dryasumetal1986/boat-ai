import streamlit as st
import requests
import pandas as pd
import numpy as np

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from itertools import permutations
from collections import defaultdict


# =========================================================
# 基本設定
# =========================================================

st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO",
    page_icon="🚤",
    layout="wide"
)

JST = ZoneInfo("Asia/Tokyo")

JCD_MAP = {
    "桐生": 1,
    "戸田": 2,
    "江戸川": 3,
    "平和島": 4,
    "多摩川": 5,
    "浜名湖": 6,
    "蒲郡": 7,
    "常滑": 8,
    "津": 9,
    "三国": 10,
    "びわこ": 11,
    "住之江": 12,
    "尼崎": 13,
    "鳴門": 14,
    "丸亀": 15,
    "児島": 16,
    "宮島": 17,
    "徳山": 18,
    "下関": 19,
    "若松": 20,
    "芦屋": 21,
    "福岡": 22,
    "唐津": 23,
    "大村": 24,
}

JCD_NAME = {v: k for k, v in JCD_MAP.items()}


# =========================================================
# API
# =========================================================

API_BASE = "https://boatraceopenapi.github.io/api/v1"


def api_url(date_obj):
    date_str = date_obj.strftime("%Y%m%d")
    year = date_obj.strftime("%Y")

    return f"{API_BASE}/{year}/{date_str}.json"


# =========================================================
# HTTP取得
# =========================================================

@st.cache_data(ttl=180)
def fetch_day(date_str):

    date_obj = datetime.strptime(
        date_str,
        "%Y-%m-%d"
    ).date()

    url = api_url(date_obj)

    try:

        r = requests.get(
            url,
            timeout=20
        )

        r.raise_for_status()

        return r.json()

    except Exception as e:

        return {
            "__error__": str(e),
            "__url__": url
        }


# =========================================================
# 1日分をレース単位に変換
# =========================================================

def extract_races(data):

    races = []

    if not isinstance(data, dict):
        return races

    if "__error__" in data:
        return races

    programs = data.get(
        "programs",
        {}
    )

    stadiums = programs.get(
        "stadiums",
        {}
    )

    for stadium_key, stadium_data in stadiums.items():

        try:
            stadium_no = int(stadium_key)
        except:
            continue

        race_dict = stadium_data.get(
            "races",
            {}
        )

        for race_key, race in race_dict.items():

            try:
                race_no = int(race_key)
            except:
                continue

            race_copy = dict(race)

            race_copy["_stadium"] = stadium_no
            race_copy["_race_no"] = race_no

            races.append(race_copy)

    return races


# =========================================================
# 全艇をDataFrameへ
# =========================================================

def race_to_rows(race):

    rows = []

    stadium = race["_stadium"]
    race_no = race["_race_no"]

    preview = race.get(
        "preview",
        {}
    )

    result = race.get(
        "result",
        {}
    )

    preview_racers = preview.get(
        "racers",
        {}
    )

    result_racers = result.get(
        "racers",
        {}
    )

    racers = race.get(
        "racers",
        {}
    )

    wind_speed = preview.get(
        "wind_speed",
        result.get("wind_speed", np.nan)
    )

    wind_direction = preview.get(
        "wind_direction_number",
        result.get("wind_direction_number", np.nan)
    )

    wave_height = preview.get(
        "wave_height",
        result.get("wave_height", np.nan)
    )

    technique = result.get(
        "technique_number",
        np.nan
    )

    for entry in range(1, 7):

        key = str(entry)

        p = racers.get(
            key,
            {}
        )

        pv = preview_racers.get(
            key,
            {}
        )

        rs = result_racers.get(
            key,
            {}
        )

        rows.append({

            "date": race.get(
                "date"
            ),

            "stadium": stadium,

            "stadium_name":
                JCD_NAME.get(
                    stadium,
                    str(stadium)
                ),

            "race_no": race_no,

            "entry":
                entry,

            "name":
                p.get(
                    "name",
                    rs.get("name", "-")
                ),

            "racer_number":
                p.get(
                    "number",
                    rs.get("number", np.nan)
                ),

            "rank_number":
                p.get(
                    "rank_number",
                    np.nan
                ),

            "national_win_rate":
                p.get(
                    "national_win_rate",
                    np.nan
                ),

            "national_top2":
                p.get(
                    "national_top_2_percent",
                    np.nan
                ),

            "national_top3":
                p.get(
                    "national_top_3_percent",
                    np.nan
                ),

            "local_win_rate":
                p.get(
                    "local_win_rate",
                    np.nan
                ),

            "local_top2":
                p.get(
                    "local_top_2_percent",
                    np.nan
                ),

            "local_top3":
                p.get(
                    "local_top_3_percent",
                    np.nan
                ),

            "avg_st":
                p.get(
                    "average_start_timing",
                    np.nan
                ),

            "motor_top2":
                p.get(
                    "motor_top_2_percent",
                    np.nan
                ),

            "motor_top3":
                p.get(
                    "motor_top_3_percent",
                    np.nan
                ),

            "boat_top2":
                p.get(
                    "boat_top_2_percent",
                    np.nan
                ),

            "boat_top3":
                p.get(
                    "boat_top_3_percent",
                    np.nan
                ),

            # 直前情報
            "course":
                pv.get(
                    "course_number",
                    entry
                ),

            "start_timing":
                pv.get(
                    "start_timing",
                    np.nan
                ),

            "exhibition_time":
                pv.get(
                    "exhibition_time",
                    np.nan
                ),

            "tilt":
                pv.get(
                    "tilt_adjustment",
                    np.nan
                ),

            "wind_speed":
                wind_speed,

            "wind_direction":
                wind_direction,

            "wave_height":
                wave_height,

            # 結果
            "finish":
                rs.get(
                    "place_number",
                    np.nan
                ),

            "result_course":
                rs.get(
                    "course_number",
                    np.nan
                ),

            "technique":
                technique
        })

    return rows


# =========================================================
# 過去データ取得
# =========================================================

@st.cache_data(ttl=3600)
def build_history(days=60):

    today = datetime.now(
        JST
    ).date()

    all_rows = []

    progress = st.progress(
        0,
        text="過去データを取得中..."
    )

    for i in range(
        1,
        days + 1
    ):

        d = today - timedelta(
            days=i
        )

        data = fetch_day(
            d.strftime("%Y-%m-%d")
        )

        if "__error__" in data:
            continue

        races = extract_races(
            data
        )

        for race in races:

            # 結果があるレースだけ
            if not race.get("result"):
                continue

            all_rows.extend(
                race_to_rows(
                    race
                )
            )

        progress.progress(
            min(
                i / days,
                1.0
            ),
            text=f"過去データ {i}/{days} 日"
        )

    progress.empty()

    df = pd.DataFrame(
        all_rows
    )

    if df.empty:
        return df

    numeric_cols = [
        "racer_number",
        "entry",
        "course",
        "finish",
        "result_course",
        "wind_speed",
        "wind_direction",
        "wave_height",
        "technique",
        "start_timing",
        "exhibition_time"
    ]

    for c in numeric_cols:

        if c in df.columns:

            df[c] = pd.to_numeric(
                df[c],
                errors="coerce"
            )

    return df


# =========================================================
# 安全な割合
# =========================================================

def rate(
    numerator,
    denominator,
    default=0.0
):

    if denominator <= 0:
        return default

    return numerator / denominator


# =========================================================
# 選手×コース成績
# =========================================================

def player_course_stats(
    history
):

    if history.empty:
        return pd.DataFrame()

    x = history.dropna(
        subset=[
            "racer_number",
            "result_course",
            "finish"
        ]
    ).copy()

    x["win"] = (
        x["finish"] == 1
    ).astype(int)

    x["top2"] = (
        x["finish"] <= 2
    ).astype(int)

    x["top3"] = (
        x["finish"] <= 3
    ).astype(int)

    stats = (
        x.groupby(
            [
                "racer_number",
                "result_course"
            ]
        )
        .agg(
            starts=("finish", "count"),
            wins=("win", "sum"),
            top2=("top2", "sum"),
            top3=("top3", "sum")
        )
        .reset_index()
    )

    stats["win_rate"] = (
        stats["wins"]
        / stats["starts"]
    )

    stats["top2_rate"] = (
        stats["top2"]
        / stats["starts"]
    )

    stats["top3_rate"] = (
        stats["top3"]
        / stats["starts"]
    )

    return stats


# =========================================================
# 会場×コース特性
# =========================================================

def venue_course_stats(
    history
):

    x = history.dropna(
        subset=[
            "stadium",
            "result_course",
            "finish"
        ]
    ).copy()

    x["win"] = (
        x["finish"] == 1
    ).astype(int)

    x["top2"] = (
        x["finish"] <= 2
    ).astype(int)

    x["top3"] = (
        x["finish"] <= 3
    ).astype(int)

    stats = (
        x.groupby(
            [
                "stadium",
                "result_course"
            ]
        )
        .agg(
            starts=("finish", "count"),
            wins=("win", "sum"),
            top2=("top2", "sum"),
            top3=("top3", "sum")
        )
        .reset_index()
    )

    stats["win_rate"] = (
        stats["wins"]
        / stats["starts"]
    )

    stats["top2_rate"] = (
        stats["top2"]
        / stats["starts"]
    )

    stats["top3_rate"] = (
        stats["top3"]
        / stats["starts"]
    )

    return stats


# =========================================================
# 選手×会場
# =========================================================

def player_venue_stats(
    history
):

    x = history.dropna(
        subset=[
            "racer_number",
            "stadium",
            "finish"
        ]
    ).copy()

    x["win"] = (
        x["finish"] == 1
    ).astype(int)

    x["top3"] = (
        x["finish"] <= 3
    ).astype(int)

    stats = (
        x.groupby(
            [
                "racer_number",
                "stadium"
            ]
        )
        .agg(
            starts=("finish", "count"),
            wins=("win", "sum"),
            top3=("top3", "sum")
        )
        .reset_index()
    )

    stats["win_rate"] = (
        stats["wins"]
        / stats["starts"]
    )

    stats["top3_rate"] = (
        stats["top3"]
        / stats["starts"]
    )

    return stats


# =========================================================
# 選手×風向
# =========================================================

def player_wind_stats(
    history
):

    x = history.dropna(
        subset=[
            "racer_number",
            "wind_direction",
            "finish"
        ]
    ).copy()

    x["win"] = (
        x["finish"] == 1
    ).astype(int)

    x["top3"] = (
        x["finish"] <= 3
    ).astype(int)

    stats = (
        x.groupby(
            [
                "racer_number",
                "wind_direction"
            ]
        )
        .agg(
            starts=("finish", "count"),
            wins=("win", "sum"),
            top3=("top3", "sum")
        )
        .reset_index()
    )

    stats["win_rate"] = (
        stats["wins"]
        / stats["starts"]
    )

    stats["top3_rate"] = (
        stats["top3"]
        / stats["starts"]
    )

    return stats


# =========================================================
# 決まり手
# =========================================================

TECHNIQUE_MAP = {

    1: "逃げ",
    2: "差し",
    3: "まくり",
    4: "まくり差し",
    5: "抜き",
    6: "恵まれ"
}


def technique_stats(
    history
):

    x = history.dropna(
        subset=[
            "racer_number",
            "technique",
            "finish"
        ]
    ).copy()

    # 1着だけを対象
    x = x[
        x["finish"] == 1
    ]

    if x.empty:
        return pd.DataFrame()

    stats = (
        x.groupby(
            [
                "racer_number",
                "technique"
            ]
        )
        .size()
        .reset_index(
            name="count"
        )
    )

    return stats


# =========================================================
# 現在のレースに特徴量を付与
# =========================================================

def add_features(
    current,
    course_stats,
    venue_stats,
    player_venue,
    player_wind,
    history
):

    df = current.copy()

    # ---------------------------------------
    # コース別選手成績
    # ---------------------------------------

    df = df.merge(
        course_stats[
            [
                "racer_number",
                "result_course",
                "starts",
                "win_rate",
                "top2_rate",
                "top3_rate"
            ]
        ],
        left_on=[
            "racer_number",
            "course"
        ],
        right_on=[
            "racer_number",
            "result_course"
        ],
        how="left",
        suffixes=(
            "",
            "_player_course"
        )
    )

    df.rename(
        columns={
            "win_rate":
                "player_course_win",
            "top2_rate":
                "player_course_top2",
            "top3_rate":
                "player_course_top3"
        },
        inplace=True
    )

    # ---------------------------------------
    # 会場×コース
    # ---------------------------------------

    df = df.merge(
        venue_stats[
            [
                "stadium",
                "result_course",
                "win_rate",
                "top2_rate",
                "top3_rate"
            ]
        ],
        left_on=[
            "stadium",
            "course"
        ],
        right_on=[
            "stadium",
            "result_course"
        ],
        how="left",
        suffixes=(
            "",
            "_venue"
        )
    )

    df.rename(
        columns={
            "win_rate":
                "venue_course_win",
            "top2_rate":
                "venue_course_top2",
            "top3_rate":
                "venue_course_top3"
        },
        inplace=True
    )

    # ---------------------------------------
    # 選手×会場
    # ---------------------------------------

    df = df.merge(
        player_venue[
            [
                "racer_number",
                "stadium",
                "win_rate",
                "top3_rate"
            ]
        ],
        on=[
            "racer_number",
            "stadium"
        ],
        how="left",
        suffixes=(
            "",
            "_player_venue"
        )
    )

    df.rename(
        columns={
            "win_rate":
                "player_venue_win",
            "top3_rate":
                "player_venue_top3"
        },
        inplace=True
    )

    # ---------------------------------------
    # 選手×風向
    # ---------------------------------------

    df = df.merge(
        player_wind[
            [
                "racer_number",
                "wind_direction",
                "win_rate",
                "top3_rate"
            ]
        ],
        on=[
            "racer_number",
            "wind_direction"
        ],
        how="left",
        suffixes=(
            "",
            "_player_wind"
        )
    )

    df.rename(
        columns={
            "win_rate":
                "player_wind_win",
            "top3_rate":
                "player_wind_top3"
        },
        inplace=True
    )

    # ---------------------------------------
    # 欠損補完
    # ---------------------------------------

    fill_cols = [
        "player_course_win",
        "player_course_top2",
        "player_course_top3",
        "venue_course_win",
        "venue_course_top2",
        "venue_course_top3",
        "player_venue_win",
        "player_venue_top3",
        "player_wind_win",
        "player_wind_top3"
    ]

    for c in fill_cols:

        if c not in df.columns:
            df[c] = 0.0

        df[c] = pd.to_numeric(
            df[c],
            errors="coerce"
        ).fillna(0.0)

    # ---------------------------------------
    # ST
    # ---------------------------------------

    df["st_score"] = (
        0.20 -
        pd.to_numeric(
            df["start_timing"],
            errors="coerce"
        ).fillna(
            0.20
        )
    )

    # ---------------------------------------
    # 展示タイム
    # ---------------------------------------

    exhibition = pd.to_numeric(
        df["exhibition_time"],
        errors="coerce"
    )

    if exhibition.notna().any():

        best = exhibition.min()

        df["exhibition_score"] = (
            best - exhibition
        ).fillna(0)

    else:

        df["exhibition_score"] = 0

    return df


# =========================================================
# 1艇ごとの総合スコア
# =========================================================

def calculate_boat_score(
    row
):

    score = 0.0

    # -----------------------------------------------------
    # 選手能力
    # -----------------------------------------------------

    score += (
        float(row.get(
            "national_win_rate",
            0
        ) or 0)
        * 7
    )

    score += (
        float(row.get(
            "national_top2",
            0
        ) or 0)
        * 0.05
    )

    score += (
        float(row.get(
            "national_top3",
            0
        ) or 0)
        * 0.025
    )

    # -----------------------------------------------------
    # コース適性
    # -----------------------------------------------------

    score += (
        row["player_course_win"]
        * 35
    )

    score += (
        row["player_course_top2"]
        * 12
    )

    score += (
        row["player_course_top3"]
        * 8
    )

    # -----------------------------------------------------
    # 会場×コース
    # -----------------------------------------------------

    score += (
        row["venue_course_win"]
        * 30
    )

    score += (
        row["venue_course_top2"]
        * 10
    )

    # -----------------------------------------------------
    # 選手×会場
   
