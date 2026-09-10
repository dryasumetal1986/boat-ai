import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime

BASE_API = "https://boatraceopenapi.github.io/api/v1"
DAY_CACHE = {}

STADIUMS = {
    "01": "桐生", "02": "戸田", "03": "江戸川", "04": "平和島",
    "05": "多摩川", "06": "浜名湖", "07": "蒲郡", "08": "常滑",
    "09": "津", "10": "三国", "11": "びわこ", "12": "住之江",
    "13": "尼崎", "14": "鳴門", "15": "丸亀", "16": "児島",
    "17": "宮島", "18": "徳山", "19": "下関", "20": "若松",
    "21": "芦屋", "22": "福岡", "23": "唐津", "24": "大村"
}

def _day_data(date):
    if date in DAY_CACHE:
        return DAY_CACHE[date]

    y = date[:4]
    url = f"{BASE_API}/{y}/{date}.json"

    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        DAY_CACHE[date] = data
        return data
    except Exception:
        return None


def get_race(date, stadium, race_no):
    data = _day_data(date)
    if not data:
        return None

    try:
        jcd = next(
            k for k, v in STADIUMS.items()
            if v == stadium
        )
        race = data["programs"]["stadiums"][jcd]["races"][str(race_no)]
        return race
    except Exception:
        return None


def _num(x, default=0.0):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default


def race_to_df(race):
    if not race:
        return pd.DataFrame()

    rows = []

    for i, r in enumerate(race.get("racers", []), 1):
        preview = {}
        previews = race.get("preview", {}).get("racers", [])

        if isinstance(previews, list):
            for p in previews:
                if str(p.get("boat_number", p.get("course_number", ""))) == str(i):
                    preview = p
                    break

        rows.append({
            "boat": i,
            "name": r.get("name", f"{i}号艇"),
            "win_rate": _num(r.get("national_win_rate")),
            "top2": _num(r.get("national_top_2_percent")),
            "top3": _num(r.get("national_top_3_percent")),
            "local_rate": _num(r.get("local_win_rate")),
            "local_top2": _num(r.get("local_top_2_percent")),
            "local_top3": _num(r.get("local_top_3_percent")),
            "motor_top2": _num(r.get("motor_top_2_percent")),
            "motor_top3": _num(r.get("motor_top_3_percent")),
            "boat_top2": _num(r.get("boat_top_2_percent")),
            "boat_top3": _num(r.get("boat_top_3_percent")),
            "flying": _num(r.get("flying_count")),
            "late": _num(r.get("late_count")),
            "start": _num(preview.get("start_timing")),
            "exhibition": _num(preview.get("exhibition_time")),
            "course": int(_num(preview.get("course_number"), i)),
        })

    return pd.DataFrame(rows)


def get_result(race):
    try:
        result = race.get("result", {})
        racers = result.get("racers", [])

        places = {}
        for r in racers:
            boat = int(r.get("boat_number", r.get("course_number", 0)))
            place = int(r.get("place_number", 0))
            if boat and place:
                places[place] = boat

        if len(places) >= 3:
            return tuple(places[i] for i in (1, 2, 3))
    except Exception:
        pass

    return None


def get_payout(race, combination):
    try:
        payouts = race.get("result", {}).get("payouts", {})
        trifecta = payouts.get("trifecta", [])

        for p in trifecta:
            c = str(p.get("combination", "")).replace("-", "").replace(" ", "")
            target = "".join(map(str, combination))
            if c == target:
                return int(_num(p.get("amount"), 0))
    except Exception:
        pass

    return 0


def get_official_odds(date, jcd, race_no):
    """
    公式3連単オッズを120通り取得。
    取得できない場合は空dict。
    """
    url = (
        "https://www.boatrace.jp/owpc/pc/race/odds3t"
        f"?hd={date}&jcd={int(jcd):02d}&rno={race_no}"
    )

    try:
        r = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        r.raise_for_status()
    except Exception:
        return {}

    soup = BeautifulSoup(r.text, "html.parser")
    odds = {}

    for tr in soup.select("tr"):
        cells = tr.find_all("td")
        texts = [x.get_text(" ", strip=True) for x in cells]
        texts = [x for x in texts if x]

        if len(texts) < 18:
            continue

        # 1着艇ごとに [2着, 3着, オッズ] が6セット
        for first in range(1, 7):
            base = (first - 1) * 3
            if base + 2 >= len(texts):
                continue

            try:
                second = int(texts[base])
                third = int(texts[base + 1])
                odd_text = texts[base + 2].replace(",", "")

                if second not in range(1, 7):
                    continue
                if third not in range(1, 7):
                    continue
                if len({first, second, third}) != 3:
                    continue

                odds_value = float(
                    odd_text.replace("倍", "").strip()
                )
                if odds_value > 0:
                    odds[(first, second, third)] = odds_value
            except Exception:
                continue

    return odds


def get_history(date, stadium, start_race=1, end_race=12):
    rows = []

    for rno in range(start_race, end_race + 1):
        race = get_race(date, stadium, rno)
        if not race:
            continue

        df = race_to_df(race)
        result = get_result(race)

        if len(df) == 6 and result:
            rows.append({
                "race_no": rno,
                "df": df,
                "result": result,
                "payout": get_payout(race, result),
            })

    return rows
