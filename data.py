import requests
import pandas as pd
from bs4 import BeautifulSoup

BASE_API = "https://boatraceopenapi.github.io/api/v1"

STADIUMS = {
    "01": "桐生", "02": "戸田", "03": "江戸川", "04": "平和島",
    "05": "多摩川", "06": "浜名湖", "07": "蒲郡", "08": "常滑",
    "09": "津", "10": "三国", "11": "びわこ", "12": "住之江",
    "13": "尼崎", "14": "鳴門", "15": "丸亀", "16": "児島",
    "17": "宮島", "18": "徳山", "19": "下関", "20": "若松",
    "21": "芦屋", "22": "福岡", "23": "唐津", "24": "大村"
}

DAY_CACHE = {}


def _num(x, default=0.0):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default


def stadium_code(name):
    for code, label in STADIUMS.items():
        if label == name:
            return code
    return None


def get_day_data(date):
    if date in DAY_CACHE:
        return DAY_CACHE[date]

    url = f"{BASE_API}/{date[:4]}/{date}.json"

    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        DAY_CACHE[date] = data
        return data
    except Exception:
        return None


def get_all_races(date):
    """
    1日分の全24場・全レースを取得。
    """
    data = get_day_data(date)
    result = []

    if not data:
        return result

    try:
        stadiums = data["programs"]["stadiums"]
    except Exception:
        return result

    for code in STADIUMS:
        stadium = stadiums.get(code)
        if not stadium:
            stadium = stadiums.get(int(code)) if isinstance(stadiums, dict) else None
        if not stadium:
            continue

        races = stadium.get("races", {})

        if isinstance(races, list):
            iterable = enumerate(races, 1)
        else:
            iterable = races.items()

        for race_no, race in iterable:
            if not race:
                continue

            try:
                rno = int(race_no)
            except Exception:
                continue

            result.append({
                "date": date,
                "stadium_code": code,
                "stadium": STADIUMS[code],
                "race_no": rno,
                "race": race,
            })

    result.sort(key=lambda x: (x["stadium_code"], x["race_no"]))
    return result


def get_race(date, stadium, race_no):
    code = stadium_code(stadium)
    if not code:
        return None

    data = get_day_data(date)
    if not data:
        return None

    try:
        stadiums = data["programs"]["stadiums"]

        st = stadiums.get(code)
        if st is None:
            st = stadiums.get(int(code))

        races = st.get("races", {})
        race = races.get(str(race_no))

        if race is None and isinstance(races, dict):
            race = races.get(int(race_no))

        if race is None and isinstance(races, list):
            race = races[race_no - 1]

        return race
    except Exception:
        return None


def _preview_list(race):
    preview = race.get("preview", {})
    racers = preview.get("racers", [])

    if isinstance(racers, dict):
        racers = list(racers.values())

    return racers if isinstance(racers, list) else []


def _find_preview(previews, boat):
    for p in previews:
        b = p.get(
            "boat_number",
            p.get("course_number", p.get("racer_number", ""))
        )
        try:
            if int(b) == boat:
                return p
        except Exception:
            pass
    return {}


def race_to_df(race):
    if not race:
        return pd.DataFrame()

    racers = race.get("racers", [])
    if isinstance(racers, dict):
        racers = list(racers.values())

    if not isinstance(racers, list):
        return pd.DataFrame()

    previews = _preview_list(race)
    rows = []

    for i in range(6):
        r = racers[i] if i < len(racers) else {}
        boat = i + 1

        b = r.get("boat_number", r.get("racer_number", boat))
        try:
            boat = int(b)
        except Exception:
            boat = i + 1

        p = _find_preview(previews, boat)

        rows.append({
            "boat": boat,
            "name": r.get("name", f"{boat}号艇"),

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

            "start": _num(p.get("start_timing")),
            "exhibition": _num(p.get("exhibition_time")),
            "course": int(_num(p.get("course_number"), boat)),
        })

    return pd.DataFrame(rows)


def get_result(race):
    try:
        result = race.get("result", {})
        racers = result.get("racers", [])

        if isinstance(racers, dict):
            racers = list(racers.values())

        places = {}

        for r in racers:
            boat = r.get(
                "boat_number",
                r.get("course_number", r.get("racer_number", 0))
            )
            place = r.get("place_number", 0)

            try:
                boat = int(boat)
                place = int(place)
            except Exception:
                continue

            if 1 <= place <= 6 and 1 <= boat <= 6:
                places[place] = boat

        if all(x in places for x in (1, 2, 3)):
            return (
                places[1],
                places[2],
                places[3],
            )
    except Exception:
        pass

    return None


def get_payout(race, combination):
    try:
        payouts = race.get("result", {}).get("payouts", {})
        trifecta = payouts.get("trifecta", [])

        if isinstance(trifecta, dict):
            trifecta = list(trifecta.values())

        target = "".join(map(str, combination))

        for p in trifecta:
            c = str(p.get("combination", ""))
            c = c.replace("-", "").replace(" ", "")

            if c == target:
                return int(_num(p.get("amount"), 0))
    except Exception:
        pass

    return 0


def get_official_odds(date, jcd, race_no):
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
        texts = [
            x.get_text(" ", strip=True)
            for x in cells
        ]
        texts = [x for x in texts if x]

        if len(texts) < 18:
            continue

        for first in range(1, 7):
            base = (first - 1) * 3

            try:
                second = int(texts[base])
                third = int(texts[base + 1])

                odd_text = (
                    texts[base + 2]
                    .replace(",", "")
                    .replace("倍", "")
                    .strip()
                )

                odd = float(odd_text)

                if (
                    1 <= second <= 6
                    and 1 <= third <= 6
                    and len({first, second, third}) == 3
                    and odd > 0
                ):
                    odds[(first, second, third)] = odd

            except Exception:
                continue

    return odds
