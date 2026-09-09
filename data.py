import requests
import pandas as pd
import streamlit as st

from datetime import (
    date,
    datetime,
    timedelta,
)


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
    24: "大村",
}


def _date_string(value):

    if isinstance(value, date):
        return value.strftime(
            "%Y-%m-%d"
        )

    return str(value)[:10]


def _date_object(value):

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    return datetime.strptime(
        str(value)[:10],
        "%Y-%m-%d",
    ).date()


def _num(
    value,
    default=0.0,
):

    try:

        if value is None or value == "":
            return default

        return float(value)

    except (
        TypeError,
        ValueError,
    ):

        return default


def _int(
    value,
    default=0,
):

    try:

        if value is None or value == "":
            return default

        return int(
            float(value)
        )

    except (
        TypeError,
        ValueError,
    ):

        return default


def _val(
    obj,
    *keys,
    default=None,
):

    if not isinstance(
        obj,
        dict,
    ):
        return default

    for key in keys:

        value = obj.get(key)

        if (
            value is not None
            and value != ""
        ):
            return value

    return default


def stadium_name(
    stadium_no,
):

    return STADIUMS.get(
        int(stadium_no),
        str(stadium_no),
    )


# =========================================================
# API取得
# =========================================================

@st.cache_data(
    ttl=180,
    show_spinner=False,
)
def get_data(
    target_date,
):

    target = _date_object(
        target_date
    )

    url = (
        f"{API}/"
        f"{target.year}/"
        f"{target.strftime('%Y%m%d')}.json"
    )

    try:

        response = requests.get(
            url,
            timeout=20,
            headers={
                "User-Agent":
                    "YacchanBoatAI/1.0"
            },
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()

        return response.json()

    except (
        requests.RequestException,
        ValueError,
    ):

        return None


# =========================================================
# レース取得
# =========================================================

def get_race(
    raw,
    stadium_no,
    race_no,
):

    if not raw:
        return None

    try:

        stadiums = (
            raw
            .get("programs", {})
            .get("stadiums", {})
        )

        stadium = (
            stadiums.get(
                str(stadium_no)
            )
            or stadiums.get(
                stadium_no
            )
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

        race = (
            races.get(
                str(race_no)
            )
            or races.get(
                race_no
            )
        )

        if not isinstance(
            race,
            dict,
        ):
            return None

        return dict(race)

    except (
        AttributeError,
        TypeError,
    ):

        return None


# =========================================================
# 結果
# =========================================================

def get_result(
    raw,
    stadium_no,
    race_no,
):

    race = get_race(
        raw,
        stadium_no,
        race_no,
    )

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

    racers = result.get(
        "racers"
    )

    if not isinstance(
        racers,
        dict,
    ):
        return None

    return result


def get_result_order(
    raw,
    stadium_no,
    race_no,
):

    result = get_result(
        raw,
        stadium_no,
        race_no,
    )

    if not result:
        return None

    racers = result.get(
        "racers",
        {},
    )

    if not isinstance(
        racers,
        dict,
    ):
        return None

    order = []

    for lane in range(1, 7):

        racer = (
            racers.get(
                str(lane)
            )
            or racers.get(lane)
        )

        if not isinstance(
            racer,
            dict,
        ):
            continue

        place = _int(
            _val(
                racer,
                "place_number",
                "finish_position",
                "rank",
                default=0,
            ),
            0,
        )

        if 1 <= place <= 6:

            order.append(
                (
                    place,
                    lane,
                )
            )

    order.sort(
        key=lambda x: x[0]
    )

    first_three = [
        lane
        for place, lane in order
        if place in (1, 2, 3)
    ]

    if len(first_three) != 3:
        return None

    return [
        int(x)
        for x in first_three
    ]


def is_completed_race(
    raw,
    stadium_no,
    race_no,
):

    return (
        get_result_order(
            raw,
            stadium_no,
            race_no,
        )
        is not None
    )


# =========================================================
# 選手データ
# =========================================================

def make_racer(
    racer,
    lane,
    preview_racer=None,
    stadium_no=None,
):

    racer = racer or {}
    preview_racer = (
        preview_racer or {}
    )

    return {

        "艇番": lane,

        "選手名": _val(
            racer,
            "name",
            "racer_name",
            default=f"{lane}号艇",
        ),

        "枠": lane,

        "全国勝率": _num(
            _val(
                racer,
                "national_win_rate",
                "win_rate",
                default=0,
            )
        ),

        "全国2連率": _num(
            _val(
                racer,
                "national_top_2_percent",
                "national_2ren_rate",
                "top_2_percent",
                default=0,
            )
        ),

        "全国3連率": _num(
            _val(
                racer,
                "national_top_3_percent",
                "national_3ren_rate",
                "top_3_percent",
                default=0,
            )
        ),

        "当地勝率": _num(
            _val(
                racer,
                "local_win_rate",
                "local_win",
                default=0,
            )
        ),

        "当地2連率": _num(
            _val(
                racer,
                "local_top_2_percent",
                "local_2ren_rate",
                default=0,
            )
        ),

        "モーター2連率": _num(
            _val(
                racer,
                "motor_top_2_percent",
                "motor_2ren_rate",
                default=0,
            )
        ),

        "平均ST": _num(
            _val(
                racer,
                "average_start_timing",
                "average_st",
                "avg_st",
                default=0,
            )
        ),

        "展示ST": _num(
            _val(
                preview_racer,
                "start_timing",
                "exhibition_start_timing",
                default=0,
            )
        ),

        "展示タイム": _num(
            _val(
                preview_racer,
                "exhibition_time",
                default=0,
            )
        ),

        "展示進入": _int(
            _val(
                preview_racer,
                "course_number",
                "entry_course",
                default=lane,
            ),
            lane,
        ),

        "場": _int(
            stadium_no,
            0,
        ),
    }


# =========================================================
# 直前情報
# =========================================================

def official_preview(
    race,
):

    if not race:
        return {}

    preview = race.get(
        "preview",
        {},
    )

    if not isinstance(
        preview,
        dict,
    ):
        return {}

    racers = preview.get(
        "racers",
        {},
    )

    if not isinstance(
        racers,
        dict,
    ):
        return {}

    return racers


# =========================================================
# AI用DataFrame
# =========================================================

def get_race_rows(
    race,
    stadium_no=None,
    race_no=None,
):

    if not race:
        return pd.DataFrame()

    racers = race.get(
        "racers",
        {},
    )

    if not isinstance(
        racers,
        dict,
    ):
        return pd.DataFrame()

    preview_racers = official_preview(
        race
    )

    rows = []

    for lane in range(1, 7):

        racer = (
            racers.get(
                str(lane)
            )
            or racers.get(lane)
        )

        if not isinstance(
            racer,
            dict,
        ):
            continue

        preview_racer = (
            preview_racers.get(
                str(lane)
            )
            or preview_racers.get(lane)
            or {}
        )

        rows.append(
            make_racer(
                racer,
                lane,
                preview_racer,
                stadium_no,
            )
        )

    if len(rows) != 6:
        return pd.DataFrame()

    return pd.DataFrame(
        rows
    )


# =========================================================
# レース検証
# =========================================================

def validate_race(
    race,
    target_date=None,
    stadium_no=None,
    race_no=None,
):

    if not isinstance(
        race,
        dict,
    ):
        return False

    racers = race.get(
        "racers"
    )

    if not isinstance(
        racers,
        dict,
    ):
        return False

    count = 0

    for lane in range(1, 7):

        racer = (
            racers.get(
                str(lane)
            )
            or racers.get(lane)
        )

        if isinstance(
            racer,
            dict,
        ):
            count += 1

    if count != 6:
        return False

    if target_date is not None:

        race_date = race.get(
            "date"
        )

        if (
            race_date
            and str(race_date)[:10]
            != _date_string(target_date)
        ):
            return False

    if stadium_no is not None:

        actual_stadium = _int(
            race.get(
                "stadium_number"
            ),
            0,
        )

        if (
            actual_stadium
            and actual_stadium
            != int(stadium_no)
        ):
            return False

    if race_no is not None:

        actual_race = _int(
            race.get(
                "race_number"
            ),
            0,
        )

        if (
            actual_race
            and actual_race
            != int(race_no)
        ):
            return False

    return True


# =========================================================
# 過去結果 → 学習データ
# =========================================================

def _build_history_rows(
    raw,
):

    if not raw:
        return []

    rows = []

    stadiums = (
        raw
        .get("programs", {})
        .get("stadiums", {})
    )

    if not isinstance(
        stadiums,
        dict,
    ):
        return rows

    for stadium_key, stadium in stadiums.items():

        if not isinstance(
            stadium,
            dict,
        ):
            continue

        stadium_no = _int(
            stadium_key,
            0,
        )

        races = stadium.get(
            "races",
            {},
        )

        if not isinstance(
            races,
            dict,
        ):
            continue

        for race_key, race in races.items():

            if not isinstance(
                race,
                dict,
            ):
                continue

            race_no = _int(
                race_key,
                0,
            )

            result = race.get(
                "result"
            )

            if not isinstance(
                result,
                dict,
            ):
                continue

            result_racers = result.get(
                "racers"
            )

            program_racers = race.get(
                "racers"
            )

            if not isinstance(
                result_racers,
                dict,
            ):
                continue

            if not isinstance(
                program_racers,
                dict,
            ):
                continue

            for lane in range(1, 7):

                program_racer = (
                    program_racers.get(
                        str(lane)
                    )
                    or program_racers.get(
                        lane
                    )
                )

                result_racer = (
                    result_racers.get(
                        str(lane)
                    )
                    or result_racers.get(
                        lane
                    )
                )

                if not isinstance(
                    program_racer,
                    dict,
                ):
                    continue

                if not isinstance(
                    result_racer,
                    dict,
                ):
                    continue

                place = _int(
                    _val(
                        result_racer,
                        "place_number",
                        "finish_position",
                        "rank",
                        default=0,
                    ),
                    0,
                )

                if not 1 <= place <= 6:
                    continue

                row = make_racer(
                    program_racer,
                    lane,
                    {},
                    stadium_no,
                )

                row["着順"] = place

                row["1着"] = (
                    1
                    if place == 1
                    else 0
                )

                row["レース場"] = (
                    stadium_no
                )

                row["レース番号"] = (
                    race_no
                )

                rows.append(row)

    return rows


# =========================================================
# 過去14日
# =========================================================

@st.cache_data(
    ttl=600,
    show_spinner=False,
)
def history14(
    target_date,
):

    target = _date_object(
        target_date
    )

    all_rows = []

    for offset in range(1, 15):

        day = (
            target
            - timedelta(days=offset)
        )

        raw = get_data(day)

        if not raw:
            continue

        rows = _build_history_rows(
            raw
        )

        if rows:
            all_rows.extend(rows)

    if not all_rows:
        return pd.DataFrame()

    return pd.DataFrame(
        all_rows
    )
