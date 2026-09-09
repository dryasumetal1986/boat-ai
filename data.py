# data.py
# 🚤 やっちゃんの競艇AI予想PRO
# データ取得・変換 完全版

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import requests


# =========================================================
# API
# =========================================================

API_BASE = (
    "https://boatraceopenapi.github.io/api/v1"
)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


# =========================================================
# 24場
# =========================================================

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


# =========================================================
# HTTP
# =========================================================

_session = requests.Session()

_session.headers.update(
    HEADERS
)


# =========================================================
# キャッシュ
# =========================================================

_DATA_CACHE: Dict[
    str,
    Optional[Dict[str, Any]]
] = {}


# =========================================================
# JSON取得
# =========================================================

def _get_json(
    url: str,
) -> Optional[Dict[str, Any]]:

    try:

        response = _session.get(
            url,
            timeout=20,
        )

        if response.status_code != 200:
            return None

        data = response.json()

        if not isinstance(
            data,
            dict,
        ):
            return None

        return data

    except Exception:

        return None


# =========================================================
# 日付データ
# =========================================================

def get_data(
    target_date: Optional[date] = None,
) -> Optional[Dict[str, Any]]:

    if target_date is None:
        target_date = date.today()

    key = target_date.isoformat()

    if key in _DATA_CACHE:
        return _DATA_CACHE[key]

    year = target_date.strftime(
        "%Y"
    )

    yyyymmdd = target_date.strftime(
        "%Y%m%d"
    )

    url = (
        f"{API_BASE}/"
        f"{year}/"
        f"{yyyymmdd}.json"
    )

    data = _get_json(url)

    # 今日ならtoday.jsonも試す
    if (
        data is None
        and target_date == date.today()
    ):

        data = _get_json(
            f"{API_BASE}/today.json"
        )

    _DATA_CACHE[key] = data

    return data


# =========================================================
# 開催場
# =========================================================

def get_stadiums(
    raw: Optional[Dict[str, Any]]
) -> Dict[str, Any]:

    if not raw:
        return {}

    programs = raw.get(
        "programs",
        {},
    )

    if not isinstance(
        programs,
        dict,
    ):
        return {}

    stadiums = programs.get(
        "stadiums",
        {},
    )

    if not isinstance(
        stadiums,
        dict,
    ):
        return {}

    return stadiums


# =========================================================
# 開催場一覧
# =========================================================

def available_stadiums(
    raw: Optional[Dict[str, Any]]
) -> List[int]:

    stadiums = get_stadiums(
        raw
    )

    result = []

    for key in stadiums:

        try:

            number = int(key)

            if 1 <= number <= 24:
                result.append(number)

        except Exception:
            continue

    return sorted(result)


# =========================================================
# レース一覧
# =========================================================

def available_races(
    raw: Optional[Dict[str, Any]],
    stadium_number: int,
) -> List[int]:

    stadiums = get_stadiums(
        raw
    )

    stadium = stadiums.get(
        str(stadium_number)
    )

    if not isinstance(
        stadium,
        dict,
    ):
        return []

    races = stadium.get(
        "races",
        {},
    )

    if not isinstance(
        races,
        dict,
    ):
        return []

    result = []

    for key in races:

        try:

            number = int(key)

            if 1 <= number <= 12:
                result.append(number)

        except Exception:
            continue

    return sorted(result)


# =========================================================
# 特定レース
# =========================================================

def get_race(
    raw: Optional[Dict[str, Any]],
    stadium_number: int,
    race_number: int,
) -> Optional[Dict[str, Any]]:

    stadiums = get_stadiums(
        raw
    )

    stadium = stadiums.get(
        str(stadium_number)
    )

    if not isinstance(
        stadium,
        dict,
    ):
        return None

    races = stadium.get(
        "races",
        {},
    )

    if not isinstance(
        races,
        dict,
    ):
        return None

    race = races.get(
        str(race_number)
    )

    if not isinstance(
        race,
        dict,
    ):
        return None

    return race


# =========================================================
# 数値
# =========================================================

def _float(
    value: Any,
    default: float = 0.0,
) -> float:

    try:

        if value in (
            None,
            "",
        ):
            return default

        return float(value)

    except Exception:

        return default


def _int(
    value: Any,
    default: int = 0,
) -> int:

    try:

        if value in (
            None,
            "",
        ):
            return default

        return int(value)

    except Exception:

        return default


# =========================================================
# 1艇変換
# =========================================================

