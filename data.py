def _parse_odds_table(table):
    """
    BOAT RACE公式3連単オッズ表を
    HTMLのrowspanを考慮して正しく解析する。
    """

    rows = table.find_all("tr")

    if not rows:
        return {}

    # rowspan / colspan を展開したグリッドを作る
    grid = []
    pending = {}

    for r, tr in enumerate(rows):
        row = []
        col = 0

        cells = tr.find_all(["th", "td"])

        for cell in cells:

            while (r, col) in pending:
                row.append(pending[(r, col)])
                col += 1

            rowspan = int(cell.get("rowspan", "1"))
            colspan = int(cell.get("colspan", "1"))

            for c in range(colspan):
                row.append(cell)

                if rowspan > 1:
                    for rr in range(1, rowspan):
                        pending[(r + rr, col + c)] = cell

                col += 1

        while (r, col) in pending:
            row.append(pending[(r, col)])
            col += 1

        grid.append(row)

    if not grid:
        return {}

    # 「3連単オッズ」本体のデータ行だけを探す
    data_rows = []

    for row in grid:
        if len(row) < 18:
            continue

        # 6ブロック × 3列 = 18列
        valid = True

        for block in range(6):
            base = block * 3

            second = row[base]
            third = row[base + 1]
            odds = row[base + 2]

            if second is None or third is None or odds is None:
                valid = False
                break

            odds_text = odds.get_text(" ", strip=True)

            if parse_odds(odds_text) is None:
                valid = False
                break

        if valid:
            data_rows.append(row)

    # 20行 × 6ブロック = 120通り
    if len(data_rows) != 20:
        return {}

    result = {}

    for row_index, row in enumerate(data_rows):

        for block in range(6):

            first = block + 1

            base = block * 3

            second_text = row[base].get_text(
                " ",
                strip=True
            )

            third_text = row[base + 1].get_text(
                " ",
                strip=True
            )

            odds_text = row[base + 2].get_text(
                " ",
                strip=True
            )

            # 2着・3着は数字だけ
            second_match = re.search(
                r"\b([1-6])\b",
                second_text
            )

            third_match = re.search(
                r"\b([1-6])\b",
                third_text
            )

            odd = parse_odds(odds_text)

            if not second_match:
                continue

            if not third_match:
                continue

            if odd is None:
                continue

            second = int(second_match.group(1))
            third = int(third_match.group(1))

            # 同じ艇が重複していたら無効
            if len({first, second, third}) != 3:
                continue

            combination = f"{first}-{second}-{third}"

            result[combination] = odd

    # 120通り全部あるか確認
    if len(result) != 120:
        return {}

    # 全組み合わせが一意か確認
    if len(set(result.keys())) != 120:
        return {}

    return result
