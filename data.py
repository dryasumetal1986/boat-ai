import re
from datetime import date, timedelta

import requests
import streamlit as st
from bs4 import BeautifulSoup


# =========================
# Boatrace Open API
# =========================

API = "https://boatraceopenapi.github.io/api/v1"


# =========================
# HTTP
# =========================

def make_session():

    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/140.0 Safari/537.36"
            )
        }
    )

    return session


# =========================
# 日付データ
# =========================

@st.cache_data(ttl=180)
def get_data(d):

    url = (
        f"{API}/"
        f"{d:%Y/%Y%m%d}.json"
    )

    session = make_session()

    response = session.get(
        url,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


# =========================
# list / dict 共通
# =========================

def racers(value):

    if isinstance(value, list):
        return value

    if isinstance(value, dict):
        return list(value.values())

    return []


# =========================
# レース取得
# =========================

def get_race(data, sno, rno):

    stadiums = (
        data
        .get("programs", {})
        .get("stadiums", {})
    )

    stadium = stadiums.get(
        str(sno)
    )

    if not stadium:
        return None

    races = stadium.get(
        "races",
        {}
    )

    return races.get(
        str(rno)
    )


# =========================
# 過去14日
# =========================

@st.cache_data(ttl=1800)
def history14(td):

    rows = []

    for i in range(1, 15):

        d = td - timedelta(days=i)

        if d < date(2026, 1, 1):
            continue

        try:
            data = get_data(d)

        except Exception:
            continue

        stadiums = (
            data
            .get("programs", {})
            .get("stadiums", {})
        )

        for sno, stadium in stadiums.items():

            races = stadium.get(
                "races",
                {}
            )

            for rno, race in races.items():

                result = race.get(
                    "result",
                    {}
                )

                result_racers = result.get(
                    "racers",
                    {}
                )

                places = {}

                for x in racers(
                    result_racers
                ):

                    place = str(
                        x.get(
                            "place_number",
                            "",
                        )
                    )

                    if place in ["1", "2", "3"]:

                        places[place] = str(
                            x.get(
                                "number",
                                "",
                            )
                        )

                if "1" not in places:
                    continue

                race_racers = race.get(
                    "racers",
                    {}
                )

                if not isinstance(
                    race_racers,
                    dict,
                ):
                    continue

                for lane in range(1, 7):

                    racer = race_racers.get(
                        str(lane),
                        {}
                    )

                    if not racer:
                        continue

                    number = str(
                        racer.get(
                            "number",
                            "",
                        )
                    )

                    if not number:
                        continue

                    rows.append(
                        {
                            "日付": d,
                            "場": int(sno),
                            "レース": int(rno),
                            "枠": lane,
                            "選手番号": number,

                            "1着": int(
                                number
                                == places.get("1")
                            ),

                            "2着": int(
                                number
                                == places.get("2")
                            ),

                            "3着": int(
                                number
                                == places.get("3")
                            ),
                        }
                    )

    return rows


# =========================================================
# 3連単オッズURL
# =========================================================

def odds_url(td, sno, rno):

    return (
        "https://www.boatrace.jp/"
        "owpc/pc/race/odds3t"
        f"?rno={rno}"
        f"&jcd={sno:02d}"
        f"&hd={td:%Y%m%d}"
    )


# =========================================================
# オッズ文字列
# =========================================================

def parse_odds(value):

    if value is None:
        return None

    text = str(value).strip()

    text = text.replace(
        ",",
        "",
    )

    if not re.search(
        r"\d",
        text,
    ):
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


# =========================================================
# 重要
#
# BOAT RACE公式3連単表の並び順
#
# ここは単純な
# 123,124,125...
# ではない
# =========================================================

TRIFECTA_CODES = [

    123, 213, 312, 412, 512, 612,
    124, 214, 314, 413, 513, 613,
    125, 215, 315, 415, 514, 614,
    126, 216, 316, 416, 516, 615,

    132, 231, 321, 421, 521, 621,
    134, 234, 324, 423, 523, 623,
    135, 235, 325, 425, 524, 624,
    136, 236, 326, 426, 526, 625,

    142, 241, 341, 431, 531, 631,
    143, 243, 342, 432, 532, 632,
    145, 245, 345, 435, 534, 634,
    146, 246, 346, 436, 536, 635,

    152, 251, 351, 451, 541, 641,
    153, 253, 352, 452, 542, 642,
    154, 254, 354, 453, 543, 643,
    156, 256, 356, 456, 546, 645,

    162, 261, 361, 461, 561, 651,
    163, 263, 362, 462, 562, 652,
    164, 264, 364, 463, 563, 653,
    165, 265, 365, 465, 564, 654,
]


# =========================================================
# 3連単オッズ取得
# =========================================================

@st.cache_data(ttl=20)
def get_odds(td, sno, rno):

    url = odds_url(
        td,
        sno,
        rno,
    )

    session = make_session()

    response = session.get(
        url,
        timeout=30,
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    # ---------------------------------
    # データなし
    # ---------------------------------

    if "データがありません" in response.text:
        return {}

    # ---------------------------------
    # 中止
    # ---------------------------------

    if "中止" in response.text:
        return {}

    # ---------------------------------
    # 公式3連単テーブル
    # ---------------------------------

    tables = soup.find_all(
        "div",
        class_="table1",
    )

    if len(tables) < 2:
        return {}

    tbody = tables[1].find(
        "tbody"
    )

    if tbody is None:
        return {}

    rows = tbody.find_all(
        "tr"
    )

    odds_list = []

    for row in rows:

        cells = row.find_all(
            "td",
            class_="oddsPoint",
        )

        for cell in cells:

            value = cell.get_text(
                " ",
                strip=True,
            )

            odd = parse_odds(
                value
            )

            if odd is not None:

                odds_list.append(
                    odd
                )

    # ---------------------------------
    # 120個取れているか確認
    # ---------------------------------

    if len(odds_list) != 120:

        return {}


    # ---------------------------------
    # 公式の並び順で対応
    # ---------------------------------

    result = {}

    for code, odd in zip(
        TRIFECTA_CODES,
        odds_list,
    ):

        code = str(code)

        key = (
            f"{code[0]}-"
            f"{code[1]}-"
            f"{code[2]}"
        )

        result[key] = odd

    return result


# =========================================================
# オッズキャッシュ削除
# =========================================================

def clear_odds_cache():

    try:
        get_odds.clear()

    except Exception:
        pass
