import time
from functools import lru_cache
from datetime import date

import requests
import pandas as pd


# =========================================================
# API設定
# =========================================================

BASE_URL = "https://boatraceopenapi.github.io/api/v1"

REQUEST_TIMEOUT = 20
REQUEST_RETRY_COUNT = 3
REQUEST_RETRY_WAIT = 1.0


# =========================================================
# 会場
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
    24: "大村",
}

STADIUM_BY_NAME = {
    v: k
    for k, v in STADIUMS.items()
}


# =========================================================
# 数値変換
# =========================================================

def _num(value, default=0.0):
    try:
        if value is None or value == "":
            return default

        value = float(value)

        if pd.isna(value):
            return default

        return value

    except (TypeError, ValueError):
        return default


def _int(value, default=0):
    try:
        if value is None or value == "":
            return default

        return int(float(value))

    except (TypeError, ValueError):
        return default


# =========================================================
# 日付
# =========================================================

def _day_string(day):
    if isinstance(day, date):
        return day.isoformat()

    return str(day)


# =========================================================
# racers正規化
# =========================================================

def _normalize_racers(racers):

    result = {}

    # -----------------------------------------------------
    # API本来の形式
    #
    # {
    #   "1": {...},
    #   "2": {...},
    #   ...
    # }
    # -----------------------------------------------------

    if isinstance(racers, dict):

        for key, racer in racers.items():

            if not isinstance(racer, dict):
                continue

            boat = _int(
                racer.get(
                    "entry_number"
                ),
                _int(
                    key,
                    0
                )
            )

            if not (
                1 <= boat <= 6
            ):
                continue

            result[boat] = racer

        return result

    # -----------------------------------------------------
    # 念のためlistにも対応
    # -----------------------------------------------------

    if isinstance(racers, list):

        for index, racer in enumerate(
            racers,
            start=1
        ):

            if not isinstance(racer, dict):
                continue

            boat = _int(
                racer.get(
                    "entry_number"
                ),
                index
            )

            if not (
                1 <= boat <= 6
            ):
                continue

            result[boat] = racer

    return result


# =========================================================
# API取得
# =========================================================

def _request_day_data(day_str):

    clean_date = (
        day_str
        .replace("-", "")
        .replace("/", "")
    )

    if len(clean_date) != 8:
        raise RuntimeError(
            f"日付形式が不正です: {day_str}"
        )

    url = (
        f"{BASE_URL}/"
        f"{clean_date[:4]}/"
        f"{clean_date}.json"
    )

    last_error = None

    for attempt in range(
        REQUEST_RETRY_COUNT
    ):

        try:

            response = requests.get(
                url,
                timeout=REQUEST_TIMEOUT,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 "
                        "(compatible; "
                        "YacchanBoatAI/1.0)"
                    ),
                    "Accept": (
                        "application/json,"
                        "text/plain,*/*"
                    ),
                },
            )

            response.raise_for_status()

            data = response.json()

            if not isinstance(
                data,
                dict
            ):
                raise RuntimeError(
                    "APIレスポンスがJSONオブジェクトではありません"
                )

            programs = data.get(
                "programs"
            )

            if not isinstance(
                programs,
                dict
            ):
                raise RuntimeError(
                    "APIレスポンスにprogramsがありません"
                )

            stadiums = programs.get(
                "stadiums"
            )

            if not isinstance(
                stadiums,
                dict
            ):
                raise RuntimeError(
                    "APIレスポンスにprograms.stadiumsがありません"
                )

            return data

        except Exception as e:

            last_error = e

            if attempt < (
                REQUEST_RETRY_COUNT - 1
            ):
                time.sleep(
                    REQUEST_RETRY_WAIT
                )

    raise RuntimeError(
        f"API取得失敗: {day_str}\n"
        f"URL: {url}\n"
        f"最後のエラー: {last_error}"
    )


# =========================================================
# 1日分データ
# =========================================================

@lru_cache(maxsize=128)
def get_day_data(day_str):

    return _request_day_data(
        day_str
    )


# =========================================================
# キャッシュクリア
# =========================================================

def clear_cache():

    try:
        get_day_data.cache_clear()

    except Exception:
        pass


# =========================================================
# レース取得
# =========================================================

def get_race(
    day,
    stadium_no,
    race_no
):

    day_str = _day_string(
        day
    )

    data = get_day_data(
        day_str
    )

    stadiums = (
        data
        .get("programs", {})
        .get("stadiums", {})
    )

    stadium = stadiums.get(
        str(
            int(stadium_no)
        ),
        {}
    )

    if not isinstance(
        stadium,
        dict
    ):
        return None

    races = stadium.get(
        "races",
        {}
    )

    if not isinstance(
        races,
        dict
    ):
        return None

    return races.get(
        str(
            int(race_no)
        )
    )


