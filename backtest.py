from datetime import timedelta

from data import (
    STADIUMS,
    get_all_races,
    get_result,
    get_payout,
    race_to_df,
)

from ai import (
    predict,
    combo_text,
)


def collect_races(
    start_date,
    target_count,
    max_days=120,
    progress=None,
):
    found = []
    current_day = start_date

    for day_index in range(max_days):

        if progress is not None:
            try:
                progress(
                    day_index + 1,
                    max_days,
                    len(found),
                    current_day,
                )
            except Exception:
                pass

        try:
            races = get_all_races(
                current_day,
                require_result=True,
            )
        except Exception:
            current_day -= timedelta(days=1)
            continue

        for stadium_no, race_no, race in races:

            try:
                actual = get_result(race)
            except Exception:
                actual = None

            if actual is None:
                continue

            if len(actual) != 3:
                continue

            if not all(
                1 <= int(boat) <= 6
                for boat in actual
            ):
                continue

            if len(set(actual)) != 3:
                continue

            found.append(
                (
                    current_day,
                    stadium_no,
                    race_no,
                    race,
                    actual,
                )
            )

            if len(found) >= target_count:
                return found

        current_day -= timedelta(days=1)

    return found


def run_backtest(
    start_date,
    target_count,
    progress=None,
):
    try:
        target_count = int(target_count)
    except Exception:
        target_count = 100

    target_count = max(
        1,
        target_count
    )

    races = collect_races(
        start_date,
        target_count,
        max_days=120,
        progress=progress,
    )

    rows = []

    hits = {
        "本線": 0,
        "対抗": 0,
        "穴": 0,
        "3点": 0,
    }

    axis_first = 0
    axis_top3 = 0

    total_bet = 0
    total_payout = 0

    # =====================================================
    # 会場別集計
    # =====================================================

    venue_stats = {}

    for stadium_no in STADIUMS:
        venue_stats[stadium_no] = {
            "検証数": 0,
            "本線": 0,
            "対抗": 0,
            "穴": 0,
            "3点": 0,
            "投資": 0,
            "払戻": 0,
        }

    # =====================================================
    # バックテスト
    # =====================================================

    for (
        day,
        stadium_no,
        race_no,
        race,
        actual,
    ) in races:

        try:

            df = race_to_df(race)

            if df.empty or len(df) != 6:
                continue

            boats = set(
                df["boat"].astype(int)
            )

            if boats != {1, 2, 3, 4, 5, 6}:
                continue

            pred = predict(df)

            tickets = {}

            for ticket in pred["tickets"]:

                label = str(
                    ticket["label"]
                )

                combo = tuple(
                    int(x)
                    for x in ticket["combo"]
                )

                if len(combo) != 3:
                    continue

                if len(set(combo)) != 3:
                    continue

                if not all(
                    1 <= x <= 6
                    for x in combo
                ):
                    continue

                tickets[label] = combo

            if not all(
                label in tickets
                for label in [
                    "本線",
                    "対抗",
                    "穴",
                ]
            ):
                continue

            actual = tuple(
                int(x)
                for x in actual
            )

            if len(actual) != 3:
                continue

            if len(set(actual)) != 3:
                continue

            if not all(
                1 <= x <= 6
                for x in actual
            ):
                continue

            # -------------------------------------------------
            # 会場別の検証数
            # -------------------------------------------------

            if stadium_no not in venue_stats:
                venue_stats[stadium_no] = {
                    "検証数": 0,
                    "本線": 0,
                    "対抗": 0,
                    "穴": 0,
                    "3点": 0,
                    "投資": 0,
                    "払戻": 0,
                }

            venue_stats[stadium_no]["検証数"] += 1

            # -------------------------------------------------
            # 的中判定
            # -------------------------------------------------

            hit_labels = []

            for label in [
                "本線",
                "対抗",
                "穴",
            ]:

                if tickets[label] == actual:

                    hits[label] += 1

                    venue_stats[
                        stadium_no
                    ][label] += 1

                    hit_labels.append(label)

            if len(hit_labels) > 0:

                hits["3点"] += 1

                venue_stats[
                    stadium_no
                ]["3点"] += 1

            # -------------------------------------------------
            # 軸判定
            # -------------------------------------------------

            axis = int(
                pred["axis"]
            )

            if axis == actual[0]:
                axis_first += 1

            if axis in actual:
                axis_top3 += 1

            # -------------------------------------------------
            # 払戻
            # -------------------------------------------------

            payout = None

            try:
                payout = get_payout(race)
            except Exception:
                payout = None

            payout_amount = 0

            if payout is not None:

                payout_combination = str(
                    payout.get(
                        "combination",
                        ""
                    )
                )

                payout_combination = (
                    payout_combination
                    .replace("=", "-")
                    .replace(" ", "")
                )

                actual_text = combo_text(
                    actual
                )

                if payout_combination == actual_text:

                    try:
                        payout_amount = int(
                            payout.get(
                                "amount",
                                0
                            )
                        )
                    except Exception:
                        payout_amount = 0

            # 1レース300円
            bet_amount = 300

            total_bet += bet_amount

            venue_stats[
                stadium_no
            ]["投資"] += bet_amount

            if len(hit_labels) > 0:

                total_payout += (
                    payout_amount
                )

                venue_stats[
                    stadium_no
                ]["払戻"] += (
                    payout_amount
                )

            # -------------------------------------------------
            # 詳細行
            # -------------------------------------------------

            rows.append(
                {
                    "日付": day.strftime(
                        "%m/%d"
                    ),
                    "会場": STADIUMS.get(
                        stadium_no,
                        str(stadium_no)
                    ),
                    "R": int(race_no),
                    "本線": combo_text(
                        tickets["本線"]
                    ),
                    "対抗": combo_text(
                        tickets["対抗"]
                    ),
                    "穴": combo_text(
                        tickets["穴"]
                    ),
                    "結果": combo_text(
                        actual
                    ),
                    "本線的中": (
                        "○"
                        if tickets["本線"]
                        == actual
                        else ""
                    ),
                    "対抗的中": (
                        "○"
                        if tickets["対抗"]
                        == actual
                        else ""
                    ),
                    "穴的中": (
                        "○"
                        if tickets["穴"]
                        == actual
                        else ""
                    ),
                    "払戻": int(
                        payout_amount
                    ),
                }
            )

        except Exception:
            continue

    # =====================================================
    # 全体集計
    # =====================================================

    n = len(rows)

    if n > 0:

        three_hit_rate = (
            hits["3点"]
            / n
            * 100
        )

        main_hit_rate = (
            hits["本線"]
            / n
            * 100
        )

        counter_hit_rate = (
            hits["対抗"]
            / n
            * 100
        )

        hole_hit_rate = (
            hits["穴"]
            / n
            * 100
        )

        axis_first_rate = (
            axis_first
            / n
            * 100
        )

        axis_top3_rate = (
            axis_top3
            / n
            * 100
        )

    else:

        three_hit_rate = 0.0
        main_hit_rate = 0.0
        counter_hit_rate = 0.0
        hole_hit_rate = 0.0
        axis_first_rate = 0.0
        axis_top3_rate = 0.0

    if total_bet > 0:

        recovery_rate = (
            total_payout
            / total_bet
            * 100
        )

    else:
        recovery_rate = 0.0

    # =====================================================
    # 会場別集計をDataFrame用の行へ変換
    # =====================================================

    venue_rows = []

    for stadium_no in sorted(
        venue_stats.keys()
    ):

        stats = venue_stats[
            stadium_no
        ]

        venue_count = int(
            stats["検証数"]
        )

        if venue_count <= 0:
            continue

        venue_three_rate = (
            stats["3点"]
            / venue_count
            * 100
        )

        venue_main_rate = (
            stats["本線"]
            / venue_count
            * 100
        )

        venue_counter_rate = (
            stats["対抗"]
            / venue_count
            * 100
        )

        venue_hole_rate = (
            stats["穴"]
            / venue_count
            * 100
        )

        venue_investment = int(
            stats["投資"]
        )

        venue_payout = int(
            stats["払戻"]
        )

        if venue_investment > 0:

            venue_recovery = (
                venue_payout
                / venue_investment
                * 100
            )

        else:
            venue_recovery = 0.0

        venue_rows.append(
            {
                "会場": STADIUMS.get(
                    stadium_no,
                    str(stadium_no)
                ),
                "検証数": venue_count,
                "3点的中率": round(
                    venue_three_rate,
                    2
                ),
                "本線": round(
                    venue_main_rate,
                    2
                ),
                "対抗": round(
                    venue_counter_rate,
                    2
                ),
                "穴": round(
                    venue_hole_rate,
                    2
                ),
                "投資": venue_investment,
                "払戻": venue_payout,
                "回収率": round(
                    venue_recovery,
                    2
                ),
            }
        )

    # 3点的中率が高い順
    venue_rows.sort(
        key=lambda row: (
            row["3点的中率"],
            row["検証数"],
        ),
        reverse=True,
    )

    summary = {
        "検証数": n,
        "3点的中率": round(
            three_hit_rate,
            2
        ),
        "本線的中率": round(
            main_hit_rate,
            2
        ),
        "対抗的中率": round(
            counter_hit_rate,
            2
        ),
        "穴的中率": round(
            hole_hit_rate,
            2
        ),
        "軸1着率": round(
            axis_first_rate,
            2
        ),
        "軸3着内率": round(
            axis_top3_rate,
            2
        ),
        "投資": int(total_bet),
        "払戻": int(total_payout),
        "回収率": round(
            recovery_rate,
            2
        ),
    }

    return (
        summary,
        rows,
        venue_rows,
    )
