import re
from datetime import date, timedelta

import requests
import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup


API = "https://boatraceopenapi.github.io/api/v1"


def session():
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0"
    return s


def val(d, keys, default=0):
    if not isinstance(d, dict):
        return default
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def num(x, default=0):
    try:
        return float(
            str(x)
            .replace(",", "")
            .replace("%", "")
            .strip()
        )
    except:
        return default


def racers(x):
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        for k in ["racers", "racer", "entries", "entry", "data"]:
            if isinstance(x.get(k), list):
                return x[k]
        return list(x.values())
    return []


# =========================================================
# レースデータ
# =========================================================

@st.cache_data(ttl=180)
def get_data(d):
    if isinstance(d, str):
        d = date.fromisoformat(d)

    url = f"{API}/{d.year}/{d:%Y%m%d}.json"
    r = session().get(url, timeout=20)
    r.raise_for_status()
    return r.json()


def get_race(data, sno, rno):
    programs = data.get("programs", {})

    if isinstance(programs, dict):
        stadiums = list(programs.values())
    else:
        stadiums = programs

    for stadium in stadiums:
        if str(val(
            stadium,
            ["stadiumNumber", "stadium", "number"]
        )) != str(sno):
            continue

        races = stadium.get("races", [])
        if isinstance(races, dict):
            races = list(races.values())

        for race in races:
            if str(val(
                race,
                ["raceNumber", "race_no", "number"]
            )) == str(rno):
                return race

    return None


# =========================================================
# 学習用過去データ
# =========================================================

@st.cache_data(ttl=1800)
def history14(td):

    if isinstance(td, str):
        td = date.fromisoformat(td)

    rows = []

    for n in range(1, 15):
        d = td - timedelta(days=n)

        if d < date(2026, 1, 1):
            continue

        try:
            data = get_data(d)
        except:
            continue

        programs = data.get("programs", {})
        stadiums = (
            list(programs.values())
            if isinstance(programs, dict)
            else programs
        )

        for stadium in stadiums:

            sno = num(val(
                stadium,
                ["stadiumNumber", "stadium", "number"]
            ))

            races = stadium.get("races", [])
            if isinstance(races, dict):
                races = list(races.values())

            for race in races:

                rno = num(val(
                    race,
                    ["raceNumber", "race_no", "number"]
                ))

                entries = racers(
                    race.get("racers")
                    or race.get("entries")
                    or race.get("entry")
                    or []
                )

                result = race.get("result") or {}
                result_entries = racers(
                    result.get("racers")
                    or result.get("entries")
                    or []
                )

                # 選手番号→着順
                finish = {}

                for x in result_entries:
                    no = val(
                        x,
                        [
                            "racerNumber",
                            "playerNumber",
                            "number",
                            "選手番号"
                        ],
                        None
                    )
                    place = val(
                        x,
                        [
                            "place",
                            "rank",
                            "arrival",
                            "着順"
                        ],
                        None
                    )

                    try:
                        finish[int(float(no))] = int(float(place))
                    except:
                        pass

                for i, r in enumerate(entries):

                    lane = num(val(
                        r,
                        [
                            "entryNumber",
                            "boatNumber",
                            "courseNumber",
                            "枠",
                            "lane"
                        ],
                        i + 1
                    ))

                    no = val(
                        r,
                        [
                            "racerNumber",
                            "playerNumber",
                            "number",
                            "選手番号"
                        ],
                        None
                    )

                    if no is None:
                        continue

                    try:
                        no = int(float(no))
                    except:
                        continue

                    # 展示データ
                    p = r.get("preview") or race.get("preview") or {}

                    if isinstance(p, list):
                        p = next(
                            (
                                x for x in p
                                if int(num(val(
                                    x,
                                    [
                                        "racerNumber",
                                        "playerNumber",
                                        "number"
                                    ],
                                    -1
                                ))) == no
                            ),
                            {}
                        )

                    place = finish.get(no, 99)

                    rows.append({
                        "日付": d,
                        "場": sno,
                        "レース": rno,
                        "枠": lane,
                        "展示進入": num(val(
                            p,
                            ["courseNumber", "entryNumber", "course"],
                            lane
                        )),
                        "選手番号": no,

                        "全国勝率": num(val(
                            r,
                            [
                                "nationwideWinRate",
                                "nationalWinRate",
                                "winRate",
                                "全国勝率"
                            ]
                        )),

                        "全国2連率": num(val(
                            r,
                            [
                                "nationwide2Rate",
                                "national2Rate",
                                "secondRate",
                                "全国2連率"
                            ]
                        )),

                        "当地勝率": num(val(
                            r,
                            [
                                "localWinRate",
                                "localRate",
                                "当地勝率"
                            ]
                        )),

                        "モーター2連率": num(val(
                            r,
                            [
                                "motor2Rate",
                                "motorSecondRate",
                                "モーター2連率"
                            ]
                        )),

                        "平均ST": num(val(
                            r,
                            [
                                "averageST",
                                "avgST",
                                "averageStartTiming",
                                "平均ST"
                            ]
                        )),

                        "展示ST": num(val(
                            p,
                            [
                                "startTiming",
                                "exhibitionST",
                                "st",
                                "展示ST"
                            ]
                        )),

                        "展示タイム": num(val(
                            p,
                            [
                                "exhibitionTime",
                                "time",
                                "展示タイム"
                            ]
                        )),

                        "1着": int(place == 1),
                        "2着": int(place == 2),
                        "3着": int(place == 3),
                    })

    return rows


