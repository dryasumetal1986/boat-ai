from datetime import datetime, timedelta

import ai
import data


START_DATE = "20260101"

BET_AMOUNT = 600
BET_UNIT = 100


def _dates_backwards(end_date):
    """
    当日は除外。
    前日からSTART_DATEまで。
    """

    current = (
        datetime.strptime(
            end_date,
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

        current -= timedelta(days=1)


def _completed_races(target_date):
    raw = data.get_data(
        target_date
    )

    if not raw:
        return []

    result = []

    for (
        stadium_number,
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

        result.append({
            "date": target_date,
            "stadium_number":
                stadium_number,
            "race_number":
                race_number,
            "race": race,
            "actual": actual,
        })

    result.sort(
        key=lambda x: (
            x["stadium_number"],
            x["race_number"],
        )
    )

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

    total_dates = max(
        len(dates),
        1,
    )

    for index, date in enumerate(
        dates,
        start=1,
    ):

        daily = _completed_races(
            date
        )

        for item in daily:

            races.append(item)

            if len(races) >= target_count:

                if progress_callback:
                    progress_callback(
                        1.0
                    )

                return _evaluate(
                    races[:target_count]
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

        race = item["race"]

        racers = data.get_race_racers(
            race
        )

        prediction = ai.tri_ai(
            racers
        )

        main = prediction["main"]
        counter = prediction["counter"]
        hole = prediction["hole"]

        actual = item["actual"]

        actual3 = set(
            actual[:3]
        )

        # 本命1着
        if (
            len(actual) >= 1
            and main == actual[0]
        ):
            main_win += 1

        # 本命3連対
        if main in actual3:
            main_top3 += 1

        # AI上位3艇が全艇3連対
        top3 = prediction[
            "ranking"
        ][:3]

        if all(
            boat in actual3
            for boat in top3
        ):
            top3_all_top3 += 1

        predicted = (
            main,
            counter,
            hole,
        )

        # 3連単完全的中
        if (
            len(actual) >= 3
            and predicted
            == tuple(actual[:3])
        ):

            trifecta_hit += 1

            # 100円払戻 × 6 = 600円購入分
            race_payout = int(
                item["race"].get(
                    "payout",
                    0,
                )
                or 0
            )

            payout += (
                race_payout
                * (
                    BET_AMOUNT
                    // BET_UNIT
                )
            )

        investment += BET_AMOUNT

        results.append({
            "date":
                item["date"],

            "stadium":
                data.get_stadium_name(
                    item[
                        "stadium_number"
                    ]
                ),

            "race":
                item["race_number"],

            "main":
                main,

            "counter":
                counter,

            "hole":
                hole,

            "actual":
                actual[:3],

            "trifecta_hit":
                (
                    len(actual) >= 3
                    and predicted
                    == tuple(actual[:3])
                ),

            "ai_top3_hit_count":
                len(
                    set(
                        [
                            main,
                            counter,
                            hole,
                        ]
                    )
                    & actual3
                ),
        })

    recovery = (
        payout
        / investment
        * 100.0
        if investment
        else 0.0
    )

    return {
        "total":
            total,

        "results":
            results,

        "recovery":
            recovery,

        "main_win_rate":
            main_win
            / total
            * 100.0,

        "main_top3_rate":
            main_top3
            / total
            * 100.0,

        "top3_all_top3_rate":
            top3_all_top3
            / total
            * 100.0,

        "trifecta_hit_rate":
            trifecta_hit
            / total
            * 100.0,

        "investment":
            investment,

        "payout":
            payout,
        }
