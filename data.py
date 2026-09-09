import re
from datetime import date, timedelta

import requests
import streamlit as st
from bs4 import BeautifulSoup


API = "https://boatraceopenapi.github.io/api/v1"


# =========================
# HTTP
# =========================

def make_session():

    session = requests.Session()

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/140.0 Safari/537.36"
        ),
        "Accept-Language": (
            "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7"
        ),
    })

    return session


# =========================
# 日別データ取得
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
# racers共通処理
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
# 過去14日データ
# =========================

@st.cache_data(ttl=1800)
def history14(td):

    rows = []

    for i in range(1, 15):

        d = td - timedelta(
            days=i
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
                            ""
                        )
                    )

                    if place in (
                        "1",
                        "2",
                        "3",
                    ):

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
                            ""
                        )
                    )

                    if not number:
                        continue

                    rows.append({

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
                    })

    return rows


# =========================
# バックテスト用
# =========================

@st.cache_data(ttl=1800)
def backtest_races(
    start_date,
    days=14,
):

    result_rows = []

    for i in range(days):

        d = start_date - timedelta(
            days=i
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
                            ""
                        )
                    )

                    number = str(
                        x.get(
                            "number",
                            ""
                        )
                    )

                    if (
                        place in (
                            "1",
                            "2",
                            "3",
                        )
                        and number
                    ):

                        places[place] = number

                if len(places) < 3:
                    continue

                trifecta = (
                    f"{places['1']}-"
                    f"{places['2']}-"
                    f"{places['3']}"
                )

                payout = 0

                # APIの払戻情報を取得
                payouts = result.get(
                    "payouts",
                    {}
                )

                if isinstance(
                    payouts,
                    dict,
                ):

                    trifecta_data = payouts.get(
                        "trifecta",
                        []
                    )

                    if isinstance(
                        trifecta_data,
                        list,
                    ):

                        for item in trifecta_data:

                            if not isinstance(
                                item,
                                dict,
                            ):
                                continue

                            combination = str(
                                item.get(
                                    "combination",
                                    ""
                                )
                            )

                            if combination == trifecta:

                                try:

                                    payout = int(
                                        item.get(
                                            "amount",
                                            0
                                        )
                                        or 0
                                    )

                                except Exception:

                                    payout = 0

                                break

                result_rows.append({

                    "日付": d,

                    "場": int(sno),

                    "レース": int(rno),

                    "1着選手番号":
                        places["1"],

                    "2着選手番号":
                        places["2"],

                    "3着選手番号":
                        places["3"],

                    "実際の3連単":
                        trifecta,

                    "払戻金":
                        payout,
                })

    return result_rows


# =========================
# オッズURL
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
# オッズ数値変換
# =========================

