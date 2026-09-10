from datetime import timedelta

from data import (
    get_all_races,
    get_result,
    get_payout,
    race_to_df,
)
from ai import predict, combo_text


def collect_races(start_date, target_count):
    """
    start_dateから過去へ遡り、
    結果が存在するレースをtarget_count件集める。

    開催場は指定しない。
    全24場を自動対象にする。
    """
    collected = []

    current = start_date

    # 1000レースなら通常数日～十数日なので
    # 十分余裕を持たせる。
    for _ in range(120):
        races = get_all_races(current)

        for item in races:
            race = item["race"]

            result = get_result(race)

            # 結果が正しく1～6の3艇でないものは除外
            if not result:
                continue

            if len(result) != 3:
                continue

            if len(set(result)) != 3:
                continue

            if not all(
                1 <= int(x) <= 6
                for x in result
            ):
                continue

            item = dict(item)
            item["result_order"] = result

            collected.append(item)

            if len(collected) >= target_count:
                return collected[:target_count]

        current -= timedelta(days=1)

    return collected[:target_count]


def run_backtest(start_date, target_count):
    """
    AI予想と全く同じpredict()を使って検証。
    """
    races = collect_races(
        start_date,
        target_count,
    )

    if not races:
        return {
            "requested": target_count,
            "valid": 0,
            "rows": [],
            "stats": {},
        }

    rows = []

    main_hits = 0
    counter_hits = 0
    hole_hits = 0
    total_hits = 0

    axis_first_hits = 0
    axis_top3_hits = 0
    box_hits = 0

    investment = 0
    payout_total = 0

    for item in races:
        race = item["race"]

        df = race_to_df(race)

        if df.empty or len(df) != 6:
            continue

        pred = predict(df)

        if not pred:
            continue

        tickets = pred["tickets"]

        result = item["result_order"]

        result_tuple = tuple(
            int(x)
            for x in result
        )

        ticket_tuples = [
            tuple(
                int(x)
                for x in t["combo"]
            )
            for t in tickets
        ]

        hit_main = (
            len(ticket_tuples) >= 1
            and ticket_tuples[0] == result_tuple
        )

        hit_counter = (
            len(ticket_tuples) >= 2
            and ticket_tuples[1] == result_tuple
        )

        hit_hole = (
            len(ticket_tuples) >= 3
            and ticket_tuples[2] == result_tuple
        )

        hit_any = (
            hit_main
            or hit_counter
            or hit_hole
        )

        if hit_main:
            main_hits += 1

        if hit_counter:
            counter_hits += 1

        if hit_hole:
            hole_hits += 1

        if hit_any:
            total_hits += 1

        # AI最上位艇
        ranking = pred.get(
            "ranking",
            [],
        )

        if ranking:
            axis = int(
                ranking[0]["boat"]
            )

            if result_tuple[0] == axis:
                axis_first_hits += 1

            if axis in result_tuple:
                axis_top3_hits += 1

            top3 = set(
                int(x["boat"])
                for x in ranking[:3]
            )

            if set(result_tuple) == top3:
                box_hits += 1

        payout = get_payout(race)

        investment += 300

        if hit_any:
            payout_total += int(
                payout or 0
            )

        rows.append({
            "date": item["date"].strftime(
                "%Y%m%d"
            ),
            "stadium": item["stadium"],
            "race": item["race_no"],

            "main": combo_text(
                tickets[0]["combo"]
            ),

            "counter": combo_text(
                tickets[1]["combo"]
            ),

            "hole": combo_text(
                tickets[2]["combo"]
            ),

            "result": combo_text(
                result_tuple
            ),

            "hit": "⭕" if hit_any else "❌",

            "payout": int(
                payout or 0
            ),
        })

    valid = len(rows)

    if valid == 0:
        return {
            "requested": target_count,
            "valid": 0,
            "rows": [],
            "stats": {},
        }

    stats = {
        "total_hit_rate": (
            total_hits / valid * 100
        ),
        "main_hit_rate": (
            main_hits / valid * 100
        ),
        "counter_hit_rate": (
            counter_hits / valid * 100
        ),
        "hole_hit_rate": (
            hole_hits / valid * 100
        ),
        "axis_first_rate": (
            axis_first_hits / valid * 100
        ),
        "axis_top3_rate": (
            axis_top3_hits / valid * 100
        ),
        "box_rate": (
            box_hits / valid * 100
        ),
        "investment": investment,
        "payout": payout_total,
        "recovery": (
            payout_total / investment * 100
            if investment > 0
            else 0
        ),
    }

    return {
        "requested": target_count,
        "valid": valid,
        "rows": rows,
        "stats": stats,
    }
