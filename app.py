import streamlit as st
import requests
import pandas as pd
import numpy as np

from datetime import datetime, timedelta, timezone
from itertools import permutations
from collections import defaultdict


# ==========================================
# 基本設定
# ==========================================

st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO",
    page_icon="🚤",
    layout="wide",
)

JST = timezone(timedelta(hours=9))

JCD_MAP = {
    "桐生": "01",
    "戸田": "02",
    "江戸川": "03",
    "平和島": "04",
    "多摩川": "05",
    "浜名湖": "06",
    "蒲郡": "07",
    "常滑": "08",
    "津": "09",
    "三国": "10",
    "びわこ": "11",
    "住之江": "12",
    "尼崎": "13",
    "鳴門": "14",
    "丸亀": "15",
    "児島": "16",
    "宮島": "17",
    "徳山": "18",
    "下関": "19",
    "若松": "20",
    "芦屋": "21",
    "福岡": "22",
    "唐津": "23",
    "大村": "24",
}

REV_JCD = {int(v): k for k, v in JCD_MAP.items()}

API_BASE = "https://boatraceopenapi.github.io/api/v1"

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


# ==========================================
# 風向
# ==========================================

WIND_NAMES = {
    1: "北",
    2: "北東",
    3: "東",
    4: "南東",
    5: "南",
    6: "南西",
    7: "西",
    8: "北西",
}


# ==========================================
# 決まり手
# ==========================================

TECHNIQUE_NAMES = {
    1: "逃げ",
    2: "差し",
    3: "まくり",
    4: "まくり差し",
    5: "抜き",
    6: "恵まれ",
}


# ==========================================
# 数値変換
# ==========================================

def safe_num(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def pct(a, b):
    if b == 0:
        return 0.0
    return 100.0 * a / b


# ==========================================
# 今日の日付
# ==========================================

def today_str():
    return datetime.now(JST).strftime("%Y-%m-%d")


# ==========================================
# データ取得
# ==========================================

@st.cache_data(ttl=180, show_spinner=False)
def fetch_day(date_str):

    dt = datetime.strptime(date_str, "%Y-%m-%d")

    url = (
        f"{API_BASE}/"
        f"{dt:%Y}/"
        f"{dt:%Y%m%d}.json"
    )

    try:

        response = requests.get(
            url,
            headers=HTTP_HEADERS,
            timeout=20
        )

        if response.status_code != 200:
            return None

        return response.json()

    except Exception:
        return None


# ==========================================
# 指定レース取得
# ==========================================

def get_race(data, jcd, rno):

    if not data:
        return None

    stadiums = (
        data
        .get("programs", {})
        .get("stadiums", {})
    )

    stadium = (
        stadiums.get(str(int(jcd)))
        or stadiums.get(str(jcd))
    )

    if not stadium:
        return None

    races = stadium.get("races") or {}

    return races.get(str(int(rno)))


# ==========================================
# 現在の出走表をDataFrame化
# ==========================================

def flatten_current_race(race):

    rows = []

    preview = race.get("preview") or {}

    racers = race.get("racers") or {}

    preview_racers = preview.get("racers") or {}

    for key, base in sorted(
        racers.items(),
        key=lambda x: int(x[0])
    ):

        entry = int(key)

        p = (
            preview_racers.get(key)
            or preview_racers.get(str(entry))
            or {}
        )

        rows.append({

            "枠": entry,

            "選手名":
                base.get("name", "-"),

            "登録番号":
                base.get("number", "-"),

            "級":
                base.get("rank_number", "-"),

            "全国勝率":
                base.get("national_win_rate"),

            "全国2連率":
                base.get("national_top_2_percent"),

            "全国3連率":
                base.get("national_top_3_percent"),

            "当地勝率":
                base.get("local_win_rate"),

            "当地2連率":
                base.get("local_top_2_percent"),

            "当地3連率":
                base.get("local_top_3_percent"),

            "モーター2連率":
                base.get("motor_top_2_percent"),

            "モーター3連率":
                base.get("motor_top_3_percent"),

            "平均ST":
                base.get("average_start_timing"),

            "F":
                base.get("flying_count"),

            "L":
                base.get("late_count"),

            "進入コース":
                p.get("course_number") or entry,

            "展示タイム":
                p.get("exhibition_time"),

            "直前ST":
                p.get("start_timing"),
        })

    return pd.DataFrame(rows)


# ==========================================
# 過去データから統計を作る
# ==========================================

@st.cache_data(ttl=3600, show_spinner=False)
def build_history(days):

    now = datetime.now(JST).date()

   
