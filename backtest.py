from datetime import timedelta

from ai import predict_race
from data import VENUES, get_race


TARGET_RACES = [
    100,
    300,
    500,
    1000,
]


def _actual_result(race):
    """
    実際の着順を取得。
    データがない場合はNone。
    """

    result = race.get("result")

    if not result:
        return None

    try:
        result = [
            int(x)
            for x in result
        ]

        if len(result) >= 3:
            return tuple(result[:3])

    except Exception:
        pass

    return None


def _box_hit(prediction, actual):
    """
    AI本命・対抗・穴の3艇が
    実着順3艇にすべて含まれているか。
    """

    selected = {
        prediction["main"],
        prediction["counter"],
        prediction["hole"],
    }

    actual_set = set(actual)

    return selected.issubset(actual_set)


def run_backtest(
    target,
    end_date,
    progress_callback=None,
):
    """
    全国24場を対象に、
    end_dateの前日から
    2026-01-01まで遡って検証。

    target:
        100 / 300 / 500 / 1000
    """

    target = int(target)

    start_date = end_date - timedelta(days=1)

    cutoff = end_date.replace(
        year=2026,
        month=1,
        day=1,
    )

    rows = []

    investment = 0.0
    payout = 0.0

    main_win = 0
    main_top3 = 0
    top3_all_top3 = 0
    box_hits = 0
    exact_hits = 0

    checked = 0

    current = start_date

    # --------------------------------
    # 日付を遡る
    # --------------------------------

    while (
        current >= cutoff
        and len(rows) < target
    ):
        date_str = current.isoformat()

        # --------------------------------
        # 全国24場
        # --------------------------------

        for venue, venue_id in VENUES.items():

            if len(rows) >= target:
                break

            for race_no in range(1, 13):

                if len(rows) >= target:
                    break

                checked += 1

                try:
                    race = get_race(
                        date_str,
                        venue,
                        race_no,
                    )

                    if not race:
                        continue

                    actual = _actual_result(
                        race
                    )

                    if not actual:
                        continue

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

                    top3 = set(
                        prediction[
                            "ranking"
                        ][:3]
                    )

                    actual_set = set(
                        actual
                    )

                    investment += 600

                    if actual[0] == main:
                        main_win += 1

                    if main in actual_set:
                        main_top3 += 1

                    if top3.issubset(
                        actual_set
                    ):
                        top3_all_top3 += 1

                    is_box = _box_hit(
                        prediction,
                        actual,
                    )

                    if is_box:
                        box_hits += 1

                    predicted = (
                        main,
                        counter,
                        hole,
                    )

                    is_exact = (
                        predicted == actual
                    )

                    if is_exact:
                        exact_hits += 1

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
                            "box_hit": is_box,
                            "exact_hit": is_exact,
                        }
                    )

                    if progress_callback:
                        try:
                            progress_callback(
                                len(rows),
                                target,
                            )
                        except Exception:
                            pass

                except Exception:
                    # 1レースでエラーが出ても
                    # バックテスト全体を止めない
                    continue

        current -= timedelta(days=1)

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
    # 払戻
    # --------------------------------
    #
    # バックテストの回収率は、
    # 1レース600円投資を基準にする。
    #
    # 3連単の実払戻を取得できる場合は
    # 後から payout を加算できる構造。
    #
    # 現時点では exact hit のみ
    # 仮払戻を入れず、
    # 実オッズ取得側と分離している。
    #

    recovery = (
        payout / investment * 100
        if investment > 0
        else 0.0
    )

    return {
        "count": count,
        "recovery": recovery,
        "main_win_rate": main_win_rate,
        "main_top3_rate": main_top3_rate,
        "top3_all_top3_rate": top3_all_top3_rate,
        "box_hit_rate": box_hit_rate,
        "exact_hit_rate": exact_hit_rate,
        "investment": investment,
        "return": payout,
        "rows": rows,
                    }
