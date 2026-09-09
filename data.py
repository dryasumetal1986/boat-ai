# data.py
# 🚤 やっちゃんの競艇AI予想PRO
# Boatrace Open API データ取得モジュール

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import requests


# =========================================================
# API設定
# =========================================================

API_BASE = "https://boatraceopenapi.github.io/api/v1"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
}


# =========================================================
# セッション
# =========================================================

_session = requests.Session()
_session.headers.update(HEADERS)


# =========================================================
# 基本API取得
# =========================================================

def _request_json(url: str) -> Optional[Dict[str, Any]]:
    """
    JSON APIを取得する。
    エラー時はNone。
    """

    try:
        response = _session.get(
            url,
            timeout=20,
        )

        if response.status_code != 200:
            return None

        if not response.text:
            return None

        data = response.json()

        if not isinstance(data, dict):
            return None

        return data

    except Exception:
        return None


# =========================================================
# 日付文字列
# =========================================================

def _date_strings(target_date: date):
    """
    2026-09-09
    20260909
    2026
    を作る。
    """

    date_text = target_date.strftime("%Y-%m-%d")
    yyyymmdd = target_date.strftime("%Y%m%d")
    year = target_date.strftime("%Y")

    return date_text, yyyymmdd, year


# =========================================================
# レースデータ取得
# =========================================================

def get_data(target_date: Optional[date] = None) -> Optional[Dict[str, Any]]:
    """
    指定日のBoatrace Open APIデータを取得。

    第一候補:
        /v1/YYYY/YYYYMMDD.json

    当日の場合:
        /v1/today.json

    """

    if target_date is None:
        target_date = date.today()

    _, yyyymmdd, year = _date_strings(target_date)

    # -----------------------------------------------------
    # ① 指定日API
    # -----------------------------------------------------

    url1 = f"{API_BASE}/{year}/{yyyymmdd}.json"

    data = _request_json(url1)

    if data is not None:
        return data

    # -----------------------------------------------------
    # ② 当日API
    # -----------------------------------------------------

    today = date.today()

    if target_date == today:
        url2 = f"{API_BASE}/today.json"

        data = _request_json(url2)

        if data is not None:
            return data

    return None


# =========================================================
# 開催場一覧
# =========================================================