def make_racer(
    racer: Dict[str, Any],
    preview: Optional[Dict[str, Any]],
    stadium_number: int,
) -> Dict[str, Any]:

    preview = (
        preview
        if isinstance(
            preview,
            dict,
        )
        else {}
    )

    entry = _int(
        racer.get(
            "entry_number"
        )
    )

    course = _int(
        preview.get(
            "course_number"
        ),
        entry,
    )

    return {

        "枠": entry,

        "選手名": racer.get(
            "name",
            f"{entry}号艇",
        ),

        "展示進入": course,

        "全国勝率": _float(
            racer.get(
                "national_win_rate"
            )
        ),

        "全国2連率": _float(
            racer.get(
                "national_top_2_percent"
            )
        ),

        "全国3連率": _float(
            racer.get(
                "national_top_3_percent"
            )
        ),

        "当地勝率": _float(
            racer.get(
                "local_win_rate"
            )
        ),

        "当地2連率": _float(
            racer.get(
                "local_top_2_percent"
            )
        ),

        "当地3連率": _float(
            racer.get(
                "local_top_3_percent"
            )
        ),

        "モーター2連率": _float(
            racer.get(
                "motor_top_2_percent"
            )
        ),

        "平均ST": _float(
            racer.get(
                "average_start_timing"
            )
        ),

        "展示ST": _float(
            preview.get(
                "start_timing"
            )
        ),

        "展示タイム": _float(
            preview.get(
                "exhibition_time"
            )
        ),

        "場": stadium_number,
    }


# =========================================================
# 6艇取得
# =========================================================

def get_race_rows(
    race: Optional[Dict[str, Any]],
    stadium_number: int,
) -> List[Dict[str, Any]]:

    if not race:
        return []

    racers = race.get(
        "racers",
        {},
    )

    preview = race.get(
        "preview",
        {},
    )

    if not isinstance(
        racers,
        dict,
    ):
        return []

    if not isinstance(
        preview,
        dict,
    ):
        preview = {}

    preview_racers = preview.get(
        "racers",
        {},
    )

    if not isinstance(
        preview_racers,
        dict,
    ):
        preview_racers = {}

    rows = []

    for number in range(1, 7):

        racer = racers.get(
            str(number)
        )

        if not isinstance(
            racer,
            dict,
        ):
            continue

        preview_racer = (
            preview_racers.get(
                str(number),
                {},
            )
        )

        rows.append(
            make_racer(
                racer,
                preview_racer,
                stadium_number,
            )
        )

    rows.sort(
        key=lambda x: x["枠"]
    )

    return rows


# =========================================================
# 結果
# =========================================================

def get_result(
    race: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:

    if not race:
        return None

    result = race.get(
        "result"
    )

    if not isinstance(
        result,
        dict,
    ):
        return None

    return result


# =========================================================
# 完了レース判定
# =========================================================

def is_completed(
    race: Optional[Dict[str, Any]]
) -> bool:

    result = get_result(
        race
    )

    if not result:
        return False

    racers = result.get(
        "racers",
        {},
    )

    if not isinstance(
        racers,
        dict,
    ):
        return False

    places = []

    for racer in racers.values():

        if not isinstance(
            racer,
            dict,
        ):
            continue

        place = _int(
            racer.get(
                "place_number"
            )
        )

        if place > 0:
            places.append(place)

    return len(places) >= 3


# =========================================================
# 着順
# =========================================================

def get_result_order(
    race: Optional[Dict[str, Any]]
) -> List[int]:

    result = get_result(
        race
    )

    if not result:
        return []

    racers = result.get(
        "racers",
        {},
    )

    if not isinstance(
        racers,
        dict,
    ):
        return []

    rows = []

    for key, racer in racers.items():

        if not isinstance(
            racer,
            dict,
        ):
            continue

        boat = _int(
            racer.get(
                "entry_number",
                key,
            )
        )

        place = _int(
            racer.get(
                "place_number"
            )
        )

        if boat > 0 and place > 0:

            rows.append(
                (
                    place,
                    boat,
                )
            )

    rows.sort(
        key=lambda x: x[0]
    )

    return [
        boat
        for _, boat in rows
    ]


# =========================================================
# 払戻
# =========================================================

def get_trifecta_payout(
    race: Optional[Dict[str, Any]],
    combination: str,
) -> int:

    result = get_result(
        race
    )

    if not result:
        return 0

    payouts = result.get(
        "payouts",
        {},
    )

    if not isinstance(
        payouts,
        dict,
    ):
        return 0

    trifecta = payouts.get(
        "trifecta",
        [],
    )

    if not isinstance(
        trifecta,
        list,
    ):
        return 0

    for item in trifecta:

        if not isinstance(
            item,
            dict,
        ):
            continue

        if str(
            item.get(
                "combination",
                "",
            )
        ) == combination:

            return _int(
                item.get(
                    "amount"
                )
            )

    return 0


# =========================================================
# 過去14日
# =========================================================

def history14(
    stadium_number: int,
    race_number: int,
    target_date: Optional[date] = None,
) -> List[Dict[str, Any]]:

    if target_date is None:
        target_date = date.today()

    history = []

    for days_ago in range(
        1,
        15,
    ):

        d = (
            target_date
            - timedelta(
                days=days_ago
            )
        )

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

        result = get_result_order(
            race
        )

        if len(rows) < 6:
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
