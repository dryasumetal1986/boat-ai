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
    value: key
    for key, value in VENUES.items()
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


def _get_value(
    data,
    keys,
    default="",
):

    for key in keys:

        value = data.get(key)

        if value not in (
            None,
            "",
        ):
            return value

    return default


def _to_float(value):

    try:

        text = str(value)

        text = text.replace(",", "")
        text = text.replace("倍", "")
        text = text.replace("%", "")
        text = text.replace("％", "")

        return float(text)

    except Exception:
        return 0.0


def get_race(
    date_str,
    venue_name,
    race_no,
):

    yyyymmdd = date_str.replace(
        "-",
        "",
    )

    data = get_day_programs(
        yyyymmdd
    )

    venue_id = VENUES.get(
        venue_name
    )

    if not data or not venue_id:
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

    items = []

    if isinstance(racers, dict):

        for key, value in racers.items():

            if not isinstance(value, dict):
                continue

            racer = dict(value)

            try:
                racer["_entry"] = int(key)

            except Exception:
                continue

            items.append(racer)

    else:
        items = racers

    items.sort(
        key=lambda x:
        x.get("_entry", 99)
    )

    boats = []

    for i, racer in enumerate(
        items[:6],
        1,
    ):

        boat_no = int(
            racer.get(
                "_entry",
                i,
            )
        )

        boats.append({
            "boat": boat_no,

            "name": str(
                _get_value(
                    racer,
                    [
                        "name",
                        "racer_name",
                        "player_name",
                    ],
                    f"{boat_no}号艇",
                )
            ),

            "class": str(
                _get_value(
                    racer,
                    [
                        "class",
                        "grade",
                        "racer_class",
                    ],
                    "",
                )
            ),

            "rate": _to_float(
                _get_value(
                    racer,
                    [
                        "national_win_rate",
                        "win_rate",
                        "rate",
                    ],
                    0,
                )
            ),

            "local_rate": _to_float(
                _get_value(
                    racer,
                    [
                        "local_win_rate",
                        "local_rate",
                    ],
                    0,
                )
            ),

            "motor": _to_float(
                _get_value(
                    racer,
                    [
                        "motor_2_rate",
                        "motor_rate",
                    ],
                    0,
                )
            ),

            "course": _to_float(
                _get_value(
                    racer,
                    [
                        "course_1_rate",
                        "course_rate",
                    ],
                    0,
                )
            ),
        })

    result = race.get(
        "result"
    ) or {}

    result_racers = result.get(
        "racers",
        {},
    )

    actual = []

    if isinstance(
        result_racers,
        dict,
    ):

        temp = []

        for key, value in result_racers.items():

            if not isinstance(value, dict):
                continue

            try:

                place = int(
                    value.get(
                        "place_number"
                    )
                )

                boat = int(key)

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

            if not isinstance(item, dict):
                continue

            payout = _to_float(
                item.get(
                    "amount",
                    0,
                )
            )

            if payout:
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


def _parse_odds(text):

    text = str(text)

    text = text.replace(",", "")
    text = text.replace("倍", "")
    text = text.strip()

    if not text:
        return None

    # -- は欠測扱い
    if text in {
        "-",
        "--",
        "－",
        "－－",
    }:
        return None

    match = re.search(
        r"\d+(?:\.\d+)?",
        text,
    )

    if not match:
        return None

    try:
        return float(
            match.group()
        )

    except Exception:
        return None


def _cell_text(cell):

    return re.sub(
        r"\s+",
        " ",
        cell.get_text(
            " ",
            strip=True,
        ),
    ).strip()


def _boat_number(text):

    match = re.fullmatch(
        r"\D*([1-6])\D*",
        str(text).strip(),
    )

    if not match:
        return None

    return int(match.group(1))


def _parse_odds_table(soup):

    odds = {}

    # --------------------------------
    # 公式3連単テーブルを探索
    # --------------------------------

    tables = soup.find_all("table")

    for table in tables:

        table_rows = table.find_all("tr")

        for tr in table_rows:

            # recursive=Falseを使わず、
            # 行の中のtdを全部取得する
            cells = tr.find_all("td")

            if len(cells) < 18:
                continue

            texts = [
                _cell_text(cell)
                for cell in cells
            ]

            # --------------------------------
            # 18セルの連続部分を探す
            #
            # 6組 ×
            # 2着・3着・オッズ
            # --------------------------------

            for start in range(
                0,
                len(texts) - 17,
            ):

                chunk = texts[
                    start:start + 18
                ]

                parsed = []

                valid = True

                for group in range(6):

                    base = group * 3

                    second = _boat_number(
                        chunk[base]
                    )

                    third = _boat_number(
                        chunk[base + 1]
                    )

                    odd = _parse_odds(
                        chunk[base + 2]
                    )

                    if (
                        second is None
                        or third is None
                        or odd is None
                    ):
                        valid = False
                        break

                    first = group + 1

                    if len({
                        first,
                        second,
                        third,
                    }) != 3:

                        valid = False
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

                if not valid:
                    continue

                # 18セルが正式な並びなら採用
                for combo, odd in parsed:
                    odds[combo] = odd

                # 1行6通り取れたので終了
                break

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
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; "
                    "Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/140.0 "
                    "Safari/537.36"
                )
            },
        )

        response.raise_for_status()

    except Exception:
        return {}

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    odds = _parse_odds_table(
        soup
    )

    return odds
