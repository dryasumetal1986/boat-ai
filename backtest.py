from datetime import date, timedelta

from ai import predict_race
from data import VENUE_BY_ID, get_race


INVEST_PER_RACE = 600

TARGET_RACES = [
    100,
    300,
    500,
    1000,
]


def run_backtest(
    target_count,
    end_date=None,
):

    if end_date is None:
        end_date = date.today()

    cursor = (
        end_date
        - timedelta(days=1)
    )

    start_date = date(
        2026,
        1,
        1,
    )

    rows = []

    total_investment = 0.0
    total_return = 0.0

    main_win_count = 0
    main_top3_count = 0
    top3_all_top3_count = 0
    box_hit_count = 0
    exact_hit_count = 0

    while (
        cursor >= start_date
        and len(rows) < target_count
    ):

        date_str = cursor.isoformat()

        for venue_id in range(1, 25):

            if len(rows) >= target_count:
                break

            venue_name = VENUE_BY_ID[
                venue_id
            ]

            for race_no in range(1, 13):

                if len(rows) >= target_count:
                    break

                race = get_race(
                    date_str,
                    venue_name,
                    race_no,
                )

                if not race:
                    continue

                if len(
                    race.get("boats", [])
                ) != 6:
                    continue

                actual = race.get(
                    "actual",
                    [],
                )

                if len(actual) < 3:
                    continue

                prediction = predict_race(
                    race
                )

                ranking = prediction[
                    "ranking"
                ]

                main = ranking[0]
                counter = ranking[1]
                hole = ranking[2]

                selected_boats = {
                    main,
                    counter,
                    hole,
                }

                actual_top3 = tuple(
                    actual[:3]
                )

                total_investment += (
                    INVEST_PER_RACE
                )

                # 本命1着
                main_win = (
                    actual_top3[0]
                    == main
                )

                if main_win:
                    main_win_count += 1

                # 本命3連対
                main_top3 = (
                    main
                    in actual_top3
                )

                if main_top3:
                    main_top3_count += 1

                # AI上位3艇が全員3連対
                top3_all_top3 = all(
                    boat in actual_top3
                    for boat in ranking[:3]
                )

                if top3_all_top3:
                    top3_all_top3_count += 1

                # 3艇BOX
                box_hit = (
                    selected_boats
                    == set(actual_top3)
                )

                if box_hit:
                    box_hit_count += 1

                # -------------------------
                # 本命1着を優先した
                # 3連単予想
                # -------------------------

                predicted_combo = (
                    prediction[
                        "main_best_combo"
                    ]
                )

                exact_hit = (
                    actual_top3
                    == predicted_combo
                )

                if exact_hit:

                    exact_hit_count += 1

                    payout = float(
                        race.get(
                            "payout",
                            0,
                        )
                    )

                    total_return += (
                        payout * 6
                    )

                rows.append({
                    "date": date_str,
                    "venue": venue_name,
                    "race_no": race_no,
                    "main": main,
                    "counter": counter,
                    "hole": hole,
                    "predicted_combo":
                        predicted_combo,
                    "actual": actual_top3,
                    "main_win":
                        main_win,
                    "main_top3":
                        main_top3,
                    "box_hit":
                        box_hit,
                    "exact_hit":
                        exact_hit,
                })

        cursor -= timedelta(days=1)

    count = len(rows)

    if count:

        recovery = (
            total_return
            / total_investment
            * 100
        )

        main_win_rate = (
            main_win_count
            / count
            * 100
        )

        main_top3_rate = (
            main_top3_count
            / count
            * 100
        )

        top3_all_top3_rate = (
            top3_all_top3_count
            / count
            * 100
        )

        box_hit_rate = (
            box_hit_count
            / count
            * 100
        )

        exact_hit_rate = (
            exact_hit_count
            / count
            * 100
        )

    else:

        recovery = 0.0
        main_win_rate = 0.0
        main_top3_rate = 0.0
        top3_all_top3_rate = 0.0
        box_hit_rate = 0.0
        exact_hit_rate = 0.0

    return {
        "rows": rows,
        "count": count,
        "investment":
            total_investment,
        "return":
            total_return,
        "recovery":
            recovery,
        "main_win_rate":
            main_win_rate,
        "main_top3_rate":
            main_top3_rate,
        "top3_all_top3_rate":
            top3_all_top3_rate,
        "box_hit_rate":
            box_hit_rate,
        "exact_hit_rate":
            exact_hit_rate,
                }
