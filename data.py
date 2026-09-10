import re
import unicodedata
import requests

from bs4 import BeautifulSoup
from functools import lru_cache


BASE_URL = "https://www.boatrace.jp/owpc/pc"


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


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    )
}


def _normalize(text):
    return unicodedata.normalize(
        "NFKC",
        str(text or ""),
    ).strip()


@lru_cache(maxsize=512)
def _get(url):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20,
        )

        response.raise_for_status()

        response.encoding = (
            response.apparent_encoding
            or "utf-8"
        )

        return response.text

    except Exception:
        return ""


def get_data(date):
    """
    日付情報。
    """
    return {
        "date": str(date),
    }


# ============================================================
# レースデータ
# ============================================================

def get_race(
    raw,
    stadium_number,
    race_number,
):
    if not raw:
        return None

    date = str(raw["date"])

    url = (
        f"{BASE_URL}/race/racelist"
        f"?hd={date}"
        f"&jcd={int(stadium_number):02d}"
        f"&rno={int(race_number)}"
    )

    html = _get(url)

    if not html:
        return None

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    racers = _parse_racers(soup)

    if len(racers) != 6:
        racers = _dummy_racers()

    return {
        "date": date,
        "stadium_number": int(stadium_number),
        "race_number": int(race_number),
        "racers": racers,
        "html": soup,
    }


def get_race_racers(race):
    if not race:
        return []

    racers = race.get("racers")

    if racers:
        return racers

    return _dummy_racers()


def _parse_float_lines(text):
    text = _normalize(text)

    lines = [
        _normalize(x)
        for x in text.splitlines()
    ]

    values = []

    for line in lines:

        if not re.fullmatch(
            r"-?\d+(?:\.\d+)?",
            line,
        ):
            continue

        try:
            values.append(float(line))
        except Exception:
            pass

    return values


def _parse_racers(soup):
    racers = {}

    for tr in soup.find_all("tr"):

        cells = tr.find_all(
            "td",
            recursive=False,
        )

        if not cells:
            continue

        texts = [
            _normalize(
                cell.get_text(
                    " ",
                    strip=True,
                )
            )
            for cell in cells
        ]

        # 行全体
        row_text = " ".join(texts)

        # A1/B1/B2等がない行は選手行ではない
        if not re.search(
            r"\b[ABC][12]\b",
            row_text,
        ):
            continue

        number = None

        for text in texts[:3]:

            m = re.fullmatch(
                r"[1-6]",
                text,
            )

            if m:
                number = int(text)
                break

        if number is None:
            continue

        # すでに取得済みならスキップ
        if number in racers:
            continue

        # 統計セルを探す
        stat_groups = []

        for text in texts:

            values = _parse_float_lines(
                text
            )

            if len(values) >= 3:
                stat_groups.append(
                    values[:3]
                )

        # 通常は
        # 全国 / 当地 / モーター / ボート
        # の4グループ
        if len(stat_groups) < 4:
            continue

        national = stat_groups[0]
        local = stat_groups[1]
        motor = stat_groups[2]
        boat = stat_groups[3]

        racers[number] = {
            "number": number,
            "raw": {
                "national_win_rate":
                    national[0],
                "national_top_2_percent":
                    national[1],
                "national_top_3_percent":
                    national[2],

                "local_win_rate":
                    local[0],
                "local_top_2_percent":
                    local[1],
                "local_top_3_percent":
                    local[2],

                "motor_top_2_percent":
                    motor[1],
                "motor_top_3_percent":
                    motor[2],

                "boat_top_2_percent":
                    boat[1],
                "boat_top_3_percent":
                    boat[2],
            },
        }

    if len(racers) != 6:
        return []

    return [
        racers[i]
        for i in range(1, 7)
    ]


def _dummy_racers():
    return [
        {
            "number": i,
            "raw": {
                "national_win_rate": 0.0,
                "national_top_2_percent": 0.0,
                "national_top_3_percent": 0.0,
                "local_win_rate": 0.0,
                "local_top_2_percent": 0.0,
                "local_top_3_percent": 0.0,
                "motor_top_2_percent": 0.0,
                "motor_top_3_percent": 0.0,
                "boat_top_2_percent": 0.0,
                "boat_top_3_percent": 0.0,
            },
        }
        for i in range(1, 7)
    ]


# ============================================================
# 3連単オッズ
# ============================================================

def _boat_number(text):
    text = _normalize(text)

    if not re.fullmatch(
        r"[1-6]",
        text,
    ):
        return None

    return int(text)


def _parse_odds(text):
    text = _normalize(text)

    text = text.replace(
        ",",
        "",
    )

    text = text.replace(
        "倍",
        "",
    )

    if not text:
        return None

    if text in (
        "-",
        "－",
        "—",
        "―",
    ):
        return None

    m = re.search(
        r"\d+(?:\.\d+)?",
        text,
    )

    if not m:
        return None

    try:
        value = float(m.group())

        if value <= 0:
            return None

        return value

    except Exception:
        return None


