import re
from datetime import date, timedelta

import requests
import streamlit as st


# =========================================================
# Boatrace Open API
# =========================================================

API = "https://boatraceopenapi.github.io/api/v1"


# =========================================================
# 共通
# =========================================================

def _num(value, default=0.0):
    try:
        if value is None or value == "":
            return default

        if isinstance(value, str):
            value = value.replace("%", "").replace("秒", "").strip()

        return float(value)
    except Exception:
        return default


def _int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def _val(data, keys, default=None):
    if not isinstance(data, dict):
        return default

    for key in keys:
        if key in data and data[key] is not None:
            return data[key]

    return default


def _session():
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/120 Safari/537.36"
            )
        }
    )
    return s


# =========================================================
# 場名
# =========================================================

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


def stadium_name(stadium_no):
    return STADIUMS.get(int(stadium_no), f"場{stadium_no}")


# =========================================================
# API取得
# =========================================================

@st.cache_data(ttl=180)
def get_data(target_date):
    """
    1日分の公式APIデータを取得。
    """
    if isinstance(target_date, str):
        target_date = date.fromisoformat(target_date)

    url = (
        f"{API}/"
        f"{target_date.year}/"
        f"{target_date:%Y%m%d}.json"
    )

    response = _session().get(url, timeout=20)
    response.raise_for_status()

    data = response.json()

    if not isinstance(data, dict):
        raise ValueError("APIのJSON形式が不正です。")

    return data


# =========================================================
# レース取得
# =========================================================

def get_race(raw, stadium_no, race_no):
    """
    【重要】
    場→Rを完全一致で取得する。

    正式なAPI構造:
      programs
        └ stadiums
            └ "1"
                └ races
                    └ "1"
    """

    stadium_no = int(stadium_no)
    race_no = int(race_no)

    if not isinstance(raw, dict):
        raise ValueError("APIデータが辞書形式ではありません。")

    programs = raw.get("programs")

    if not isinstance(programs, dict):
        raise ValueError("APIに programs がありません。")

    stadiums = programs.get("stadiums")

    if not isinstance(stadiums, dict):
        raise ValueError("APIに programs.stadiums がありません。")

    # -----------------------------------------------------
    # ここが今回の最重要部分
    # dictの中を総当たり検索しない。
    # 必ず指定された場番号のキーを直接見る。
    # -----------------------------------------------------

    stadium = stadiums.get(str(stadium_no))

    if not isinstance(stadium, dict):
        raise ValueError(
            f"{stadium_name(stadium_no)}({stadium_no})のデータがありません。"
        )

    races = stadium.get("races")

    if not isinstance(races, dict):
        raise ValueError(
            f"{stadium_name(stadium_no)}にレースデータがありません。"
        )

    race = races.get(str(race_no))

    if not isinstance(race, dict):
        raise ValueError(
            f"{stadium_name(stadium_no)} {race_no}Rのデータがありません。"
        )

    # -----------------------------------------------------
    # 二重チェック
    # -----------------------------------------------------

    actual_stadium = _int(
        race.get("stadium_number"),
        default=-1,
    )

    actual_race = _int(
        race.get("race_number"),
        default=-1,
    )

    if actual_stadium != stadium_no:
        raise ValueError(
            "場番号の不一致を検出しました。"
            f"指定={stadium_no}, API={actual_stadium}"
        )

    if actual_race != race_no:
        raise ValueError(
            "レース番号の不一致を検出しました。"
            f"指定={race_no}, API={actual_race}"
        )

    return race


# =========================================================
# 選手データ作成
# =========================================================

