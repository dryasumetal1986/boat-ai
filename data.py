import re
from datetime import datetime

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


def _get(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 "
            "Version/17.0 Mobile/15E148 Safari/604.1"
        )
    }

    try:
        r = requests.get(
            url,
            headers=headers,
            timeout=15,
        )

        r.raise_for_status()

        return r.text

    except Exception:
        return ""


def get_race(
    date,
    venue,
    race_no,
):
    venue_id = VENUES.get(venue)

    if not venue_id:
        return None

    url = (
        "https://www.boatrace.jp/"
        "owpc/pc/race/racelist"
        f"?hd={date.replace('-', '')}"
        f"&jcd={venue_id}"
        f"&rno={race_no}"
    )

    html = _get(url)

    # 取得できない場合でも
    # AIを動かせる最低限のデータを返す
    boats = []

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    for boat in range(1, 7):
        name = f"{boat}号艇"

        candidates = soup.select(
            f".is-fs12.boatColor{boat}"
        )

        if candidates:
            text = candidates[0].get_text(
                " ",
                strip=True,
            )

            if text:
                name = text

        boats.append(
            {
                "boat": boat,
                "name": name,
                "win_rate": 0.0,
                "local_rate": 0.0,
                "motor_rate": 0.0,
                "course_score": (
                    7.0
                    if boat == 1
                    else 4.0
                ),
            }
        )

    return {
        "date": date,
        "venue": venue,
        "venue_id": venue_id,
        "race_no": race_no,
        "boats": boats,
    }


def get_trifecta_odds(
    date,
    venue_id,
    race_no,
):
    """
    BOATRACE公式3連単オッズ取得。

    3連単表は、
      ・18個の数値を持つ行
      ・12個の数値を持つ行
    が混在する。

    18個:
      2着/3着/オッズ × 6

    12個:
      3着/オッズ × 6

    これを解析して最大120通り取得する。
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

    # -------------------------
    # 公式オッズ表
    # -------------------------

    tables = soup.find_all("table")

    for table in tables:
        rows = table.find_all("tr")

        first_boat = None

        for tr in rows:
            text = tr.get_text(
                " ",
                strip=True,
            )

            # 行の先頭に艇番があるケース
            m = re.match(
                r"^\s*([1-6])\s+",
                text,
            )

            if m:
                first_boat = int(
                    m.group(1)
                )

            cells = []

            for cell in tr.find_all(
                ["td", "th"]
            ):
                value = cell.get_text(
                    " ",
                    strip=True,
                )

                value = value.replace(
                    ",",
                    "",
                )

                if value:
                    cells.append(value)

            numeric = []

            for value in cells:
                if re.fullmatch(
                    r"\d+(?:\.\d+)?",
                    value,
                ):
                    try:
                        numeric.append(
                            float(value)
                        )
                    except Exception:
                        pass

            if first_boat is None:
                continue

            # ---------------------
            # 18セル形式
            # ---------------------

            if len(numeric) >= 18:
                for i in range(0, 18, 3):
                    second = int(
                        numeric[i]
                    )

                    third = int(
                        numeric[i + 1]
                    )

                    odd = float(
                        numeric[i + 2]
                    )

                    if (
                        1 <= second <= 6
                        and 1 <= third <= 6
                        and len(
                            {
                                first_boat,
                                second,
                                third,
                            }
                        )
                        == 3
                        and odd > 0
                    ):
                        odds[
                            (
                                first_boat,
                                second,
                                third,
                            )
                        ] = odd

            # ---------------------
            # 12セル形式
            # ---------------------

            elif len(numeric) >= 12:
                for i in range(0, 12, 2):
                    third = int(
                        numeric[i]
                    )

                    odd = float(
                        numeric[i + 1]
                    )

                    if (
                        1 <= third <= 6
                        and third != first_boat
                        and odd > 0
                    ):
                        # 12セル形式では
                        # 2着艇を特定できない場合が
                        # あるため、後述の解析対象外。
                        #
                        # 公式HTMLの別属性を
                        # 探すためここでは保存しない。
                        pass

    # -------------------------
    # oddsPoint 属性を持つ
    # 個別セルからの補完
    # -------------------------

    for point in soup.select(
        "[class*='oddsPoint']"
    ):
        value = point.get_text(
            " ",
            strip=True,
        )

        value = value.replace(
            ",",
            "",
        )

        try:
            odd = float(
                re.search(
                    r"\d+(?:\.\d+)?",
                    value,
                ).group()
            )
        except Exception:
            continue

        parent = point.parent

        if not parent:
            continue

        text = parent.get_text(
            " ",
            strip=True,
        )

        nums = re.findall(
            r"\b[1-6]\b",
            text,
        )

        if len(nums) >= 3:
            combo = tuple(
                int(x)
                for x in nums[-3:]
            )

            if (
                len(set(combo)) == 3
                and combo not in odds
                and odd > 0
            ):
                odds[combo] = odd

    return odds
