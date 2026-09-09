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


# ---------------------------------------------------------
# 値取得
# ---------------------------------------------------------

def val(d, keys, default=0):
    if not isinstance(d, dict):
        return default

    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]

    # 入れ子の中も探す
    for v in d.values():
        if isinstance(v, dict):
            x = val(v, keys, None)
            if x is not None:
                return x

    return default


def num(x, default=0):
    try:
        s = str(x).strip()
        s = s.replace(",", "").replace("%", "")
        s = s.replace("秒", "")
        return float(s)
    except:
        return default


def racers(x):
    if isinstance(x, list):
        return x

    if isinstance(x, dict):
        for k in [
            "racers",
            "racer",
            "entries",
            "entry",
            "players",
            "player",
            "data",
        ]:
            if isinstance(x.get(k), list):
                return x[k]

        return list(x.values())

    return []


# ---------------------------------------------------------
# レースデータ
# ---------------------------------------------------------

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

    stadiums = (
        list(programs.values())
        if isinstance(programs, dict)
        else programs
    )

    for stadium in stadiums:

        if str(
            val(
                stadium,
                [
                    "stadiumNumber",
                    "stadium_number",
                    "stadium",
                    "number",
                ],
            )
        ) != str(sno):
            continue

        races = stadium.get("races", [])

        if isinstance(races, dict):
            races = list(races.values())

        for race in races:

            if str(
                val(
                    race,
                    [
                        "raceNumber",
                        "race_number",
                        "race_no",
                        "number",
                    ],
                )
            ) == str(rno):

                return race

    return None


# ---------------------------------------------------------
# 選手データ
# ---------------------------------------------------------

def racer_value(r, keys, default=0):
    return val(r, keys, default)


def make_racer(r, lane):

    return {
        "枠": lane,

        "選手名": racer_value(
            r,
            [
                "racerName",
                "racer_name",
                "playerName",
                "player_name",
                "name",
                "選手名",
            ],
            "-",
        ),

        "選手番号": racer_value(
            r,
            [
                "racerNumber",
                "racer_number",
                "playerNumber",
                "player_number",
                "registrationNumber",
                "registration_number",
                "number",
                "選手番号",
            ],
            0,
        ),

        "級別": racer_value(
            r,
            [
                "grade",
                "racerClass",
                "racer_class",
                "class",
                "級別",
            ],
            "-",
        ),

        "全国勝率": num(
            racer_value(
                r,
                [
                    "nationwideWinRate",
                    "nationwide_win_rate",
                    "nationalWinRate",
                    "national_win_rate",
                    "winRate",
                    "win_rate",
                    "全国勝率",
                ],
                0,
            )
        ),

        "全国2連率": num(
            racer_value(
                r,
                [
                    "nationwide2Rate",
                    "nationwide_2_rate",
                    "national2Rate",
                    "national_2_rate",
                    "nationalTop2Percent",
                    "national_top_2_percent",
                    "nationalSecondRate",
                    "national_second_rate",
                    "全国2連率",
                ],
                0,
            )
        ),

        "当地勝率": num(
            racer_value(
                r,
                [
                    "localWinRate",
                    "local_win_rate",
                    "placeWinRate",
                    "place_win_rate",
                    "localRate",
                    "local_rate",
                    "当地勝率",
                ],
                0,
            )
        ),

        "モーター2連率": num(
            racer_value(
                r,
                [
                    "motor2Rate",
                    "motor_2_rate",
                    "motorSecondRate",
                    "motor_second_rate",
                    "motorTop2Percent",
                    "motor_top_2_percent",
                    "motorSecondPercent",
                    "motor_second_percent",
                    "モーター2連率",
                ],
                0,
            )
        ),

        "平均ST": num(
            racer_value(
                r,
                [
                    "averageST",
                    "average_st",
                    "avgST",
                    "avg_st",
                    "averageStartTiming",
                    "average_start_timing",
                    "平均ST",
                ],
                0,
            )
        ),
    }


# ---------------------------------------------------------
# 直前情報
# ---------------------------------------------------------

