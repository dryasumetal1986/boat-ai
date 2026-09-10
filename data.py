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


def _json(url):
    r = requests.get(
        url,
        timeout=15
    )
    r.raise_for_status()
    return r.json()


@lru_cache(maxsize=400)
def get_day_programs(yyyymmdd):

    try:
        return _json(
            f"{API_BASE}/"
            f"{yyyymmdd[:4]}/"
            f"{yyyymmdd}.json"
        )

    except Exception:
        return None


def _val(d, keys, default=""):

    for k in keys:

        if d.get(k) not in (
            None,
            ""
        ):
            return d[k]

    return default


def _float(v):

    try:
        return float(
            str(v)
            .replace(",", "")
            .replace("%", "")
            .replace("％", "")
        )

    except Exception:
        return 0.0


def get_race(
    date_str,
    venue_name,
    race_no
):

    d = get_day_programs(
        date_str.replace("-", "")
    )

    sid = VENUES.get(venue_name)

    if not d or not sid:
        return None

    stadiums = (
        d.get("programs", {})
        .get("stadiums", {})
    )

    stadium = (
        stadiums.get(str(sid))
        or stadiums.get(sid)
    )

    if not stadium:
        return None

    races = stadium.get(
        "races",
        {}
    )

    race = (
        races.get(str(race_no))
        or races.get(race_no)
    )

    if not race:
        return None

    racers = race.get(
        "racers",
        {}
    )

    items = []

    if isinstance(racers, dict):

        for k, v in racers.items():

            if not isinstance(v, dict):
                continue

            x = dict(v)

            try:
                x["_entry"] = int(k)

            except Exception:
                continue

            items.append(x)

    elif isinstance(racers, list):

        items = racers

    items.sort(
        key=lambda x: x.get(
            "_entry",
            99
        )
    )

    boats = []

    for i, r in enumerate(
        items[:6],
        1
    ):

        n = int(
            r.get(
                "_entry",
                i
            )
        )

        boats.append(
            {
                "boat": n,

                "name": str(
                    _val(
                        r,
                        [
                            "name",
                            "racer_name",
                            "player_name",
                        ],
                        f"{n}号艇"
                    )
                ),

                "class": str(
                    _val(
                        r,
                        [
                            "class",
                            "grade",
                            "racer_class",
                        ],
                        ""
                    )
                ),

                "rate": _float(
                    _val(
                        r,
                        [
                            "national_win_rate",
                            "win_rate",
                            "rate",
                        ],
                        0
                    )
                ),

                "local_rate": _float(
                    _val(
                        r,
                        [
                            "local_win_rate",
                            "local_rate",
                        ],
                        0
                    )
                ),

                "motor": _float(
                    _val(
                        r,
                        [
                            "motor_2_rate",
                            "motor_rate",
                        ],
                        0
                    )
                ),

                "course": _float(
                    _val(
                        r,
                        [
                            "course_1_rate",
                            "course_rate",
                        ],
                        0
                    )
                ),
            }
        )

    result = race.get(
        "result"
    ) or {}

    rr = result.get(
        "racers",
        {}
    )

    actual = []

    if isinstance(rr, dict):

        tmp = []

        for k, v in rr.items():

            if not isinstance(v, dict):
                continue

            try:
                tmp.append(
                    (
                        int(
                            v.get(
                                "place_number"
                            )
                        ),
                        int(k)
                    )
                )

            except Exception:
                pass

        tmp.sort()

        actual = [
            x[1]
            for x in tmp[:3]
        ]

    payout = 0.0

    for x in (
        result
        .get("payouts", {})
        .get("trifecta", [])
        or []
    ):

        if isinstance(x, dict):

            payout = _float(
                x.get(
                    "amount",
                    0
                )
            )

            if payout:
                break

    return {
        "date": date_str,
        "venue": venue_name,
        "venue_id": sid,
        "race_no": race_no,
        "boats": boats,
        "actual": actual,
        "payout": payout,
        "raw": race,
    }