def parse_odds(value):

    if value is None:
        return None

    text = (
        str(value)
        .strip()
        .replace(",", "")
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


# =========================
# HTMLセル
# =========================

def _cell_classes(cell):

    return cell.get(
        "class",
        []
    )


def _is_odds_cell(cell):

    return (
        "oddsPoint"
        in _cell_classes(cell)
    )


# =========================
# rowspan / colspan展開
# =========================

def _expand_table(table):

    rows = table.find_all(
        "tr"
    )

    grid = []

    occupied = {}

    for r, tr in enumerate(rows):

        row = []

        cells = tr.find_all(
            ["th", "td"],
            recursive=False,
        )

        col = 0

        for cell in cells:

            while (
                r,
                col
            ) in occupied:

                row.append(
                    occupied[
                        (r, col)
                    ]
                )

                col += 1

            rowspan = cell.get(
                "rowspan",
                "1",
            )

            colspan = cell.get(
                "colspan",
                "1",
            )

            try:

                rowspan = int(
                    rowspan
                )

            except Exception:

                rowspan = 1

            try:

                colspan = int(
                    colspan
                )

            except Exception:

                colspan = 1

            for c in range(
                colspan
            ):

                row.append(
                    cell
                )

                if rowspan > 1:

                    for rr in range(
                        1,
                        rowspan,
                    ):

                        occupied[
                            (
                                r + rr,
                                col + c,
                            )
                        ] = cell

                col += 1

        while (
            r,
            col
        ) in occupied:

            row.append(
                occupied[
                    (r, col)
                ]
            )

            col += 1

        grid.append(
            row
        )

    return grid


# =========================
# オッズ表検索
# =========================

def _find_odds_table(
    soup
):

    tables = soup.find_all(
        "table"
    )

    for table in tables:

        odds_cells = table.find_all(
            "td",
            class_="oddsPoint"
        )

        if len(
            odds_cells
        ) != 120:

            continue

        text = table.get_text(
            " ",
            strip=True
        )

        if "3連単" in text:

            return table

    div_tables = soup.find_all(
        "div",
        class_="table1"
    )

    for table in div_tables:

        odds_cells = table.find_all(
            "td",
            class_="oddsPoint"
        )

        if len(
            odds_cells
        ) == 120:

            return table

    return None


# =========================
# 公式オッズ解析
# =========================

def _parse_official_odds_table(
    table
):

    grid = _expand_table(
        table
    )

    if not grid:
        return {}

    data_rows = []

    for row in grid:

        if len(row) < 18:
            continue

        valid = True

        for block in range(6):

            base = block * 3

            second_cell = row[
                base
            ]

            third_cell = row[
                base + 1
            ]

            odds_cell = row[
                base + 2
            ]

            if (
                second_cell is None
                or third_cell is None
                or odds_cell is None
            ):

                valid = False
                break

            if not _is_odds_cell(
                odds_cell
            ):

                valid = False
                break

            odd = parse_odds(
                odds_cell.get_text(
                    " ",
                    strip=True
                )
            )

            if odd is None:

                valid = False
                break

        if valid:

            data_rows.append(
                row
            )

    if len(
        data_rows
    ) != 20:

        return {}

    result = {}

    for row in data_rows:

        for block in range(6):

            first = block + 1

            base = block * 3

            second_cell = row[
                base
            ]

            third_cell = row[
                base + 1
            ]

            odds_cell = row[
                base + 2
            ]

            second_text = (
                second_cell.get_text(
                    " ",
                    strip=True
                )
            )

            third_text = (
                third_cell.get_text(
                    " ",
                    strip=True
                )
            )

            odds_text = (
                odds_cell.get_text(
                    " ",
                    strip=True
                )
            )

            second_match = re.search(
                r"(?<!\d)([1-6])(?!\d)",
                second_text,
            )

            third_match = re.search(
                r"(?<!\d)([1-6])(?!\d)",
                third_text,
            )

            odd = parse_odds(
                odds_text
            )

            if (
                second_match is None
                or third_match is None
                or odd is None
            ):

                continue

            second = int(
                second_match.group(1)
            )

            third = int(
                third_match.group(1)
            )

            if len({
                first,
                second,
                third,
            }) != 3:

                continue

            combination = (
                f"{first}-"
                f"{second}-"
                f"{third}"
            )

            result[
                combination
            ] = odd

    if len(result) != 120:
        return {}

    if len(
        set(result.keys())
    ) != 120:

        return {}

    return result


# =========================
# オッズ取得
# =========================

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

    try:

        response = session.get(
            url,
            timeout=30,
        )

        response.raise_for_status()

    except Exception:

        return {}

    html = response.text

    if (
        "データがありません"
        in html
        or "中止"
        in html
    ):

        return {}

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    table = _find_odds_table(
        soup
    )

    if table is None:
        return {}

    result = (
        _parse_official_odds_table(
            table
        )
    )

    if len(result) != 120:
        return {}

    return result


# =========================
# オッズキャッシュ削除
# =========================

def clear_odds_cache():

    try:

        get_odds.clear()

    except Exception:

        pass
@st.cache_data(ttl=1800)
def backtest_races(start_date, days=14):
    rows = []

    for i in range(days):
        d = start_date - timedelta(days=i)

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
            races = stadium.get("races", {})

            for rno, race in races.items():
                result = race.get("result", {})
                result_racers = result.get(
                    "racers", {}
                )

                places = {}

                for x in racers(result_racers):
                    place = str(
                        x.get("place_number", "")
                    )
                    number = str(
                        x.get("number", "")
                    )

                    if place in ["1", "2", "3"]:
                        if number:
                            places[place] = number

                if len(places) < 3:
                    continue

                actual = (
                    f"{places['1']}-"
                    f"{places['2']}-"
                    f"{places['3']}"
                )

                payout = 0

                payouts = result.get(
                    "payouts", {}
                )

                if isinstance(payouts, dict):
                    trifecta = payouts.get(
                        "trifecta", []
                    )

                    if isinstance(trifecta, list):
                        for item in trifecta:
                            if not isinstance(item, dict):
                                continue

                            if str(
                                item.get(
                                    "combination",
                                    ""
                                )
                            ) == actual:
                                try:
                                    payout = int(
                                        item.get(
                                            "amount",
                                            0
                                        ) or 0
                                    )
                                except Exception:
                                    payout = 0
                                break

                rows.append({
                    "日付": d,
                    "場": int(sno),
                    "レース": int(rno),
                    "実際の3連単": actual,
                    "払戻金": payout,
                })

    return rows
