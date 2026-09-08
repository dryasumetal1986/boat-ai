import itertools
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import requests
import streamlit as st


# ============================================================
# やっちゃんの競艇AI予想 PRO
# CSSなし・シンプル安定版
# ============================================================

st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO",
    page_icon="🚤",
    layout="wide",
)


# ============================================================
# 基本設定
# ============================================================

API_BASE = "https://boatraceopenapi.github.io/api/v1"

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


TECHNIQUES = {
    1: "逃げ",
    2: "差し",
    3: "まくり",
    4: "まくり差し",
    5: "抜き",
    6: "恵まれ",
}


WIND_DIRECTIONS = {
    1: "北",
    2: "北東",
    3: "東",
    4: "南東",
    5: "南",
    6: "南西",
    7: "西",
    8: "北西",
}


# ============================================================
# 共通関数
# ============================================================

def safe_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(value)
    except Exception:
        return default


def clamp(value, low, high):
    return max(low, min(high, value))


def fmt_percent(value):
    return f"{value:.1f}%"


def date_string(d):
    return d.strftime("%Y%m%d")


# ============================================================
# API取得
# ============================================================

@st.cache_data(ttl=180, show_spinner=False)
def fetch_day_data(target_date):
    """
    Boatrace Open APIから1日分を取得。
    APIは2026-01-01以降のv1を使用。
    """

    if isinstance(target_date, datetime):
        target_date = target_date.date()

    if target_date < date(2026, 1, 1):
        return None, "2026年1月1日以前のデータには対応していません。"

    today = date.today()

    if target_date > today:
        return None, "未来の日付には対応していません。"

    y = target_date.strftime("%Y")
    ymd = target_date.strftime("%Y%m%d")

    url = f"{API_BASE}/{y}/{ymd}.json"

    try:
        response = requests.get(
            url,
            timeout=20,
            headers={
                "User-Agent": "Mozilla/5.0",
            },
        )

        if response.status_code == 404:
            return None, f"{ymd} のデータがまだありません。"

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):
            return None, "APIから不正なデータが返されました。"

        return data, None

    except requests.exceptions.Timeout:
        return None, "データ取得がタイムアウトしました。"

    except requests.exceptions.RequestException as e:
        return None, f"通信エラー: {e}"

    except ValueError:
        return None, "JSONデータの読み込みに失敗しました。"

    except Exception as e:
        return None, f"予期しないエラー: {e}"


# ============================================================
# レース取得
# ============================================================

def get_race(data, stadium_number, race_number):
    if not data:
        return None

    try:
        stadiums = data.get("programs", {}).get("stadiums", {})
        stadium = stadiums.get(str(stadium_number))

        if not stadium:
            return None

        races = stadium.get("races", {})
        race = races.get(str(race_number))

        return race

    except Exception:
        return None


# ============================================================
# 現在レースの出走表をDataFrame化
# ============================================================

