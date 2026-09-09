import requests
import pandas as pd
import streamlit as st

from bs4 import BeautifulSoup
from datetime import date, timedelta


API = "https://boatraceopenapi.github.io/api/v1"


# =========================================================
# 基本データ取得
# =========================================================

@st.cache_data(ttl=180)
def get_data(d):

    url = f"{API}/{d:%Y/%Y%m%d}.json"

    r = requests.get(
        url,
        timeout=20,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    r.raise_for_status()

    return r.json()


# =========================================================
# racer list 共通処理
# =========================================================

def racers(x):

    if isinstance(x, list):
        return x

    if isinstance(x, dict):
        return list(x.values())

    return []


# =========================================================
# race取得
# =========================================================

def get_race(data, sno, rno):

    stadiums = (
        data
        .get("programs", {})
        .get("stadiums", {})
    )

    stadium = stadiums.get(str(sno))

    if not stadium:
        return None

    return (
        stadium
        .get("races", {})
        .get(str(rno))
    )


# =========================================================
# 直前情報 map
# =========================================================

def pmap(race):

    out = {}

    preview = (
        race
        .get("preview", {})
        .get("racers", {})
    )

    for p in racers(preview):

        entry = p.get("entry_number")
        course = p.get("course_number")

        if entry is not None:
            out[str(entry)] = p

        if course is not None:
            out.setdefault(
                str(course),
                p
            )

    return out


# =========================================================
# 過去14日データ
# =========================================================

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

                result_racers = (
                    race
                    .get("result", {})
                    .get("racers", {})
                )

                places = {}

                for x in racers(result_racers):

                    place = str(
                        x.get(
                            "place_number",
                            ""
                        )
                    )

                    if place in ["1", "2", "3"]:

                        places[place] = str(
                            x.get(
                                "number",
                                ""
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
                    dict
                ):
                    continue

                preview = (
                    race
                    .get("preview", {})
                    .get("racers", {})
                )

                preview_map = {}

                for p in racers(preview):

                    entry = p.get(
                        "entry_number"
                    )

                    course = p.get(
                        "course_number"
                    )

                    if entry is not None:
                        preview_map[
                            str(entry)
                        ] = p

                    if course is not None:
                        preview_map.setdefault(
                            str(course),
                            p
                        )

                for lane in range(1, 7):

                    r = race_racers.get(
                        str(lane),
                        {}
                    )

                    if not r:
                        continue

                    number = str(
                        r.get(
                            "number",
                            ""
                        )
                    )

                    p = preview_map.get(
                        str(lane),
                        {}
                    )

                    course = p.get(
                        "course_number"
                    )

                    try:
                        course = int(course)
                    except Exception:
                        course = lane

                    rows.append({

                        "日付": d,

                        "場": int(sno),

                        "レース": int(rno),

                        "枠": lane,

                        "コース": course,

                        "選手番号": number,

                        "1着": int(
                            number ==
                            places.get("1")
                        ),

                        "2着": int(
                            number ==
                            places.get("2")
                        ),

                        "3着": int(
                            number ==
                            places.get("3")
                        )

                    })

    return rows


# =========================================================
# 3連単オッズ取得
# =========================================================

@st.cache_data(ttl=30)
def get_odds(td, sno, rno):

    """
    BOATRACE公式サイトから
    3連単オッズを取得する。

    戻り値:
        {
            "1-2-3": 12.5,
            "1-2-4": 18.2,
            ...
        }
    """

    hd = td.strftime("%Y%m%d")

    url = (
        "https://www.boatrace.jp"
        "/owpc/pc/race/odds3t"
        f"?jcd={int(sno):02d}"
        f"&hd={hd}"
        f"&rno={int(rno)}"
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/131.0 Safari/537.36"
        ),
        "Accept-Language": "ja-JP,ja;q=0.9"
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=20
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        odds = {}

        # ---------------------------------------------
        # オッズ表の table を検索
        # ---------------------------------------------

        tables = soup.find_all("table")

        for table in tables:

            rows = table.find_all("tr")

            for row in rows:

                cells = row.find_all(
                    ["th", "td"]
                )

                if not cells:
                    continue

                text = [
                    c.get_text(
                        " ",
                        strip=True
                    )
                    for c in cells
                ]

                line = " ".join(text)

                # -----------------------------------------
                # 3連単組み合わせを探す
                # -----------------------------------------

                import re

                matches = re.findall(
                    r"([1-6])\s*-\s*([1-6])\s*-\s*([1-6])",
                    line
                )

                if not matches:
                    continue

                for a, b, c in matches:

                    if (
                        a == b
                        or a == c
                        or b == c
                    ):
                        continue

                    combo = (
                        f"{a}-{b}-{c}"
                    )

                    # 行内の数値からオッズ候補を探す
                    for value in text:

                        value = value.replace(
                            ",",
                            ""
                        )

                        value = value.replace(
                            "倍",
                            ""
                        )

                        try:

                            x = float(value)

                        except Exception:
                            continue

                        if (
                            x >= 1.0
                            and x <= 10000
                        ):

                            odds.setdefault(
                                combo,
                                x
                            )

                            break

        return odds

    except Exception:

        return {}


# =========================================================
# オッズ取得確認用
# =========================================================

def odds_url(td, sno, rno):

    hd = td.strftime("%Y%m%d")

    return (
        "https://www.boatrace.jp"
        "/owpc/pc/race/odds3t"
        f"?jcd={int(sno):02d}"
        f"&hd={hd}"
        f"&rno={int(rno)}"
            )
