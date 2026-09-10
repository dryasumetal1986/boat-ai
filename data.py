import time
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

API_BASE = "https://boatraceopenapi.github.io/api/v1"
API_START_DATE = date(2026, 1, 1)
JST = timezone(timedelta(hours=9))

STADIUM_NAMES = {
    1:"桐生",2:"戸田",3:"江戸川",4:"平和島",5:"多摩川",6:"浜名湖",
    7:"蒲郡",8:"常滑",9:"津",10:"三国",11:"びわこ",12:"住之江",
    13:"尼崎",14:"鳴門",15:"丸亀",16:"児島",17:"宮島",18:"徳山",
    19:"下関",20:"若松",21:"芦屋",22:"福岡",23:"唐津",24:"大村"
}


def jst_today():
    return datetime.now(JST).date()


def _to_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                pass
    raise ValueError(f"日付を解釈できません: {value}")


def stadium_name(stadium_number):
    try:
        n = int(stadium_number)
    except Exception:
        return str(stadium_number)
    return STADIUM_NAMES.get(n, f"{n}号場")


def _request_json(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
        "Accept": "application/json,text/plain,*/*",
    }

    for attempt in range(2):
        try:
            r = requests.get(url, headers=headers, timeout=15)

            if r.status_code == 200:
                return r.json()

            if r.status_code == 404:
                return None

        except requests.RequestException:
            if attempt == 0:
                time.sleep(0.8)

    return None


@st.cache_data(ttl=180, show_spinner=False)
def get_data(target_date):
    d = _to_date(target_date)

    if d < API_START_DATE:
        return None

    urls = []

    if d == jst_today():
        urls.append(f"{API_BASE}/today.json")

    urls.append(
        f"{API_BASE}/{d:%Y}/{d:%Y%m%d}.json"
    )

    for url in urls:
        raw = _request_json(url)
        if isinstance(raw, dict) and "programs" in raw:
            return raw

    return None


def get_race(raw, stadium_number, race_number):
    if not raw:
        return None

    stadiums = raw.get("programs", {}).get("stadiums", {})
    stadium = stadiums.get(str(int(stadium_number)))

    if not isinstance(stadium, dict):
        return None

    races = stadium.get("races", {})
    return races.get(str(int(race_number)))


def get_result(race):
    if not isinstance(race, dict):
        return {}
    result = race.get("result")
    return result if isinstance(result, dict) else {}


def _entry_dict(obj, number):
    if not isinstance(obj, dict):
        return {}

    value = obj.get(str(number))

    if value is None:
        value = obj.get(number)

    return value if isinstance(value, dict) else {}


def get_race_rows(race):
    if not isinstance(race, dict):
        return pd.DataFrame()

    racers = race.get("racers", {})
    preview = race.get("preview", {})
    preview_racers = preview.get("racers", {})

    rows = []

    for boat in range(1, 7):
        r = _entry_dict(racers, boat)
        p = _entry_dict(preview_racers, boat)

        row = {
            "枠": boat,
            "艇": boat,
            "艇番": boat,
            "entry_number": boat,
            "選手名": (
                r.get("name")
                or r.get("racer_name")
                or r.get("選手名")
                or f"{boat}号艇"
            ),

            "展示進入": p.get("course")
                or p.get("entry_course")
                or p.get("展示進入")
                or boat,

            "展示ST": p.get("start_time")
                or p.get("exhibition_start")
                or p.get("展示ST")
                or 0,

            "展示タイム": p.get("exhibition_time")
                or p.get("展示タイム")
                or 0,

            "全国勝率": r.get("national_win_rate")
                or r.get("全国勝率")
                or 0,

            "全国2連率": r.get("national_2_rate")
                or r.get("全国2連率")
                or 0,

            "全国3連率": r.get("national_3_rate")
                or r.get("全国3連率")
                or 0,

            "当地勝率": r.get("local_win_rate")
                or r.get("当地勝率")
                or 0,

            "当地2連率": r.get("local_2_rate")
                or r.get("当地2連率")
                or 0,

            "当地3連率": r.get("local_3_rate")
                or r.get("当地3連率")
                or 0,

            "モーター2連率": r.get("motor_2_rate")
                or r.get("モーター2連率")
                or 0,

            "モーター3連率": r.get("motor_3_rate")
                or r.get("モーター3連率")
                or 0,

            "平均ST": r.get("average_start_time")
                or r.get("平均ST")
                or 0,
        }

        rows.append(row)

    return pd.DataFrame(rows)


