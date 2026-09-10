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
    """
    start_dateから過去へ遡り、
    結果が確定しているレースをtarget_count件集める。

    全24場を対象にする。

    progress:
        app.pyから進捗表示用の関数を受け取る。
    """

    found = []

    current_day = start_date

    for day_index in range(max_days):

        # 進捗表示
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

            # 念のため結果が1〜6号艇だけか確認
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
    """
    AI予想のバックテスト。

    現在のAIが出す
    本線・対抗・穴の3点を、
    そのまま過去レースの結果と比較する。

    重要:
    予想も結果も必ず1〜6号艇で比較する。
    """

    try:
        target_count = int(
            target_count
        )
    except Exception:
        target_count = 100

    target_count = max(
        1,
        target_count
    )

    # ------------------------------------------------
    # 過去レース収集
    # ------------------------------------------------

    races = collect_races(
        start_date,
        target_count,
        max_days=120,
        progress=progress,
    )

    rows = []

    # 的中数
    hits = {
        "本線": 0,
        "対抗": 0,
        "穴": 0,
        "3点": 0,
    }

    # 軸成績
    axis_first = 0
    axis_top3 = 0

    # 投資・払戻
    total_bet = 0
    total_payout = 0

    # ------------------------------------------------
    # 各レースを検証
    # ------------------------------------------------

    for (
        day,
        stadium_no,
        race_no,
        race,
        actual,
    ) in races:

        try:

            # 出走表をDataFrame化
            df = race_to_df(
                race
            )

            if df.empty:
                continue

            if len(df) != 6:
                continue

            # 艇番が1〜6か確認
            boats = set(
                df["boat"]
                .astype(int)
            )

            if boats != {
                1, 2, 3, 4, 5, 6
            }:
                continue

            # ------------------------------------------------
            # 現在のAIで予想
            # ------------------------------------------------

            pred = predict(
                df
            )

            tickets = {}

            for ticket in pred["tickets"]:

                label = str(
                    ticket["label"]
                )

                combo = tuple(
                    int(x)
                    for x in ticket["combo"]
                )

                # 予想の最終安全確認
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

            # 3点すべて揃っていなければ
            # このレースは検証対象から除外
            if not all(
                label in tickets
                for label in [
                    "本線",
                    "対抗",
                    "穴",
                ]
            ):
                continue

            # ------------------------------------------------
            # 実結果も1〜6号艇で確認
            # ------------------------------------------------

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

            # ------------------------------------------------
            # 的中判定
            # ------------------------------------------------

            hit_labels = []

            for label in [
                "本線",
                "対抗",
                "穴",
            ]:

                if tickets[label] == actual:

                    hits[label] += 1

                    hit_labels.append(
                        label
                    )

            # 3点のどれかが当たった
            if len(hit_labels) > 0:
                hits["3点"] += 1

            # ------------------------------------------------
            # 軸成績
            # ------------------------------------------------

            axis = int(
                pred["axis"]
            )

            if axis == actual[0]:
                axis_first += 1

            if axis in actual:
                axis_top3 += 1

            # ------------------------------------------------
            # 払戻
            # ------------------------------------------------

            payout = None

            try:
                payout = get_payout(
                    race
                )
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
                    .replace(
                        "=",
                        "-"
                    )
                    .replace(
                        " ",
                        ""
                    )
                )

                actual_text = combo_text(
                    actual
                )

                if (
                    payout_combination
                    == actual_text
                ):

                    try:
                        payout_amount = int(
                            payout.get(
                                "amount",
                                0
                            )
                        )
                    except Exception:
                        payout_amount = 0

            # 1レース3点購入
            bet_amount = 300

            total_bet += bet_amount

            # 3点のいずれかに的中していた場合、
            # 実際の払戻を加算
            if len(hit_labels) > 0:
                total_payout += payout_amount

            # ------------------------------------------------
            # 表示用行
            # ------------------------------------------------

            rows.append(
                {
                    "日付": day.strftime(
                        "%m/%d"
                    ),

                    "会場": STADIUMS.get(
                        stadium_no,
                        str(stadium_no)
                    ),

                    "R": int(
                        race_no
                    ),

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
            # 1レースの不具合で
            # バックテスト全体を止めない
            continue

    # ------------------------------------------------
    # 集計
    # ------------------------------------------------

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

    # ------------------------------------------------
    # 最終結果
    # ------------------------------------------------

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

        "投資": int(
            total_bet
        ),

        "払戻": int(
            total_payout
        ),

        "回収率": round(
            recovery_rate,
            2
        ),
    }

    return summary, rows
