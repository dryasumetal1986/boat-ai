import re
from datetime import date, timedelta

import requests
import streamlit as st
from bs4 import BeautifulSoup


# =========================
# Boatrace Open API
# =========================

API = (
    "https://boatraceopenapi.github.io/api/v1"
)


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
# 日付データ取得
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

    if isinstance(
        value,
        list,
    ):

        return value


    if isinstance(
        value,
        dict,
    ):

        return list(
            value.values()
        )


    return []


# =========================
# レース取得
# =========================

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


# =========================
# 過去14日
# =========================

@st.cache_data(ttl=1800)
def history14(td):

    rows = []


    for i in range(
        1,
        15,
    ):

        d = (
            td
            - timedelta(days=i)
        )


        if d < date(
            2026,
            1,
            1,
        ):

            continue


        try:

            data = get_data(
                d
            )

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

                # -------------------------
                # 結果
                # -------------------------

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

                        places[
                            place
                        ] = str(
                            x.get(
                                "number",
                                "",
                            )
                        )


                if "1" not in places:

                    continue


                # -------------------------
                # 出走選手
                # -------------------------

                race_racers = race.get(
                    "racers",
                    {}
                )


                if not isinstance(
                    race_racers,
                    dict,
                ):

                    continue


                for lane in range(
                    1,
                    7,
                ):

                    racer = race_racers.get(
                        str(lane),
                        {},
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

                            "場": int(
                                sno
                            ),

                            "レース": int(
                                rno
                            ),

                            "枠": lane,

                            "選手番号": number,

                            "1着": int(
                                number
                                == places.get(
                                    "1"
                                )
                            ),

                            "2着": int(
                                number
                                == places.get(
                                    "2"
                                )
                            ),

                            "3着": int(
                                number
                                == places.get(
                                    "3"
                                )
                            ),
                        }
                    )


    return rows


# =========================
# 3連単オッズURL
# =========================

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


# =========================
# オッズ文字列を数字化
# =========================

def parse_odds(
    value,
):

    if value is None:

        return None


    text = str(
        value
    ).strip()


    text = text.replace(
        ",",
        "",
    )


    # 「発売なし」など
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


# =========================
# 3連単120通り
# =========================

TRIFECTA_CODES = [

    "123", "124", "125", "126",
    "132", "134", "135", "136",
    "142", "143", "145", "146",
    "152", "153", "154", "156",
    "162", "163", "164", "165",

    "213", "214", "215", "216",
    "231", "234", "235", "236",
    "241", "243", "245", "246",
    "251", "253", "254", "256",
    "261", "263", "264", "265",

    "312", "314", "315", "316",
    "321", "324", "325", "326",
    "341", "342", "345", "346",
    "351", "352", "354", "356",
    "361", "362", "364", "365",

    "412", "413", "415", "416",
    "421", "423", "425", "426",
    "431", "432", "435", "436",
    "451", "452", "453", "456",
    "461", "462", "463", "465",

    "512", "513", "514", "516",
    "521", "523", "524", "526",
    "531", "532", "534", "536",
    "541", "542", "543", "546",
    "561", "562", "563", "564",

    "612", "613", "614", "615",
    "621", "623", "624", "625",
    "631", "632", "634", "635",
    "641", "642", "643", "645",
    "651", "652", "653", "654",
]


# =========================
# オッズ取得
# =========================

@st.cache_data(ttl=30)
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


    # =========================
    # オッズ表
    # =========================

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


    rows = tbody.find_all(
        "tr"
    )


    values = []


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


            odds = parse_odds(
                text
            )


            if odds is not None:

                values.append(
                    odds
                )


    # =========================
    # 120通りに対応
    # =========================

    result = {}


    for code, odd in zip(
        TRIFECTA_CODES,
        values,
    ):

        result[
            f"{code[0]}-"
            f"{code[1]}-"
            f"{code[2]}"
        ] = odd


    return result


# =========================
# オッズキャッシュ削除
# =========================

def clear_odds_cache():

    try:

        get_odds.clear()

    except Exception:

        pass
