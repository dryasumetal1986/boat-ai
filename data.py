import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import date, timedelta

BASE_API = "https://boatraceopenapi.github.io/api/v1"

STADIUMS = {
    "桐生": 1, "戸田": 2, "江戸川": 3, "平和島": 4,
    "多摩川": 5, "浜名湖": 6, "蒲郡": 7, "常滑": 8,
    "津": 9, "三国": 10, "びわこ": 11, "住之江": 12,
    "尼崎": 13, "鳴門": 14, "丸亀": 15, "児島": 16,
    "宮島": 17, "徳山": 18, "下関": 19, "若松": 20,
    "芦屋": 21, "福岡": 22, "唐津": 23, "大村": 24,
}

DAY_CACHE = {}


def _num(v, default=0.0):
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def stadium_code(name):
    return STADIUMS.get(name)


def get_day_data(target_date):
    """
    1日分の24場データを取得。
    """
    key = target_date.strftime("%Y%m%d")

    if key in DAY_CACHE:
        return DAY_CACHE[key]

    url = f"{BASE_API}/{target_date.year}/{key}.json"

    try:
        r = requests.get(
            url,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        r.raise_for_status()
        data = r.json()
        DAY_CACHE[key] = data
        return data
    except Exception:
        DAY_CACHE[key] = {}
        return {}


def get_all_races(target_date):
    """
    1日分の全24場・全レースを返す。
    """
    data = get_day_data(target_date)
    out = []

    programs = data.get("programs", {})
    stadiums = programs.get("stadiums", {})

    for stadium_no, stadium_data in stadiums.items():
        try:
            stadium_no = int(stadium_no)
        except Exception:
            continue

        stadium_name = next(
            (k for k, v in STADIUMS.items() if v == stadium_no),
            str(stadium_no),
        )

        races = stadium_data.get("races", {})

        for race_no, race in races.items():
            try:
                race_no_int = int(race_no)
            except Exception:
                continue

            out.append({
                "date": target_date,
                "stadium_no": stadium_no,
                "stadium": stadium_name,
                "race_no": race_no_int,
                "race": race,
            })

    out.sort(key=lambda x: (x["stadium_no"], x["race_no"]))
    return out


def get_race(target_date, stadium_name, race_no):
    """
    指定場・指定レースを取得。
    """
    data = get_day_data(target_date)
    stadium_no = stadium_code(stadium_name)

    if not stadium_no:
        return None

    stadiums = data.get("programs", {}).get("stadiums", {})
    stadium = stadiums.get(str(stadium_no), stadiums.get(stadium_no, {}))

    races = stadium.get("races", {})
    race = races.get(str(race_no), races.get(race_no))

    return race


def _preview_list(race):
    preview = race.get("preview", {}) if isinstance(race, dict) else {}

    if isinstance(preview, list):
        return preview

    for key in ["racers", "entries", "players"]:
        value = preview.get(key)
        if isinstance(value, list):
            return value

    return []


def _safe_boat(v):
    """
    1～6だけを艇番として認める。
    67などは絶対に艇番にしない。
    """
    try:
        n = int(v)
        if 1 <= n <= 6:
            return n
    except Exception:
        pass
    return None


def _find_preview(previews, boat, racer=None):
    """
    プレビュー情報を艇番で探す。

    racer_numberは艇番として使わない。
    """
    boat = _safe_boat(boat)

    if boat is not None:
        for p in previews:
            if not isinstance(p, dict):
                continue

            pboat = _safe_boat(
                p.get("boat_number", p.get("course_number"))
            )

            if pboat == boat:
                return p

    # コース番号がない古い形式の場合だけ、
    # リスト位置を艇番として利用する。
    if boat is not None and 1 <= boat <= len(previews):
        p = previews[boat - 1]
        if isinstance(p, dict):
            return p

    return {}


def _racer_id(r):
    if not isinstance(r, dict):
        return None

    for key in [
        "racer_number",
        "racer_no",
        "player_number",
        "id",
    ]:
        value = r.get(key)
        if value not in (None, ""):
            return str(value)

    return None


def _racer_name(r):
    if not isinstance(r, dict):
        return ""

    for key in ["name", "racer_name", "player_name"]:
        value = r.get(key)
        if value:
            return str(value).strip()

    return ""


def race_to_df(race):
    """
    出走表をAI用DataFrameに変換。

    ★重要
    APIのracer_numberは選手ID。
    艇番には絶対に使用しない。

    racerの配列順を1～6号艇として扱う。
    """
    if not race:
        return pd.DataFrame()

    racers = race.get("racers", [])
    if not isinstance(racers, list):
        return pd.DataFrame()

    previews = _preview_list(race)

    rows = []

    for i, r in enumerate(racers[:6]):
        if not isinstance(r, dict):
            continue

        # ★艇番は必ず配列位置から決定
        boat = i + 1

        p = _find_preview(previews, boat, r)

        row = {
            "boat": boat,
            "name": _racer_name(r),

            # 選手IDは別項目
            "racer_number": _racer_id(r) or "",

            "average_start_timing": _num(
                r.get("average_start_timing")
            ),

            "national_win_rate": _num(
                r.get("national_win_rate")
            ),
            "national_top_2_percent": _num(
                r.get("national_top_2_percent")
            ),
            "national_top_3_percent": _num(
                r.get("national_top_3_percent")
            ),

            "local_win_rate": _num(
                r.get("local_win_rate")
            ),
            "local_top_2_percent": _num(
                r.get("local_top_2_percent")
            ),
            "local_top_3_percent": _num(
                r.get("local_top_3_percent")
            ),

            "motor_top_2_percent": _num(
                r.get("motor_top_2_percent")
            ),
            "motor_top_3_percent": _num(
                r.get("motor_top_3_percent")
            ),

            "boat_top_2_percent": _num(
                r.get("boat_top_2_percent")
            ),
            "boat_top_3_percent": _num(
                r.get("boat_top_3_percent")
            ),

            "flying_count": _num(
                r.get("flying_count")
            ),
            "late_count": _num(
                r.get("late_count")
            ),

            "course_number": boat,

            "start_timing": _num(
                p.get("start_timing")
            ),
            "exhibition_time": _num(
                p.get("exhibition_time")
            ),
            "weight": _num(
                p.get("weight")
            ),
            "tilt": _num(
                p.get("tilt")
            ),
        }

        rows.append(row)

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    # 念のため艇番を1～6に固定
    df["boat"] = range(1, len(df) + 1)

    return df


def _result_racers(race):
    result = race.get("result", {}) if isinstance(race, dict) else {}

    if isinstance(result, list):
        return result

    for key in ["racers", "results", "ranking"]:
        value = result.get(key)
        if isinstance(value, list):
            return value

    return []


def _result_place(r):
    if not isinstance(r, dict):
        return None

    for key in [
        "place_number",
        "place",
        "rank",
        "arrival",
    ]:
        value = r.get(key)
        try:
            n = int(value)
            if 1 <= n <= 6:
                return n
        except Exception:
            pass

    return None


def _result_explicit_boat(r):
    if not isinstance(r, dict):
        return None

    # racer_numberはここでも使わない
    for key in [
        "boat_number",
        "course_number",
        "boat",
    ]:
        boat = _safe_boat(r.get(key))
        if boat is not None:
            return boat

    return None


def get_result(race):
    """
    結果を「1着艇, 2着艇, 3着艇」で返す。

    例:
        (2, 1, 4)

    ★選手IDを艇番として使わない。
    """
    if not race:
        return None

    result_racers = _result_racers(race)

    if not result_racers:
        return None

    program_racers = race.get("racers", [])
    if not isinstance(program_racers, list):
        program_racers = []

    # 選手ID → 本来の艇番
    id_to_boat = {}

    # 選手名 → 本来の艇番
    name_to_boat = {}

    for i, r in enumerate(program_racers[:6]):
        boat = i + 1

        rid = _racer_id(r)
        name = _racer_name(r)

        if rid:
            id_to_boat[rid] = boat

        if name:
            name_to_boat[name] = boat

    placements = {}

    for idx, rr in enumerate(result_racers):
        if not isinstance(rr, dict):
            continue

        place = _result_place(rr)

        if place is None:
            continue

        # まず明示された艇番
        boat = _result_explicit_boat(rr)

        # なければ選手IDからプログラムの艇番を逆引き
        if boat is None:
            rid = _racer_id(rr)
            if rid and rid in id_to_boat:
                boat = id_to_boat[rid]

        # 名前から逆引き
        if boat is None:
            name = _racer_name(rr)
            if name and name in name_to_boat:
                boat = name_to_boat[name]

        # 最後の非常手段
        # 結果データが「艇番順」でしか入っていない場合のみ使用
        if boat is None and idx < 6:
            candidate = idx + 1
            if candidate in range(1, 7):
                boat = candidate

        if boat in range(1, 7):
            placements[place] = boat

    if not all(p in placements for p in [1, 2, 3]):
        return None

    result = (
        placements[1],
        placements[2],
        placements[3],
    )

    # 重複艇番は不正
    if len(set(result)) != 3:
        return None

    return result


def get_payout(race):
    """
    3連単払戻金を取得。
    """
    if not race:
        return 0

    result = race.get("result", {})

    payouts = result.get("payouts", {})
    trifecta = payouts.get("trifecta", [])

    if isinstance(trifecta, dict):
        trifecta = [trifecta]

    if isinstance(trifecta, list):
        for item in trifecta:
            if not isinstance(item, dict):
                continue

            amount = item.get("amount")

            try:
                return int(float(amount))
            except Exception:
                continue

    return 0


def get_official_odds(target_date, stadium_name, race_no):
    """
    BOATRACE公式3連単オッズを取得。

    取得できなかった場合は {}。
    """
    code = stadium_code(stadium_name)

    if not code:
        return {}

    date_str = target_date.strftime("%Y%m%d")

    url = (
        "https://www.boatrace.jp/owpc/pc/race/odds3t"
        f"?hd={date_str}&jcd={code:02d}&rno={race_no}"
    )

    try:
        r = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0"
            },
        )
        r.raise_for_status()
    except Exception:
        return {}

    soup = BeautifulSoup(r.text, "html.parser")

    odds = {}

    # 3連単表のtrを探索
    rows = soup.select("tr")

    for tr in rows:
        cells = tr.find_all(["td", "th"])

        texts = []
        for cell in cells:
            text = cell.get_text(" ", strip=True)
            if text:
                texts.append(text)

        # 18セル程度の行が3連単表
        if len(texts) < 18:
            continue

        # 数字らしいものだけを残す
        values = []
        for text in texts:
            cleaned = text.replace(",", "").replace("¥", "").strip()
            values.append(cleaned)

        # 6グループ × 3セル
        for group in range(6):
            start = group * 3

            if start + 2 >= len(values):
                break

            second = values[start]
            third = values[start + 1]
            oddstext = values[start + 2]

            try:
                second_i = int(second)
                third_i = int(third)
                odds_value = float(
                    oddstext.replace("倍", "")
                )

                first_i = group + 1

                if (
                    1 <= first_i <= 6
                    and 1 <= second_i <= 6
                    and 1 <= third_i <= 6
                    and len({
                        first_i,
                        second_i,
                        third_i,
                    }) == 3
                ):
                    key = (
                        first_i,
                        second_i,
                        third_i,
                    )
                    odds[key] = odds_value

            except Exception:
                continue

    return odds