def get_trifecta_odds(
    stadium_number,
    race_number,
    date,
):
    """
    BOAT RACE公式3連単オッズ。

    公式HTMLはrowspan構造になっており、

    1行目:
        2着 / 3着 / オッズ

    続く行:
        3着 / オッズ

    となる。

    2着を列ごとに保持しながら解析する。
    """

    url = (
        f"{BASE_URL}/race/odds3t"
        f"?hd={date}"
        f"&jcd={int(stadium_number):02d}"
        f"&rno={int(race_number)}"
    )

    html = _get(url)

    if not html:
        return {}

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    odds = {}

    # 各1着艇の現在の2着艇
    second_cache = {
        i: None
        for i in range(1, 7)
    }

    for tr in soup.find_all("tr"):

        cells = tr.find_all(
            "td",
            recursive=False,
        )

        if not cells:
            continue

        # oddsPointを6個含む行だけ
        odds_positions = []

        for index, cell in enumerate(cells):

            classes = cell.get(
                "class",
                [],
            )

            if "oddsPoint" in classes:
                odds_positions.append(index)

        if len(odds_positions) != 6:
            continue

        groups = []
        current = []

        for cell in cells:

            classes = cell.get(
                "class",
                [],
            )

            is_odds = (
                "oddsPoint"
                in classes
            )

            text = _normalize(
                cell.get_text(
                    " ",
                    strip=True,
                )
            )

            if is_odds:

                current.append(text)

                groups.append(
                    current
                )

                current = []

            else:
                current.append(text)

        if len(groups) != 6:
            continue

        for first in range(1, 7):

            group = groups[first - 1]

            if len(group) < 2:
                continue

            odd = _parse_odds(
                group[-1]
            )

            if odd is None:
                continue

            values = group[:-1]

            second = None
            third = None

            # ------------------------------------------------
            # 3セル構造
            # [2着, 3着, オッズ]
            # ------------------------------------------------

            if len(values) >= 2:

                possible_second = (
                    _boat_number(
                        values[-2]
                    )
                )

                possible_third = (
                    _boat_number(
                        values[-1]
                    )
                )

                if (
                    possible_second
                    is not None
                    and
                    possible_third
                    is not None
                ):
                    second = (
                        possible_second
                    )

                    third = (
                        possible_third
                    )

                    second_cache[
                        first
                    ] = second

            # ------------------------------------------------
            # 2セル構造
            # [3着, オッズ]
            # ------------------------------------------------

            elif len(values) == 1:

                second = (
                    second_cache[first]
                )

                third = _boat_number(
                    values[0]
                )

            if (
                second is None
                or third is None
            ):
                continue

            if (
                first == second
                or first == third
                or second == third
            ):
                continue

            odds[
                (
                    first,
                    second,
                    third,
                )
            ] = odd

    return odds


# ============================================================
# バックテスト用 結果一覧
# ============================================================

@lru_cache(maxsize=128)
def _resultlist_html(
    date,
    stadium_number,
):
    url = (
        f"{BASE_URL}/race/resultlist"
        f"?hd={date}"
        f"&jcd={int(stadium_number):02d}"
    )

    return _get(url)


def all_races_for_date(raw):
    """
    その日に完了している全レース。
    """

    if not raw:
        return []

    date = str(raw["date"])

    result = []

    for stadium_number in range(1, 25):

        html = _resultlist_html(
            date,
            stadium_number,
        )

        if not html:
            continue

        races = _parse_resultlist(
            html
        )

        for race in races:

            result.append(
                (
                    stadium_number,
                    race["race_number"],
                    race,
                )
            )

    # R順を維持
    result.sort(
        key=lambda x: (
            x[1],
            x[0],
        )
    )

    return result


def _parse_resultlist(html):
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    results = []

    for tr in soup.find_all("tr"):

        cells = tr.find_all(
            ["th", "td"],
            recursive=False,
        )

        if not cells:
            continue

        texts = [
            _normalize(
                cell.get_text(
                    " ",
                    strip=True,
                )
            )
            for cell in cells
        ]

        if not texts:
            continue

        m_race = re.match(
            r"^(\d{1,2})R$",
            texts[0],
        )

        if not m_race:
            continue

        race_number = int(
            m_race.group(1)
        )

        row_text = " ".join(texts)

        m_combo = re.search(
            r"([1-6])\s*-\s*"
            r"([1-6])\s*-\s*"
            r"([1-6])",
            row_text,
        )

        if not m_combo:
            continue

        actual = [
            int(m_combo.group(1)),
            int(m_combo.group(2)),
            int(m_combo.group(3)),
        ]

        # 払戻金
        amounts = re.findall(
            r"¥\s*([0-9,]+)",
            row_text,
        )

        payout = 0

        if amounts:
            try:
                payout = int(
                    amounts[0].replace(
                        ",",
                        "",
                    )
                )
            except Exception:
                payout = 0

        results.append({
            "race_number": race_number,
            "actual": actual,
            "payout": payout,
        })

    return results


def get_actual_order(race):
    if not race:
        return []

    actual = race.get(
        "actual",
        [],
    )

    return [
        int(x)
        for x in actual
        if str(x).isdigit()
    ][:6]


def get_payouts(race):
    if not race:
        return {}

    combo = race.get(
        "actual",
        [],
    )

    payout = int(
        race.get(
            "payout",
            0,
        )
        or 0
    )

    if len(combo) < 3:
        return {}

    actual_combo = "-".join(
        str(x)
        for x in combo[:3]
    )

    return {
        "trifecta": [
            {
                "combination":
                    actual_combo,
                "amount":
                    payout,
            }
        ]
    }


def get_stadium_name(number):
    return STADIUMS.get(
        int(number),
        str(number),
    )
