import requests
import streamlit as st
from bs4 import BeautifulSoup

API_URL = "https://boatraceopenapi.github.io/api/v1/{date}.json"
ODDS_URL = "https://www.boatrace.jp/owpc/pc/race/odds3t?hd={date}&jcd={stadium:02d}&rno={race}"

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


@st.cache_data(ttl=3600, show_spinner=False)
def get_data(target_date):
    url = API_URL.format(date=target_date)

    try:
        r = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
        )

        if r.status_code != 200:
            return {}

        return r.json()

    except Exception:
        return {}


def get_stadium_name(number):
    return STADIUMS.get(number, f"{number}場")


def get_race_rows(raw):
    rows = []

    programs = raw.get("programs", {})

    for stadium_key, stadium_data in programs.get("stadiums", {}).items():
        try:
            stadium_number = int(stadium_key)
        except Exception:
            continue

        races = stadium_data.get("races", {})

        for race_key, race in races.items():
            try:
                race_number = int(race_key)
            except Exception:
                continue

            racers = race.get("racers", [])

            if not racers:
                continue

            rows.append(
                {
                    "stadium_number": stadium_number,
                    "stadium": get_stadium_name(stadium_number),
                    "race_number": race_number,
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


def get_race(raw, stadium_number, race_number):
    programs = raw.get("programs", {})
    stadiums = programs.get("stadiums", {})

    stadium = stadiums.get(str(stadium_number), {})
    races = stadium.get("races", {})

    return races.get(str(race_number), {})


def get_actual_order(race):
    result = race.get("result", {})
    racers = result.get("racers", [])

    order = []

    for racer in racers:
        number = racer.get("number")

        if number is None:
            number = racer.get("racer_number")

        try:
            number = int(number)
        except Exception:
            continue

        order.append(number)

    return order


def get_racer_name(racer):
    for key in [
        "name",
        "racer_name",
        "racerName",
    ]:
        if racer.get(key):
            return str(racer[key])

    return "選手"


def get_race_racers(race):
    racers = race.get("racers", [])

    result = []

    for racer in racers:
        number = racer.get("number")

        if number is None:
            number = racer.get("racer_number")

        try:
            number = int(number)
        except Exception:
            continue

        result.append(
            {
                "number": number,
                "name": get_racer_name(racer),
                "raw": racer,
            }
        )

    result.sort(key=lambda x: x["number"])

    return result


def get_race_date(race, fallback=""):
    value = race.get("date")

    if value:
        return str(value)

    return fallback


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


def _parse_odds_text(text):
    text = text.strip()
    text = text.replace(",", "")

    if not text:
        return None

    for bad in [
        "欠場",
        "発売なし",
        "---",
        "－",
        "-",
    ]:
        if bad in text:
            return None

    try:
        return float(text)
    except Exception:
        return None


@st.cache_data(ttl=60, show_spinner=False)
def get_trifecta_odds(target_date, stadium_number, race_number):
    """
    BOATRACE公式3連単オッズを取得。

    重要:
    公式ページは単純な120個のオッズ配列ではない。
    1行につき6艇分の
        2着 / 3着 / オッズ
    が並ぶため、その表構造を使って
    (1着,2着,3着) -> オッズ
    に正しく変換する。
    """

    url = ODDS_URL.format(
        date=target_date,
        stadium=stadium_number,
        race=race_number,
    )

    try:
        r = requests.get(
            url,
            timeout=10,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(iPhone; CPU iPhone OS 17_0 like Mac OS X)"
                )
            },
        )

        if r.status_code != 200:
            return {}

        soup = BeautifulSoup(r.text, "html.parser")

        odds = {}

        # oddsPoint が6個ある行を対象にする。
        for tr in soup.select("tr"):
            odds_nodes = tr.select("td.oddsPoint")

            if len(odds_nodes) != 6:
                continue

            cells = tr.find_all("td")

            if len(cells) < 18:
                continue

            texts = [
                c.get_text(" ", strip=True)
                for c in cells
            ]

            # 1艇につき
            # 2着 / 3着 / オッズ
            # の3セル。
            for first in range(1, 7):
                base = (first - 1) * 3

                if base + 2 >= len(texts):
                    continue

                second_text = texts[base]
                third_text = texts[base + 1]
                odds_text = texts[base + 2]

                try:
                    second = int(second_text)
                    third = int(third_text)
                except Exception:
                    continue

                if not (
                    1 <= first <= 6
                    and 1 <= second <= 6
                    and 1 <= third <= 6
                ):
                    continue

                if len({first, second, third}) != 3:
                    continue

                value = _parse_odds_text(odds_text)

                if value is None:
                    continue

                odds[(first, second, third)] = value

        # 念のため別方式でも補完。
        if len(odds) < 100:
            for tr in soup.select("tr"):
                nodes = tr.select("td.oddsPoint")

                if len(nodes) != 6:
                    continue

                cells = tr.find_all("td")

                if len(cells) < 18:
                    continue

                for i, node in enumerate(nodes):
                    previous = []
                    current = node

                    for sibling in reversed(list(current.previous_siblings)):
                        if getattr(sibling, "name", None) == "td":
                            previous.append(
                                sibling.get_text(
                                    " ",
                                    strip=True,
                                )
                            )

                            if len(previous) == 2:
                                break

                    if len(previous) != 2:
                        continue

                    try:
                        second = int(previous[1])
                        third = int(previous[0])
                    except Exception:
                        continue

                    first = i + 1

                    value = _parse_odds_text(
                        node.get_text(" ", strip=True)
                    )

                    if value is None:
                        continue

                    if len({first, second, third}) != 3:
                        continue

                    odds[(first, second, third)] = value

        return odds

    except Exception:
        return {}
