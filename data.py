import re
from datetime import date, timedelta

import requests
import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup


API = "https://boatraceopenapi.github.io/api/v1"


def _val(d, keys, default=0):
    if not isinstance(d, dict):
        return default

    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return v

    for v in d.values():
        if isinstance(v, dict):
            x = _val(v, keys, None)
            if x is not None:
                return x

    return default


def _num(x, default=0.0):
    try:
        return float(
            str(x)
            .replace(",", "")
            .replace("%", "")
            .replace("秒", "")
            .strip()
        )
    except:
        return default


def _list(x):
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


def _session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0"
    })
    return s


# =========================================================
# APIデータ取得
# =========================================================

@st.cache_data(ttl=180)
def get_data(d):

    if isinstance(d, str):
        d = date.fromisoformat(d)

    url = f"{API}/{d.year}/{d:%Y%m%d}.json"

    r = _session().get(
        url,
        timeout=20
    )

    r.raise_for_status()

    return r.json()


# =========================================================
# 指定レース取得
# =========================================================

def get_race(raw, sno, rno):

    programs = raw.get(
        "programs",
        {}
    )

    if isinstance(programs, dict):
        stadiums = list(
            programs.values()
        )
    else:
        stadiums = programs

    for stadium in stadiums:

        stadium_no = _val(
            stadium,
            [
                "stadiumNumber",
                "stadium_number",
                "stadium",
                "number",
            ],
            None
        )

        if str(stadium_no) != str(sno):
            continue

        races = stadium.get(
            "races",
            []
        )

        if isinstance(races, dict):
            races = list(
                races.values()
            )

        for race in races:

            race_no = _val(
                race,
                [
                    "raceNumber",
                    "race_number",
                    "race_no",
                    "number",
                ],
                None
            )

            if str(race_no) == str(rno):
                return race

    return None


# =========================================================
# 選手データ
# =========================================================

def make_racer(r, lane):

    return {
        "枠": lane,

        "選手名": _val(
            r,
            [
                "racerName",
                "racer_name",
                "playerName",
                "player_name",
                "name",
                "選手名",
            ],
            "-"
        ),

        "選手番号": _val(
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
            0
        ),

        "級別": _val(
            r,
            [
                "grade",
                "racerClass",
                "racer_class",
                "class",
                "級別",
            ],
            "-"
        ),

        "全国勝率": _num(
            _val(
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
                0
            )
        ),

        "全国2連率": _num(
            _val(
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
                0
            )
        ),

        "当地勝率": _num(
            _val(
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
                0
            )
        ),

        "モーター2連率": _num(
            _val(
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
                0
            )
        ),

        "平均ST": _num(
            _val(
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
                0
            )
        ),
    }


# =========================================================
# 公式展示情報
# =========================================================

@st.cache_data(ttl=120)
def official_preview(sno, rno, td):

    url = (
        "https://www.boatrace.jp/owpc/pc/race/beforeinfo"
        f"?rno={rno}"
        f"&jcd={int(sno):02d}"
        f"&hd={td:%Y%m%d}"
    )

    try:

        r = _session().get(
            url,
            timeout=15
        )

        r.raise_for_status()

        soup = BeautifulSoup(
            r.text,
            "html.parser"
        )

        result = {}

        for tr in soup.find_all("tr"):

            cells = [
                x.get_text(
                    " ",
                    strip=True
                )
                for x in tr.find_all(
                    ["th", "td"]
                )
            ]

            if not cells:
                continue

            lane = None

            for x in cells:
                if re.fullmatch(
                    r"[1-6]",
                    x
                ):
                    lane = int(x)
                    break

            if lane is None:
                continue

            text = " ".join(cells)

            nums = re.findall(
                r"(?:\d+\.\d+|\.\d+)",
                text
            )

            exhibition = 0
            exhibition_st = 0

            for x in nums:

                f = float(x)

                if (
                    exhibition == 0
                    and 6.0 <= f <= 8.0
                ):
                    exhibition = f

                if (
                    exhibition_st == 0
                    and 0 < f <= 0.60
                ):
                    exhibition_st = f

            if exhibition or exhibition_st:

                result[lane] = {
                    "展示進入": lane,
                    "展示ST": exhibition_st,
                    "展示タイム": exhibition,
                }

        return result

    except:
        return {}


# =========================================================
# 現在レースの6選手データ
# =========================================================