def preview_value(p, keys, default=0):
    return val(p, keys, default)


@st.cache_data(ttl=120)
def official_preview(sno, rno, td):

    try:
        url = (
            "https://www.boatrace.jp/owpc/pc/race/beforeinfo"
            f"?rno={rno}"
            f"&jcd={int(sno):02d}"
            f"&hd={td:%Y%m%d}"
        )

        r = session().get(url, timeout=15)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")

        result = {}

        for tr in soup.find_all("tr"):

            cells = [
                x.get_text(" ", strip=True)
                for x in tr.find_all(["th", "td"])
            ]

            if not cells:
                continue

            lane = None

            for x in cells:
                if re.fullmatch(r"[1-6]", x):
                    lane = int(x)
                    break

            if lane is None:
                continue

            text = " ".join(cells)

            times = re.findall(
                r"\d\.\d{2}",
                text
            )

            exhibition = 0

            for x in times:
                f = float(x)
                if 6.0 <= f <= 8.0:
                    exhibition = f
                    break

            st_value = 0

            for x in times:
                f = float(x)
                if 0 < f <= 0.60:
                    st_value = f
                    break

            result[lane] = {
                "展示タイム": exhibition,
                "展示ST": st_value,
                "展示進入": lane,
            }

        return result

    except:
        return {}


# ---------------------------------------------------------
# 現在のレース用データ
# ---------------------------------------------------------

def get_race_rows(race, sno, rno, td):

    entries = racers(
        race.get("racers")
        or race.get("entries")
        or race.get("entry")
        or race.get("players")
        or []
    )

    preview = (
        race.get("preview")
        or race.get("previews")
        or race.get("beforeInfo")
        or race.get("before_info")
        or []
    )

    preview_list = racers(preview)

    pmap = {}

    for p in preview_list:

        no = val(
            p,
            [
                "racerNumber",
                "racer_number",
                "playerNumber",
                "player_number",
                "number",
            ],
            None,
        )

        try:
            pmap[int(float(no))] = p
        except:
            pass

    official = official_preview(
        sno,
        rno,
        td
    )

    rows = []

    for i, r in enumerate(entries):

        lane = val(
            r,
            [
                "entryNumber",
                "entry_number",
                "boatNumber",
                "boat_number",
                "courseNumber",
                "course_number",
                "lane",
                "枠",
            ],
            i + 1,
        )

        try:
            lane = int(float(lane))
        except:
            lane = i + 1

        row = make_racer(r, lane)

        try:
            no = int(float(row["選手番号"]))
        except:
            no = 0

        p = pmap.get(no, {})
        op = official.get(lane, {})

        row["展示進入"] = num(
            preview_value(
                p,
                [
                    "courseNumber",
                    "course_number",
                    "entryNumber",
                    "entry_number",
                    "course",
                    "展示進入",
                ],
                op.get("展示進入", lane),
            ),
            lane,
        )

        row["展示ST"] = num(
            preview_value(
                p,
                [
                    "startTiming",
                    "start_timing",
                    "exhibitionST",
                    "exhibition_st",
                    "st",
                    "展示ST",
                ],
                op.get("展示ST", 0),
            )
        )

        row["展示タイム"] = num(
            preview_value(
                p,
                [
                    "exhibitionTime",
                    "exhibition_time",
                    "exTime",
                    "ex_time",
                    "time",
                    "展示タイム",
                ],
                op.get("展示タイム", 0),
            )
        )

        row["場"] = sno

        rows.append(row)

    return rows


