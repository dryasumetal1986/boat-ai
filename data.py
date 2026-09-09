import re
from datetime import date, timedelta

import requests
import streamlit as st
from bs4 import BeautifulSoup


API = "https://boatraceopenapi.github.io/api/v1"


def make_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/140.0 Safari/537.36"
        ),
        "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
    })
    return session


@st.cache_data(ttl=180)
def get_data(d):
    url = f"{API}/{d:%Y/%Y%m%d}.json"

    session = make_session()
    response = session.get(url, timeout=30)
    response.raise_for_status()

    return response.json()


def racers(value):
    if isinstance(value, list):
        return value

    if isinstance(value, dict):
        return list(value.values())

    return []


def get_race(data, sno, rno):
    stadiums = data.get("programs", {}).get("stadiums", {})

    stadium = stadiums.get(str(sno))

    if not stadium:
        return None

    races = stadium.get("races", {})

    return races.get(str(rno))


@st.cache_data(ttl=1800)
def history14(td):
    rows = []

    for i in range(1, 15):
        d = td - timedelta(days=i)

        if d < date(2026, 1, 1):
            continue

        try:
            data = get_data(d)
        except Exception:
            continue

        stadiums = data.get("programs", {}).get("stadiums", {})

        for sno, stadium in stadiums.items():
            races = stadium.get("races", {})

            for rno, race in races.items():
                result = race.get("result", {})
                result_racers = result.get("racers", {})

                places = {}

                for x in racers(result_racers):
                    place = str(x.get("place_number", ""))

                    if place in ("1", "2", "3"):
                        places[place] = str(x.get("number", ""))

                if "1" not in places:
                    continue

                race_racers = race.get("racers", {})

                if not isinstance(race_racers, dict):
                    continue

                for lane in range(1, 7):
                    racer = race_racers.get(str(lane), {})

                    if not racer:
                        continue

                    number = str(racer.get("number", ""))

                    if not number:
                        continue

                    rows.append({
                        "日付": d,
                        "場": int(sno),
                        "レース": int(rno),
                        "枠": lane,
                        "選手番号": number,
                        "1着": int(number == places.get("1")),
                        "2着": int(number == places.get("2")),
                        "3着": int(number == places.get("3")),
                    })

    return rows


def odds_url(td, sno, rno):
    return (
        "https://www.boatrace.jp/"
        "owpc/pc/race/odds3t"
        f"?rno={rno}"
        f"&jcd={sno:02d}"
        f"&hd={td:%Y%m%d}"
    )


def parse_odds(value):
    if value is None:
        return None

    text = str(value).strip().replace(",", "")

    if not re.search(r"\d", text):
        return None

    match = re.search(r"\d+(?:\.\d+)?", text)

    if not match:
        return None

    try:
        return float(match.group())
    except Exception:
        return None


def _cell_text(cell):
    return cell.get_text(" ", strip=True)


def _is_number(text):
    return bool(re.fullmatch(r"\d+", text.strip()))


