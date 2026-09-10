import requests
import streamlit as st

from bs4 import BeautifulSoup


API_BASE = "https://boatraceopenapi.github.io/api/v1"
ODDS_URL = (
    "https://www.boatrace.jp/owpc/pc/race/odds3t"
    "?hd={date}&jcd={stadium:02d}&rno={race}"
)


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


def get_stadium_name(number):
    return STADIUMS.get(
        int(number),
        f"{number}場",
    )


@st.cache_data(
    ttl=1800,
    show_spinner=False,
)
def get_data(target_date):
    """
    target_date:
        YYYYMMDD
    """

    target_date = str(target_date)

    if len(target_date) != 8:
        return {}

    year = target_date[:4]

    url = (
        f"{API_BASE}/"
        f"{year}/"
        f"{target_date}.json"
    )

    try:
        response = requests.get(
            url,
            timeout=12,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(iPhone; CPU iPhone OS 17_0 "
                    "like Mac OS X)"
                )
            },
        )

        if response.status_code != 200:
            return {}

        return response.json()

    except Exception:
        return {}


def get_race(
    raw,
    stadium_number,
    race_number,
):
    if not raw:
        return {}

    programs = raw.get(
        "programs",
        {},
    )

    stadiums = programs.get(
        "stadiums",
        {},
    )

    stadium = stadiums.get(
        str(stadium_number),
        {},
    )

    races = stadium.get(
        "races",
        {},
    )

    return races.get(
        str(race_number),
        {},
    )


def get_race_rows(raw):
    rows = []

    if not raw:
        return rows

    programs = raw.get(
        "programs",
        {},
    )

    stadiums = programs.get(
        "stadiums",
        {},
    )

    for stadium_key, stadium_data in stadiums.items():

        try:
            stadium_number = int(
                stadium_key
            )
        except Exception:
            continue

        races = stadium_data.get(
            "races",
            {},
        )

        for race_key, race in races.items():

            try:
                race_number = int(
                    race_key
                )
            except Exception:
                continue

            if not race:
                continue

            rows.append(
                {
                    "stadium_number": (
                        stadium_number
                    ),
                    "stadium": (
                        get_stadium_name(
                            stadium_number
                        )
                    ),
                    "race_number": (
                        race_number
                    ),
                    "race": race,
                }
            )

    rows.sort(
        key=lambda x: (
            x["stadium_number"],
            x["race_number"],
        )
    )

    return rows


def all_races_for_date(raw):
    result = []

    for row in get_race_rows(raw):
        result.append(
            (
                row["stadium_number"],
                row["race_number"],
                row["race"],
            )
        )

    return result


def _normalize_racers(racers):
    """
    API v1は
        {"1": {...}, "2": {...}}
    の辞書形式。

    念のためリスト形式にも対応。
    """

    if not racers:
        return []

    result = []

    if isinstance(
        racers,
        dict,
    ):
        iterable = racers.items()
    else:
        iterable = enumerate(
            racers,
            start=1,
        )

    for key, racer in iterable:

        if not isinstance(
            racer,
            dict,
        ):
            continue

        entry_number = racer.get(
            "entry_number"
        )

        if entry_number is None:
            try:
                entry_number = int(key)
            except Exception:
                continue

        try:
            entry_number = int(
                entry_number
            )
        except Exception:
            continue

        result.append(
            {
                "number": entry_number,
                "name": str(
                    racer.get(
                        "name",
                        "選手",
                    )
                ),
                "raw": racer,
            }
        )

    result.sort(
        key=lambda x: x["number"]
    )

    return result


def get_race_racers(race):
    if not race:
        return []

    racers = race.get(
        "racers",
        {},
    )

    return _normalize_racers(
        racers
    )


def get_actual_order(race):
    if not race:
        return []

    result = race.get(
        "result",
        {},
    )

    racers = result.get(
        "racers",
        {},
    )

    normalized = []

    if isinstance(
        racers,
        dict,
    ):
        iterable = racers.items()
    else:
        iterable = enumerate(
            racers,
            start=1,
        )

    for key, racer in iterable:

        if not isinstance(
            racer,
            dict,
        ):
            continue

        place = racer.get(
            "place_number"
        )

        if place is None:
            place = racer.get(
                "place"
            )

        entry = racer.get(
            "entry_number"
        )

        if entry is None:
            try:
                entry = int(key)
            except Exception:
                continue

        try:
            place = int(place)
            entry = int(entry)
        except Exception:
            continue

        if place > 0:
            normalized.append(
                (
                    place,
                    entry,
                )
            )

    normalized.sort(
        key=lambda x: x[0]
    )

    return [
        entry
        for _, entry in normalized
    ]


def get_race_date(
    race,
    fallback="",
):
    value = race.get(
        "date"
    )

    if value:
        return str(value)

    return fallback


def _parse_odds(text):
    if not text:
        return None

    text = (
        text.strip()
        .replace(",", "")
        .replace("倍", "")
    )

    if text in [
        "",
        "---",
        "－",
        "-",
        "欠場",
        "発売なし",
    ]:
        return None

    try:
        return float(text)
    except Exception:
        return None


@st.cache_data(
    ttl=60,
    show_spinner=False,
)
def get_trifecta_odds(
    target_date,
    stadium_number,
    race_number,
):
    """
    BOATRACE公式3連単オッズ。

    公式表は120個の数字を単純に
    zipしてはいけない。

    1着ごとに
        2着 / 3着 / オッズ
    が6組並ぶため、
    HTMLの表構造から
        (1着, 2着, 3着)
    を復元する。
    """

    url = ODDS_URL.format(
        date=target_date,
        stadium=int(
            stadium_number
        ),
        race=int(
            race_number
        ),
    )

    try:
        response = requests.get(
            url,
            timeout=12,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(iPhone; CPU iPhone OS 17_0 "
                    "like Mac OS X)"
                )
            },
        )

        if response.status_code != 200:
            return {}

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        odds = {}

        for tr in soup.select("tr"):

            nodes = tr.select(
                "td.oddsPoint"
            )

            if len(nodes) != 6:
                continue

            cells = tr.find_all("td")

            if len(cells) < 18:
                continue

            texts = [
                cell.get_text(
                    " ",
                    strip=True,
                )
                for cell in cells
            ]

            for first in range(1, 7):

                base = (
                    first - 1
                ) * 3

                if base + 2 >= len(
                    texts
                ):
                    continue

                second_text = texts[
                    base
                ]

                third_text = texts[
                    base + 1
                ]

                odds_text = texts[
                    base + 2
                ]

                try:
                    second = int(
                        second_text
                    )

                    third = int(
                        third_text
                    )
                except Exception:
                    continue

                if len(
                    {
                        first,
                        second,
                        third,
                    }
                ) != 3:
                    continue

                value = _parse_odds(
                    odds_text
                )

                if value is None:
                    continue

                odds[
                    (
                        first,
                        second,
                        third,
                    )
                ] = value

        return odds

    except Exception:
        return {}
