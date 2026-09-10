from datetime import timedelta

from ai import predict_race
from data import (
    VENUES,
    get_all_races_for_day,
    get_race_result,
)


TARGET_RACES = [
    100,
    300,
    500,
    1000,
]


def _box_hit(
    prediction,
    actual,
):
    selected = {
        prediction["main"],
        prediction["counter"],
        prediction["hole"],
    }

    return selected.issubset(
        set(actual)
    )


def _ticket_hits(
    prediction,
    actual,
):
    tickets = prediction.get(
        "tickets",
        [],
    )

    return [
        tuple(ticket) == tuple(actual)
        for ticket in tickets
    ]


def run_backtest(
    target,
    end_date,
    progress_callback=None,
):
    """
    全国24場バックテスト。

    対象:
        2026-01-01 〜 前日

    購入:
        本線 100円
        対抗 100円
        穴   100円

        合計300円/レース

    EVではなく、
    AIが選んだ3点をそのまま検証。
    """

    target = int(target)

    cutoff = end_date.replace(
        year=2026,
        month=1,
        day=1,
    )

    current = (
        end_date
        - timedelta(days=1)
    )

    rows = []

    investment = 0.0
    payout = 0.0

    main_first_hits = 0
    main_top3_hits = 0

    top3_all_top3 = 0
    box_hits = 0

    exact_hits = 0
    three_bet_hits = 0

    main_ticket_hits = 0
    counter_ticket_hits = 0
    hole_ticket_hits = 0

    days_checked = 0

    while (
        current >= cutoff
        and len(rows) < target
    ):
        date_str = current.isoformat()

        races = get_all_races_for_day(
            date_str
        )

        days_checked += 1

        if not races:
            current -= timedelta(
                days=1
            )
            continue

        for race in races:
            if len(rows) >= target:
                break

            venue = race[
                "venue"
            ]

            venue_id = race[
                "venue_id"
            ]

            race_no = race[
                "race_no"
            ]

            result = get_race_result(
                date_str,
                venue_id,
                race_no,
            )

            if not result:
                continue

            actual = result[
                "actual"
            ]

            actual_payout = result[
                "trifecta_payout"
            ]

            if len(actual) != 3:
                continue

            prediction = predict_race(
                race
            )

            tickets = prediction.get(
                "tickets",
                [],
            )

            if len(tickets) < 3:
                continue

            main_ticket = tuple(
                tickets[0]
            )

            counter_ticket = tuple(
                tickets[1]
            )

            hole_ticket = tuple(
                tickets[2]
            )

            bet = 300.0

            investment += bet

            main = prediction[
                "main"
            ]

            counter = prediction[
                "counter"
            ]

            hole = prediction[
                "hole"
            ]

            ranking = prediction[
                "ranking"
            ]

            actual_set = set(
                actual
            )

            if actual[0] == main:
                main_first_hits += 1

            if main in actual_set:
                main_top3_hits += 1

            top3 = set(
                ranking[:3]
            )

            if top3.issubset(
                actual_set
            ):
                top3_all_top3 += 1

            box_hit = _box_hit(
                prediction,
                actual,
            )

            if box_hit:
                box_hits += 1

            ticket_results = (
                _ticket_hits(
                    prediction,
                    actual,
                )
            )

            exact_hit = any(
                ticket_results
            )

            if exact_hit:
                exact_hits += 1

                if (
                    actual_payout
                    > 0
                ):
                    payout += (
                        actual_payout
                    )

            if ticket_results[0]:
                main_ticket_hits += 1

            if ticket_results[1]:
                counter_ticket_hits += 1

            if ticket_results[2]:
                hole_ticket_hits += 1

            if exact_hit:
                three_bet_hits += 1

            rows.append(
                {
                    "date": date_str,
                    "venue": venue,
                    "race_no": race_no,

                    "main": main,
                    "counter": counter,
                    "hole": hole,

                    "tickets": [
                        main_ticket,
                        counter_ticket,
                        hole_ticket,
                    ],

                    "predicted": main_ticket,

                    "actual": actual,

                    "box_hit": box_hit,

                    "exact_hit": exact_hit,

                    "main_hit": (
                        ticket_results[0]
                    ),

                    "counter_hit": (
                        ticket_results[1]
                    ),

                    "hole_hit": (
                        ticket_results[2]
                    ),

                    "payout": (
                        actual_payout
                        if exact_hit
                        else 0
                    ),
                }
            )

            if progress_callback:
                try:
                    progress_callback(
                        len(rows),
                        target,
                        days_checked,
                    )
                except Exception:
                    pass

        current -= timedelta(
            days=1
        )

    count = len(rows)

    if count > 0:
        main_win_rate = (
            main_first_hits
            / count
            * 100
        )

        main_top3_rate = (
            main_top3_hits
            / count
            * 100
        )

        top3_all_top3_rate = (
            top3_all_top3
            / count
            * 100
        )

        box_hit_rate = (
            box_hits
            / count
            * 100
        )

        exact_hit_rate = (
            exact_hits
            / count
            * 100
        )

        three_bet_hit_rate = (
            three_bet_hits
            / count
            * 100
        )

        main_ticket_hit_rate = (
            main_ticket_hits
            / count
            * 100
        )

        counter_ticket_hit_rate = (
            counter_ticket_hits
            / count
            * 100
        )

        hole_ticket_hit_rate = (
            hole_ticket_hits
            / count
            * 100
        )

    else:
        main_win_rate = 0.0
        main_top3_rate = 0.0
        top3_all_top3_rate = 0.0
        box_hit_rate = 0.0
        exact_hit_rate = 0.0
        three_bet_hit_rate = 0.0
        main_ticket_hit_rate = 0.0
        counter_ticket_hit_rate = 0.0
        hole_ticket_hit_rate = 0.0

    if investment > 0:
        recovery = (
            payout
            / investment
            * 100
        )
    else:
        recovery = 0.0

    return {
        "count": count,

        "recovery": recovery,

        "main_win_rate": (
            main_win_rate
        ),

        "main_top3_rate": (
            main_top3_rate
        ),

        "top3_all_top3_rate": (
            top3_all_top3_rate
        ),

        "box_hit_rate": (
            box_hit_rate
        ),

        "exact_hit_rate": (
            exact_hit_rate
        ),

        "three_bet_hit_rate": (
            three_bet_hit_rate
        ),

        "main_ticket_hit_rate": (
            main_ticket_hit_rate
        ),

        "counter_ticket_hit_rate": (
            counter_ticket_hit_rate
        ),

        "hole_ticket_hit_rate": (
            hole_ticket_hit_rate
        ),

        "investment": investment,

        "return": payout,

        "rows": rows,
    }