def _numeric_tokens_from_row(tr):

    tokens = []

    for text in tr.stripped_strings:

        value = (
            str(text)
            .strip()
            .replace(",", "")
            .replace("倍", "")
        )

        if re.fullmatch(
            r"\d+(?:\.\d+)?",
            value
        ):
            tokens.append(value)

    return tokens


@lru_cache(maxsize=2000)
def get_trifecta_odds(
    date_str,
    venue_id,
    race_no
):

    url = (
        f"{ODDS_URL}"
        f"?hd={date_str.replace('-', '')}"
        f"&jcd={int(venue_id):02d}"
        f"&rno={race_no}"
    )

    try:

        r = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent":
                "Mozilla/5.0"
            }
        )

        r.raise_for_status()

    except Exception:
        return {}

    soup = BeautifulSoup(
        r.text,
        "html.parser"
    )

    out = {}

    current_second = None

    # -----------------------------------------
    # 公式BOATRACEの3連単オッズ表
    #
    # 18数値の行
    # → 2着・3着・オッズ × 6
    #
    # 12数値の行
    # → 3着・オッズ × 6
    # -----------------------------------------

    for tr in soup.find_all("tr"):

        tokens = _numeric_tokens_from_row(tr)

        if len(tokens) == 18:

            for i in range(
                0,
                18,
                3
            ):

                try:

                    second = int(
                        tokens[i]
                    )

                    third = int(
                        tokens[i + 1]
                    )

                    odd = float(
                        tokens[i + 2]
                    )

                except Exception:
                    continue

                first = (
                    i // 3
                ) + 1

                if (
                    odd > 0
                    and len(
                        {
                            first,
                            second,
                            third,
                        }
                    ) == 3
                ):

                    out[
                        (
                            first,
                            second,
                            third,
                        )
                    ] = odd

            seconds = [
                int(tokens[i])
                for i in range(
                    0,
                    18,
                    3
                )
            ]

            if (
                len(set(seconds)) == 1
            ):
                current_second = (
                    seconds[0]
                )
            else:
                current_second = None

        elif (
            len(tokens) == 12
            and current_second is not None
        ):

            for i in range(
                0,
                12,
                2
            ):

                try:

                    third = int(
                        tokens[i]
                    )

                    odd = float(
                        tokens[i + 1]
                    )

                except Exception:
                    continue

                first = (
                    i // 2
                ) + 1

                if (
                    odd > 0
                    and len(
                        {
                            first,
                            current_second,
                            third,
                        }
                    ) == 3
                ):

                    out[
                        (
                            first,
                            current_second,
                            third,
                        )
                    ] = odd

    # -----------------------------------------
    # oddsPoint構造からも補完
    # -----------------------------------------

    for tr in soup.find_all("tr"):

        cells = tr.find_all("td")

        idxs = [
            i
            for i, c in enumerate(cells)
            if "oddsPoint"
            in c.get("class", [])
        ]

        if len(idxs) != 6:
            continue

        for first, idx in enumerate(
            idxs,
            1
        ):

            if idx < 2:
                continue

            try:

                second = int(
                    cells[idx - 2]
                    .get_text(
                        " ",
                        strip=True
                    )
                )

                third = int(
                    cells[idx - 1]
                    .get_text(
                        " ",
                        strip=True
                    )
                )

                text = cells[idx].get_text(
                    " ",
                    strip=True
                )

                m = re.search(
                    r"\d+(?:\.\d+)?",
                    text.replace(",", "")
                )

                odd = (
                    float(m.group())
                    if m
                    else 0
                )

            except Exception:
                continue

            if (
                odd > 0
                and len(
                    {
                        first,
                        second,
                        third,
                    }
                ) == 3
            ):

                out[
                    (
                        first,
                        second,
                        third,
                    )
                ] = odd

    return out
