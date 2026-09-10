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

    investment = 0.0
    total_return = 0.0

    main_win = 0
    main_top3 = 0
    all_top3 = 0
    box_hit = 0
    exact_hit = 0

    while (
        cursor >= start_date
        and len(rows) < target_count
    ):

        date_str = cursor.isoformat()

        for venue_id in range(1, 25):

            if len(rows) >= target_count:
                break

            venue = VENUE_BY_ID[
                venue_id
            ]

            for race_no in range(1, 13):

                if len(rows) >= target_count:
                    break

                race = get_race(
                    date_str,
                    venue,
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

                pred = predict_race(
                    race
                )

                ranking = pred[
                    "ranking"
                ]

                main = ranking[0]
                counter = ranking[1]
                hole = ranking[2]

                actual_top3 = tuple(
                    actual[:3]
                )

                investment += (
                    INVEST_PER_RACE
                )

                # 本命1着
                if actual_top3[0] == main:
                    main_win += 1

                # 本命3連対
                if main in actual_top3:
                    main_top3 += 1

                # AI上位3艇が全て3連対
                if all(
                    x in actual_top3
                    for x in ranking[:3]
                ):
                    all_top3 += 1

                # BOX
                if (
                    set(ranking[:3])
                    == set(actual_top3)
                ):
                    box_hit += 1

                # 本命1着を基本とする
                predicted_combo = pred[
                    "main_best_combo"
                ]

                hit = (
                    actual_top3
                    == predicted_combo
                )

                if hit:

                    exact_hit += 1

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
                    "venue": venue,
                    "race_no": race_no,
                    "main": main,
                    "counter": counter,
                    "hole": hole,
                    "predicted_combo":
                        predicted_combo,
                    "actual":
                        actual_top3,
                    "main_win":
                        actual_top3[0] == main,
                    "main_top3":
                        main in actual_top3,
                    "box_hit":
                        set(ranking[:3])
                        == set(actual_top3),
                    "exact_hit": hit,
                })

        cursor -= timedelta(days=1)

    count = len(rows)

    if count:

        recovery = (
            total_return
            / investment
            * 100
        )

        main_win_rate = (
            main_win
            / count
            * 100
        )

        main_top3_rate = (
            main_top3
            / count
            * 100
        )

        all_top3_rate = (
            all_top3
            / count
            * 100
        )

        box_rate = (
            box_hit
            / count
            * 100
        )

        exact_rate = (
            exact_hit
            / count
            * 100
        )

    else:

        recovery = 0
        main_win_rate = 0
        main_top3_rate = 0
        all_top3_rate = 0
        box_rate = 0
        exact_rate = 0

    return {
        "rows": rows,
        "count": count,
        "investment": investment,
        "return": total_return,
        "recovery": recovery,
        "main_win_rate":
            main_win_rate,
        "main_top3_rate":
            main_top3_rate,
        "top3_all_top3_rate":
            all_top3_rate,
        "box_hit_rate":
            box_rate,
        "exact_hit_rate":
            exact_rate,
                    }
