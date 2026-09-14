from datetime import timedelta

from data import (
    STADIUMS,
    get_all_races,
    get_result,
    get_payout,
    race_to_df,
)

from ai import predict, combo_text


def _detect_active_df(df):
    if df is None or df.empty or len(df) != 6:
        return df

    work = df.copy()
    exhibition = work["exhibition_time"].astype(float).fillna(0.0)
    start_timing = work["start_timing"].astype(float).fillna(0.0)
    course = work["course_number"].astype(int)
    duplicated_course = course.duplicated(keep=False)

    scratch = (
        (exhibition <= 0.0)
        & (start_timing <= 0.0)
        & duplicated_course
    )

    if scratch.sum() <= 0:
        return work

    active = work.loc[~scratch].copy()
    return active if 3 <= len(active) <= 6 else work


def _safe_float(value):
    try:
        return float(value) if value is not None else 0.0
    except Exception:
        return 0.0


def _get_boat_row(df, boat):
    try:
        matched = df.loc[df["boat"].astype(int) == int(boat)]
        return None if matched.empty else matched.iloc[0]
    except Exception:
        return None


def _boat_features(df, boat):
    row = _get_boat_row(df, boat)
    keys = [
        "national_win_rate",
        "national_top_2_percent",
        "national_top_3_percent",
        "local_win_rate",
        "local_top_2_percent",
        "local_top_3_percent",
        "motor_top_2_percent",
        "motor_top_3_percent",
        "boat_top_2_percent",
        "boat_top_3_percent",
        "average_start_timing",
        "exhibition_time",
        "start_timing",
        "course_number",
        "motor_number",
        "boat_number",
    ]

    result = {"boat": int(boat)}

    for key in keys:
        result[key] = (
            _safe_float(row.get(key, 0.0))
            if row is not None
            else 0.0
        )

    return result


def _add_features(target, prefix, features):
    for key, value in features.items():
        target[f"{prefix}_{key}"] = value


def _first_two_match(combo, actual):
    return (
        combo is not None
        and len(combo) == 3
        and len(actual) == 3
        and int(combo[0]) == int(actual[0])
        and int(combo[1]) == int(actual[1])
    )


def _build_analysis_data(df, tickets, actual):
    data = {
        "実際1着": int(actual[0]),
        "実際2着": int(actual[1]),
        "実際3着": int(actual[2]),
    }

    actual_features = _boat_features(df, actual[2])
    _add_features(data, "実際3着艇", actual_features)

    matched_label = ""

    for label in ("本線", "対抗", "穴"):
        combo = tickets.get(label)
        if combo is None:
            continue

        data[f"{label}3着"] = int(combo[2])
        data[f"{label}1-2一致"] = (
            "○" if _first_two_match(combo, actual) else ""
        )
        data[f"{label}3着一致"] = (
            "○" if int(combo[2]) == int(actual[2]) else ""
        )

        if not matched_label and _first_two_match(combo, actual):
            matched_label = label

    data["1-2ペア一致券"] = matched_label

    if not matched_label:
        data["1-2一致時AI3着"] = 0
        data["1-2一致時3着的中"] = ""
        data["1-2一致時3着ミス"] = ""
        return data

    predicted_third = int(tickets[matched_label][2])
    predicted_features = _boat_features(df, predicted_third)

    data["1-2一致時AI3着"] = predicted_third
    data["1-2一致時3着的中"] = (
        "○" if predicted_third == int(actual[2]) else ""
    )
    data["1-2一致時3着ミス"] = (
        "" if predicted_third == int(actual[2]) else "○"
    )

    _add_features(
        data,
        "1-2一致時AI3着艇",
        predicted_features,
    )

    diff_pairs = [
        ("national_win_rate", "全国勝率差_実際-AI"),
        ("national_top_2_percent", "全国2連率差_実際-AI"),
        ("national_top_3_percent", "全国3連率差_実際-AI"),
        ("local_win_rate", "当地勝率差_実際-AI"),
        ("local_top_2_percent", "当地2連率差_実際-AI"),
        ("local_top_3_percent", "当地3連率差_実際-AI"),
        ("motor_top_2_percent", "モーター2連率差_実際-AI"),
        ("motor_top_3_percent", "モーター3連率差_実際-AI"),
        ("boat_top_2_percent", "ボート2連率差_実際-AI"),
        ("boat_top_3_percent", "ボート3連率差_実際-AI"),
    ]

    for key, name in diff_pairs:
        data[name] = round(
            actual_features[key] - predicted_features[key],
            4,
        )

    data["平均ST差_AI-実際"] = round(
        predicted_features["average_start_timing"]
        - actual_features["average_start_timing"],
        4,
    )

    data["展示タイム差_AI-実際"] = round(
        predicted_features["exhibition_time"]
        - actual_features["exhibition_time"],
        4,
    )

    return data


def collect_races(start_date, target_count, max_days=120, progress=None):
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

            if actual is None or len(actual) != 3:
                continue

            actual = tuple(int(x) for x in actual)

            if (
                len(set(actual)) != 3
                or not all(1 <= x <= 6 for x in actual)
            ):
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


