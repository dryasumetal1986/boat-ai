import re
from datetime import date, timedelta

import requests
import streamlit as st


# =========================
# API
# =========================
API = "https://boatraceopenapi.github.io/api/v1"


# =========================
# 競艇場
# =========================
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


# =========================
# 共通処理
# =========================
def _date_string(target_date):
    """
    date / datetime.date / str のどれが来ても
    YYYY-MM-DD に統一する。
    """

    if isinstance(target_date, date):
        return target_date.isoformat()

    value = str(target_date).strip()

    # YYYY-MM-DD
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value

    # YYYYMMDD
    if re.fullmatch(r"\d{8}", value):
        return (
            f"{value[:4]}-{value[4:6]}-{value[6:8]}"
        )

    raise ValueError(
        f"日付形式が不正です: {target_date}"
    )


def _date_object(target_date):
    value = _date_string(target_date)
    return date.fromisoformat(value)


def _num(value, default=0.0):
    """
    数字文字列をfloatへ変換。
    """
    if value is None:
        return default

    if isinstance(value, bool):
        return default

    try:
        text = str(value).strip()

        if text in ("", "-", "--", "null", "None"):
            return default

        text = text.replace("%", "")
        text = text.replace("秒", "")

        return float(text)

    except Exception:
        return default


def _int(value, default=0):
    try:
        return int(float(value))
    except Exception:
        return default


def _val(obj, *keys, default=None):
    """
    複数候補キーから値を取得。
    """
    if not isinstance(obj, dict):
        return default

    for key in keys:
        if key in obj and obj[key] not in (None, ""):
            return obj[key]

    return default


# =========================
# 場名
# =========================
def stadium_name(stadium_no):
    return STADIUMS.get(
        _int(stadium_no),
        str(stadium_no),
    )


# =========================
# APIデータ取得
# =========================
@st.cache_data(ttl=180)
def get_data(target_date):
    """
    指定日のBoatrace Open APIデータを取得。
    日付型でも文字列でもOK。
    """

    date_text = _date_string(target_date)

    yyyy = date_text[:4]
    yyyymmdd = date_text.replace("-", "")

    url = (
        f"{API}/{yyyy}/{yyyymmdd}.json"
    )

    response = requests.get(
        url,
        timeout=20,
    )

    response.raise_for_status()

    return response.json()


# =========================
# 指定場・指定R取得
# =========================
def get_race(raw, stadium_no, race_no):
    """
    指定した場・Rを正確に取得する。

    以前のように全体を再帰検索せず、
    stadiums -> races を直接指定する。
    """

    stadium_no = _int(stadium_no)
    race_no = _int(race_no)

    programs = raw.get("programs", {})
    stadiums = programs.get("stadiums", {})

    stadium = stadiums.get(str(stadium_no))

    if not isinstance(stadium, dict):
        raise ValueError(
            f"場番号 {stadium_no} のデータがありません。"
        )

    races = stadium.get("races", {})

    race = races.get(str(race_no))

    if not isinstance(race, dict):
        raise ValueError(
            f"{stadium_name(stadium_no)} {race_no}R のデータがありません。"
        )

    actual_stadium = _int(
        _val(
            race,
            "stadium_number",
            "stadiumNumber",
            default=stadium_no,
        )
    )

    actual_race = _int(
        _val(
            race,
            "race_number",
            "raceNumber",
            default=race_no,
        )
    )

    if actual_stadium != stadium_no:
        raise ValueError(
            "場番号が一致しません。"
        )

    if actual_race != race_no:
        raise ValueError(
            "レース番号が一致しません。"
        )

    return race


