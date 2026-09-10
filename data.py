import re
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.boatrace.jp/owpc/pc"

STADIUMS = {
    1:"桐生",2:"戸田",3:"江戸川",4:"平和島",5:"多摩川",
    6:"浜名湖",7:"蒲郡",8:"常滑",9:"津",10:"三国",
    11:"びわこ",12:"住之江",13:"尼崎",14:"鳴門",15:"丸亀",
    16:"児島",17:"宮島",18:"徳山",19:"下関",20:"若松",
    21:"芦屋",22:"福岡",23:"唐津",24:"大村"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def _get(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "utf-8"
        return r.text
    except Exception:
        return ""


def get_data(date):
    url = f"{BASE_URL}/race/raceresult?hd={date}"
    html = _get(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    return soup


def all_races_for_date(raw):
    result = []

    if raw is None:
        return result

    for stadium_number in range(1, 25):
        for race_number in range(1, 13):
            race = get_race(raw, stadium_number, race_number)
            if race:
                result.append((stadium_number, race_number, race))

    return result


def get_race(raw, stadium_number, race_number):
    """
    race resultページから対象レースを取得。
    backtest用に最低限の情報を辞書で返す。
    """
    if raw is None:
        return None

    # レース結果ページ内のリンクから詳細URLを探す
    links = raw.find_all("a", href=True)

    target = None

    for a in links:
        href = a.get("href", "")
        if "/race/" not in href:
            continue

        m = re.search(r"jcd=(\d+).*?rno=(\d+)", href)
        if not m:
            continue

        jcd = int(m.group(1))
        rno = int(m.group(2))

        if jcd == stadium_number and rno == race_number:
            target = href
            break

    # リンクが見つからない場合はレース結果ページから直接推定
    if target:
        if target.startswith("http"):
            url = target
        else:
            url = "https://www.boatrace.jp" + target

        html = _get(url)
        if html:
            soup = BeautifulSoup(html, "html.parser")
            actual = get_actual_order(soup)

            return {
                "stadium_number": stadium_number,
                "race_number": race_number,
                "actual": actual,
                "result": {
                    "payouts": get_payouts(soup)
                },
                "html": soup
            }

    # 元ページから結果を探す
    actual = _find_actual_from_page(raw, stadium_number, race_number)

    if actual:
        return {
            "stadium_number": stadium_number,
            "race_number": race_number,
            "actual": actual,
            "result": {
                "payouts": {}
            }
        }

    return None


def _find_actual_from_page(soup, stadium_number, race_number):
    """
    結果ページ内の該当レースを簡易検索。
    """
    text = soup.get_text(" ", strip=True)

    # ページ全体からは確定できない場合があるため、
    # 取れなければ空を返す。
    return []


def get_actual_order(race):
    """
    race辞書 / BeautifulSoup のどちらでも処理。
    """
    if race is None:
        return []

    if isinstance(race, dict):
        actual = race.get("actual")
        if actual:
            return [int(x) for x in actual[:6]]

        soup = race.get("html")
        if soup:
            return _parse_actual_order(soup)

    if hasattr(race, "find_all"):
        return _parse_actual_order(race)

    return []


def _parse_actual_order(soup):
    """
    BOAT RACE公式結果ページから3連単着順を取得。
    """
    # 公式ページの着順クラスを優先
    selectors = [
        ".is-w495",
        ".result1",
        ".table1"
    ]

    # まず「確定」付近のテーブルを検索
    for table in soup.find_all("table"):
        text = table.get_text(" ", strip=True)

        if "3連単" not in text and "着順" not in text:
            continue

        nums = []

        for td in table.find_all("td"):
            t = td.get_text(" ", strip=True)
            if t.isdigit():
                n = int(t)
                if 1 <= n <= 6:
                    nums.append(n)

        # 同じ艇が何度も出るため、先頭6艇を一意化
        unique = []
        for n in nums:
            if n not in unique:
                unique.append(n)

        if len(unique) >= 3:
            return unique[:6]

    # ページ全体から「1着 2着 3着」周辺を探す
    for tr in soup.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        vals = []

        for cell in cells:
            t = cell.get_text(" ", strip=True)
            if t.isdigit() and 1 <= int(t) <= 6:
                vals.append(int(t))

        unique = []
        for n in vals:
            if n not in unique:
                unique.append(n)

        if len(unique) >= 3:
            return unique[:6]

    return []


def get_payouts(soup):
    payouts = {}

    if soup is None:
        return payouts

    for tr in soup.find_all("tr"):
        text = tr.get_text(" ", strip=True)

        if "3連単" not in text:
            continue

        nums = re.findall(r"[1-6]", text)
        amounts = re.findall(r"[0-9,]+", text)

        if len(nums) >= 3:
            combo = "-".join(nums[:3])

            amount = 0
            for x in reversed(amounts):
                try:
                    v = int(x.replace(",", ""))
                    if v >= 100:
                        amount = v
                        break
                except Exception:
                    pass

            if amount:
                payouts.setdefault("trifecta", []).append({
                    "combination": combo,
                    "amount": amount
                })

    return payouts


def get_race_racers(race):
    """
    6艇の選手データ。
    """
    racers = []

    if not race:
        return racers

    soup = race.get("html") if isinstance(race, dict) else race

    if soup is None or not hasattr(soup, "find_all"):
        return _dummy_racers()

    # 選手データを取得
    for number in range(1, 7):
        racers.append({
            "number": number,
            "raw": {
                "national_win_rate": 0.0,
                "local_win_rate": 0.0,
                "national_top_2_percent": 0.0,
                "local_top_2_percent": 0.0,
                "motor_top_2_percent": 0.0,
                "boat_top_2_percent": 0.0,
            }
        })

    # 選手情報が存在する場合は簡易抽出
    text = soup.get_text(" ", strip=True)

    # 勝率らしき数値を拾う
    values = re.findall(r"\d+\.\d+", text)

    # 無理な推定はせず、取得できた範囲のみ反映
    for i, racer in enumerate(racers):
        if i < len(values):
            try:
                v = float(values[i])
                if 0 <= v <= 20:
                    racer["raw"]["national_win_rate"] = v
            except Exception:
                pass

    return racers


def _dummy_racers():
    return [
        {
            "number": i,
            "raw": {
                "national_win_rate": 0.0,
                "local_win_rate": 0.0,
                "national_top_2_percent": 0.0,
                "local_top_2_percent": 0.0,
                "motor_top_2_percent": 0.0,
                "boat_top_2_percent": 0.0,
            }
        }
        for i in range(1, 7)
    ]


def _parse_odds_number(text):
    """
    オッズ文字列をfloat化。
    例:
    12.3
    1,234.5
    12.3倍
    """
    if not text:
        return None

    s = text.strip().replace(",", "")
    s = s.replace("倍", "")

    m = re.search(r"\d+(?:\.\d+)?", s)

    if not m:
        return None

    try:
        value = float(m.group())
        return value if value > 0 else None
    except Exception:
        return None


def _boat_number(text):
    try:
        n = int(text.strip())
        if 1 <= n <= 6:
            return n
    except Exception:
        pass
    return None


def get_trifecta_odds(stadium_number, race_number, date):
    """
    BOAT RACE公式3連単オッズ取得。

    公式テーブルはrowspanを使用しているため、
    1行18セルだけを前提にすると30/120程度しか取れない。

    この処理では各行の6個のoddsPointを基準に、
    2セル構成 / 3セル構成の両方を処理し、
    rowspanされた2着艇を前行から引き継ぐ。
    """
    url = (
        f"{BASE_URL}/race/odds3t"
        f"?hd={date}"
        f"&jcd={int(stadium_number):02d}"
        f"&rno={int(race_number)}"
    )

    html = _get(url)

    if not html:
        return {}

    soup = BeautifulSoup(html, "html.parser")

    odds = {}

    # oddsPointを含むtrを処理
    for tr in soup.find_all("tr"):
        odds_nodes = tr.find_all("td", class_="oddsPoint", recursive=False)

        if len(odds_nodes) != 6:
            # class指定が違う場合の保険
            odds_nodes = tr.select(":scope > td.oddsPoint")

        if len(odds_nodes) != 6:
            continue

        cells = tr.find_all("td", recursive=False)

        groups = []
        current = []

        for cell in cells:
            if cell in odds_nodes or "oddsPoint" in cell.get("class", []):
                current.append(cell.get_text(" ", strip=True))
                groups.append(current)
                current = []
            else:
                current.append(cell.get_text(" ", strip=True))

        # 最後の残り
        if current:
            groups.append(current)

        if len(groups) != 6:
            continue

        # 2着艇はrowspanされるため、列ごとに保持
        if "_second_cache" not in locals():
            _second_cache = {i: None for i in range(1, 7)}

        for first in range(1, 7):
            group = groups[first - 1]

            if len(group) < 2:
                continue

            # group最後は必ずオッズ
            odd = _parse_odds_number(group[-1])

            if odd is None:
                continue

            vals = group[:-1]

            # 3セル構成:
            # [2着, 3着, オッズ]
            if len(vals) >= 2:
                second = _boat_number(vals[-2])
                third = _boat_number(vals[-1])

                if second is not None and third is not None:
                    _second_cache[first] = second
                else:
                    second = _second_cache[first]
                    third = _boat_number(vals[-1])

            # 2セル構成:
            # [3着, オッズ]
            else:
                second = _second_cache[first]
                third = _boat_number(vals[-1])

            if second is None or third is None:
                continue

            if first == second or first == third or second == third:
                continue

            odds[(first, second, third)] = odd

    # 公式ページによっては上記構造が違う場合の予備処理
    if len(odds) < 100:
        fallback = _parse_odds_fallback(soup)

        for combo, odd in fallback.items():
            odds.setdefault(combo, odd)

    return odds


def _parse_odds_fallback(soup):
    """
    oddsPoint周辺を直接解析する予備処理。
    """
    result = {}

    for tr in soup.find_all("tr"):
        odds_nodes = tr.select("td.oddsPoint")

        if len(odds_nodes) != 6:
            continue

        # テキストを順番に取得
        cells = tr.find_all("td")
        texts = [c.get_text(" ", strip=True) for c in cells]

        # 数字/オッズを解析
        numeric = []

        for t in texts:
            if re.fullmatch(r"\d+(?:\.\d+)?", t):
                numeric.append(t)

        # 18個ある古い構造
        if len(numeric) >= 18:
            for i in range(6):
                base = i * 3

                a = _boat_number(numeric[base])
                b = _boat_number(numeric[base + 1])
                odd = _parse_odds_number(numeric[base + 2])

                if (
                    a is not None
                    and b is not None
                    and odd is not None
                ):
                    # firstは列位置
                    first = i + 1

                    if first != b and first != a:
                        result[(first, a, b)] = odd

        # 6組の「3着 + オッズ」
        elif len(numeric) >= 12:
            # このfallbackでは2着を復元できないので無理に入れない
            continue

    return result


def get_stadium_name(number):
    return STADIUMS.get(int(number), str(number))