def run_backtest(start_date, target_count, progress=None):
    try:
        target_count = max(1, int(target_count))
    except Exception:
        target_count = 100

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

    venue_stats = {
        stadium_no: {
            "検証数": 0,
            "本線": 0,
            "対抗": 0,
            "穴": 0,
            "3点": 0,
            "投資": 0,
            "払戻": 0,
        }
        for stadium_no in STADIUMS
    }

    for day, stadium_no, race_no, race, actual in races:
        try:
            df = race_to_df(race)

            if df.empty:
                continue

            df = _detect_active_df(df)

            if not 3 <= len(df) <= 6:
                continue

            boats = set(df["boat"].astype(int))

            if not all(1 <= boat <= 6 for boat in boats):
                continue

            pred = predict(df, stadium_no=stadium_no)

            tickets = {}

            for ticket in pred["tickets"]:
                label = str(ticket["label"])
                combo = tuple(int(x) for x in ticket["combo"])

                if (
                    len(combo) == 3
                    and len(set(combo)) == 3
                    and all(1 <= x <= 6 for x in combo)
                    and all(x in boats for x in combo)
                ):
                    tickets[label] = combo

            if not all(
                label in tickets
                for label in ("本線", "対抗", "穴")
            ):
                continue

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

            hit_labels = []

            for label in ("本線", "対抗", "穴"):
                if tickets[label] == actual:
                    hits[label] += 1
                    venue_stats[stadium_no][label] += 1
                    hit_labels.append(label)

            if hit_labels:
                hits["3点"] += 1
                venue_stats[stadium_no]["3点"] += 1

            axis = int(pred["axis"])

            if axis == actual[0]:
                axis_first += 1

            if axis in actual:
                axis_top3 += 1

            payout_amount = 0

            try:
                payout = get_payout(race)
            except Exception:
                payout = None

            if payout is not None:
                payout_combination = (
                    str(payout.get("combination", ""))
                    .replace("=", "-")
                    .replace(" ", "")
                )

                if payout_combination == combo_text(actual):
                    try:
                        payout_amount = int(
                            payout.get("amount", 0)
                        )
                    except Exception:
                        payout_amount = 0

            bet_amount = 300
            total_bet += bet_amount
            venue_stats[stadium_no]["投資"] += bet_amount

            if hit_labels:
                total_payout += payout_amount
                venue_stats[stadium_no]["払戻"] += payout_amount

            row_data = {
                "日付": day.strftime("%m/%d"),
                "会場": STADIUMS.get(
                    stadium_no,
                    str(stadium_no),
                ),
                "R": int(race_no),
                "本線": combo_text(tickets["本線"]),
                "対抗": combo_text(tickets["対抗"]),
                "穴": combo_text(tickets["穴"]),
                "結果": combo_text(actual),
                "本線的中": (
                    "○"
                    if tickets["本線"] == actual
                    else ""
                ),
                "対抗的中": (
                    "○"
                    if tickets["対抗"] == actual
                    else ""
                ),
                "穴的中": (
                    "○"
                    if tickets["穴"] == actual
                    else ""
                ),
                "払戻": int(payout_amount),
            }

            row_data.update(
                _build_analysis_data(
                    df,
                    tickets,
                    actual,
                )
            )

            rows.append(row_data)

        except Exception:
            continue

    n = len(rows)

    if n:
        three_hit_rate = hits["3点"] / n * 100
        main_hit_rate = hits["本線"] / n * 100
        counter_hit_rate = hits["対抗"] / n * 100
        hole_hit_rate = hits["穴"] / n * 100
        axis_first_rate = axis_first / n * 100
        axis_top3_rate = axis_top3 / n * 100
    else:
        three_hit_rate = 0.0
        main_hit_rate = 0.0
        counter_hit_rate = 0.0
        hole_hit_rate = 0.0
        axis_first_rate = 0.0
        axis_top3_rate = 0.0

    recovery_rate = (
        total_payout / total_bet * 100
        if total_bet > 0
        else 0.0
    )

    venue_rows = []

    for stadium_no in sorted(venue_stats):
        stats = venue_stats[stadium_no]
        count = int(stats["検証数"])

        if count <= 0:
            continue

        investment = int(stats["投資"])
        payout = int(stats["払戻"])

        venue_rows.append({
            "会場": STADIUMS.get(
                stadium_no,
                str(stadium_no),
            ),
            "検証数": count,
            "3点的中率": round(
                stats["3点"] / count * 100,
                2,
            ),
            "本線": round(
                stats["本線"] / count * 100,
                2,
            ),
            "対抗": round(
                stats["対抗"] / count * 100,
                2,
            ),
            "穴": round(
                stats["穴"] / count * 100,
                2,
            ),
            "投資": investment,
            "払戻": payout,
            "回収率": round(
                payout / investment * 100,
                2,
            ) if investment > 0 else 0.0,
        })

    venue_rows.sort(
        key=lambda row: (
            row["3点的中率"],
            row["検証数"],
        ),
        reverse=True,
    )

    summary = {
        "検証数": n,
        "3点的中率": round(three_hit_rate, 2),
        "本線的中率": round(main_hit_rate, 2),
        "対抗的中率": round(counter_hit_rate, 2),
        "穴的中率": round(hole_hit_rate, 2),
        "軸1着率": round(axis_first_rate, 2),
        "軸3着内率": round(axis_top3_rate, 2),
        "投資": int(total_bet),
        "払戻": int(total_payout),
        "回収率": round(recovery_rate, 2),
    }

    return summary, rows, venue_rows