def make_racer(program_racer, preview_racer, lane):
    """
    出走表 + 直前情報から1選手分のデータを作る。
    """

    program_racer = program_racer or {}
    preview_racer = preview_racer or {}

    name = str(
        _val(
            program_racer,
            ["name"],
            "不明",
        )
    )

    course = _int(
        _val(
            preview_racer,
            ["course_number"],
            lane,
        ),
        lane,
    )

    # 進入コースは異常値なら枠番に戻す
    if course < 1 or course > 6:
        course = lane

    exhibition_time = _num(
        _val(
            preview_racer,
            ["exhibition_time"],
            0,
        ),
        0,
    )

    exhibition_st = _num(
        _val(
            preview_racer,
            ["start_timing"],
            0,
        ),
        0,
    )

    return {
        "枠": lane,
        "選手名": name,
        "登録番号": _int(
            _val(program_racer, ["number"], 0),
            0,
        ),
        "級別": _int(
            _val(program_racer, ["rank_number"], 0),
            0,
        ),
        "展示進入": course,
        "全国勝率": _num(
            _val(
                program_racer,
                ["national_win_rate"],
                0,
            ),
            0,
        ),
        "全国2連率": _num(
            _val(
                program_racer,
                ["national_top_2_percent"],
                0,
            ),
            0,
        ),
        "全国3連率": _num(
            _val(
                program_racer,
                ["national_top_3_percent"],
                0,
            ),
            0,
        ),
        "当地勝率": _num(
            _val(
                program_racer,
                ["local_win_rate"],
                0,
            ),
            0,
        ),
        "当地2連率": _num(
            _val(
                program_racer,
                ["local_top_2_percent"],
                0,
            ),
            0,
        ),
        "モーター": _int(
            _val(
                program_racer,
                ["motor_number"],
                0,
            ),
            0,
        ),
        "モーター2連率": _num(
            _val(
                program_racer,
                ["motor_top_2_percent"],
                0,
            ),
            0,
        ),
        "ボート": _int(
            _val(
                program_racer,
                ["boat_number"],
                0,
            ),
            0,
        ),
        "平均ST": _num(
            _val(
                program_racer,
                ["average_start_timing"],
                0,
            ),
            0,
        ),
        "展示ST": exhibition_st,
        "展示タイム": exhibition_time,
    }


# =========================================================
# 展示・出走表
# =========================================================

@st.cache_data(ttl=120)
def official_preview(stadium_no, race_no, target_date):
    """
    互換用。
    現在のv1 APIではrace.previewをそのまま利用する。
    """

    raw = get_data(target_date)
    race = get_race(
        raw,
        int(stadium_no),
        int(race_no),
    )

    return race.get("preview") or {}


def get_race_rows(race, stadium_no, race_no, target_date):
    """
    指定された場・Rの6選手をDataFrameにする。
    """

    import pandas as pd

    if not isinstance(race, dict):
        raise ValueError("raceデータが不正です。")

    # -----------------------------------------------------
    # 最終安全チェック
    # -----------------------------------------------------

    stadium_no = int(stadium_no)
    race_no = int(race_no)

    if _int(race.get("stadium_number"), -1) != stadium_no:
        raise ValueError("表示対象の場と取得データの場が一致していません。")

    if _int(race.get("race_number"), -1) != race_no:
        raise ValueError("表示対象のRと取得データのRが一致していません。")

    # 日付チェック
    api_date = str(race.get("date", ""))

    if api_date:
        if isinstance(target_date, str):
            target_date = date.fromisoformat(target_date)

        if api_date != target_date.isoformat():
            raise ValueError(
                f"日付が一致していません。"
                f"指定={target_date.isoformat()}, API={api_date}"
            )

    racers = race.get("racers")

    if not isinstance(racers, dict):
        raise ValueError("このレースの選手データがありません。")

    preview = race.get("preview") or {}
    preview_racers = preview.get("racers") or {}

    rows = []

    # 必ず1号艇→6号艇の順で取得
    for lane in range(1, 7):

        program_racer = (
            racers.get(str(lane))
            or racers.get(lane)
        )

        if not isinstance(program_racer, dict):
            raise ValueError(
                f"{stadium_name(stadium_no)} "
                f"{race_no}Rの{lane}号艇データがありません。"
            )

        preview_racer = (
            preview_racers.get(str(lane))
            or preview_racers.get(lane)
            or {}
        )

        row = make_racer(
            program_racer,
            preview_racer,
            lane,
        )

        rows.append(row)

    df = pd.DataFrame(rows)

    # -----------------------------------------------------
    # 6艇チェック
    # -----------------------------------------------------

    if len(df) != 6:
        raise ValueError(
            f"選手数が6人ではありません。取得数={len(df)}"
        )

    if list(df["枠"]) != [1, 2, 3, 4, 5, 6]:
        raise ValueError("1〜6号艇の並びが壊れています。")

    if df["選手名"].eq("不明").any():
        raise ValueError("選手名を取得できない艇があります。")

    # API上の場・Rを付与
    df["場"] = stadium_no
    df["レース"] = race_no

    return df


