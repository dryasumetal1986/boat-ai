import re
import requests
from bs4 import BeautifulSoup


VENUES = {
    "桐生": "01",
    "戸田": "02",
    "江戸川": "03",
    "平和島": "04",
    "多摩川": "05",
    "浜名湖": "06",
    "蒲郡": "07",
    "常滑": "08",
    "津": "09",
    "三国": "10",
    "びわこ": "11",
    "住之江": "12",
    "尼崎": "13",
    "鳴門": "14",
    "丸亀": "15",
    "児島": "16",
    "宮島": "17",
    "徳山": "18",
    "下関": "19",
    "若松": "20",
    "芦屋": "21",
    "福岡": "22",
    "唐津": "23",
    "大村": "24",
}

VENUE_NAMES = {
    int(v): k
    for k, v in VENUES.items()
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) "
        "Version/17.0 Mobile/15E148 Safari/604.1"
    )
}

API_BASE = (
    "https://boatraceopenapi.github.io/api/v1"
)

_SESSION = requests.Session()
_SESSION.headers.update(HEADERS)

_DAY_CACHE = {}


def _get_json(url, timeout=8):
    try:
        r = _SESSION.get(
            url,
            timeout=timeout,
        )

        if r.status_code != 200:
            return None

        return r.json()

    except Exception:
        return None


def _get_html(url, timeout=8):
    try:
        r = _SESSION.get(
            url,
            timeout=timeout,
        )

        if r.status_code != 200:
            return ""

        return r.text

    except Exception:
        return ""


def _num(value, default=0.0):
    try:
        if value is None:
            return default

        return float(
            str(value)
            .replace(",", "")
            .replace("%", "")
            .replace("％", "")
            .strip()
        )

    except Exception:
        return default


def _int(value, default=0):
    try:
        return int(float(value))
    except Exception:
        return default


def _api_url(date):
    clean = str(date).replace("-", "")
    year = clean[:4]

    return (
        f"{API_BASE}/{year}/{clean}.json"
    )


def get_day_data(date, force=False):
    """
    1日分のデータを1回だけ取得。

    1日分のJSONに全国24場が入っているため、
    バックテストのHTTPアクセス数を大幅削減する。
    """

    key = str(date)

    if not force and key in _DAY_CACHE:
        return _DAY_CACHE[key]

    data = _get_json(
        _api_url(date),
        timeout=10,
    )

    if data is None:
        return None

    _DAY_CACHE[key] = data

    return data


def clear_cache():
    _DAY_CACHE.clear()


def _find_race(
    date,
    venue_id,
    race_no,
):
    data = get_day_data(date)

    if not data:
        return None

    stadiums = (
        data
        .get("programs", {})
        .get("stadiums", {})
    )

    stadium = stadiums.get(
        str(int(venue_id))
    )

    if not stadium:
        return None

    races = stadium.get(
        "races",
        {},
    )

    race = races.get(
        str(int(race_no))
    )

    return race


def _course_score(course):
    values = {
        1: 1.00,
        2: 0.82,
        3: 0.70,
        4: 0.58,
        5: 0.46,
        6: 0.36,
    }

    return values.get(
        int(course),
        0.50,
    )


def _build_boat(
    boat,
    base,
    preview,
):
    boat = int(boat)

    base = base or {}
    preview = preview or {}

    return {
        "boat": boat,

        "name": str(
            base.get(
                "name",
                f"{boat}号艇",
            )
        ),

        "national_win_rate": _num(
            base.get(
                "national_win_rate"
            )
        ),

        "national_top2": _num(
            base.get(
                "national_top_2_percent"
            )
        ),

        "national_top3": _num(
            base.get(
                "national_top_3_percent"
            )
        ),

        "local_win_rate": _num(
            base.get(
                "local_win_rate"
            )
        ),

        "local_top2": _num(
            base.get(
                "local_top_2_percent"
            )
        ),

        "local_top3": _num(
            base.get(
                "local_top_3_percent"
            )
        ),

        "motor_top2": _num(
            base.get(
                "motor_top_2_percent"
            )
        ),

        "motor_top3": _num(
            base.get(
                "motor_top_3_percent"
            )
        ),

        "boat_top2": _num(
            base.get(
                "boat_top_2_percent"
            )
        ),

        "boat_top3": _num(
            base.get(
                "boat_top_3_percent"
            )
        ),

        "average_start": _num(
            base.get(
                "average_start_timing"
            )
        ),

        "flying_count": _int(
            base.get(
                "flying_count"
            )
        ),

        "late_count": _int(
            base.get(
                "late_count"
            )
        ),

        "course": _int(
            preview.get(
                "course_number",
                boat,
            ),
            boat,
        ),

        "start_timing": _num(
            preview.get(
                "start_timing"
            )
        ),

        "exhibition_time": _num(
            preview.get(
                "exhibition_time"
            )
        ),

        "course_score": _course_score(
            _int(
                preview.get(
                    "course_number",
                    boat,
                ),
                boat,
            )
        ),
    }