# =========================
# 選手データ作成
# =========================
def make_racer(
    program_racer,
    preview_racer=None,
    lane=0,
):
    """
    1艇分の特徴量を作成。
    """

    program_racer = (
        program_racer
        if isinstance(program_racer, dict)
        else {}
    )

    preview_racer = (
        preview_racer
        if isinstance(preview_racer, dict)
        else {}
    )

    player = _val(
        program_racer,
        "player",
        "racer",
        default={},
    )

    if not isinstance(player, dict):
        player = {}

    name = _val(
        program_racer,
        "name",
        "racer_name",
        "racerName",
        default=None,
    )

    if not name:
        name = _val(
            player,
            "name",
            "racer_name",
            "racerName",
            default="",
        )

    register_number = _val(
        program_racer,
        "registration_number",
        "registrationNumber",
        "reg_no",
        default=None,
    )

    if register_number is None:
        register_number = _val(
            player,
            "registration_number",
            "registrationNumber",
            "reg_no",
            default=0,
        )

    grade = _val(
        program_racer,
        "grade",
        "class",
        "racer_grade",
        default=None,
    )

    if grade is None:
        grade = _val(
            player,
            "grade",
            "class",
            "racer_grade",
            default="",
        )

    national = _val(
        program_racer,
        "national",
        "nation",
        default={},
    )

    local = _val(
        program_racer,
        "local",
        "stadium",
        default={},
    )

    motor = _val(
        program_racer,
        "motor",
        default={},
    )

    boat = _val(
        program_racer,
        "boat",
        default={},
    )

    if not isinstance(national, dict):
        national = {}

    if not isinstance(local, dict):
        local = {}

    if not isinstance(motor, dict):
        motor = {}

    if not isinstance(boat, dict):
        boat = {}

    avg_st = _val(
        program_racer,
        "average_start_timing",
        "averageStartTiming",
        "avg_st",
        "average_st",
        default=0,
    )

    exhibition_st = _val(
        preview_racer,
        "start_timing",
        "startTiming",
        "exhibition_st",
        "exhibitionStartTiming",
        default=avg_st,
    )

    exhibition_time = _val(
        preview_racer,
        "exhibition_time",
        "exhibitionTime",
        "exhibition_time_second",
        default=0,
    )

    exhibition_entry = _val(
        preview_racer,
        "entry",
        "entry_number",
        "entryNumber",
        "start_course",
        "startCourse",
        default=lane,
    )

    return {
        "枠": lane,
        "選手名": str(name),
        "登録番号": _int(register_number),
        "級別": str(grade),

        "展示進入": _num(
            exhibition_entry,
            lane,
        ),

        "全国勝率": _num(
            _val(
                national,
                "win_rate",
                "winRate",
                "rate",
                default=0,
            )
        ),

        "全国2連率": _num(
            _val(
                national,
                "second_place_rate",
                "secondPlaceRate",
                "2ren_rate",
                "2renRate",
                default=0,
            )
        ),

        "全国3連率": _num(
            _val(
                national,
                "third_place_rate",
                "thirdPlaceRate",
                "3ren_rate",
                "3renRate",
                default=0,
            )
        ),

        "当地勝率": _num(
            _val(
                local,
                "win_rate",
                "winRate",
                "rate",
                default=0,
            )
        ),

        "当地2連率": _num(
            _val(
                local,
                "second_place_rate",
                "secondPlaceRate",
                "2ren_rate",
                "2renRate",
                default=0,
            )
        ),

        "モーター": _int(
            _val(
                motor,
                "number",
                "motor_number",
                "motorNumber",
                default=0,
            )
        ),

        "モーター2連率": _num(
            _val(
                motor,
                "second_place_rate",
                "secondPlaceRate",
                "2ren_rate",
                "2renRate",
                default=0,
            )
        ),

        "ボート": _int(
            _val(
                boat,
                "number",
                "boat_number",
                "boatNumber",
                default=0,
            )
        ),

        "平均ST": _num(avg_st),

        "展示ST": _num(exhibition_st),

        "展示タイム": _num(exhibition_time),

        "場": 0,
    }


# =========================
# 公式展示データ互換
# =========================
def official_preview(race):
    preview = race.get("preview", {})

    if not isinstance(preview, dict):
        return {}

    racers = preview.get("racers", {})

    if isinstance(racers, list):
        return {
            str(i + 1): item
            for i, item in enumerate(racers)
        }

    if isinstance(racers, dict):
        return racers

    return {}


# =========================
# 6艇データ作成
# =========================
def get_race_rows(
    race,
    stadium_no,
    race_no,
):
    stadium_no = _int(stadium_no)
    race_no = _int(race_no)

    racers = race.get("racers", {})

    if isinstance(racers, list):
        program_racers = {
            str(i + 1): item
            for i, item in enumerate(racers)
        }
    elif isinstance(racers, dict):
        program_racers = racers
    else:
        program_racers = {}

    preview_racers = official_preview(race)

    rows = []

    for lane in range(1, 7):

        program_racer = program_racers.get(
            str(lane),
            {},
        )

        preview_racer = preview_racers.get(
            str(lane),
            {},
        )

        row = make_racer(
            program_racer,
            preview_racer,
            lane,
        )

        row["場"] = stadium_no

        rows.append(row)

    if len(rows) != 6:
        raise ValueError(
            "6艇分の選手データを取得できませんでした。"
        )

    names = [
        str(row["選手名"]).strip()
        for row in rows
    ]

    if any(not name for name in names):
        raise ValueError(
            "選手名を取得できない艇があります。"
        )

    import pandas as pd

    return pd.DataFrame(rows)


