from datetime import timedelta

from ai import (
    predict_race,
    recommend_bets,
)

from data import (
    VENUES,
    get_race,
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


def run_backtest(
    target,
    end_date,
    progress_callback=None,
):
    """
    全国24場を対象。

    end_date当日は除外し、
    前日から2026-01-01まで遡る。

    新ルール：

    ・本線100円
    ・対抗100円
    ・穴100円

    合計300円/レース。

    3点のうちどれかが
    的中したかを評価する。
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

    main_win = 0
    main_top3 = 0
    top3_all_top3 = 0
    box_hits = 0

    three_bet_hits = 0
    exact_hits = 0

    main_exact_hits = 0
    counter_exact_hits = 0
    hole_exact_hits = 0

    while (
        current >= cutoff
        and len(rows) < target
    ):

        date_str = (
            current.isoformat()
        )

        for venue, venue_id in VENUES.items():

            if len(rows) >= target:
                break

            for race_no in range(
                1,
                13,
            ):

                if len(rows) >= target:
                    break

                try:

                    # -------------------------
                    # レース
                    # -------------------------

                    race = get_race(
                        date_str,
                        venue,
                        race_no,
                    )

                    if not race:
                        continue

                    # -------------------------
                    # 結果
                    # -------------------------

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

                    # -------------------------
                    # AI
                    # -------------------------

                    prediction = predict_race(
                        race
                    )

                    bets = recommend_bets(
                        prediction
                    )

                    if len(bets) < 3:
                        continue

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

                    top3 = set(
                        ranking[:3]
                    )

                    actual_set = set(
                        actual
                    )

                    # -------------------------
                    # 3点
                    # -------------------------

                    bet_combos = [
                        bet["combo"]
                        for bet in bets
                    ]

                    bet_texts = [
                        "-".join(
                            map(
                                str,
                                combo,
                            )
                        )
                        for combo in bet_combos
                    ]

                    # -------------------------
                    # 投資
                    # -------------------------

                    bet_amount = 100 * len(
                        bet_combos
                    )

                    investment += (
                        bet_amount
                    )

                    # -------------------------
                    # 本命1着
                    # -------------------------

                    if actual[0] == main:
                        main_win += 1

                    # -------------------------
                    # 本命3連対
                    # -------------------------

                    if main in actual_set:
                        main_top3 += 1

                    # -------------------------
                    # AI上位3艇
                    # 全艇3連対
                    # -------------------------

                    if top3.issubset(
                        actual_set
                    ):
                        top3_all_top3 += 1

                    # -------------------------
                    # 3艇BOX
                    # -------------------------

                    box_hit = _box_hit(
                        prediction,
                        actual,
                    )

                    if box_hit:
                        box_hits += 1

                    # -------------------------
                    # 3点的中
                    # -------------------------

                    hit_indexes = []

                    for i, combo in enumerate(
                        bet_combos
                    ):

                        if combo == actual:
                            hit_indexes.append(i)

                    three_bet_hit = (
                        len(hit_indexes) > 0
                    )

                    if three_bet_hit:
                        three_bet_hits += 1

                    # -------------------------
                    # 各買い目の的中
                    # -------------------------

                    main_exact = (
                        bet_combos[0]
                        == actual
                    )

                    counter_exact = (
                        bet_combos[1]
                        == actual
                    )

                    hole_exact = (
                        bet_combos[2]
                        == actual
                    )

                    if main_exact:
                        main_exact_hits += 1

                    if counter_exact:
                        counter_exact_hits += 1

                    if hole_exact:
                        hole_exact_hits += 1

                    # -------------------------
                    # 完全的中
                    # -------------------------

                    exact_hit = (
                        main_exact
                        or counter_exact
                        or hole_exact
                    )

                    if exact_hit:
                        exact_hits += 1

                        # 3点のうち1点のみ
                        # 的中する通常ケースを想定
                        if actual_payout > 0:
                            payout += (
                                float(
                                    actual_payout
                                )
                            )

                    # -------------------------
                    # 結果保存
                    # -------------------------

                    rows.append(
                        {
                            "date": date_str,
                            "venue": venue,
                            "race_no": race_no,

                            "main": main,
                            "counter": counter,
                            "hole": hole,

                            "predicted": (
                                bet_combos[0]
                            ),

                            "bets": bet_combos,
                            "bet_texts": bet_texts,

                            "actual": actual,

                            "box_hit": box_hit,
                            "three_bet_hit": (
                                three_bet_hit
                            ),
                            "exact_hit": exact_hit,

                            "main_exact": (
                                main_exact
                            ),
                            "counter_exact": (
                                counter_exact
                            ),
                            "hole_exact": (
                                hole_exact
                            ),

                            "payout": (
                                actual_payout
                                if exact_hit
                                else 0
                            ),
                        }
                    )

                    # -------------------------
                    # Progress
                    # -------------------------

                    if progress_callback:

                        try:
                            progress_callback(
                                len(rows),
                                target,
                            )
                        except Exception:
                            pass

                except Exception:
                    continue

        current -= timedelta(
            days=1
        )

    # =================================
    # 指標
    # =================================

    count = len(rows)

    if count > 0:

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

        three_bet_hit_rate = (
            three_bet_hits
            / count
            * 100
        )

        exact_hit_rate = (
            exact_hits
            / count
            * 100
        )

        main_exact_rate = (
            main_exact_hits
            / count
            * 100
        )

        counter_exact_rate = (
            counter_exact_hits
            / count
            * 100
        )

        hole_exact_rate = (
            hole_exact_hits
            / count
            * 100
        )

    else:

        main_win_rate = 0.0
        main_top3_rate = 0.0
        top3_all_top3_rate = 0.0
        box_hit_rate = 0.0
        three_bet_hit_rate = 0.0
        exact_hit_rate = 0.0
        main_exact_rate = 0.0
        counter_exact_rate = 0.0
        hole_exact_rate = 0.0

    # =================================
    # 回収率
    # =================================

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

        "main_win_rate":
            main_win_rate,

        "main_top3_rate":
            main_top3_rate,

        "top3_all_top3_rate":
            top3_all_top3_rate,

        "box_hit_rate":
            box_hit_rate,

        "three_bet_hit_rate":
            three_bet_hit_rate,

        "exact_hit_rate":
            exact_hit_rate,

        "main_exact_rate":
            main_exact_rate,

        "counter_exact_rate":
            counter_exact_rate,

        "hole_exact_rate":
            hole_exact_rate,

        "investment":
            investment,

        "return":
            payout,

        "rows":
            rows,
                    }