def get_race(
    date,
    venue,
    race_no,
):
    """
    APIから1レースを取得し、
    AIが扱いやすい形式へ変換する。
    """

    venue_id = VENUES.get(
        venue
    )

    if not venue_id:
        return None

    raw = _find_race(
        date,
        venue_id,
        race_no,
    )

    if not raw:
        return None

    raw_racers = raw.get(
        "racers",
        {},
    )

    preview = raw.get(
        "preview",
        {}
    )

    preview_racers = preview.get(
        "racers",
        {},
    )

    boats = []

    for boat in range(1, 7):
        base = raw_racers.get(
            str(boat),
            {}
        )

        pre = preview_racers.get(
            str(boat),
            {}
        )

        if not base:
            continue

        boats.append(
            _build_boat(
                boat,
                base,
                pre,
            )
        )

    if len(boats) != 6:
        return None

    return {
        "date": str(
            raw.get(
                "date",
                date,
            )
        ),
        "venue": venue,
        "venue_id": venue_id,
        "race_no": int(race_no),

        "title": raw.get(
            "title",
            "",
        ),

        "day_number": _int(
            raw.get(
                "day_number"
            )
        ),

        "grade_number": _int(
            raw.get(
                "grade_number"
            )
        ),

        "closed_at": raw.get(
            "closed_at",
            "",
        ),

        "preview": {
            "wind_speed": _num(
                preview.get(
                    "wind_speed"
                )
            ),
            "wave_height": _num(
                preview.get(
                    "wave_height"
                )
            ),
            "air_temperature": _num(
                preview.get(
                    "air_temperature"
                )
            ),
            "water_temperature": _num(
                preview.get(
                    "water_temperature"
                )
            ),
        },

        "boats": boats,
    }


def get_race_result(
    date,
    venue_id,
    race_no,
):
    """
    APIの結果から着順と3連単払戻を取得。
    """

    raw = _find_race(
        date,
        venue_id,
        race_no,
    )

    if not raw:
        return None

    result = raw.get(
        "result"
    )

    if not result:
        return None

    racers = result.get(
        "racers",
        {}
    )

    positions = []

    for key, value in racers.items():
        place = _int(
            value.get(
                "place_number"
            )
        )

        entry = _int(
            value.get(
                "entry_number",
                key,
            )
        )

        if (
            1 <= place <= 6
            and 1 <= entry <= 6
        ):
            positions.append(
                (
                    place,
                    entry,
                )
            )

    positions.sort(
        key=lambda x: x[0]
    )

    actual = tuple(
        x[1]
        for x in positions[:3]
    )

    if len(actual) != 3:
        return None

    payout = 0

    payouts = result.get(
        "payouts",
        {}
    )

    trifecta = payouts.get(
        "trifecta",
        []
    )

    for item in trifecta:
        combo = str(
            item.get(
                "combination",
                ""
            )
        )

        numbers = re.findall(
            r"[1-6]",
            combo,
        )

        if len(numbers) >= 3:
            parsed = tuple(
                int(x)
                for x in numbers[:3]
            )

            if parsed == actual:
                payout = _int(
                    item.get(
                        "amount"
                    )
                )
                break

    return {
        "actual": actual,
        "trifecta_payout": payout,
    }


def _parse_odds_rows(
    soup
):
    """
    BOATRACE公式3連単オッズ表を解析。

    1行につき
    [2着, 3着, オッズ] × 6艇
    の構造になっているため、
    それを120通りへ復元する。
    """

    odds = {}

    tables = soup.find_all(
        "table"
    )

    for table in tables:
        rows = table.find_all(
            "tr"
        )

        for row in rows:
            cells = row.find_all(
                ["td", "th"]
            )

            texts = [
                c.get_text(
                    " ",
                    strip=True,
                )
                for c in cells
            ]

            if len(texts) < 18:
                continue

            groups = []

            for i in range(6):
                chunk = texts[
                    i * 3:
                    i * 3 + 3
                ]

                if len(chunk) != 3:
                    continue

                second = _int(
                    chunk[0],
                    -1,
                )

                third = _int(
                    chunk[1],
                    -1,
                )

                odd_text = chunk[2]

                m = re.search(
                    r"\d+(?:\.\d+)?",
                    odd_text,
                )

                if not m:
                    continue

                odd = float(
                    m.group()
                )

                first = i + 1

                if not (
                    1 <= first <= 6
                    and 1 <= second <= 6
                    and 1 <= third <= 6
                ):
                    continue

                combo = (
                    first,
                    second,
                    third,
                )

                if (
                    len(set(combo)) != 3
                ):
                    continue

                if odd <= 0:
                    continue

                groups.append(
                    (
                        combo,
                        odd,
                    )
                )

            for combo, odd in groups:
                odds[combo] = odd

    return odds


def get_trifecta_odds(
    date,
    venue_id,
    race_no,
):
    """
    公式BOATRACEの3連単オッズ。
    """

    hd = str(date).replace(
        "-",
        "",
    )

    url = (
        "https://www.boatrace.jp/"
        "owpc/pc/race/odds3t"
        f"?hd={hd}"
        f"&jcd={int(venue_id):02d}"
        f"&rno={int(race_no)}"
    )

    html = _get_html(
        url,
        timeout=8,
    )

    if not html:
        return {}

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    return _parse_odds_rows(
        soup
    )


def get_all_races_for_day(
    date
):
    """
    バックテスト用。

    1日分のAPIをすでに取得しているので、
    全国24場・最大288レースを
    メモリ上から高速に取り出せる。
    """

    data = get_day_data(
        date
    )

    if not data:
        return []

    stadiums = (
        data
        .get("programs", {})
        .get("stadiums", {})
    )

    results = []

    for venue_id, stadium in stadiums.items():
        venue = VENUE_NAMES.get(
            int(venue_id),
            str(venue_id),
        )

        races = stadium.get(
            "races",
            {}
        )

        for race_no in range(
            1,
            13,
        ):
            if str(race_no) not in races:
                continue

            race = get_race(
                date,
                venue,
                race_no,
            )

            if race:
                results.append(
                    race
                )

    return results
