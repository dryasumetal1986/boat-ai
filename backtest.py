from datetime import date, timedelta

from ai import predict_race
from data import (
    VENUE_BY_ID,
    get_race,
)


INVEST_PER_RACE = 600

TARGET_RACES = [
    100,
    300,
    500,
    1000,
]

START_DATE = date(
    2026,
    1,
    1
)


def run_backtest(
    target_count,
    end_date=None
):

    end_date = (
        end_date
        or date.today()
    )

    cursor = (
        end_date
        - timedelta(days=1)
    )

    rows = []

    investment = 0
    returned = 0

    main_win = 0
    main_top3 = 0
    top3_all = 0
    box_hit = 0
    exact = 0

    while (
        cursor >= START_DATE
        and len(rows) < target_count
    ):

        ds = cursor.isoformat()

        # 全国24場
        for sid in range(1, 25):

            venue = VENUE_BY_ID[sid]

            # 1R〜12R
            for race_no in range(1, 13):

                if len(rows) >= target_count:
                    break

                race = get_race(
                    ds,
                    venue,
                    race_no
                )

                if not race:
                    continue

                if len(
                    race["boats"]
                ) != 6:
                    continue

                if len(
                    race["actual"]
                ) < 3:
                    continue

                pred = predict_race(
                    race
                )

                main, counter, hole = (
                    pred["ranking"][:3]
                )

                actual = tuple(
                    race["actual"][:3]
                )

                selected = (
                    main,
                    counter,
                    hole
                )

                investment += (
                    INVEST_PER_RACE
                )

                mw = (
                    actual[0]
                    == main
                )

                mt = (
                    main
                    in actual
                )

                ta = all(
                    x in actual
                    for x in pred[
                        "ranking"
                    ][:3]
                )

                bx = (
                    set(selected)
                    == set(actual)
                )

                ex = (
                    actual
                    == selected
                )

                main_win += int(mw)
                main_top3 += int(mt)
                top3_all += int(ta)
                box_hit += int(bx)
                exact += int(ex)

                if ex:

                    # 100円券の払戻 × 600円投資
                    returned += (
                        race["payout"]
                        * 6
                    )

                rows.append(
                    {
                        "date": ds,
                        "venue": venue,
                        "race_no": race_no,
                        "main": main,
                        "counter": counter,
                        "hole": hole,
                        "actual": actual,
                        "box_hit": bx,
                        "exact_hit": ex,
                    }
                )

        cursor -= timedelta(days=1)

    n = len(rows)

    return {
        "rows": rows,
        "count": n,
        "investment": investment,
        "return": returned,

        "recovery": (
            returned
            / investment
            * 100
            if investment
            else 0
        ),

        "main_win_rate": (
            main_win
            / n
            * 100
            if n
            else 0
        ),

        "main_top3_rate": (
            main_top3
            / n
            * 100
            if n
            else 0
        ),

        "top3_all_top3_rate": (
            top3_all
            / n
            * 100
            if n
            else 0
        ),

        "box_hit_rate": (
            box_hit
            / n
            * 100
            if n
            else 0
        ),

        "exact_hit_rate": (
            exact
            / n
            * 100
            if n
            else 0
        ),
    }
