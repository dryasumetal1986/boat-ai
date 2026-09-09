import time
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import requests
import streamlit as st


API_BASE = "https://boatraceopenapi.github.io/api/v1"
API_START_DATE = date(2026, 1, 1)
JST = timezone(timedelta(hours=9))

STADIUM_NAMES = {
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


def jst_today():
    return datetime.now(JST).date()


def _to_date(value):
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                pass

    raise ValueError(f"日付を解釈できません: {value}")


def stadium_name(stadium_number):
    try:
        return STADIUM_NAMES.get(
            int(stadium_number),
            f"{stadium_number}号場",
        )
    except Exception:
        return str(stadium_number)


def _request_json(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Linux; Android 10) "
            "AppleWebKit/537.36 "
            "Chrome/130.0 Mobile Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
    }

    for attempt in range(2):
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=15,
            )

            if response.status_code == 200:
                try:
                    return response.json()
                except Exception:
                    return None

            if response.status_code == 404:
                return None

        except requests.RequestException:
            if attempt == 0:
                time.sleep(0.8)

    return None


@st.cache_data(ttl=180, show_spinner=False)
def get_data(target_date):
    """
    BOAT RACE Open APIから指定日のデータを取得する。
    2026-01-01以前は対象外。
    """

    try:
        d = _to_date(target_date)
    except Exception:
        return None

    if d < API_START_DATE:
        return None

    urls = []

    # 当日は today.json を優先
    if d == jst_today():
        urls.append(f"{API_BASE}/today.json")

    # 通常の日付API
    urls.append(
        f"{API_BASE}/{d.year}/{d.strftime('%Y%m%d')}.json"
    )

    for url in urls:
        raw = _request_json(url)

        if isinstance(raw, dict) and "programs" in raw:
            return raw

    return None


def get_race(raw, stadium_number, race_number):
    if not raw:
        return None

    try:
        stadiums = raw["programs"]["stadiums"]

        stadium = stadiums.get(str(int(stadium_number)))
        if stadium is None:
            return None

        races = stadium.get("races", {})

        race = races.get(str(int(race_number)))
        if race is None:
            return None

        return race

    except Exception:
        return None


def get_result(race):
    if not isinstance(race, dict):
        return {}

    result = race.get("result")

    if isinstance(result, dict):
        return result

    return {}


def _numeric(value):
    try:
        if value is None:
            return None

        if isinstance(value, bool):
            return None

        text = str(value).strip()

        if text == "":
            return None

        return float(text.replace("%", "").replace(",", ""))

    except Exception:
        return None


def _entry_dict(obj, number):
    if not isinstance(obj, dict):
        return {}

    value = obj.get(str(number))

    if value is None:
        value = obj.get(number)

    return value if isinstance(value, dict) else {}


def get_race_rows(race):
    """
    APIのracers / previewをUI用DataFrameに変換する。
    """

    if not isinstance(race, dict):
        return pd.DataFrame()

    racers = race.get("racers", {})
    preview = race.get("preview", {})
    preview_racers = (
        preview.get("racers", {})
        if isinstance(preview, dict)
        else {}
    )

    rows = []

    for boat in range(1, 7):
        racer = _entry_dict(racers, boat)
        prev = _entry_dict(preview_racers, boat)

        name = (
            racer.get("name")
            or prev.get("name")
            or f"{boat}号艇"
        )

        row = {
            "枠": boat,
            "艇": boat,
            "艇番": boat,
            "entry_number": boat,
            "選手名": name,
            "展示進入": (
                prev.get("course_number")
                if prev.get("course_number") is not None
                else boat
            ),
            "展示ST": prev.get("start_timing"),
            "展示タイム": prev.get("exhibition_time"),
            "全国勝率": racer.get("national_win_rate"),
            "全国2連率": racer.get("national_top_2_percent"),
            "全国3連率": racer.get("national_top_3_percent"),
            "当地勝率": racer.get("local_win_rate"),
            "当地2連率": racer.get("local_top_2_percent"),
            "当地3連率": racer.get("local_top_3_percent"),
            "モーター2連率": racer.get("motor_top_2_percent"),
            "モーター3連率": racer.get("motor_top_3_percent"),
            "平均ST": racer.get("average_start_timing"),
        }

        rows.append(row)

    return pd.DataFrame(rows)


def get_result_order(race):
    """
    結果を1着→6着の艇番リストで返す。
    例: [1, 4, 3, 2, 6, 5]
    """

    result = get_result(race)
    racers = result.get("racers", {})

    if not isinstance(racers, dict):
        return []

    values = []

    for key, item in racers.items():
        if not isinstance(item, dict):
            continue

        boat = item.get("entry_number")

        if boat is None:
            try:
                boat = int(key)
            except Exception:
                continue

        place = item.get("place_number")

        try:
            boat = int(boat)
            place = int(place)
        except Exception:
            continue

        if 1 <= boat <= 6 and 1 <= place <= 6:
            values.append((place, boat))

    values.sort(key=lambda x: x[0])

    return [boat for _, boat in values]


def available_stadiums(raw):
    """
    実際にデータが存在する場だけ返す。
    """

    if not raw:
        return []

    try:
        stadiums = raw["programs"]["stadiums"]
    except Exception:
        return []

    result = []

    for key, stadium in stadiums.items():
        try:
            number = int(key)
        except Exception:
            continue

        races = stadium.get("races", {}) if isinstance(stadium, dict) else {}

        if isinstance(races, dict) and races:
            result.append(number)

    return sorted(result)


def available_races(raw, stadium_number):
    """
    指定場で実際に存在するレース番号を返す。
    """

    if not raw:
        return []

    try:
        stadiums = raw["programs"]["stadiums"]
        stadium = stadiums.get(str(int(stadium_number)))

        if not stadium:
            return []

        races = stadium.get("races", {})

        result = []

        for key, race in races.items():
            try:
                number = int(key)
            except Exception:
                continue

            if isinstance(race, dict):
                result.append(number)

        return sorted(result)

    except Exception:
        return []


def race_has_result(race):
    order = get_result_order(race)
    return len(order) >= 3


@st.cache_data(ttl=1800, show_spinner=False)
def history14(stadium_number, race_number, target_date):
    """
    対象レースより前の14日間から、
    同じ場・同じレース番号の結果を収集する。
    """

    try:
        d = _to_date(target_date)
    except Exception:
        return pd.DataFrame()

    records = []

    for days_back in range(1, 15):
        history_date = d - timedelta(days=days_back)

        if history_date < API_START_DATE:
            break

        raw = get_data(history_date)

        if not raw:
            continue

        race = get_race(
            raw,
            stadium_number,
            race_number,
        )

        if not race:
            continue

        result_order = get_result_order(race)

        if len(result_order) < 3:
            continue

        rows = get_race_rows(race)

        if rows.empty:
            continue

        place_map = {
            boat: place + 1
            for place, boat in enumerate(result_order)
        }

        rows = rows.copy()
        rows["着順"] = rows["枠"].map(place_map)

        rows["日付"] = history_date.isoformat()

        rows = rows.dropna(subset=["着順"])

        if not rows.empty:
            records.append(rows)

    if not records:
        return pd.DataFrame()

    return pd.concat(
        records,
        ignore_index=True,
    )


def all_races_for_date(raw):
    """
    指定日の全場・全レースを返す。
    """

    result = []

    for stadium_number in available_stadiums(raw):
        for race_number in available_races(
            raw,
            stadium_number,
        ):
            race = get_race(
                raw,
                stadium_number,
                race_number,
            )

            if race:
                result.append(
                    (
                        stadium_number,
                        race_number,
                        race,
                    )
                )

    return result
