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


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) "
        "Version/17.0 Mobile/15E148 Safari/604.1"
    )
}


def _get(url):
    try:

        r = requests.get(
            url,
            headers=HEADERS,
            timeout=15,
        )

        r.raise_for_status()

        return r.text

    except Exception:
        return ""


def _num(text):
    try:

        return float(
            str(text)
            .replace(",", "")
            .replace("％", "")
            .replace("%", "")
            .strip()
        )

    except Exception:
        return 0.0


def _boat_name(
    soup,
    boat,
):
    patterns = [
        f".boatColor{boat}",
        f".is-fs12.boatColor{boat}",
    ]

    for selector in patterns:

        node = soup.select_one(
            selector
        )

        if node:

            text = node.get_text(
                " ",
                strip=True,
            )

            if text:

                text = re.sub(
                    r"\s+",
                    " ",
                    text,
                )

                if len(text) <= 30:
                    return text

    return f"{boat}号艇"


def get_race(
    date,
    venue,
    race_no,
):
    """
    公式BOATRACEから
    レース情報を取得。

    現在は安全性を優先し、
    選手名＋基本コース情報を
    AIへ渡す。
    """

    venue_id = VENUES.get(
        venue
    )

    if not venue_id:
        return None

    hd = date.replace(
        "-",
        "",
    )

    url = (
        "https://www.boatrace.jp/"
        "owpc/pc/race/racelist"
        f"?hd={hd}"
        f"&jcd={venue_id}"
        f"&rno={race_no}"
    )

    html = _get(url)

    if not html:
        return None

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    boats = []

    for boat in range(1, 7):

        # --------------------------------
        # 基本コーススコア
        # --------------------------------
        #
        # 1号艇を最も高く、
        # 内枠をやや有利にする。
        #

        course_scores = {
            1: 7.0,
            2: 5.2,
            3: 4.6,
            4: 4.0,
            5: 3.5,
            6: 3.0,
        }

        boats.append(
            {
                "boat": boat,

                "name": _boat_name(
                    soup,
                    boat,
                ),

                # --------------------------------
                # 将来拡張用の成績項目
                # --------------------------------

                "win_rate": 0.0,
                "local_rate": 0.0,
                "motor_rate": 0.0,

                "course_score":
                    course_scores[boat],
            }
        )

    return {
        "date": date,
        "venue": venue,
        "venue_id": venue_id,
        "race_no": int(race_no),
        "boats": boats,
    }


def get_race_result(
    date,
    venue_id,
    race_no,
):
    """
    公式BOATRACEの
    レース結果を取得。

    actual:
        (1, 2, 3)

    trifecta_payout:
        3連単払戻金額
        例 12340
    """

    hd = date.replace(
        "-",
        "",
    )

    url = (
        "https://www.boatrace.jp/"
        "owpc/pc/race/raceresult"
        f"?hd={hd}"
        f"&jcd={venue_id}"
        f"&rno={race_no}"
    )

    html = _get(url)

    if not html:
        return None

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    # =================================
    # 着順
    # =================================

    actual = []

    selectors = [
        ".is-fs14",
        ".is-fs12",
        "td",
    ]

    candidates = []

    for selector in selectors:

        candidates.extend(
            soup.select(selector)
        )

    for node in candidates:

        text = node.get_text(
            " ",
            strip=True,
        )

        if re.fullmatch(
            r"[1-6]",
            text,
        ):

            value = int(text)

            if value not in actual:
                actual.append(value)

            if len(actual) == 3:
                break

    # --------------------------------
    # fallback
    # --------------------------------

    if len(actual) < 3:

        text = soup.get_text(
            " ",
            strip=True,
        )

        for m in re.finditer(
            r"\b([1-6])\b",
            text,
        ):

            value = int(
                m.group(1)
            )

            if value not in actual:
                actual.append(value)

            if len(actual) == 3:
                break

    if len(actual) < 3:
        return None

    actual = tuple(
        actual[:3]
    )

    # =================================
    # 3連単払戻
    # =================================

    payout = 0

    for row in soup.find_all(
        "tr"
    ):

        text = row.get_text(
            " ",
            strip=True,
        )

        if "3連単" not in text:
            continue

        m = re.search(
            r"([1-6])\s*[-－]\s*"
            r"([1-6])\s*[-－]\s*"
            r"([1-6]).*?"
            r"([\d,]+)\s*円?",
            text,
        )

        if not m:
            continue

        combo = (
            int(m.group(1)),
            int(m.group(2)),
            int(m.group(3)),
        )

        if combo == actual:

            payout = int(
                m.group(4).replace(
                    ",",
                    "",
                )
            )

            break

    # --------------------------------
    # fallback payout
    # --------------------------------

    if payout <= 0:

        for node in soup.select(
            ".is-payout1"
        ):

            text = node.get_text(
                " ",
                strip=True,
            )

            m = re.search(
                r"([\d,]+)\s*円",
                text,
            )

            if m:

                payout = int(
                    m.group(1).replace(
                        ",",
                        "",
                    )
                )

                break

    return {
        "actual": actual,
        "trifecta_payout": payout,
    }