def get_race_rows(race, sno, rno, td):

    entries = _list(
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

    preview_list = _list(
        preview
    )

    pmap = {}

    for p in preview_list:

        no = _val(
            p,
            [
                "racerNumber",
                "racer_number",
                "playerNumber",
                "player_number",
                "number",
            ],
            None
        )

        try:
            pmap[
                int(float(no))
            ] = p
        except:
            pass

    official = official_preview(
        sno,
        rno,
        td
    )

    rows = []

    for i, racer in enumerate(entries):

        lane = _val(
            racer,
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
            i + 1
        )

        try:
            lane = int(
                float(lane)
            )
        except:
            lane = i + 1

        row = make_racer(
            racer,
            lane
        )

        try:
            no = int(
                float(
                    row["選手番号"]
                )
            )
        except:
            no = 0

        p = pmap.get(
            no,
            {}
        )

        op = official.get(
            lane,
            {}
        )

        row["展示進入"] = _num(
            _val(
                p,
                [
                    "courseNumber",
                    "course_number",
                    "entryNumber",
                    "entry_number",
                    "course",
                    "展示進入",
                ],
                op.get(
                    "展示進入",
                    lane
                )
            ),
            lane
        )

        row["展示ST"] = _num(
            _val(
                p,
                [
                    "startTiming",
                    "start_timing",
                    "exhibitionST",
                    "exhibition_st",
                    "st",
                    "展示ST",
                ],
                op.get(
                    "展示ST",
                    0
                )
            )
        )

        row["展示タイム"] = _num(
            _val(
                p,
                [
                    "exhibitionTime",
                    "exhibition_time",
                    "exTime",
                    "ex_time",
                    "time",
                    "展示タイム",
                ],
                op.get(
                    "展示タイム",
                    0
                )
            )
        )

        row["場"] = int(
            sno
        )

        rows.append(row)

    return rows


# =========================================================
# 過去14日間の学習データ
# =========================================================

@st.cache_data(ttl=1800)
def history14(td):

    if isinstance(td, str):
        td = date.fromisoformat(td)

    rows = []

    for n in range(1, 15):

        d = td - timedelta(
            days=n
        )

        if d < date(
            2026,
            1,
            1
        ):
            continue

        try:
            raw = get_data(d)
        except:
            continue

        programs = raw.get(
            "programs",
            {}
        )

        if isinstance(programs, dict):
            stadiums = list(
                programs.values()
            )
        else:
            stadiums = programs

        for stadium in stadiums:

            sno = _num(
                _val(
                    stadium,
                    [
                        "stadiumNumber",
                        "stadium_number",
                        "stadium",
                        "number",
                    ],
                    0
                )
            )

            races = stadium.get(
                "races",
                []
            )

            if isinstance(races, dict):
                races = list(
                    races.values()
                )

            for race in races:

                rno = _num(
                    _val(
                        race,
                        [
                            "raceNumber",
                            "race_number",
                            "race_no",
                            "number",
                        ],
                        0
                    )
                )

                entries = _list(
                    race.get("racers")
                    or race.get("entries")
                    or race.get("entry")
                    or []
                )

                result = (
                    race.get("result")
                    or {}
                )

                result_entries = _list(
                    result.get("racers")
                    or result.get("entries")
                    or []
                )

                finish = {}

                for x in result_entries:

                    no = _val(
                        x,
                        [
                            "racerNumber",
                            "racer_number",
                            "playerNumber",
                            "player_number",
                            "number",
                        ],
                        None
                    )

                    place = _val(
                        x,
                        [
                            "place",
                            "rank",
                            "arrival",
                            "着順",
                        ],
                        None
                    )

                    try:
                        finish[
                            int(float(no))
                        ] = int(
                            float(place)
                        )
                    except:
                        pass

                for i, racer in enumerate(entries):

                    lane = _val(
                        racer,
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
                        i + 1
                    )

                    try:
                        lane = int(
                            float(lane)
                        )
                    except:
                        lane = i + 1

                    no = _val(
                        racer,
                        [
                            "racerNumber",
                            "racer_number",
                            "playerNumber",
                            "player_number",
                            "number",
                        ],
                        None
                    )

                    try:
                        no = int(
                            float(no)
                        )
                    except:
                        continue

                    row = make_racer(
                        racer,
                        lane
                    )

                    row["日付"] = d
                    row["レース"] = rno

                    place = finish.get(
                        no,
                        99
                    )

                    row["1着"] = int(
                        place == 1
                    )

                    row["2着"] = int(
                        place == 2
                    )

                    row["3着"] = int(
                        place == 3
                    )

                    row["展示進入"] = lane
                    row["展示ST"] = 0
                    row["展示タイム"] = 0
                    row["場"] = int(
                        sno
                    )

                    rows.append(row)

    return rows