# =========================================================
# 会場内レース番号
# =========================================================

def get_races_for_stadium(
    day,
    stadium_no
):

    day_str = _day_string(
        day
    )

    data = get_day_data(
        day_str
    )

    stadium = (
        data
        .get("programs", {})
        .get("stadiums", {})
        .get(
            str(
                int(stadium_no)
            ),
            {}
        )
    )

    if not isinstance(
        stadium,
        dict
    ):
        return []

    races = stadium.get(
        "races",
        {}
    )

    if not isinstance(
        races,
        dict
    ):
        return []

    race_numbers = []

    for race_key, race in races.items():

        if not isinstance(
            race,
            dict
        ):
            continue

        racers = _normalize_racers(
            race.get(
                "racers"
            )
        )

        if not (
            3 <= len(racers) <= 6
        ):
            continue

        race_no = _int(
            race_key,
            0
        )

        if 1 <= race_no <= 12:
            race_numbers.append(
                race_no
            )

    return sorted(
        set(race_numbers)
    )


# =========================================================
# レース → DataFrame
# =========================================================

def race_to_df(race):

    if not isinstance(
        race,
        dict
    ):
        return pd.DataFrame()

    racers = _normalize_racers(
        race.get(
            "racers"
        )
    )

    preview_root = race.get(
        "preview",
        {}
    )

    if not isinstance(
        preview_root,
        dict
    ):
        preview_root = {}

    preview = _normalize_racers(
        preview_root.get(
            "racers"
        )
    )

    active_boats = sorted(
        racers.keys()
    )

    if not (
        3 <= len(active_boats) <= 6
    ):
        return pd.DataFrame()

    rows = []

    for boat in active_boats:

        racer = racers.get(
            boat,
            {}
        )

        if not isinstance(
            racer,
            dict
        ):
            continue

        preview_data = preview.get(
            boat,
            {}
        )

        if not isinstance(
            preview_data,
            dict
        ):
            preview_data = {}

        row = {
            "boat": boat,

            "entry_number": boat,

            "name": str(
                racer.get(
                    "name",
                    ""
                )
            ),

            "racer_number": _int(
                racer.get(
                    "number"
                ),
                0
            ),

            "rank_number": _int(
                racer.get(
                    "rank_number"
                ),
                0
            ),

            "age": _int(
                racer.get(
                    "age"
                ),
                0
            ),

            "average_start_timing": _num(
                racer.get(
                    "average_start_timing"
                ),
                0
            ),

            "national_win_rate": _num(
                racer.get(
                    "national_win_rate"
                ),
                0
            ),

            "national_top_2_percent": _num(
                racer.get(
                    "national_top_2_percent"
                ),
                0
            ),

            "national_top_3_percent": _num(
                racer.get(
                    "national_top_3_percent"
                ),
                0
            ),

            "local_win_rate": _num(
                racer.get(
                    "local_win_rate"
                ),
                0
            ),

            "local_top_2_percent": _num(
                racer.get(
                    "local_top_2_percent"
                ),
                0
            ),

            "local_top_3_percent": _num(
                racer.get(
                    "local_top_3_percent"
                ),
                0
            ),

            "motor_number": _int(
                racer.get(
                    "motor_number"
                ),
                0
            ),

            "motor_top_2_percent": _num(
                racer.get(
                    "motor_top_2_percent"
                ),
                0
            ),

            "motor_top_3_percent": _num(
                racer.get(
                    "motor_top_3_percent"
                ),
                0
            ),

            "boat_number": _int(
                racer.get(
                    "boat_number"
                ),
                0
            ),

            "boat_top_2_percent": _num(
                racer.get(
                    "boat_top_2_percent"
                ),
                0
            ),

            "boat_top_3_percent": _num(
                racer.get(
                    "boat_top_3_percent"
                ),
                0
            ),

            "flying_count": _int(
                racer.get(
                    "flying_count"
                ),
                0
            ),

            "late_count": _int(
                racer.get(
                    "late_count"
                ),
                0
            ),

            "course_number": _int(
                preview_data.get(
                    "course_number"
                ),
                boat
            ),

            "start_timing": _num(
                preview_data.get(
                    "start_timing"
                ),
                0
            ),

            "exhibition_time": _num(
                preview_data.get(
                    "exhibition_time"
                ),
                0
            ),

            "weight": _num(
                preview_data.get(
                    "weight"
                ),
                0
            ),

            "tilt_adjustment": _num(
                preview_data.get(
                    "tilt_adjustment"
                ),
                0
            ),
        }

        rows.append(
            row
        )

    df = pd.DataFrame(
        rows
    )

    if not (
        3 <= len(df) <= 6
    ):
        return pd.DataFrame()

    if len(
        set(
            df["boat"].astype(int)
        )
    ) != len(df):
        return pd.DataFrame()

    df = df.sort_values(
        "boat"
    ).reset_index(
        drop=True
    )

    df.attrs[
        "active_boats"
    ] = [
        int(x)
        for x in df["boat"]
    ]

    df.attrs[
        "withdrawn_boats"
    ] = [
        boat
        for boat in range(1, 7)
        if boat not in df.attrs[
            "active_boats"
        ]
    ]

    return df