def get_result_order(race):
    result = get_result(race)
    racers = result.get("racers", {})

    if not isinstance(racers, dict):
        return []

    values = []

    for key, item in racers.items():
        if not isinstance(item, dict):
            continue

        try:
            boat = int(
                item.get("entry_number")
                or item.get("boat_number")
                or key
            )
            place = int(
                item.get("place_number")
                or item.get("rank")
                or 0
            )
        except Exception:
            continue

        if 1 <= boat <= 6 and 1 <= place <= 6:
            values.append((place, boat))

    values.sort(key=lambda x: x[0])
    return [boat for _, boat in values]


def available_stadiums(raw):
    if not raw:
        return []

    stadiums = raw.get("programs", {}).get("stadiums", {})
    result = []

    for key in stadiums:
        try:
            result.append(int(key))
        except Exception:
            pass

    return sorted(result)


def available_races(raw, stadium_number):
    if not raw:
        return []

    stadiums = raw.get("programs", {}).get("stadiums", {})
    stadium = stadiums.get(str(int(stadium_number)))

    if not isinstance(stadium, dict):
        return []

    races = stadium.get("races", {})
    result = []

    for key in races:
        try:
            result.append(int(key))
        except Exception:
            pass

    return sorted(result)


def race_has_result(race):
    return len(get_result_order(race)) >= 3


@st.cache_data(ttl=1800, show_spinner=False)
def history14(stadium_number, race_number, target_date):
    d = _to_date(target_date)
    records = []

    for days_back in range(1, 15):
        hd = d - timedelta(days=days_back)

        if hd < API_START_DATE:
            break

        raw = get_data(hd)
        race = get_race(raw, stadium_number, race_number)

        if not race:
            continue

        order = get_result_order(race)

        if len(order) < 3:
            continue

        rows = get_race_rows(race)

        if rows.empty:
            continue

        rows = rows.copy()
        rows["着順"] = rows["枠"].map(
            {boat: place + 1 for place, boat in enumerate(order)}
        )

        rows["履歴日"] = str(hd)
        records.append(rows)

    if not records:
        return pd.DataFrame()

    return pd.concat(records, ignore_index=True)


def all_races_for_date(raw):
    result = []

    for stadium in available_stadiums(raw):
        for race_number in available_races(raw, stadium):
            race = get_race(raw, stadium, race_number)

            if race:
                result.append(
                    (stadium, race_number, race)
                )

    return result


# ---------------------------------------------------------
# 公式BOATRACE 3連単オッズ
# ---------------------------------------------------------

ODDS_URL = (
    "https://www.boatrace.jp/owpc/pc/race/"
    "odds3t?rno={race}&jcd={stadium:02d}&hd={date}"
)


def _request_html(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 "
            "like Mac OS X) AppleWebKit/605.1.15"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "ja-JP,ja;q=0.9",
    }

    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.text
    except requests.RequestException:
        pass

    return None


@st.cache_data(ttl=60, show_spinner=False)
def get_trifecta_odds(target_date, stadium_number, race_number):
    """
    公式BOATRACEの3連単オッズを取得。

    戻り値:
      {
        (1,2,3): 19.5,
        (1,2,4): 35.2,
        ...
      }

    取得できない場合は {}。
    """

    d = _to_date(target_date)

    url = ODDS_URL.format(
        date=d.strftime("%Y%m%d"),
        stadium=int(stadium_number),
        race=int(race_number),
    )

    html = _request_html(url)

    if not html:
        return {}

    soup = BeautifulSoup(html, "html.parser")

    # 公式サイトの3連単表は oddsPoint にオッズが入る。
    odds_nodes = soup.select("td.oddsPoint")

    values = []

    for node in odds_nodes:
        text = node.get_text(" ", strip=True)
        text = text.replace(",", "")

        try:
            value = float(text)
            if value > 0:
                values.append(value)
        except Exception:
            pass

    # 正常な3連単表は120通り
    if len(values) < 120:
        return {}

    values = values[:120]

    combinations = []

    for a in range(1, 7):
        for b in range(1, 7):
            if b == a:
                continue

            for c in range(1, 7):
                if c == a or c == b:
                    continue

                combinations.append((a, b, c))

    return dict(zip(combinations, values))
