import requests
import pandas as pd
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
# 日付
# =========================

def _date_object(value):

    if hasattr(value, "year"):
        return value

    return pd.to_datetime(value).date()


def _date_string(value):

    return _date_object(value).isoformat()


# =========================
# 数値
# =========================

def _num(value):

    try:

        if value is None:
            return 0.0

        if pd.isna(value):
            return 0.0

        return float(value)

    except Exception:

        return 0.0


def _int(value):

    try:
        return int(float(value))
    except Exception:
        return 0


def _val(
    obj,
    *keys,
    default=None,
):

    if not isinstance(obj, dict):
        return default

    for key in keys:

        if key in obj:

            value = obj[key]

            if value is not None:
                return value

    return default


# =========================
# 場名
# =========================

def stadium_name(number):

    try:
        return STADIUMS[int(number)]

    except Exception:
        return "不明"


# =========================
# APIデータ取得
# =========================

@st.cache_data(
    ttl=300,
    show_spinner=False,
)
def get_data(date):

    date_obj = _date_object(date)

    year = date_obj.strftime("%Y")
    yyyymmdd = date_obj.strftime("%Y%m%d")

    # 現在の正しいv1形式
    url = (
        f"{API}/"
        f"{year}/"
        f"{yyyymmdd}.json"
    )

    try:

        response = requests.get(
            url,
            timeout=20,
        )

    except Exception:

        return None


    if response.status_code == 200:

        try:
            return response.json()
        except Exception:
            return None


    # 今日だけtoday.jsonも試す
    today = pd.Timestamp.now(
        tz="Asia/Tokyo"
    ).date()


    if date_obj == today:

        today_url = (
            f"{API}/today.json"
        )

        try:

            response = requests.get(
                today_url,
                timeout=20,
            )

            if response.status_code == 200:
                return response.json()

        except Exception:
            pass


    return None


# =========================
# レース取得
# =========================

def get_race(
    raw,
    stadium_no,
    race_no,
):

    if not isinstance(raw, dict):
        return None


    programs = raw.get(
        "programs",
        {},
    )

    stadiums = programs.get(
        "stadiums",
        {},
    )


    stadium = (
        stadiums.get(str(stadium_no))
        or stadiums.get(stadium_no)
    )


    if not stadium:
        return None


    races = stadium.get(
        "races",
        {},
    )


    return (
        races.get(str(race_no))
        or races.get(race_no)
    )


# =========================
# 結果取得
# =========================

def get_result(
    raw,
    stadium_no,
    race_no,
):

    race = get_race(
        raw,
        stadium_no,
        race_no,
    )


    if not race:
        return None


    return race.get(
        "result"
    )


# =========================
# 結果順位
# =========================

def get_result_order(
    raw,
    stadium_no,
    race_no,
):

    result = get_result(
        raw,
        stadium_no,
        race_no,
    )


    if not result:
        return []


    racers = result.get(
        "racers",
        {},
    )


    if isinstance(
        racers,
        dict,
    ):

        racers = list(
            racers.values()
        )


    if not isinstance(
        racers,
        list,
    ):
        return []


    ordered = []


    for item in racers:

        if not isinstance(
            item,
            dict,
        ):
            continue


        place = _val(
            item,
            "place_number",
            "finish_position",
            "rank",
            "着順",
            "順位",
        )


        boat = _val(
            item,
            "entry_number",
            "boat_number",
            "boat_no",
            "number",
            "艇番",
        )


        if place is None:
            continue

        if boat is None:
            continue


        ordered.append(
            (
                _int(place),
                _int(boat),
            )
        )


    ordered.sort(
        key=lambda x: x[0]
    )


    return [
        boat
        for _, boat in ordered
        if boat > 0
    ]


# =========================
# 完了レース判定
# =========================

def is_completed_race(
    raw,
    stadium_no,
    race_no,
):

    result = get_result(
        raw,
        stadium_no,
        race_no,
    )


    if not result:
        return False


    order = get_result_order(
        raw,
        stadium_no,
        race_no,
    )


    return len(order) >= 3


# =========================
# 選手データ
# =========================

def make_racer(
    item,
    stadium_no=None,
    preview=None,
):

    if preview is None:
        preview = {}


    boat_no = _int(
        _val(
            item,
            "entry_number",
            "boat_number",
            "boat_no",
            "number",
            "艇番",
            default=0,
        )
    )


    preview_course = _int(
        _val(
            preview,
            "course_number",
            "exhibition_course",
            "展示進入",
            default=0,
        )
    )


    return {

        # =========================
        # 基本
        # =========================

        "艇番": boat_no,

        "選手名": str(
            _val(
                item,
                "name",
                "racer_name",
                "player_name",
                "選手名",
                default="選手",
            )
        ),

        "枠": boat_no,


        # =========================
        # 選手成績
        # =========================

        "全国勝率": _num(
            _val(
                item,
                "national_win_rate",
                "win_rate",
                "全国勝率",
            )
        ),

        "全国2連率": _num(
            _val(
                item,
                "national_top_2_percent",
                "national_2rentai_rate",
                "national_second_rate",
                "全国2連率",
            )
        ),

        "全国3連率": _num(
            _val(
                item,
                "national_top_3_percent",
                "national_3rentai_rate",
                "national_third_rate",
                "全国3連率",
            )
        ),

        "当地勝率": _num(
            _val(
                item,
                "local_win_rate",
                "当地勝率",
            )
        ),

        "当地2連率": _num(
            _val(
                item,
                "local_top_2_percent",
                "local_2rentai_rate",
                "当地2連率",
            )
        ),

        "モーター2連率": _num(
            _val(
                item,
                "motor_top_2_percent",
                "motor_2rentai_rate",
                "motor_second_rate",
                "モーター2連率",
            )
        ),


        # =========================
        # ST
        # =========================

        "平均ST": _num(
            _val(
                item,
                "average_start_timing",
                "average_st",
                "avg_st",
                "平均ST",
            )
        ),

        "展示ST": _num(
            _val(
                preview,
                "start_timing",
                "exhibition_st",
                "展示ST",
            )
        ),


        # =========================
        # 展示
        # =========================

        "展示タイム": _num(
            _val(
                preview,
                "exhibition_time",
                "展示タイム",
            )
        ),

        "展示進入": (
            preview_course
            if preview_course > 0
            else boat_no
        ),


        # =========================
        # 場
        # =========================

        "場": int(
            stadium_no or 0
        ),
    }


