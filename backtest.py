from datetime import datetime, timedelta

import ai
import data


START_DATE = "20260101"


def _dates_backwards(
    end_date,
):
    current = datetime.strptime(
        end_date,
        "%Y%m%d",
    )

    minimum = datetime.strptime(
        START_DATE,
        "%Y%m%d",
    )

    while current >= minimum:

        yield current.strftime(
            "%Y%m%d"
        )

        current -= timedelta(
            days=1
        )


def _completed_races(
    target_date,
):
    raw = data.get_data(
        target_date
    )

    if not raw:
        return []

    groups = {}

    for (
        stadium,
        race_number,
        race,
    ) in data.all_races_for_date(
        raw
    ):

        actual = data.get_actual_order(
            race
        )

        if len(actual) < 3:
            continue

        groups.setdefault(
            stadium,
            [],
        ).append(
            (
                race_number,
                race,
                actual,
            )
        )

    for stadium in groups:

        groups[stadium].sort(
            key=lambda x: x[0]
        )

    result = []

    while True:

        added = False

        for stadium in sorted(
            groups
        ):

            if groups[stadium]:

                result.append(
                    (
                        stadium,
                        *groups[
                            stadium
                        ].pop(0),
                    )
                )

                added = True

        if not added:
            break

    return result


def run_backtest(
    end_date,
    target_count,
    progress_callback=None,
):
    races = []

    dates = list(
        _dates_backwards(
            end_date
        )
    )

    total_dates = len(
        dates
    )

    for index, date in enumerate(
        dates,
        start=1,
    ):

        daily = (
            _completed_races(
                date
            )
        )

        for (
            stadium,
            race_number,
            race,
            actual,
        ) in daily:

            races.append(
                {
                    "date": date,
                    "stadium_number": stadium,
                    "race_number": (
                        race_number
                    ),
                    "race": race,
                    "actual": actual,
                }
            )

            if (
                len(races)
                >= target_count
            ):

                if progress_callback:
                    progress_callback(
                        1.0
                    )

                return _evaluate(
                    races[
                        :target_count
                    ]
                )

        if progress_callback:

            progress_callback(
                min(
                    index
                    / total_dates,
                    0.99,
                )
            )

    return _evaluate(
        races[
            :target_count
        ]
    )


def _evaluate(
    races
):
    total = len(
        races
    )

    if total == 0:

        return {
            "total": 0,
            "results": [],
            "recovery": 0.0,
            "main_win_rate": 0.0,
            "main_top3_rate": 0.0,
            "buy_hit_rate": 0.0,
            "top3_all_top3_rate": 0.0,
            "trifecta_hit_rate": 0.0,
            "investment": 0,
            "payout": 0,
        }

    results = []

    main_win = 0
    main_top3 = 0
    buy_hit = 0
    top3_all_top3 = 0
    trifecta_hit = 0

    investment = 0
    payout = 0

    for item in races:

        racers = data.get_race_racers(
            item["race"]
        )

        prediction = ai.tri_ai(
            racers
        )

        main = prediction[
            "main"
        ]

        counter = prediction[
            "counter"
        ]

        hole = prediction[
            "hole"
        ]

        actual = item[
            "actual"
        ]

        actual3 = set(
            actual[:3]
        )

        if main in actual[:1]:
            main_win += 1

        if main in actual3:
            main_top3 += 1

        top3 = prediction[
            "ranking"
        ][:3]

        if all(
            boat in actual3
            for boat in top3
        ):
            top3_all_top3 += 1

        if (
            main in actual3
            or counter in actual3
            or hole in actual3
        ):
            buy_hit += 1

        predicted = (
            main,
            counter,
            hole,
        )

        if (
            len(actual) >= 3
            and predicted
            == tuple(
                actual[:3]
            )
        ):
            trifecta_hit += 1

        investment += 600

        # 実際の3連単払戻
        result_data = item[
            "race"
        ].get(
            "result",
            {},
        )

        payouts = result_data.get(
            "payouts",
            {},
        )

        trifecta_payouts = (
            payouts.get(
                "trifecta",
                [],
            )
        )

        actual_combo = "-".join(
            str(x)
            for x in actual[:3]
        )

        race_payout = 0

        for p in trifecta_payouts:

            combination = str(
                p.get(
                    "combination",
                    "",
                )
            )

            if combination == (
                actual_combo
            ):

                try:
                    race_payout = int(
                        p.get(
                            "amount",
                            0,
                        )
                    )
                except Exception:
                    race_payout = 0

                break

        if predicted == tuple(
            actual[:3]
        ):
            payout += race_payout

        results.append(
            {
                "date": item[
                    "date"
                ],
                "stadium": (
                    data.get_stadium_name(
                        item[
                            "stadium_number"
                        ]
                    )
                ),
                "race": item[
                    "race_number"
                ],
                "main": main,
                "counter": counter,
                "hole": hole,
                "actual": actual[:3],
            }
        )

    return {
        "total": total,
        "results": results,
        "recovery": (
            payout
            / investment
            * 100
            if investment
            else 0.0
        ),
        "main_win_rate": (
            main_win
            / total
            * 100
        ),
        "main_top3_rate": (
            main_top3
            / total
            * 100
        ),
        "buy_hit_rate": (
            buy_hit
            / total
            * 100
        ),
        "top3_all_top3_rate": (
            top3_all_top3
            / total
            * 100
        ),
        "trifecta_hit_rate": (
            trifecta_hit
            / total
            * 100
        ),
        "investment": investment,
        "payout": payout,
    }