# =========================================================
# 過去レース確認
# =========================================================

@st.cache_data(ttl=1800)
def backtest_races(start_date, days=14):

    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)

    rows = []

    for n in range(1, days + 1):

        d = start_date - timedelta(days=n)

        if d < date(2026, 1, 1):
            continue

        try:
            data = get_data(d)
        except:
            continue

        programs = data.get("programs", {})
        stadiums = (
            list(programs.values())
            if isinstance(programs, dict)
            else programs
        )

        for stadium in stadiums:

            sno = val(
                stadium,
                ["stadiumNumber", "stadium", "number"],
                0
            )

            races = stadium.get("races", [])
            if isinstance(races, dict):
                races = list(races.values())

            for race in races:

                rno = val(
                    race,
                    ["raceNumber", "race_no", "number"],
                    0
                )

                result = race.get("result") or {}
                rr = racers(result.get("racers", []))

                finish = {}

                for x in rr:
                    place = val(
                        x,
                        ["place", "rank", "arrival", "着順"],
                        None
                    )
                    lane = val(
                        x,
                        [
                            "entryNumber",
                            "boatNumber",
                            "courseNumber",
                            "枠",
                            "lane"
                        ],
                        None
                    )

                    try:
                        finish[int(float(place))] = int(float(lane))
                    except:
                        pass

                actual = None

                if all(x in finish for x in [1, 2, 3]):
                    actual = (
                        f"{finish[1]}-"
                        f"{finish[2]}-"
                        f"{finish[3]}"
                    )

                rows.append({
                    "日付": d,
                    "場": sno,
                    "レース": rno,
                    "実際の3連単": actual,
                    "払戻金": None,
                })

    return rows


# =========================================================
# オッズ
# =========================================================

def odds_url(sno, rno, d):

    if isinstance(d, str):
        d = date.fromisoformat(d)

    return (
        "https://www.boatrace.jp/owpc/pc/race/odds3tf"
        f"?rno={rno}&jcd={int(sno):02d}&hd={d:%Y%m%d}"
    )


def parse_odds(x):

    try:
        return float(
            str(x)
            .replace("倍", "")
            .replace(",", "")
            .strip()
        )
    except:
        return None


@st.cache_data(ttl=180)
def get_odds(sno, rno, d):

    try:
        r = session().get(
            odds_url(sno, rno, d),
            timeout=20
        )
        r.raise_for_status()
    except:
        return pd.DataFrame(
            columns=["3連単", "オッズ"]
        )

    soup = BeautifulSoup(
        r.text,
        "html.parser"
    )

    rows = []

    for table in soup.find_all("table"):

        text = table.get_text(
            " ",
            strip=True
        )

        if "3連単" not in text:
            continue

        for tr in table.find_all("tr"):

            s = tr.get_text(
                " ",
                strip=True
            )

            m = re.search(
                r"([1-6])\s*-\s*([1-6])\s*-\s*([1-6])",
                s
            )

            if not m:
                continue

            nums = "-".join(m.groups())
            values = re.findall(
                r"\d+\.\d+",
                s
            )

            if not values:
                continue

            odds = parse_odds(values[-1])

            if odds is not None:
                rows.append({
                    "3連単": nums,
                    "オッズ": odds
                })

        if rows:
            break

    return pd.DataFrame(rows)


def clear_odds_cache():
    try:
        get_odds.clear()
    except:
        pass
