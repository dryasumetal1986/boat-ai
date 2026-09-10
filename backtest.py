import pandas as pd
from data import get_race, race_to_df, get_result, get_payout
from ai import predict


def run_backtest(date, races, progress_callback=None):
    records = []

    total = len(races)

    for n, item in enumerate(races):
        stadium = item["stadium"]
        race_no = int(item["race_no"])

        race = get_race(date, stadium, race_no)

        if not race:
            continue

        df = race_to_df(race)
        result = get_result(race)

        if len(df) != 6 or not result:
            continue

        try:
            pred = predict(df)
        except Exception:
            continue

        main = tuple(pred["tickets"]["main"]["combo"])
        counter = tuple(pred["tickets"]["counter"]["combo"])
        hole = tuple(pred["tickets"]["hole"]["combo"])

        hit_main = result == main
        hit_counter = result == counter
        hit_hole = result == hole

        hit3 = hit_main or hit_counter or hit_hole

        payout = get_payout(race, result)

        records.append({
            "stadium": stadium,
            "race_no": race_no,
            "main": main,
            "counter": counter,
            "hole": hole,
            "result": result,
            "payout": payout,
            "hit_main": hit_main,
            "hit_counter": hit_counter,
            "hit_hole": hit_hole,
            "hit3": hit3,
            "first_pred": pred["ranking"][0]["boat"],
            "first_hit": pred["ranking"][0]["boat"] == result[0],
            "top3_hit": pred["ranking"][0]["boat"] in result,
            "ai_top3_all": all(
                x["boat"] in result
                for x in pred["ranking"][:3]
            ),
        })

        if progress_callback:
            progress_callback((n + 1) / total)

    if not records:
        return {
            "records": [],
            "stats": {},
        }

    df_result = pd.DataFrame(records)

    total_races = len(df_result)
    bet = total_races * 300

    hits = int(df_result["hit3"].sum())
    main_hits = int(df_result["hit_main"].sum())
    counter_hits = int(df_result["hit_counter"].sum())
    hole_hits = int(df_result["hit_hole"].sum())

    first_hits = int(df_result["first_hit"].sum())
    top3_hits = int(df_result["top3_hit"].sum())
    box_hits = int(df_result["ai_top3_all"].sum())

    payout_total = int(
        df_result.loc[df_result["hit3"], "payout"].sum()
    )

    stats = {
        "races": total_races,
        "three_bet_hit_rate": hits / total_races,
        "main_hit_rate": main_hits / total_races,
        "counter_hit_rate": counter_hits / total_races,
        "hole_hit_rate": hole_hits / total_races,
        "first_hit_rate": first_hits / total_races,
        "top3_hit_rate": top3_hits / total_races,
        "box_hit_rate": box_hits / total_races,
        "investment": bet,
        "payout": payout_total,
        "return_rate": payout_total / bet if bet else 0,
    }

    return {
        "records": df_result,
        "stats": stats,
    }