# =========================================================
# 結果取得
# =========================================================

def get_result(race):

    if not isinstance(
        race,
        dict
    ):
        return None

    result = race.get(
        "result"
    )

    if not isinstance(
        result,
        dict
    ):
        return None

    racers = _normalize_racers(
        result.get(
            "racers"
        )
    )

    if len(racers) < 3:
        return None

    finish = []

    for boat, racer in racers.items():

        if not isinstance(
            racer,
            dict
        ):
            continue

        place = _int(
            racer.get(
                "place_number"
            ),
            0
        )

        if not (
            1 <= boat <= 6
        ):
            continue

        if place <= 0:
            continue

        finish.append(
            (
                place,
                boat
            )
        )

    if len(finish) < 3:
        return None

    finish.sort(
        key=lambda x: (
            x[0],
            x[1]
        )
    )

    top3 = tuple(
        boat
        for _, boat
        in finish[:3]
    )

    if len(top3) != 3:
        return None

    if len(
        set(top3)
    ) != 3:
        return None

    if not all(
        1 <= boat <= 6
        for boat in top3
    ):
        return None

    return top3


# =========================================================
# 払戻取得
# =========================================================

def get_payout(race):

    if not isinstance(
        race,
        dict
    ):
        return None

    result = race.get(
        "result",
        {}
    )

    if not isinstance(
        result,
        dict
    ):
        return None

    payouts = (
        result
        .get(
            "payouts",
            {}
        )
    )

    if not isinstance(
        payouts,
        dict
    ):
        return None

    trifecta = payouts.get(
        "trifecta",
        []
    )

    if not isinstance(
        trifecta,
        list
    ):
        return None

    for item in trifecta:

        if not isinstance(
            item,
            dict
        ):
            continue

        combination = str(
            item.get(
                "combination",
                ""
            )
        )

        combination = (
            combination
            .replace(
                "=",
                "-"
            )
            .replace(
                " ",
                ""
            )
        )

        parts = combination.split(
            "-"
        )

        if len(parts) != 3:
            continue

        if not all(
            part.isdigit()
            for part in parts
        ):
            continue

        return {
            "combination": combination,
            "amount": _int(
                item.get(
                    "amount"
                ),
                0
            ),
        }

    return None


# =========================================================
# 全レース取得
# =========================================================

def get_all_races(
    day,
    require_result=False
):

    day_str = _day_string(
        day
    )

    data = get_day_data(
        day_str
    )

    stadiums = (
        data
        .get("programs", {})
        .get("stadiums", {})
    )

    if not isinstance(
        stadiums,
        dict
    ):
        return []

    result = []

    for stadium_key, stadium in (
        stadiums.items()
    ):

        stadium_no = _int(
            stadium_key,
            0
        )

        if not (
            1 <= stadium_no <= 24
        ):
            continue

        if not isinstance(
            stadium,
            dict
        ):
            continue

        races = stadium.get(
            "races",
            {}
        )

        if not isinstance(
            races,
            dict
        ):
            continue

        for race_key, race in (
            races.items()
        ):

            race_no = _int(
                race_key,
                0
            )

            if not (
                1 <= race_no <= 12
            ):
                continue

            if not isinstance(
                race,
                dict
            ):
                continue

            racers = _normalize_racers(
                race.get(
                    "racers"
                )
            )

            if not (
                3 <= len(racers) <= 6
            ):
                continue

            if require_result:

                actual = get_result(
                    race
                )

                if actual is None:
                    continue

            result.append(
                (
                    stadium_no,
                    race_no,
                    race
                )
            )

    result.sort(
        key=lambda x: (
            x[0],
            x[1]
        )
    )

    return result
