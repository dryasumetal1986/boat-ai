import re
import time
from datetime import date, timedelta

import requests
import streamlit as st
from bs4 import BeautifulSoup


# =========================================================
# BOATRACE OPEN API
# =========================================================

API = "https://boatraceopenapi.github.io/api/v1"


# =========================================================
# HTTP Session
# =========================================================

SESSION = requests.Session()

SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    ),
    "Accept-Language": "ja-JP,ja;q=0.9",
})


# =========================================================
# 基本データ取得
# =========================================================

@st.cache_data(ttl=180)
def get_data(d):

    url = f"{API}/{d:%Y/%Y%m%d}.json"

    response = SESSION.get(
        url,
        timeout=20
    )

    response.raise_for_status()

    return response.json()


# =========================================================
# racer list 共通処理
# =========================================================

def racers(value):

    if isinstance(value, list):
        return value

    if isinstance(value, dict):
        return list(value.values())

    return []


# =========================================================
# レース取得
# =========================================================

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


# =========================================================
# 直前情報MAP
# =========================================================

def pmap(race):

    result = {}

    preview = (
        race
        .get("preview", {})
        .get("racers", {})
    )

    for p in racers(preview):

        entry_number = p.get(
            "entry_number"
        )

        course_number = p.get(
            "course_number"
        )

        if entry_number is not None:

            result[
                str(entry_number)
            ] = p

        if course_number is not None:

            result.setdefault(
                str(course_number),
                p
            )

    return result


# =========================================================
# 数値変換
# =========================================================

def to_float(value, default=0.0):

    if value is None:
        return default

    try:
        return float(value)

    except (TypeError, ValueError):
        return default


# =========================================================
# 過去14日データ
# =========================================================

@st.cache_data(ttl=1800)
def history14(td):

    rows = []

    for days_ago in range(1, 15):

        d = td - timedelta(
            days=days_ago
        )

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

                # -----------------------------------------
                # 結果
                # -----------------------------------------

                result_racers = (
                    race
                    .get("result", {})
                    .get("racers", {})
                )

                places = {}

                for item in racers(
                    result_racers
                ):

                    place = str(
                        item.get(
                            "place_number",
                            ""
                        )
                    )

                    if place in (
                        "1",
                        "2",
                        "3"
                    ):

                        places[place] = str(
                            item.get(
                                "number",
                                ""
                            )
                        )

                if "1" not in places:
                    continue

                # -----------------------------------------
                # 出走選手
                # -----------------------------------------

                race_racers = race.get(
                    "racers",
                    {}
                )

                if not isinstance(
                    race_racers,
                    dict
                ):
                    continue

                # -----------------------------------------
                # 直前情報
                # -----------------------------------------

                preview = (
                    race
                    .get("preview", {})
                    .get("racers", {})
                )

                preview_map = {}

                for p in racers(
                    preview
                ):

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

                # -----------------------------------------
                # 6艇
                # -----------------------------------------

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
                            ""
                        )
                    )

                    preview_data = preview_map.get(
                        str(lane),
                        {}
                    )

                    course = preview_data.get(
                        "course_number"
                    )

                    try:
                        course = int(course)

                    except (TypeError, ValueError):
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
# 公式3連単オッズURL
# =========================================================

def odds_url(td, sno, rno):

    hd = td.strftime(
        "%Y%m%d"
    )

    return (
        "https://www.boatrace.jp"
        "/owpc/pc/race/odds3t"
        f"?rno={int(rno)}"
        f"&jcd={int(sno):02d}"
        f"&hd={hd}"
    )


# =========================================================
# 3連単120通り
#
# BOATRACE公式オッズ表の並び順
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
# オッズ文字列 → float
# =========================================================

def parse_odds(value):

    if value is None:
        return None

    text = str(value)

    # 空欄・欠場など
    if not text:
        return None

    # 改行など除去
    text = (
        text
        .replace("\n", "")
        .replace("\r", "")
        .replace("\t", "")
        .strip()
    )

    # -----------------------------
    # 数字を取得
    # -----------------------------

    match = re.search(
        r"\d+(?:\.\d+)?",
        text
    )

    if not match:
        return None

    try:

        odds = float(
            match.group()
        )

    except ValueError:

        return None

    # -----------------------------
    # 明らかにおかしい値を除外
    # -----------------------------

    if odds < 1:
        return None

    if odds > 100000:
        return None

    return odds


# =========================================================
# 公式3連単オッズ取得
# =========================================================

@st.cache_data(ttl=30)
def get_odds(td, sno, rno):

    url = odds_url(
        td,
        sno,
        rno
    )

    try:

        response = SESSION.get(
            url,
            timeout=20
        )

        response.raise_for_status()

    except requests.RequestException:

        return {}


    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )


    # =====================================================
    # データなし
    # =====================================================

    no_data = soup.find(
        "span",
        string=lambda x:
        x and "データがありません" in x
    )

    if no_data:

        return {}


    # =====================================================
    # 中止
    # =====================================================

    page_text = soup.get_text(
        " ",
        strip=True
    )

    if "中止" in page_text:

        return {}


    # =====================================================
    # 公式サイトの3連単表
    #
    # 現行ページでは table1 の2番目のテーブル内に
    # oddsPoint が並ぶ構造
    # =====================================================

    tables = soup.find_all(
        "div",
        class_="table1"
    )

    if len(tables) < 2:

        return {}


    try:

        tbody = tables[
            1
        ].find(
            "tbody"
        )

        if tbody is None:

            return {}

        rows = tbody.find_all(
            "tr"
        )

    except Exception:

        return {}


    odds_values = []


    # =====================================================
    # oddsPointだけ取得
    # =====================================================

    for row in rows:

        cells = row.find_all(
            "td",
            class_="oddsPoint"
        )

        for cell in cells:

            value = parse_odds(
                cell.get_text(
                    " ",
                    strip=True
                )
            )

            odds_values.append(
                value
            )


    # =====================================================
    # 120個取れなかった場合
    # =====================================================

    if len(odds_values) < 120:

        # 別パターンを試す
        cells = soup.select(
            "td.oddsPoint"
        )

        odds_values = []

        for cell in cells:

            value = parse_odds(
                cell.get_text(
                    " ",
                    strip=True
                )
            )

            odds_values.append(
                value
            )


    # =====================================================
    # 120通りに対応
    # =====================================================

    result = {}

    for code, value in zip(
        TRIFECTA_CODES,
        odds_values
    ):

        code_text = str(
            code
        ).zfill(3)

        combo = (
            f"{code_text[0]}-"
            f"{code_text[1]}-"
            f"{code_text[2]}"
        )

        if value is not None:

            result[
                combo
            ] = value


    return result


# =========================================================
# オッズキャッシュ強制更新
# =========================================================

def clear_odds_cache():

    get_odds.clear()
