from datetime import date, timedelta

from ai import predict_race
from data import VENUE_BY_ID, get_race


# 1レースあたり600円投資
INVEST_PER_RACE = 600

# 選択できる検証レース数
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
    """
    全国24場を対象にバックテスト。

    現在日のレースは使用せず、
    前日から2026-01-01まで
    遡って完成済みレースを集める。
    """

    if end_date is None:
        end_date = date.today()

    # 当日を除外して「前日」から開始
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

    # -------------------------
    # 集計
    # -------------------------

    total_investment = 0.0
    total_return = 0.0

    main_win_count = 0
    main_top3_count = 0

    top3_all_top3_count = 0

    box_hit_count = 0
    exact_hit_count = 0

    # -------------------------
    # 日付を遡る
    # -------------------------

    while (
        cursor >= start_date
        and len(rows) < target_count
    ):

        date_str = (
            cursor.isoformat()
        )

        # 全国24場
        for venue_id in range(
            1,
            25,
        ):

            if len(rows) >= target_count:
                break

            venue_name = VENUE_BY_ID[
                venue_id
            ]

            # 1R～12R
            for race_no in range(
                1,
                13,
            ):

                if len(rows) >= target_count:
                    break

                race = get_race(
                    date_str,
                    venue_name,
                    race_no,
                )

                # データがないレースは除外
                if not race:
                    continue

                # 6艇揃っていない場合は除外
                if len(
                    race.get(
                        "boats",
                        [],
                    )
                ) != 6:
                    continue

                # 結果がないレースは除外
                actual = race.get(
                    "actual",
                    [],
                )

                if len(actual) < 3:
                    continue

                # -------------------------
                # AI予想
                # -------------------------

                prediction = predict_race(
                    race
                )

                ranking = prediction[
                    "ranking"
                ]

                main = ranking[0]
                counter = ranking[1]
                hole = ranking[2]

                # AIが選んだ3艇
                selected_boats = {
                    main,
                    counter,
                    hole,
                }

                # 実際の3着
                actual_top3 = tuple(
                    actual[:3]
                )

                # -------------------------
                # 投資
                # -------------------------

                total_investment += (
                    INVEST_PER_RACE
                )

                # -------------------------
                # 本命1着
                # -------------------------

                main_win = (
                    actual_top3[0]
                    == main
                )

                if main_win:
                    main_win_count += 1

                # -------------------------
                # 本命3連対
                # -------------------------

                main_top3 = (
                    main
                    in actual_top3
                )

                if main_top3:
                    main_top3_count += 1

                # -------------------------
                # AI上位3艇
                # 全艇が3着以内
                # -------------------------

                top3_all_top3 = all(
                    boat in actual_top3
                    for boat in ranking[:3]
                )

                if top3_all_top3:
                    top3_all_top3_count += 1

                # -------------------------
                # AI選出3艇BOX的中
                #
                # 順番は問わず
                # 3艇すべてが実着3艇と一致
                # -------------------------

                box_hit = (
                    selected_boats
                    == set(actual_top3)
                )

                if box_hit:
                    box_hit_count += 1

                # -------------------------
                # 3連単完全的中
                # -------------------------

                predicted_combo = (
                    main,
                    counter,
                    hole,
                )

                exact_hit = (
                    actual_top3
                    == predicted_combo
                )

                if exact_hit:
                    exact_hit_count += 1

                    # 公式払戻は100円券の金額。
                    #
                    # このバックテストでは
                    # 1点に600円投資するため、
                    # 払戻を6倍する。
                    payout = float(
                        race.get(
                            "payout",
                            0,
                        )
                    )

                    total_return += (
                        payout * 6
                    )

                # -------------------------
                # 検証結果
                # -------------------------

                rows.append({
                    "date": date_str,

                    "venue": venue_name,

                    "race_no": race_no,

                    "main": main,

                    "counter": counter,

                    "hole": hole,

                    "actual": actual_top3,

                    "main_win": main_win,

                    "main_top3": main_top3,

                    "box_hit": box_hit,

                    "exact_hit": exact_hit,
                })

        # 1日前へ
        cursor -= timedelta(
            days=1
        )

    # -------------------------
    # 集計
    # -------------------------

    race_count = len(rows)

    if race_count > 0:

        recovery_rate = (
            total_return
            / total_investment
            * 100
        )

        main_win_rate = (
            main_win_count
            / race_count
            * 100
        )

        main_top3_rate = (
            main_top3_count
            / race_count
            * 100
        )

        top3_all_top3_rate = (
            top3_all_top3_count
            / race_count
            * 100
        )

        box_hit_rate = (
            box_hit_count
            / race_count
            * 100
        )

        exact_hit_rate = (
            exact_hit_count
            / race_count
            * 100
        )

    else:

        recovery_rate = 0.0
        main_win_rate = 0.0
        main_top3_rate = 0.0
        top3_all_top3_rate = 0.0
        box_hit_rate = 0.0
        exact_hit_rate = 0.0

    return {
        "rows": rows,

        "count": race_count,

        "investment": total_investment,

        "return": total_return,

        "recovery": recovery_rate,

        "main_win_rate":
            main_win_rate,

        "main_top3_rate":
            main_top3_rate,

        "top3_all_top3_rate":
            top3_all_top3_rate,

        "box_hit_rate":
            box_hit_rate,

        "exact_hit_rate":
            exact_hit_rate,
    }
