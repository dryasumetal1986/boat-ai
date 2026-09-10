import re
from functools import lru_cache

import requests
from bs4 import BeautifulSoup


API_BASE = (
    "https://boatraceopenapi.github.io/api/v1"
)

ODDS_URL = (
    "https://www.boatrace.jp/owpc/pc/race/odds3t"
)


VENUES = {
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

VENUE_BY_ID = {
    v: k
    for k, v in VENUES.items()
}


def _get_json(url):
    response = requests.get(
        url,
        timeout=15,
    )

    response.raise_for_status()

    return response.json()


@lru_cache(maxsize=400)
def get_day_programs(yyyymmdd):

    url = (
        f"{API_BASE}/"
        f"{yyyymmdd[:4]}/"
        f"{yyyymmdd}.json"
    )

    try:
        return _get_json(url)

    except Exception:
        return None


def _float(value):

    try:
        text = str(value)

        text = text.replace(
            ",",
            "",
        )

        text = text.replace(
            "倍",
            "",
        )

        return float(text)

    except Exception:
        return 0.0


def _value(
    data,
    keys,
    default=0,
):

    for key in keys:

        if key in data:

            value = data[key]

            if value not in (
                None,
                "",
            ):
                return value

    return default


def get_race(
    date_str,
    venue_name,
    race_no,
):

    yyyymmdd = date_str.replace(
        "-",
        "",
    )

    venue_id = VENUES.get(
        venue_name
    )

    if not venue_id:
        return None

    data = get_day_programs(
        yyyymmdd
    )

    if not data:
        return None

    stadiums = (
        data
        .get("programs", {})
        .get("stadiums", {})
    )

    stadium = (
        stadiums.get(str(venue_id))
        or stadiums.get(venue_id)
    )

    if not stadium:
        return None

    races = stadium.get(
        "races",
        {},
    )

    race = (
        races.get(str(race_no))
        or races.get(race_no)
    )

    if not race:
        return None

    racers = race.get(
        "racers",
        {},
    )

    boats = []

    if isinstance(
        racers,
        dict,
    ):

        for key, value in racers.items():

            if not isinstance(
                value,
                dict,
            ):
                continue

            try:
                boat_no = int(key)

            except Exception:
                continue

            boats.append({
                "boat": boat_no,

                "name": str(
                    _value(
                        value,
                        [
                            "name",
                            "racer_name",
                            "player_name",
                        ],
                        f"{boat_no}号艇",
                    )
                ),

                "rate": _float(
                    _value(
                        value,
                        [
                            "national_win_rate",
                            "win_rate",
                            "rate",
                        ],
                        0,
                    )
                ),

                "local_rate": _float(
                    _value(
                        value,
                        [
                            "local_win_rate",
                            "local_rate",
                        ],
                        0,
                    )
                ),

                "motor": _float(
                    _value(
                        value,
                        [
                            "motor_2_rate",
                            "motor_rate",
                        ],
                        0,
                    )
                ),

                "course": _float(
                    _value(
                        value,
                        [
                            "course_1_rate",
                            "course_rate",
                        ],
                        0,
                    )
                ),
            })

    boats.sort(
        key=lambda x: x["boat"]
    )

    result = race.get(
        "result",
        {},
    )

    result_racers = result.get(
        "racers",
        {},
    )

    actual = []

    temp = []

    if isinstance(
        result_racers,
        dict,
    ):

        for key, value in result_racers.items():

            if not isinstance(
                value,
                dict,
            ):
                continue

            try:

                boat = int(key)

                place = int(
                    value.get(
                        "place_number"
                    )
                )

                temp.append(
                    (
                        place,
                        boat,
                    )
                )

            except Exception:
                continue

    temp.sort()

    actual = [
        boat
        for _, boat in temp[:3]
    ]

    payout = 0.0

    payouts = result.get(
        "payouts",
        {},
    )

    trifecta = payouts.get(
        "trifecta",
        [],
    )

    if isinstance(
        trifecta,
        list,
    ):

        for item in trifecta:

            if not isinstance(
                item,
                dict,
            ):
                continue

            payout = _float(
                item.get(
                    "amount",
                    0,
                )
            )

            if payout > 0:
                break

    return {
        "date": date_str,
        "venue": venue_name,
        "venue_id": venue_id,
        "race_no": race_no,
        "boats": boats,
        "actual": actual,
        "payout": payout,
        "raw": race,
    }


# =========================================================
# オッズ解析
# =========================================================


def _boat(text):

    text = str(text).strip()

    if re.fullmatch(
        r"[1-6]",
        text,
    ):
        return int(text)

    return None


def _odd(text):

    text = str(text).strip()

    text = text.replace(
        ",",
        "",
    )

    text = text.replace(
        "倍",
        "",
    )

    if not re.fullmatch(
        r"\d+(?:\.\d+)?",
        text,
    ):
        return None

    try:
        return float(text)

    except Exception:
        return None


def _numeric_tokens_from_row(tr):

    tokens = []

    for text in tr.stripped_strings:

        value = str(text).strip()

        value = value.replace(
            ",",
            "",
        )

        value = value.replace(
            "倍",
            "",
        )

        if re.fullmatch(
            r"\d+(?:\.\d+)?",
            value,
        ):

            tokens.append(value)

    return tokens


def _parse_official_odds(html):

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    odds = {}

    # 現在の2着艇
    current_second = [
        None,
        None,
        None,
        None,
        None,
        None,
    ]

    for tr in soup.find_all("tr"):

        tokens = (
            _numeric_tokens_from_row(
                tr
            )
        )

        # 公式3連単表は
        #
        # 18個
        # ↓
        # 12個
        # ↓
        # 12個
        # ↓
        # 12個
        #
        # を繰り返す
        if len(tokens) not in (
            12,
            18,
        ):
            continue

        # -------------------------------------------------
        # 18個の行
        #
        # 2着 / 3着 / オッズ
        # を6艇分
        # -------------------------------------------------

        if len(tokens) == 18:

            parsed = []

            new_second = [
                None,
                None,
                None,
                None,
                None,
                None,
            ]

            ok = True

            for i in range(6):

                p = i * 3

                second = _boat(
                    tokens[p]
                )

                third = _boat(
                    tokens[p + 1]
                )

                odd = _odd(
                    tokens[p + 2]
                )

                first = i + 1

                if (
                    second is None
                    or third is None
                    or odd is None
                ):
                    ok = False
                    break

                if len({
                    first,
                    second,
                    third,
                }) != 3:
                    ok = False
                    break

                new_second[i] = second

                parsed.append(
                    (
                        (
                            first,
                            second,
                            third,
                        ),
                        odd,
                    )
                )

            if not ok:
                continue

            current_second = (
                new_second
            )

            for combo, odd in parsed:

                odds[combo] = odd

        # -------------------------------------------------
        # 12個の行
        #
        # 3着 / オッズ
        # だけが並ぶ
        #
        # 2着は直前の18個行から引き継ぐ
        # -------------------------------------------------

        else:

            if not all(
                x is not None
                for x in current_second
            ):
                continue

            parsed = []

            ok = True

            for i in range(6):

                p = i * 2

                third = _boat(
                    tokens[p]
                )

                odd = _odd(
                    tokens[p + 1]
                )

                second = (
                    current_second[i]
                )

                first = i + 1

                if (
                    third is None
                    or odd is None
                    or second is None
                ):
                    ok = False
                    break

                if len({
                    first,
                    second,
                    third,
                }) != 3:
                    ok = False
                    break

                parsed.append(
                    (
                        (
                            first,
                            second,
                            third,
                        ),
                        odd,
                    )
                )

            if not ok:
                continue

            for combo, odd in parsed:

                odds[combo] = odd

    return odds


@lru_cache(maxsize=2000)
def get_trifecta_odds(
    date_str,
    venue_id,
    race_no,
):

    hd = date_str.replace(
        "-",
        "",
    )

    jcd = f"{int(venue_id):02d}"

    url = (
        f"{ODDS_URL}"
        f"?hd={hd}"
        f"&jcd={jcd}"
        f"&rno={race_no}"
    )

    try:

        response = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent":
                    "Mozilla/5.0"
            },
        )

        response.raise_for_status()

    except Exception:

        return {}

    return _parse_official_odds(
        response.text
    )