def get_trifecta_odds(
    date,
    venue_id,
    race_no,
):
    """
    公式3連単オッズを取得。

    戻り値:

        {
            (1,2,3): 23.9,
            ...
        }

    最大120通り。
    """

    hd = date.replace(
        "-",
        "",
    )

    url = (
        "https://www.boatrace.jp/"
        "owpc/pc/race/odds3t"
        f"?hd={hd}"
        f"&jcd={venue_id}"
        f"&rno={race_no}"
    )

    html = _get(url)

    if not html:
        return {}

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    odds = {}

    # =================================
    # oddsPoint
    # =================================

    for point in soup.select(
        "[class*='oddsPoint']"
    ):

        text = point.get_text(
            " ",
            strip=True,
        )

        m = re.search(
            r"\d+(?:\.\d+)?",
            text,
        )

        if not m:
            continue

        odd = float(
            m.group()
        )

        if odd <= 0:
            continue

        parent = point

        for _ in range(4):

            if not parent:
                break

            parent = parent.parent

            if not parent:
                break

            nums = re.findall(
                r"\b[1-6]\b",
                parent.get_text(
                    " ",
                    strip=True,
                ),
            )

            unique = []

            for n in nums:

                n = int(n)

                if n not in unique:
                    unique.append(n)

            if len(unique) >= 3:

                combo = tuple(
                    unique[-3:]
                )

                if (
                    len(set(combo)) == 3
                    and combo not in odds
                ):

                    odds[combo] = odd
                    break

    # =================================
    # テーブル解析
    # =================================

    for table in soup.find_all(
        "table"
    ):

        first_boat = None

        for tr in table.find_all(
            "tr"
        ):

            row_text = tr.get_text(
                " ",
                strip=True,
            )

            m = re.match(
                r"^\s*([1-6])(?:\s|$)",
                row_text,
            )

            if m:

                first_boat = int(
                    m.group(1)
                )

            if first_boat is None:
                continue

            cells = []

            for cell in tr.find_all(
                ["td", "th"]
            ):

                text = cell.get_text(
                    " ",
                    strip=True,
                )

                if text:
                    cells.append(text)

            for cell in cells:

                m = re.search(
                    r"([1-6])\s*[-－]\s*"
                    r"([1-6])\s*[-－]\s*"
                    r"([1-6]).*?"
                    r"(\d+(?:\.\d+)?)",
                    cell,
                )

                if not m:
                    continue

                combo = (
                    int(m.group(1)),
                    int(m.group(2)),
                    int(m.group(3)),
                )

                odd = float(
                    m.group(4)
                )

                if (
                    len(set(combo)) == 3
                    and odd > 0
                ):
                    odds[combo] = odd

    return odds
