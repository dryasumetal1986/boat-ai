from datetime import timedelta

from ai import predict_race
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

    1レース600円投資。
    本命・対抗・穴の3連単1点を購入。

    的中した場合は公式3連単払戻を
    実際に加算する。
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
    exact_hits = 0

    while (
        current >= cutoff
        and len(rows) < target
    ):
        date_str = current.isoformat()

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
                    # レース情報
                    # -------------------------

                    race = get_race(
                        date_str,
                        venue,
                        race_no,
                    )

                    if not race:
                        continue

                    # -------------------------
                    # 実際の結果
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
                    # AI予想
                    # -------------------------

                    prediction = predict_race(
                        race
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

                    predicted = (
                        main,
                        counter,
                        hole,
                    )

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
                    # 投資
                    # -------------------------

                    bet = 600

                    investment += bet

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
                    # AI3艇BOX
                    # -------------------------

                    box_hit = _box_hit(
                        prediction,
                        actual,
                    )

                    if box_hit:
                        box_hits += 1

                    # -------------------------
                    # 完全的中
                    # -------------------------

                    exact_hit = (
                        predicted
                        == actual
                    )

                    if exact_hit:
                        exact_hits += 1

                        # 実際の払戻
                        if actual_payout > 0:
                            payout += (
                                actual_payout
                                / 100
                                * 100
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
                            "predicted": predicted,
                            "actual": actual,
                            "box_hit": box_hit,
                            "exact_hit": exact_hit,
                            "payout": (
                                actual_payout
                                if exact_hit
                                else 0
                            ),
                        }
                    )

                    # -------------------------
                    # 進捗
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

    # --------------------------------
    # 指標
    # --------------------------------

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

        exact_hit_rate = (
            exact_hits
            / count
            * 100
        )

    else:

        main_win_rate = 0.0
        main_top3_rate = 0.0
        top3_all_top3_rate = 0.0
        box_hit_rate = 0.0
        exact_hit_rate = 0.0

    # --------------------------------
    # 回収率
    # --------------------------------

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
        "main_win_rate": main_win_rate,
        "main_top3_rate": main_top3_rate,
        "top3_all_top3_rate": (
            top3_all_top3_rate
        ),
        "box_hit_rate": box_hit_rate,
        "exact_hit_rate": exact_hit_rate,
        "investment": investment,
        "return": payout,
        "rows": rows,
    }