def get_stadiums(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    APIから開催場データを取得。
    """

    if not raw:
        return {}

    try:
        programs = raw.get("programs", {})

        if not isinstance(programs, dict):
            return {}

        stadiums = programs.get("stadiums", {})

        if not isinstance(stadiums, dict):
            return {}

        return stadiums

    except Exception:
        return {}


# =========================================================
# 特定レース取得
# =========================================================

def get_race(
    raw: Optional[Dict[str, Any]],
    stadium_number: int,
    race_number: int,
) -> Optional[Dict[str, Any]]:
    """
    開催場番号とレース番号からレース情報を取得。
    """

    if not raw:
        return None

    try:
        stadiums = get_stadiums(raw)

        stadium = stadiums.get(str(stadium_number))

        if not isinstance(stadium, dict):
            return None

        races = stadium.get("races", {})

        if not isinstance(races, dict):
            return None

        race = races.get(str(race_number))

        if not isinstance(race, dict):
            return None

        return race

    except Exception:
        return None


# =========================================================
# レーサー情報
# =========================================================

def _safe_float(value: Any, default: float = 0.0) -> float:
    """
    数値変換。
    """

    try:
        if value is None:
            return default

        if value == "":
            return default

        return float(value)

    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """
    整数変換。
    """

    try:
        if value is None:
            return default

        if value == "":
            return default

        return int(value)

    except Exception:
        return default


# =========================================================
# 選手1人分を内部形式へ変換
# =========================================================

def make_racer(
    racer: Dict[str, Any],
    preview: Optional[Dict[str, Any]] = None,
    stadium_number: int = 0,
) -> Dict[str, Any]:

    if preview is None:
        preview = {}

    entry_number = _safe_int(
        racer.get("entry_number"),
        0,
    )

    course_number = _safe_int(
        preview.get("course_number"),
        entry_number,
    )

    return {
        # 基本
        "枠": entry_number,
        "選手名": racer.get("name", f"{entry_number}号艇"),

        # 展示
        "展示進入": course_number,
        "展示ST": _safe_float(
            preview.get("start_timing"),
            0.0,
        ),
        "展示タイム": _safe_float(
            preview.get("exhibition_time"),
            0.0,
        ),

        # 全国成績
        "全国勝率": _safe_float(
            racer.get("national_win_rate"),
            0.0,
        ),
        "全国2連率": _safe_float(
            racer.get("national_top_2_percent"),
            0.0,
        ),
        "全国3連率": _safe_float(
            racer.get("national_top_3_percent"),
            0.0,
        ),

        # 当地成績
        "当地勝率": _safe_float(
            racer.get("local_win_rate"),
            0.0,
        ),
        "当地2連率": _safe_float(
            racer.get("local_top_2_percent"),
            0.0,
        ),
        "当地3連率": _safe_float(
            racer.get("local_top_3_percent"),
            0.0,
        ),

        # モーター
        "モーター2連率": _safe_float(
            racer.get("motor_top_2_percent"),
            0.0,
        ),

        # ST
        "平均ST": _safe_float(
            racer.get("average_start_timing"),
            0.0,
        ),

        # 場
        "場": stadium_number,
    }


# =========================================================
# レース6艇をDataFrame用のListへ変換
# =========================================================

def get_race_rows(
    race: Optional[Dict[str, Any]],
    stadium_number: int = 0,
) -> List[Dict[str, Any]]:
    """
    race情報から6艇分の内部データを作る。
    """

    if not race:
        return []

    racers = race.get("racers", {})

    if not isinstance(racers, dict):
        return []

    preview_block = race.get("preview", {})

    if not isinstance(preview_block, dict):
        preview_block = {}

    preview_racers = preview_block.get("racers", {})

    if not isinstance(preview_racers, dict):
        preview_racers = {}

    rows: List[Dict[str, Any]] = []

    # -----------------------------------------------------
    # 1号艇〜6号艇
    # -----------------------------------------------------

    for number in range(1, 7):

        racer = racers.get(str(number))

        if racer is None:
            racer = racers.get(number)

        if not isinstance(racer, dict):
            continue

        preview = preview_racers.get(str(number))

        if preview is None:
            preview = preview_racers.get(number)

        if not isinstance(preview, dict):
            preview = {}

        row = make_racer(
            racer=racer,
            preview=preview,
            stadium_number=stadium_number,
        )

        rows.append(row)

    return rows


# =========================================================
# 結果取得
# =========================================================

def get_result(
    race: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    レース結果を取得。
    """

    if not race:
        return None

    result = race.get("result")

    if not isinstance(result, dict):
        return None

    return result


# =========================================================
# 結果着順取得
# =========================================================

def get_result_order(
    race: Optional[Dict[str, Any]],
) -> List[int]:
    """
    結果から1着〜3着の艇番を返す。

    例:
        [1, 3, 2]
    """

    result = get_result(race)

    if not result:
        return []

    racers = result.get("racers", {})

    if not isinstance(racers, dict):
        return []

    result_rows = []

    for key, racer in racers.items():

        if not isinstance(racer, dict):
            continue

        entry_number = _safe_int(
            racer.get("entry_number", key),
            0,
        )

        place_number = _safe_int(
            racer.get("place_number"),
            0,
        )

        if entry_number <= 0:
            continue

        if place_number <= 0:
            continue

        result_rows.append(
            (
                place_number,
                entry_number,
            )
        )

    result_rows.sort(
        key=lambda x: x[0]
    )

    return [
        entry_number
        for _, entry_number in result_rows[:3]
    ]


# =========================================================
# 過去データ
# =========================================================

def history14(
    stadium_number: int,
    race_number: int,
    target_date: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """
    過去14日分の同場・同レースを取得。
    """

    if target_date is None:
        target_date = date.today()

    history: List[Dict[str, Any]] = []

    for days_ago in range(1, 15):

        d = target_date - timedelta(days=days_ago)

        raw = get_data(d)

        if raw is None:
            continue

        race = get_race(
            raw,
            stadium_number,
            race_number,
        )

        if race is None:
            continue

        rows = get_race_rows(
            race,
            stadium_number,
        )

        result = get_result_order(race)

        if not rows:
            continue

        history.append(
            {
                "date": d,
                "stadium_number": stadium_number,
                "race_number": race_number,
                "rows": rows,
                "result": result,
            }
        )

    return history


# =========================================================
# 今日の開催場一覧
# =========================================================

def available_stadiums(
    raw: Optional[Dict[str, Any]]
) -> List[int]:
    """
    実際にAPIに存在する開催場番号。
    """

    stadiums = get_stadiums(raw)

    numbers = []

    for key in stadiums.keys():

        try:
            numbers.append(int(key))
        except Exception:
            pass

    return sorted(numbers)


# =========================================================
# 今日のレース一覧
# =========================================================

def available_races(
    raw: Optional[Dict[str, Any]],
    stadium_number: int,
) -> List[int]:
    """
    指定場に存在するレース番号。
    """

    race = get_stadiums(raw).get(
        str(stadium_number)
    )

    if not isinstance(race, dict):
        return []

    races = race.get("races", {})

    if not isinstance(races, dict):
        return []

    numbers = []

    for key in races.keys():

        try:
            numbers.append(int(key))
        except Exception:
            pass

    return sorted(numbers)


# =========================================================
# デバッグ用
# =========================================================

def api_status(
    target_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    API状態確認用。
    """

    if target_date is None:
        target_date = date.today()

    _, yyyymmdd, year = _date_strings(target_date)

    urls = [
        f"{API_BASE}/{year}/{yyyymmdd}.json",
        f"{API_BASE}/today.json",
    ]

    result = {
        "date": str(target_date),
        "urls": urls,
        "success": False,
        "status": None,
    }

    for url in urls:

        try:
            response = _session.get(
                url,
                timeout=20,
            )

            result["status"] = response.status_code
            result["url"] = url

            if response.status_code == 200:

                try:
                    data = response.json()

                    if isinstance(data, dict):
                        result["success"] = True
                        result["has_programs"] = (
                            "programs" in data
                        )
                        return result

                except Exception:
                    pass

        except Exception as e:
            result["error"] = str(e)

    return result