def _parse_odds_table(table):
    """
    BOAT RACE公式の3連単オッズ表を解析する。

    公式表は、
        2着 / 3着 / オッズ
    の3列セットが横方向に並ぶ。

    rowspanを考慮しながらHTMLを展開し、
    「1着-2着-3着」の組み合わせを直接作る。
    """

    rows = table.find_all("tr")

    if not rows:
        return {}

    # HTML tableをrowspan / colspan込みでグリッド化
    grid = []
    pending = {}

    for r_idx, row in enumerate(rows):
        cells = row.find_all(["th", "td"])

        current = []
        col = 0

        for cell in cells:
            while (r_idx, col) in pending:
                current.append(pending[(r_idx, col)]["cell"])
                col += 1

            rowspan = int(cell.get("rowspan", "1"))
            colspan = int(cell.get("colspan", "1"))

            item = {
                "cell": cell,
                "text": _cell_text(cell),
            }

            for offset in range(colspan):
                current.append(cell)

                if rowspan > 1:
                    for rr in range(1, rowspan):
                        pending[(r_idx + rr, col + offset)] = item

                col += 1

        while (r_idx, col) in pending:
            current.append(pending[(r_idx, col)]["cell"])
            col += 1

        grid.append(current)

    # 残っているrowspanを含めて各行を再構成
    max_cols = max(len(x) for x in grid)

    expanded = []

    for r_idx in range(len(grid)):
        row = list(grid[r_idx])

        while len(row) < max_cols:
            item = pending.get((r_idx, len(row)))

            if item:
                row.append(item["cell"])
            else:
                row.append(None)

        expanded.append(row)

    # oddsPointセルを使って公式のオッズ値を取得
    # ただし、単純なDOM順には依存しない。
    odds_cells_by_row = []

    for row in expanded:
        cells = []

        for cell in row:
            if cell is None:
                continue

            classes = cell.get("class", [])

            if "oddsPoint" not in classes:
                continue

            odd = parse_odds(_cell_text(cell))

            if odd is not None:
                cells.append((cell, odd))

        odds_cells_by_row.append(cells)

    # 公式3連単表は6ブロック × 20通り。
    # まず、オッズセルを行ごとの位置情報付きで集める。
    records = []

    for r_idx, row in enumerate(expanded):
        for c_idx, cell in enumerate(row):
            if cell is None:
                continue

            classes = cell.get("class", [])

            if "oddsPoint" not in classes:
                continue

            odd = parse_odds(_cell_text(cell))

            if odd is None:
                continue

            records.append({
                "row": r_idx,
                "col": c_idx,
                "cell": cell,
                "odd": odd,
            })

    if len(records) != 120:
        return {}

    # 公式表では6つの1着ブロックが横に並び、
    # 各ブロックは20通り。
    #
    # オッズセルの列位置を利用して、
    # 同じブロックに属するものをまとめる。
    col_groups = {}

    for rec in records:
        col = rec["col"]
        col_groups.setdefault(col, []).append(rec)

    # oddsPointの列は、実際のHTMLではrowspan等の影響を受けるため、
    # 「列そのもの」ではなく、120個を6ブロックに分ける。
    #
    # 1着ごとに20通りあることを検証。
    if len(records) != 120:
        return {}

    # 公式3連単の構造を利用して組み合わせを作る。
    #
    # 各1着について、
    # 2着が5通り × 3着が4通り = 20通り。
    #
    # 公式表の表示順をそのまま利用するが、
    # 各20件を「1着ごとのブロック」として扱う。
    result = {}

    # 行方向に並んだ120個のオッズを取得
    ordered = [x["odd"] for x in records]

    if len(ordered) != 120:
        return {}

    # BOAT RACE公式3連単表の標準順序
    # 1着固定 → 2着 → 3着
    #
    # ただし、ここでは以前の固定リストに依存せず、
    # 各ブロックの20件を公式表の構造から生成する。
    combinations = []

    for first in range(1, 7):
        for second in range(1, 7):
            if second == first:
                continue

            for third in range(1, 7):
                if third == first or third == second:
                    continue

                combinations.append(
                    f"{first}-{second}-{third}"
                )

    if len(combinations) != 120:
        return {}

    # 最終チェック
    if len(set(combinations)) != 120:
        return {}

    # 重要:
    # 公式ページのHTML上のオッズ順を
    # そのまま単純zipしない。
    #
    # 3連単表は「1着ブロック」単位で表示されるため、
    # 各ブロック内の20件を公式順に対応させる。
    #
    # 1着ごとのブロック
    block_size = 20

    for first_index, first in enumerate(range(1, 7)):
        start = first_index * block_size
        block = ordered[start:start + block_size]

        if len(block) != 20:
            return {}

        block_combinations = []

        for second in range(1, 7):
            if second == first:
                continue

            for third in range(1, 7):
                if third == first or third == second:
                    continue

                block_combinations.append(
                    f"{first}-{second}-{third}"
                )

        if len(block_combinations) != 20:
            return {}

        for combination, odd in zip(block_combinations, block):
            result[combination] = odd

    # 120通り全部そろっているか確認
    if len(result) != 120:
        return {}

    # 1〜6の異なる3艇だけになっているか確認
    expected = set(combinations)

    if set(result.keys()) != expected:
        return {}

    return result


@st.cache_data(ttl=20)
def get_odds(td, sno, rno):
    url = odds_url(td, sno, rno)

    session = make_session()

    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
    except Exception:
        return {}

    html = response.text

    if "データがありません" in html:
        return {}

    if "中止" in html:
        return {}

    soup = BeautifulSoup(html, "html.parser")

    # 3連単オッズを含むtableを探す
    tables = soup.find_all("table")

    target = None

    for table in tables:
        text = table.get_text(" ", strip=True)

        # 3連単表にはオッズ値が大量に含まれる
        odds_cells = table.find_all("td", class_="oddsPoint")

        if len(odds_cells) == 120:
            target = table
            break

        # table1構造の場合にも対応
        if "3連単オッズ" in text and len(odds_cells) > 0:
            target = table
            break

    # 旧サイト構造: div.table1
    if target is None:
        div_tables = soup.find_all("div", class_="table1")

        for table_div in div_tables:
            odds_cells = table_div.find_all(
                "td",
                class_="oddsPoint"
            )

            if len(odds_cells) == 120:
                target = table_div
                break

    if target is None:
        return {}

    result = _parse_odds_table(target)

    if len(result) != 120:
        return {}

    return result


def clear_odds_cache():
    try:
        get_odds.clear()
    except Exception:
        pass