# ---------------------------------------------------------
# 学習用過去データ
# ---------------------------------------------------------

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
            raw = get_data(d)
        except:
            continue

        programs = raw.get("programs", {})

        stadiums = (
            list(programs.values())
            if isinstance(programs, dict)
            else programs
        )

        for stadium in stadiums:

            sno = num(
                val(
                    stadium,
                    [
                        "stadiumNumber",
                        "stadium_number",
                        "stadium",
                        "number",
                    ],
                )
            )

            races = stadium.get("races", [])

            if isinstance(races, dict):
                races = list(races.values())

            for race in races:

                rno = num(
                    val(
                        race,
                        [
                            "raceNumber",
                            "race_number",
                            "race_no",
                            "number",
                        ],
                    )
                )

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

                finish = {}

                for x in result_entries:

                    no = val(
                        x,
                        [
                            "racerNumber",
                            "racer_number",
                            "playerNumber",
                            "player_number",
                            "number",
                            "選手番号",
                        ],
                        None,
                    )

                    place = val(
                        x,
                        [
                            "place",
                            "rank",
                            "arrival",
                            "着順",
                        ],
                        None,
                    )

                    try:
                        finish[int(float(no))] = int(
                            float(place)
                        )
                    except:
                        pass

                for i, r in enumerate(entries):

                    lane = val(
                        r,
                        [
                            "entryNumber",
                            "entry_number",
                            "boatNumber",
                            "boat_number",
                            "courseNumber",
                            "course_number",
                            "lane",
                            "枠",
                        ],
                        i + 1,
                    )

                    try:
                        lane = int(float(lane))
                    except:
                        lane = i + 1

                    no = val(
                        r,
                        [
                            "racerNumber",
                            "racer_number",
                            "playerNumber",
                            "player_number",
                            "number",
                            "選手番号",
                        ],
                        None,
                    )

                    if no is None:
                        continue

                    try:
                        no = int(float(no))
                    except:
                        continue

                    row = make_racer(r, lane)

                    p = r.get("preview") or {}

                    if isinstance(p, list):
                        p = next(
                            (
                                x for x in p
                                if int(
                                    num(
                                        val(
                                            x,
                                            [
                                                "racerNumber",
                                                "racer_number",
                                                "playerNumber",
                                                "player_number",
                                                "number",
                                            ],
                                            -1,
                                        )
                                    )
                                ) == no
                            ),
                            {},
                        )

                    row["日付"] = d
                    row["レース"] = rno
                    row["選手番号"] = no
                    row["展示進入"] = num(
                        val(
                            p,
                            [
                                "courseNumber",
                                "course_number",
                                "entryNumber",
                                "entry_number",
                                "course",
                            ],
                            lane,
                        ),
                        lane,
                    )

                    row["展示ST"] = num(
                        val(
                            p,
                            [
                                "startTiming",
                                "start_timing",
                                "exhibitionST",
                                "exhibition_st",
                                "st",
                            ],
                            0,
                        )
                    )

                    row["展示タイム"] = num(
                        val(
                            p,
                            [
                                "exhibitionTime",
                                "exhibition_time",
                                "exTime",
                                "ex_time",
                                "time",
                            ],
                            0,
                        )
                    )

                    place = finish.get(no, 99)

                    row["1着"] = int(place == 1)
                    row["2着"] = int(place == 2)
                    row["3着"] = int(place == 3)

                    rows.append(row)

    return rows


# ---------------------------------------------------------
# 過去レース確認
# ---------------------------------------------------------

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
            raw = get_data(d)
        except:
            continue

        programs = raw.get("programs", {})

        stadiums = (
            list(programs.values())
            if isinstance(programs, dict)
            else programs
        )

        for stadium in stadiums:

            sno = val(
                stadium,
                [
                    "stadiumNumber",
                    "stadium_number",
                    "stadium",
                    "number",
                ],
                0,
            )

            races = stadium.get("races", [])

            if isinstance(races, dict):
                races = list(races.values())

            for race in races:

                rno = val(
                    race,
                    [
                        "raceNumber",
                        "race_number",
                        "race_no",
                        "number",
                    ],
                    0,
                )

                result = race.get("result") or {}

                rr = racers(
                    result.get("racers", [])
                )

                finish = {}

                for x in rr:

                    place = val(
                        x,
                        [
                            "place",
                            "rank",
                            "arrival",
                            "着順",
                        ],
                        None,
                    )

                    lane = val(
                        x,
                        [
                            "entryNumber",
                            "entry_number",
                            "boatNumber",
                            "boat_number",
                            "courseNumber",
                            "cours
