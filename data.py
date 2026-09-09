import re
from datetime import date, timedelta

import requests
import streamlit as st
from bs4 import BeautifulSoup


# =========================================================
# Boatrace Open API
# =========================================================

API = "https://boatraceopenapi.github.io/api/v1"


# =========================================================
# HTTPセッション
# =========================================================

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
            ),
            "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
        }
    )

    return session


# =========================================================
# レースデータ取得
# =========================================================

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


# =========================================================
# list / dict 共通処理
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

def get_race(
    data,
    sno,
    rno,
):

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

                    if place in [
                        "1",
                        "2",
                        "3",
                    ]:

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
# 公式3連単オッズURL
# =========================================================

def odds_url(
    td,
    sno,
    rno,
):

    return (
        "https://www.boatrace.jp/"
        "owpc/pc/race/odds3t"
        f"?rno={rno}"
        f"&jcd={sno:02d}"
        f"&hd={td:%Y%m%d}"
    )


# =========================================================
# オッズ文字列 → float
# =========================================================

def parse_odds(value):

    if value is None:
        return None

    text = str(
        value
    ).strip()

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
# 3連単の公式順序を自動生成
#
# 公式の並び:
#
# 123
# 124
# 125
# 126
# 132
# 134
# 135
# 136
# 142
# 143
# ...
#
# 213
# 214
# ...
#
# 612
# ...
#
# 全120通り
# =========================================================

TRIFECTA_CODES = [
    int(f"{a}{b}{c}")
    for a in range(1, 7)
    for b in range(1, 7)
    for c in range(1, 7)
    if a != b
    and a != c
    and b != c
]


# =========================================================
# 念のため120通りあるか確認
# =========================================================

if len(TRIFECTA_CODES) != 120:

    raise RuntimeError(
        "3連単の組み合わせ数が120ではありません。"
    )


# =========================================================
# 公式3連単オッズ取得
# =========================================================

@st.cache_data(ttl=20)
def get_odds(
    td,
    sno,
    rno,
):

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


    # -----------------------------------------------------
    # データなし
    # -----------------------------------------------------

    if "データがありません" in response.text:

        return {}


    # -----------------------------------------------------
    # 中止
    # -----------------------------------------------------

    if "中止" in response.text:

        return {}


    # -----------------------------------------------------
    # 公式3連単テーブル
    #
    # BOAT RACE公式ページの
    # table1 2番目を使用
    # -----------------------------------------------------

    tables = soup.find_all(
        "div",
        class_="table1",
    )


    if len(tables) < 2:

        return {}


    table = tables[1]


    tbody = table.find(
        "tbody"
    )


    if tbody is None:

        return {}


    # -----------------------------------------------------
    # オッズ取得
    # -----------------------------------------------------

    odds_list = []


    rows = tbody.find_all(
        "tr"
    )


    for row in rows:

        cells = row.find_all(
            "td",
            class_="oddsPoint",
        )


        for cell in cells:

            text = cell.get_text(
                " ",
                strip=True,
            )


            odd = parse_odds(
                text
            )


            if odd is not None:

                odds_list.append(
                    odd
                )


    # -----------------------------------------------------
    # 120個取得できなかった場合
    #
    # HTML構造が想定と違う状態で
    # 間違った買い目にオッズを割り当てるのを防ぐ
    # -----------------------------------------------------

    if len(odds_list) != 120:

        return {}


    # -----------------------------------------------------
    # 公式順序で割り当て
    # -----------------------------------------------------

    result = {}


    for code, odd in zip(
        TRIFECTA_CODES,
        odds_list,
    ):

        code = str(code)

        combination = (
            f"{code[0]}-"
            f"{code[1]}-"
            f"{code[2]}"
        )

        result[
            combination
        ] = odd


    return result


# =========================================================
# オッズキャッシュ削除
# =========================================================

def clear_odds_cache():

    try:

        get_odds.clear()

    except Exception:

        pass


# =========================================================
# デバッグ用
#
# 必要ならStreamlit上で
# get_odds() の中身を確認できる。
# =========================================================

def validate_odds(
    odds,
):

    if not odds:
        return False

    if len(odds) != 120:
        return False

    expected = {
        f"{a}-{b}-{c}"
        for a in range(1, 7)
        for b in range(1, 7)
        for c in range(1, 7)
        if a != b
        and a != c
        and b != c
    }

    return set(odds.keys()) == expected
