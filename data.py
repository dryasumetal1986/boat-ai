import json
from functools import lru_cache
from datetime import date

import requests
import pandas as pd


BASE_URL = "https://boatraceopenapi.github.io/api/v1"


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

STADIUM_BY_NAME = {v: k for k, v in STADIUMS.items()}


def _num(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _normalize_racers(racers):
    """
    API v1のracersを、
    {1: {...}, 2: {...}, ..., 6: {...}}
    の形に統一する。

    v1はdict形式。
    念のため旧list形式も受け付ける。
    """

    result = {}

    if isinstance(racers, dict):

        for key, racer in racers.items():

            if not isinstance(racer, dict):
                continue

            boat = _int(
                racer.get("entry_number"),
                _int(key, 0)
            )

            if 1 <= boat <= 6:
                result[boat] = racer

    elif isinstance(racers, list):

        for index, racer in enumerate(racers, start=1):

            if not isinstance(racer, dict):
                continue

            boat = _int(
                racer.get("entry_number"),
                index
            )

            if 1 <= boat <= 6:
                result[boat] = racer

    return result


@lru_cache(maxsize=128)
def get_day_data(day_str):
    """
    1日分の全国24場データを取得する。
    """

    clean_date = day_str.replace("-", "")

    url = (
        f"{BASE_URL}/"
        f"{clean_date[:4]}/"
        f"{clean_date}.json"
    )

    try:

        response = requests.get(
            url,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

    except Exception as e:

        raise RuntimeError(
            f"API取得失敗: {day_str}\n{e}"
        )

    if not isinstance(data, dict):

        raise RuntimeError(
            f"APIデータ形式が不正です: {day_str}"
        )

    if not isinstance(
        data.get("programs"),
        dict
    ):

        raise RuntimeError(
            f"programsデータがありません: {day_str}"
        )

    return data


def get_race(day, stadium_no, race_no):
    """
    指定日・指定場・指定レースを取得。
    """

    if isinstance(day, date):
        day_str = day.isoformat()
    else:
        day_str = str(day)

    data = get_day_data(day_str)

    stadiums = (
        data
        .get("programs", {})
        .get("stadiums", {})
    )

    stadium = stadiums.get(
        str(int(stadium_no)),
        {}
    )

    races = stadium.get(
        "races",
        {}
    )

    return races.get(
        str(int(race_no))
    )


def get_races_for_stadium(
    day,
    stadium_no
):
    """
    指定日の指定場について、
    出走表が6艇揃っているレース番号を返す。
    """

    if isinstance(day, date):
        day_str = day.isoformat()
    else:
        day_str = str(day)

    data = get_day_data(day_str)

    stadium = (
        data
        .get("programs", {})
        .get("stadiums", {})
        .get(str(int(stadium_no)), {})
    )

    races = stadium.get(
        "races",
        {}
    )

    race_numbers = []

    for race_key, race in races.items():

        if not isinstance(race, dict):
            continue

        racers = _normalize_racers(
            race.get("racers")
        )

        if len(racers) == 6:

            race_no = _int(
                race_key,
                0
            )

            if 1 <= race_no <= 12:
                race_numbers.append(
                    race_no
                )

    return sorted(race_numbers)


def race_to_df(race):
    """
    出走表と直前情報をDataFrameへ変換。

    最重要:
    「艇番」は必ず1〜6のentry_numberを使用する。
    """

    if not isinstance(race, dict):
        return pd.DataFrame()

    racers = _normalize_racers(
        race.get("racers")
    )

    preview = (
        race
        .get("preview", {})
        .get("racers", {})
    )

    preview = _normalize_racers(
        preview
    )

    if set(racers.keys()) != set(range(1, 7)):
        return pd.DataFrame()

    rows = []

    for boat in range(1, 7):

        racer = racers[boat]
        preview_data = preview.get(
            boat,
            {}
        )

        row = {

            # ここが艇番
            "boat": boat,

            # API上の枠番
            "entry_number": boat,

            # 選手情報
            "name": str(
                racer.get(
                    "name",
                    ""
                )
            ),

            # 選手登録番号
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

            # 全国成績
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

            # 当地成績
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

            # モーター
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

            # ボート
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

            # F/L
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

            # 直前情報
            # course_numberは「進入コース」であり、
            # 艇番そのものではない
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

        rows.append(row)

    df = pd.DataFrame(rows)

    # 最終安全確認
    if len(df) != 6:
        return pd.DataFrame()

    if set(
        df["boat"].astype(int)
    ) != set(range(1, 7)):
        return pd.DataFrame()

    return df


def get_result(race):
    """
    結果を1着-2着-3着の艇番で返す。

    例:
    (4, 1, 2)

    API v1では
    result.racers["4"].place_number == 1
    なら4号艇が1着。
    """

    if not isinstance(race, dict):
        return None

    result = race.get(
        "result"
    )

    if not isinstance(result, dict):
        return None

    racers = _normalize_racers(
        result.get("racers")
    )

    if len(racers) < 6:
        return None

    finish = []

    for boat, racer in racers.items():

        place = _int(
            racer.get(
                "place_number"
            ),
            0
        )

        if (
            1 <= boat <= 6
            and place > 0
        ):
            finish.append(
                (
                    place,
                    boat
                )
            )

    finish.sort(
        key=lambda x: x[0]
    )

    if len(finish) < 3:
        return None

    top3 = tuple(
        boat
        for place, boat
        in finish[:3]
    )

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


def get_payout(race):
    """
    3連単払戻を取得。
    """

    if not isinstance(race, dict):
        return None

    payouts = (
        race
        .get("result", {})
        .get("payouts", {})
        .get("trifecta", [])
    )

    if not isinstance(
        payouts,
        list
    ):
        return None

    for item in payouts:

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
            .replace("=", "-")
            .replace(" ", "")
        )

        parts = combination.split("-")

        if len(parts) == 3:

            return {
                "combination": combination,
                "amount": _int(
                    item.get(
                        "amount"
                    ),
                    0
                )
            }

    return None


def get_all_races(
    day,
    require_result=False
):
    """
    1日分の全24場レースを取得。

    戻り値:
    [
        (stadium_no, race_no, race),
        ...
    ]
    """

    if isinstance(day, date):
        day_str = day.isoformat()
    else:
        day_str = str(day)

    data = get_day_data(
        day_str
    )

    stadiums = (
        data
        .get("programs", {})
        .get("stadiums", {})
    )

    result = []

    for stadium_key, stadium in stadiums.items():

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

        for race_key, race in races.items():

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
                race.get("racers")
            )

            if len(racers) != 6:
                continue

            if require_result:

                if get_result(race) is None:
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