def build_current_dataframe(race):
    if not race:
        return pd.DataFrame()

    racers = race.get("racers", {})
    preview = race.get("preview", {}).get("racers", {})

    rows = []

    for entry in range(1, 7):
        racer = racers.get(str(entry), {})
        prev = preview.get(str(entry), {})

        if not racer:
            continue

        course = safe_int(
            prev.get("course_number"),
            entry,
        )

        rows.append(
            {
                "枠": entry,
                "選手名": racer.get("name", "不明"),
                "登録番号": racer.get("number", 0),
                "級別": racer.get("rank_number", 0),
                "年齢": racer.get("age", 0),
                "平均ST": safe_float(
                    racer.get("average_start_timing")
                ),
                "全国勝率": safe_float(
                    racer.get("national_win_rate")
                ),
                "全国2連率": safe_float(
                    racer.get("national_top_2_percent")
                ),
                "全国3連率": safe_float(
                    racer.get("national_top_3_percent")
                ),
                "当地勝率": safe_float(
                    racer.get("local_win_rate")
                ),
                "当地2連率": safe_float(
                    racer.get("local_top_2_percent")
                ),
                "当地3連率": safe_float(
                    racer.get("local_top_3_percent")
                ),
                "モーター2連率": safe_float(
                    racer.get("motor_top_2_percent")
                ),
                "モーター3連率": safe_float(
                    racer.get("motor_top_3_percent")
                ),
                "ボート2連率": safe_float(
                    racer.get("boat_top_2_percent")
                ),
                "ボート3連率": safe_float(
                    racer.get("boat_top_3_percent")
                ),
                "進入コース": course,
                "展示タイム": safe_float(
                    prev.get("exhibition_time")
                ),
                "展示ST": safe_float(
                    prev.get("start_timing")
                ),
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# 直前情報
# ============================================================

def get_preview_info(race):
    if not race:
        return {}

    preview = race.get("preview", {})

    wind_number = safe_int(
        preview.get("wind_direction_number")
    )

    return {
        "風速": safe_int(preview.get("wind_speed")),
        "風向": WIND_DIRECTIONS.get(
            wind_number,
            f"風向{wind_number}",
        ),
        "波高": safe_int(preview.get("wave_height")),
        "気温": safe_float(preview.get("air_temperature")),
        "水温": safe_float(preview.get("water_temperature")),
    }


# ============================================================
# 履歴データ作成
# ============================================================

@st.cache_data(ttl=1800, show_spinner=False)
def build_history(target_date, days):
    """
    過去days日分の結果から統計を作る。
    """

    if isinstance(target_date, datetime):
        target_date = target_date.date()

    player_course = {}
    venue_course = {}
    venue_wind = {}
    player_technique = {}
    venue_technique = {}

    loaded_days = 0
    loaded_races = 0

    for offset in range(1, days + 1):
        d = target_date - timedelta(days=offset)

        if d < date(2026, 1, 1):
            break

        data, error = fetch_day_data(d)

        if not data:
            continue

        loaded_days += 1

        stadiums = (
            data
            .get("programs", {})
            .get("stadiums", {})
        )

        for stadium_key, stadium in stadiums.items():

            stadium_number = safe_int(stadium_key)

            races = stadium.get("races", {})

            for race_key, race in races.items():

                result = race.get("result")

                if not result:
                    continue

                result_racers = result.get(
                    "racers",
                    {},
                )

                if not result_racers:
                    continue

                loaded_races += 1

                # ----------------------------------------
                # 風向
                # 1レースにつき1回だけカウント
                # ----------------------------------------

                wind_number = safe_int(
                    result.get(
                        "wind_direction_number"
                    )
                )

                wind_key = (
                    stadium_number,
                    wind_number,
                )

                if wind_key not in venue_wind:
                    venue_wind[wind_key] = {
                        "races": 0,
                        "wins": 0,
                    }

                venue_wind[wind_key]["races"] += 1

                # ----------------------------------------
                # 決まり手
                # ----------------------------------------

                technique_number = safe_int(
                    result.get("technique_number")
                )

                technique_name = TECHNIQUES.get(
                    technique_number,
                    "不明",
                )

                venue_technique_key = (
                    stadium_number,
                    technique_name,
                )

                if venue_technique_key not in venue_technique:
                    venue_technique[
                        venue_technique_key
                    ] = {
                        "wins": 0,
                    }

                venue_technique[
                    venue_technique_key
                ]["wins"] += 1

                # ----------------------------------------
                # 選手結果
                # ----------------------------------------

                for entry_key, rr in result_racers.items():

                    place = safe_int(
                        rr.get("place_number")
                    )

                    if place <= 0:
                        continue

                    course = safe_int(
                        rr.get("course_number")
                    )

                    player_number = safe_int(
                        rr.get("number")
                    )

                    if player_number <= 0:
                        continue

                    # 選手×コース
                    pc_key = (
                        player_number,
                        course,
                    )

                    if pc_key not in player_course:
                        player_course[pc_key] = {
                            "starts": 0,
                            "wins": 0,
                            "top2": 0,
                            "top3": 0,
                        }

                    player_course[pc_key]["starts"] += 1

                    if place == 1:
                        player_course[pc_key]["wins"] += 1

                    if place <= 2:
                        player_course[pc_key]["top2"] += 1

                    if place <= 3:
                        player_course[pc_key]["top3"] += 1

                    # 選手×決まり手
                    if place == 1:
                        pt_key = (
                            player_number,
                            technique_name,
                        )

                        if pt_key not in player_technique:
                            player_technique[
                                pt_key
                            ] = {
                                "wins": 0,
                            }

                        player_technique[
                            pt_key
                        ]["wins"] += 1

                    # 会場×コース
                    vc_key = (
                        stadium_number,
                        course,
                    )

                    if vc_key not in venue_course:
                        venue_course[vc_key] = {
                            "starts": 0,
                            "wins": 0,
                        }

                    venue_course[vc_key]["starts"] += 1

                    if place == 1:
                        venue_course[vc_key]["wins"] += 1

                # 風向で1着コースも記録
                winners = [
                    rr
                    for rr in result_racers.values()
                    if safe_int(
                        rr.get("place_number")
                    ) == 1
                ]

                for winner in winners:
                    venue_wind[wind_key]["wins"] += 1

    return {
        "player_course": player_course,
        "venue_course": venue_course,
        "venue_wind": venue_wind,
        "player_technique": player_technique,
        "venue_technique": venue_technique,
        "loaded_days": loaded_days,
        "loaded_races": loaded_races,
    }


# ============================================================
# AI評価
# ============================================================

def get_player_course_stats(history, player_number, course):
    item = history["player_course"].get(
        (player_number, course),
        {},
    )

    starts = item.get("starts", 0)

    if starts <= 0:
        return {
            "starts": 0,
            "win_rate": 0.0,
            "top2_rate": 0.0,
            "top3_rate": 0.0,
        }

    return {
        "starts": starts,
        "win_rate": item.get("wins", 0)
        / starts
        * 100,
        "top2_rate": item.get("top2", 0)
        / starts
        * 100,
        "top3_rate": item.get("top3", 0)
        / starts
        * 100,
    }


def get_venue_course_stats(history, stadium_number, course):
    item = history["venue_course"].get(
        (stadium_number, course),
        {},
    )

    starts = item.get("starts", 0)

    if starts <= 0:
        return {
            "starts": 0,
            "win_rate": 0.0,
        }

    return {
        "starts": starts,
        "win_rate": item.get("wins", 0)
        / starts
        * 100,
    }


def calculate_ai_score(
    row,
    stadium_number,
    preview_info,
    history,
):
    course = safe_int(row["進入コース"])
    player_number = safe_int(row["登録番号"])

    national = safe_float(row["全国勝率"])
    local = safe_float(row["当地勝率"])

    motor = safe_float(row["モーター2連率"])
    motor3 = safe_float(row["モーター3連率"])

    avg_st = safe_float(row["平均ST"])
    exhibition = safe_float(row["展示タイム"])

    player_course = get_player_course_stats(
        history,
        player_number,
        course,
    )

    venue_course = get_venue_course_stats(
        history,
        stadium_number,
        course,
    )

    # --------------------------------------------------------
    # 基本点
    # --------------------------------------------------------

    score = 0.0

    # 全国勝率
    score += clamp(national * 4.0, 0, 32)

    # 当地勝率
    score += clamp(local * 3.0, 0, 24)

    # モーター
    score += clamp(motor * 0.18, 0, 18)

    score += clamp(motor3 * 0.08, 0, 8)

    # 選手のコース実績
    score += clamp(
        player_course["win_rate"] * 0.30,
        0,
        15,
    )

    score += clamp(
        player_course["top2_rate"] * 0.08,
        0,
        8,
    )

    # 会場コース実績
    score += clamp(
        venue_course["win_rate"] * 0.30,
        0,
        15,
    )

    # --------------------------------------------------------
    # コース補正
    # --------------------------------------------------------

    course_bonus = {
        1: 18,
        2: 8,
        3: 6,
        4: 7,
        5: 2,
        6: -2,
    }

    score += course_bonus.get(course, 0)

    # --------------------------------------------------------
    # ST補正
    # --------------------------------------------------------

    if avg_st > 0:
        if avg_st <= 0.12:
            score += 10
        elif avg_st <= 0.15:
            score += 6
        elif avg_st <= 0.18:
            score += 2
        elif avg_st >= 0.22:
            score -= 5

    # --------------------------------------------------------
    # 展示タイム補正
    # レース内で後ほど相対比較するため軽め
    # --------------------------------------------------------

    if exhibition > 0:
        score += clamp(
            (6.90 - exhibition) * 12,
            -8,
            8,
        )

    # --------------------------------------------------------
    # 風補正
    # --------------------------------------------------------

    wind_speed = safe_int(
        preview_info.get("風速", 0)
    )

    wind_direction = preview_info.get(
        "風向",
        "",
    )

    # 強風時は内枠を少し優先
    if wind_speed >= 5:
        if course == 1:
            score += 5
        elif course == 2:
            score += 2
        elif course >= 5:
            score -= 2

    # --------------------------------------------------------
    # 風向×会場の過去データ
    # --------------------------------------------------------

    wind_number = None

    for number, name in WIND_DIRECTIONS.items():
        if name == wind_direction:
            wind_number = number
            break

    if wind_number is not None:
        wind_stats = history["venue_wind"].get(
            (stadium_number, wind_number),
            {},
        )

        races = wind_stats.get("races", 0)

        if races >= 10:
            # 風向データがあること自体を軽く加点
            score += 1.0

    # --------------------------------------------------------
    # AI1着率に変換
    # --------------------------------------------------------

    ai_rate = clamp(
        15 + score * 0.65,
        1,
        95,
    )

    return score, ai_rate


# ============================================================
# 3連単候補
# ============================================================

def build_trifecta_predictions(df):
    if df.empty:
        return pd.DataFrame()

    scores = {}

    for _, row in df.iterrows():
        scores[int(row["枠"])] = safe_float(
            row["AI評価"]
        )

    candidates = []

    for combo in itertools.permutations(
        range(1, 7),
        3,
    ):
        if any(
            x not in scores
            for x in combo
        ):
            continue

        first = scores[combo[0]]
        second = scores[combo[1]]
        third = scores[combo[2]]

        # 1着を強く評価
        total = (
            first * 0.55
            + second * 0.28
            + third * 0.17
        )

        candidates.append(
            {
                "買い目": (
                    f"{combo[0]}-"
                    f"{combo[1]}-"
                    f"{combo[2]}"
                ),
                "AI指数": round(total, 2),
            }
        )

    result = pd.DataFrame(candidates)

    if result.empty:
        return result

    return result.sort_values(
        "AI指数",
        ascending=False,
    ).reset_index(drop=True)


# ============================================================
# メイン画面
# ============================================================

st.title("🚤 やっちゃんの競艇AI予想 PRO")

st.write(
    "全国24場・全12R対応。"
    "選手成績、当地成績、モーター、ST、展示タイム、"
    "コース実績、風向などを使ってAI評価します。"
)

st.warning(
    "⚠️ このアプリは予想支援用です。"
    "データは非公式APIを利用しており、"
    "数分程度の遅延や欠損が発生する場合があります。"
    "投票前には必ず公式情報を確認してください。"
)


# ============================================================
# 条件選択
# ============================================================

st.subheader("📅 レース選択")

col1, col2, col3 = st.columns(3)

with col1:
    target_date = st.date_input(
        "開催日",
        value=date.today(),
        min_value=date(2026, 1, 1),
        max_value=date.today(),
    )

with col2:
    stadium_name = st.selectbox(
        "競艇場",
        list(STADIUMS.values()),
    )

stadium_number = next(
    number
    for number, name in STADIUMS.items()
    if name == stadium_name
)

with col3:
    race_number = st.selectbox(
        "レース",
        list(range(1, 13)),
        format_func=lambda x: f"{x}R",
    )


history_days = st.selectbox(
    "AI分