# =========================
# 公式プレビュー
# =========================

def official_preview(
    race,
):

    if not race:
        return []


    racers = race.get(
        "racers",
        {},
    )


    if isinstance(
        racers,
        dict,
    ):

        racers = list(
            racers.values()
        )


    if not isinstance(
        racers,
        list,
    ):
        return []


    return racers


# =========================
# 6艇取得
# =========================

def get_race_rows(
    race,
    stadium_no=None,
    race_no=None,
):

    if not race:
        return pd.DataFrame()


    racers = race.get(
        "racers",
        {},
    )


    previews = (
        race.get(
            "preview",
            {}
        )
        or {}
    )


    preview_racers = previews.get(
        "racers",
        {},
    )


    if isinstance(
        racers,
        dict,
    ):

        racer_items = list(
            racers.items()
        )

    else:

        racer_items = []


    rows = []


    for key, item in racer_items:

        if not isinstance(
            item,
            dict,
        ):
            continue


        entry_number = _int(
            _val(
                item,
                "entry_number",
                default=key,
            )
        )


        preview = {}


        if isinstance(
            preview_racers,
            dict,
        ):

            preview = (
                preview_racers.get(
                    str(entry_number),
                    {}
                )
                or preview_racers.get(
                    entry_number,
                    {}
                )
                or {}
            )


        row = make_racer(
            item,
            stadium_no,
            preview,
        )


        rows.append(row)


    df = pd.DataFrame(
        rows
    )


    if df.empty:
        return df


    df = df.sort_values(
        "艇番"
    )


    return df.reset_index(
        drop=True
    )


# =========================
# レース確認
# =========================

def validate_race(
    race,
    target_date=None,
    stadium_no=None,
    race_no=None,
):

    if not race:
        return False


    rows = get_race_rows(
        race,
        stadium_no,
        race_no,
    )


    if len(rows) != 6:
        return False


    boats = sorted(
        rows["艇番"].tolist()
    )


    if boats != [
        1, 2, 3, 4, 5, 6
    ]:

        return False


    race_stadium = _val(
        race,
        "stadium_number",
    )


    race_number = _val(
        race,
        "race_number",
    )


    if (
        stadium_no is not None
        and race_stadium is not None
        and _int(race_stadium)
        != _int(stadium_no)
    ):

        return False


    if (
        race_no is not None
        and race_number is not None
        and _int(race_number)
        != _int(race_no)
    ):

        return False


    return True


# =========================
# 履歴
# =========================

def _build_history_rows(
    raw,
):

    rows = []


    if not isinstance(
        raw,
        dict,
    ):
        return rows


    stadiums = (
        raw.get(
            "programs",
            {}
        )
        .get(
            "stadiums",
            {}
        )
    )


    for sk, stadium in stadiums.items():

        try:
            sn = int(sk)
        except Exception:
            continue


        races = stadium.get(
            "races",
            {}
        )


        for rk, race in races.items():

            try:
                rn = int(rk)
            except Exception:
                continue


            if not is_completed_race(
                raw,
                sn,
                rn,
            ):

                continue


            race_rows = get_race_rows(
                race,
                sn,
                rn,
            )


            if len(race_rows) != 6:
                continue


            order = get_result_order(
                raw,
                sn,
                rn,
            )


            if len(order) < 3:
                continue


            for _, row in race_rows.iterrows():

                item = row.to_dict()


                item["1着"] = int(
                    order[0]
                    == int(row["艇番"])
                )


                item["2着"] = int(
                    order[1]
                    == int(row["艇番"])
                )


                item["3着"] = int(
                    order[2]
                    == int(row["艇番"])
                )


                rows.append(
                    item
                )


    return rows


# =========================
# 過去14日
# =========================

@st.cache_data(
    ttl=1800,
    show_spinner=False,
)
def history14(
    target_date,
):

    date_obj = _date_object(
        target_date
    )


    all_rows = []


    for days in range(
        1,
        15,
    ):

        day = (
            date_obj
            - pd.Timedelta(
                days=days
            )
        )


        date_text = (
            day.strftime(
                "%Y-%m-%d"
            )
        )


        try:

            raw = get_data(
                date_text
            )

        except Exception:

            continue


        if not raw:
            continue


        all_rows.extend(
            _build_history_rows(
                raw
            )
        )


    if not all_rows:
        return pd.DataFrame()


    return pd.DataFrame(
        all_rows
    )
