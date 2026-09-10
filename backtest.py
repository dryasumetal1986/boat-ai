from datetime import datetime, timedelta

import ai
import data


START_DATE = "20260101"

BET_AMOUNT = 600
BET_UNIT = 100


def _dates_backwards(run_date):
    """
    当日を除外し、
    前日からSTART_DATEまで遡る。

    例:
        run_date = 20260910
        ↓
        20260909
        20260908
        ...
    """

    current = (
        datetime.strptime(
            str(run_date),
            "%Y%m%d",
        )
        - timedelta(days=1)
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


def _completed_races(target_date):
    """
    指定日の結果確定済みレースだけを取得。
    """

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
    ) in data.all_races_for_date(raw):

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

    # 全国24場をなるべく均等に
    # 時系列へ混ぜる
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
    run_date,
    target_count,
    progress_callback=None,
):
    """
    当日を除外して、
    前日から過去へ遡って検証。

    target_count:
        100 / 300 / 500 など
    """

    races = []

    dates = list(
        _dates_backwards(
            run_date
        )
    )

    total_dates = len(dates)

    if total_dates == 0:
        return _evaluate([])

    for index, date in enumerate(
        dates,
        start=1,
    ):

        daily = _completed_races(
            date
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
                    "stadium_number": (
                        stadium
                    ),
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
        races[:target_count]
    )


def _find_trifecta_payout(
    race,
    actual,
):
    """
    APIの3連単払戻は100円単位。

    例:
        1-3-5 = 880円

    600円投資なら:
        880 × 6 = 5,280円
    """

    if len(actual) < 3:
        return 0

    result = race.get(
        "result",
        {},
    )

    payouts = result.get(
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

    for payout in trifecta_payouts:

        if not isinstance(
            payout,
            dict,
        ):
            continue

        combination = str(
            payout.get(
                "combination",
                "",
            )
        )

        if combination != actual_combo:
            continue

        try:
            amount = int(
                payout.get(
                    "amount",
                    0,
                )
            )
        except Exception:
            amount = 0

        return amount

    return 0


def _evaluate(races):
    total = len(races)

    if total == 0:
        return {
            "total": 0,
            "results": [],
            "recovery": 0.0,
            "main_win_rate": 0.0,
            "main_top3_rate": 0.0,
            "top3_all_top3_rate": 0.0,
            "trifecta_hit_rate": 0.0,
            "investment": 0,
            "payout": 0,
        }

    results = []

    main_win = 0
    main_top3 = 0
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

        main = prediction.get(
            "main"
        )

        counter = prediction.get(
            "counter"
        )

        hole = prediction.get(
            "hole"
        )

        ranking = prediction.get(
            "ranking",
            [],
        )

        actual = item["actual"]

        actual3 = set(
            actual[:3]
        )

        # 本命1着率
        if (
            main is not None
            and len(actual) >= 1
            and main == actual[0]
        ):
            main_win += 1

        # 本命3連対率
        if (
            main is not None
            and main in actual3
        ):
            main_top3 += 1

        # AI上位3艇「全艇」3連対率
        ai_top3 = ranking[:3]

        if (
            len(ai_top3) == 3
            and all(
                boat in actual3
                for boat in ai_top3
            )
        ):
            top3_all_top3 += 1

        # AI3連単完全的中
        predicted = (
            main,
            counter,
            hole,
        )

        if (
            len(actual) >= 3
            and predicted
            == tuple(actual[:3])
        ):
            trifecta_hit += 1

            # 600円投資
            # 公式払戻は100円単位
            race_payout = (
                _find_trifecta_payout(
                    item["race"],
                    actual,
                )
            )

            payout += (
                race_payout
                * (
                    BET_AMOUNT
                    // BET_UNIT
                )
            )

        # 1レース600円投資
        investment += BET_AMOUNT

        results.append(
            {
                "date": item["date"],
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
                "trifecta_hit": (
                    len(actual) >= 3
                    and predicted
                    == tuple(actual[:3])
                ),
                "ai_top3_hit_count": sum(
                    1
                    for boat in ai_top3
                    if boat in actual3
                ),
            }
        )

    recovery = (
        payout / investment * 100
        if investment > 0
        else 0.0
    )

    return {
        "total": total,
        "results": results,
        "recovery": recovery,
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