# =========================================================
# 過去データ
# =========================================================

def _build_history_rows(raw):
    """
    1日分の結果からAI学習用データを作る。
    """

    import pandas as pd

    result = []

    if not isinstance(raw, dict):
        return result

    programs = raw.get("programs") or {}
    stadiums = programs.get("stadiums") or {}

    if not isinstance(stadiums, dict):
        return result

    for stadium_key, stadium in stadiums.items():

        if not isinstance(stadium, dict):
            continue

        stadium_no = _int(stadium_key, -1)

        if stadium_no < 1 or stadium_no > 24:
            continue

        races = stadium.get("races") or {}

        if not isinstance(races, dict):
            continue

        for race_key, race in races.items():

            if not isinstance(race, dict):
                continue

            race_no = _int(race_key, -1)

            if race_no < 1 or race_no > 12:
                continue

            racers = race.get("racers") or {}
            result_data = race.get("result") or {}
            result_racers = result_data.get("racers") or {}

            if not isinstance(racers, dict):
                continue

            if not isinstance(result_racers, dict):
                continue

            for lane in range(1, 7):

                program_racer = (
                    racers.get(str(lane))
                    or racers.get(lane)
                    or {}
                )

                result_racer = (
                    result_racers.get(str(lane))
                    or result_racers.get(lane)
                    or {}
                )

                if not program_racer:
                    continue

                row = make_racer(
                    program_racer,
                    {},
                    lane,
                )

                place = _int(
                    result_racer.get("place_number"),
                    0,
                )

                row["着順"] = place
                row["1着"] = 1 if place == 1 else 0
                row["場"] = stadium_no
                row["レース"] = race_no

                result.append(row)

    return result


@st.cache_data(ttl=1800)
def history14(target_date):
    """
    直近14日分の結果をAI学習用DataFrameにする。
    """

    import pandas as pd

    if isinstance(target_date, str):
        target_date = date.fromisoformat(target_date)

    all_rows = []

    # 今日を含めて過去14日
    for days_ago in range(0, 14):

        d = target_date - timedelta(days=days_ago)

        try:
            raw = get_data(d)
            rows = _build_history_rows(raw)
            all_rows.extend(rows)

        except Exception:
            # データがない日があっても続行
            continue

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)

    return df


# =========================================================
# レース情報確認
# =========================================================

def validate_race(race, stadium_no, race_no, target_date):
    """
    UI表示前の最終検証。
    """

    stadium_no = int(stadium_no)
    race_no = int(race_no)

    if not isinstance(race, dict):
        return False, "raceデータが辞書ではありません。"

    if _int(race.get("stadium_number"), -1) != stadium_no:
        return False, "場番号が一致しません。"

    if _int(race.get("race_number"), -1) != race_no:
        return False, "レース番号が一致しません。"

    expected_date = (
        target_date.isoformat()
        if isinstance(target_date, date)
        else str(target_date)
    )

    actual_date = str(race.get("date", ""))

    if actual_date and actual_date != expected_date:
        return False, "開催日が一致しません。"

    racers = race.get("racers")

    if not isinstance(racers, dict):
        return False, "出走選手データがありません。"

    for lane in range(1, 7):
        r = racers.get(str(lane)) or racers.get(lane)

        if not isinstance(r, dict):
            return False, f"{lane}号艇がありません。"

        if not r.get("name"):
            return False, f"{lane}号艇の選手名がありません。"

    return True, "OK"
