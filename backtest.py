from datetime import datetime, timedelta

import pandas as pd

from data import (
    get_all_races,
    race_to_df,
    get_result,
    get_payout,
)
from ai import predict


def collect_races(start_date, target_count):
    """
    start_dateから過去へ遡り、
    結果のあるレースをtarget_count件集める。
    """

    collected = []
    current = datetime.strptime(
        start_date,
        "%Y%m%d"
    )

    max_days = 120

    for _ in range(max_days):

        date_str = current.strftime("%Y%m%d")
        daily = get_all_races(date_str)

        for item in daily:

            race = item["race"]
            result = get_result(race)

            if not result:
                continue

            item["result"] = result
            collected.append(item)

            if len(collected) >= target_count:
                return collected

        current -= timedelta(days=1)

    return collected


def run_backtest(
    start_date,
    target_count,
    progress_callback=None
):
    races = collect_races(
        start_date,
        target_count
    )

    if not races:
        return {
            "records": pd.DataFrame(),
            "stats": {},
        }

    records = []
    total = len(races)

    for i, item in enumerate(races):

        race = item["race"]
        df = race_to_df(race)

        if len(df) != 6:
            continue

        try:
            pred = predict(df)
        except Exception:
            continue

        main = tuple(
            pred["tickets"]["main"]["combo"]
        )

        counter = tuple(
            pred["tickets"]["counter"]["combo"]
        )

        hole = tuple(
            pred["tickets"]["hole"]["combo"]
        )

        result = tuple(item["result"])

        hit_main = result == main
        hit_counter = result == counter
        hit_hole = result == hole
        hit3 = (
            hit_main or
            hit_counter or
            hit_hole
        )

        payout = get_payout(
            race,
            result
        )

        top1 = pred["ranking"][0]["boat"]

        top3_boats = [
            x["boat"]
            for x in pred["ranking"][:3]
        ]

        records.append({
            "date": item["date"],
            "stadium": item["stadium"],
            "race_no": item["race_no"],

            "main": main,
            "counter": counter,
            "hole": hole,

            "result": result,
            "payout": payout,

            "hit_main": hit_main,
            "hit_counter": hit_counter,
            "hit_hole": hit_hole,
            "hit3": hit3,

            "first_pred": top1,
            "first_hit": top1 == result[0],

            "top3_hit": top1 in result,

            "ai_top3_all": all(
                x in result
                for x in top3_boats
            ),
        })

        if progress_callback:
            progress_callback(
                (i + 1) / total
            )

    if not records:
        return {
            "records": pd.DataFrame(),
            "stats": {},
        }

    result_df = pd.DataFrame(records)

    n = len(result_df)

    hits = int(
        result_df["hit3"].sum()
    )

    main_hits = int(
        result_df["hit_main"].sum()
    )

    counter_hits = int(
        result_df["hit_counter"].sum()
    )

    hole_hits = int(
        result_df["hit_hole"].sum()
    )

    first_hits = int(
        result_df["first_hit"].sum()
    )

    top3_hits = int(
        result_df["top3_hit"].sum()
    )

    box_hits = int(
        result_df["ai_top3_all"].sum()
    )

    investment = n * 300

    payout = int(
        result_df.loc[
            result_df["hit3"],
            "payout"
        ].sum()
    )

    stats = {
        "races": n,

        "three_bet_hit_rate":
            hits / n,

        "main_hit_rate":
            main_hits / n,

        "counter_hit_rate":
            counter_hits / n,

        "hole_hit_rate":
            hole_hits / n,

        "first_hit_rate":
            first_hits / n,

        "top3_hit_rate":
            top3_hits / n,

        "box_hit_rate":
            box_hits / n,

        "investment":
            investment,

        "payout":
            payout,

        "return_rate":
            payout / investment
            if investment else 0,
    }

    return {
        "records": result_df,
        "stats": stats,
    }