# =========================
# 過去データ作成
# =========================
def _build_history_rows(raw):
    """
    APIデータから過去成績用の学習データを作る。
    """

    import pandas as pd

    rows = []

    programs = raw.get("programs", {})
    stadiums = programs.get("stadiums", {})

    if not isinstance(stadiums, dict):
        return pd.DataFrame()

    results = raw.get("results", {})

    if not isinstance(results, dict):
        results = {}

    for stadium_key, stadium_data in stadiums.items():

        stadium_no = _int(stadium_key)

        if not isinstance(stadium_data, dict):
            continue

        races = stadium_data.get("races", {})

        if not isinstance(races, dict):
            continue

        for race_key, race in races.items():

            if not isinstance(race, dict):
                continue

            race_no = _int(race_key)

            racers = race.get("racers", {})

            if isinstance(racers, list):
                racers = {
                    str(i + 1): item
                    for i, item in enumerate(racers)
                }

            if not isinstance(racers, dict):
                continue

            # 結果データ
            race_result = results.get(
                str(stadium_no),
                {},
            )

            if not isinstance(race_result, dict):
                race_result = {}

            result_race = race_result.get(
                str(race_no),
                {},
            )

            if not isinstance(result_race, dict):
                result_race = {}

            result_racers = result_race.get(
                "racers",
                result_race.get("results", {}),
            )

            if isinstance(result_racers, list):
                result_racers = {
                    str(i + 1): item
                    for i, item in enumerate(result_racers)
                }

            if not isinstance(result_racers, dict):
                result_racers = {}

            for lane in range(1, 7):

                racer = racers.get(
                    str(lane),
                    {},
                )

                result_racer = result_racers.get(
                    str(lane),
                    {},
                )

                if not isinstance(racer, dict):
                    racer = {}

                if not isinstance(result_racer, dict):
                    result_racer = {}

                preview = {}

                row = make_racer(
                    racer,
                    preview,
                    lane,
                )

                row["場"] = stadium_no

                finish = _val(
                    result_racer,
                    "finish_position",
                    "finishPosition",
                    "rank",
                    "着順",
                    default=0,
                )

                finish = _int(finish)

                row["1着"] = (
                    1 if finish == 1 else 0
                )

                rows.append(row)

    return pd.DataFrame(rows)


# =========================
# 過去14日
# =========================
@st.cache_data(ttl=600)
def history14(target_date):

    target = _date_object(target_date)

    all_rows = []

    # 今日を含めて過去14日
    for i in range(1, 15):

        d = target - timedelta(days=i)

        try:
            raw = get_data(d)

            df = _build_history_rows(raw)

            if not df.empty:
                all_rows.append(df)

        except Exception:
            # 過去データが存在しない日は無視
            continue

    if not all_rows:
        import pandas as pd
        return pd.DataFrame()

    import pandas as pd

    return pd.concat(
        all_rows,
        ignore_index=True,
    )


# =========================
# データ検証
# =========================
def validate_race(
    race,
    target_date,
    stadium_no,
    race_no,
):
    stadium_no = _int(stadium_no)
    race_no = _int(race_no)

    expected_date = _date_string(
        target_date
    )

    actual_stadium = _int(
        _val(
            race,
            "stadium_number",
            "stadiumNumber",
            default=stadium_no,
        )
    )

    actual_race = _int(
        _val(
            race,
            "race_number",
            "raceNumber",
            default=race_no,
        )
    )

    actual_date = _val(
        race,
        "date",
        "race_date",
        "raceDate",
        default=expected_date,
    )

    if actual_stadium != stadium_no:
        raise ValueError(
            f"場が一致しません: "
            f"{actual_stadium} / {stadium_no}"
        )

    if actual_race != race_no:
        raise ValueError(
            f"Rが一致しません: "
            f"{actual_race} / {race_no}"
        )

    if actual_date:
        actual_date = str(actual_date)[:10]

        if actual_date != expected_date:
            raise ValueError(
                f"日付が一致しません: "
                f"{actual_date} / {expected_date}"
            )

    return True
