import itertools
import numpy as np
import pandas as pd

BOATS = (1, 2, 3, 4, 5, 6)


def combo_text(combo):
    return "-".join(str(int(x)) for x in combo)


def _norm_series(series, higher=True):
    x = pd.to_numeric(series, errors="coerce").fillna(0.0).astype(float)
    lo = float(x.min())
    hi = float(x.max())

    if hi - lo < 1e-12:
        return pd.Series(0.5, index=x.index)

    z = (x - lo) / (hi - lo)

    if higher:
        return z

    return 1.0 - z


def _prepare(df):
    x = df.copy().sort_values("boat").reset_index(drop=True)

    x["win_n"] = _norm_series(x["national_win_rate"])
    x["win_l"] = _norm_series(x["local_win_rate"])
    x["top2_n"] = _norm_series(x["national_top_2_percent"])
    x["top3_n"] = _norm_series(x["national_top_3_percent"])
    x["top2_l"] = _norm_series(x["local_top_2_percent"])
    x["top3_l"] = _norm_series(x["local_top_3_percent"])
    x["motor2"] = _norm_series(x["motor_top_2_percent"])
    x["motor3"] = _norm_series(x["motor_top_3_percent"])
    x["boat2"] = _norm_series(x["boat_top_2_percent"])
    x["boat3"] = _norm_series(x["boat_top_3_percent"])
    x["st"] = _norm_series(
        x["average_start_timing"],
        higher=False
    )

    exhibition = pd.to_numeric(
        x["exhibition_time"],
        errors="coerce"
    )

    valid_exhibition = exhibition[exhibition > 0]

    if len(valid_exhibition) > 0:
        exhibition_median = float(
            valid_exhibition.median()
        )
    else:
        exhibition_median = 1.0

    exhibition = (
        exhibition
        .replace(0, np.nan)
        .fillna(exhibition_median)
    )

    x["exh"] = _norm_series(
        exhibition,
        higher=False
    )

    course = pd.to_numeric(
        x["course_number"],
        errors="coerce"
    )

    course = course.fillna(
        pd.to_numeric(x["boat"], errors="coerce")
    )

    x["course"] = (
        1.0 - (course - 1.0) / 10.0
    ).clip(0.4, 1.0)

    x["first_score"] = (
        0.22 * x["win_n"]
        + 0.13 * x["win_l"]
        + 0.13 * x["top2_n"]
        + 0.08 * x["top2_l"]
        + 0.10 * x["motor2"]
        + 0.06 * x["boat2"]
        + 0.12 * x["st"]
        + 0.10 * x["exh"]
        + 0.06 * x["course"]
    )

    x["second_score"] = (
        0.18 * x["top2_n"]
        + 0.14 * x["top2_l"]
        + 0.16 * x["top3_n"]
        + 0.10 * x["top3_l"]
        + 0.14 * x["motor2"]
        + 0.08 * x["motor3"]
        + 0.10 * x["boat2"]
        + 0.10 * x["st"]
    )

    x["third_score"] = (
        0.18 * x["top3_n"]
        + 0.14 * x["top3_l"]
        + 0.16 * x["motor3"]
        + 0.12 * x["boat3"]
        + 0.12 * x["top2_n"]
        + 0.10 * x["top2_l"]
        + 0.10 * x["st"]
        + 0.08 * x["exh"]
    )

    return x


def _softmax(values, temperature=0.075):
    values = np.asarray(values, dtype=float)

    if len(values) == 0:
        return np.array([])

    temperature = max(float(temperature), 0.001)

    scaled = values / temperature
    scaled -= np.max(scaled)

    exp_values = np.exp(scaled)
    total = exp_values.sum()

    if total <= 0:
        return np.ones(len(values)) / len(values)

    return exp_values / total


def _combo_score(
    a,
    b,
    c,
    first_score,
    second_score,
    third_score
):
    score = (
        1.00 * first_score[a]
        + 0.72 * second_score[b]
        + 0.58 * third_score[c]
    )

    if a == 1:
        score += 0.055
    elif a == 2:
        score += 0.025

    if b == 1:
        score += 0.020

    return float(score)


def _ordering_bonus(
    second_boat,
    third_boat,
    second_score,
    third_score
):
    second_strength = float(
        second_score[second_boat]
    )

    third_strength = float(
        third_score[third_boat]
    )

    second_role = float(
        second_score[second_boat]
        - third_score[second_boat]
    )

    third_role = float(
        third_score[third_boat]
        - second_score[third_boat]
    )

    second_role = float(
        np.clip(second_role, -0.30, 0.30)
    )

    third_role = float(
        np.clip(third_role, -0.30, 0.30)
    )

    role = (
        second_role + third_role
    ) / 2.0

    strength_gap = float(
        np.clip(
            second_strength - third_strength,
            -0.30,
            0.30
        )
    )

    return (
        0.045 * strength_gap
        + 0.025 * role
    )


def _select_main_counter(
    ranked,
    first_score,
    second_score,
    third_score
):
    if not ranked:
        raise ValueError(
            "予想候補がありません。"
        )

    original_main = ranked[0]
    original_axis = int(
        original_main[0][0]
    )

    candidate_main = original_main

    if (
        original_axis != 5
        and 5 in first_score
    ):
        current_axis_score = float(
            first_score[original_axis]
        )

        boat5_score = float(
            first_score[5]
        )

        axis_gap = (
            current_axis_score
            - boat5_score
        )

        if axis_gap <= 0.025:
            boat5_candidates = [
                item
                for item in ranked
                if int(item[0][0]) == 5
            ]

            if boat5_candidates:
                best_boat5 = boat5_candidates[0]

                original_raw = float(
                    original_main[2]
                )

                boat5_raw = float(
                    best_boat5[2]
                )

                if (
                    boat5_raw
                    >= original_raw - 0.035
                ):
                    candidate_main = best_boat5

    axis = int(candidate_main[0][0])

    same_axis = [
        item
        for item in ranked
        if int(item[0][0]) == axis
    ]

    if len(same_axis) < 2:
        if len(ranked) >= 2:
            return candidate_main, ranked[1]

        return candidate_main, candidate_main

    pool = same_axis[:10]

    adjusted = []

    for combo, probability, raw_score in pool:
        _, second_boat, third_boat = combo

        bonus = _ordering_bonus(
            second_boat,
            third_boat,
            second_score,
            third_score
        )

        adjusted_score = (
            float(raw_score)
            + float(bonus)
        )

        adjusted.append({
            "combo": combo,
            "prob": float(probability),
            "raw_score": float(raw_score),
            "adjusted_score": adjusted_score,
        })

    adjusted.sort(
        key=lambda item: (
            item["adjusted_score"],
            item["raw_score"]
        ),
        reverse=True
    )

    main_candidate = adjusted[0]

    counter_candidates = [
        item
        for item in adjusted
        if item["combo"]
        != main_candidate["combo"]
    ]

    if not counter_candidates:
        return candidate_main, same_axis[1]

    counter_candidate = counter_candidates[0]

    main = (
        main_candidate["combo"],
        main_candidate["prob"],
        main_candidate["raw_score"]
    )

    counter = (
        counter_candidate["combo"],
        counter_candidate["prob"],
        counter_candidate["raw_score"]
    )

    original_raw_score = float(
        candidate_main[2]
    )

    if (
        main_candidate["raw_score"]
        < original_raw_score - 0.045
    ):
        main = candidate_main

        fallback = [
            item
            for item in ranked
            if (
                item[0] != main[0]
                and int(item[0][0]) == axis
            )
        ]

        if fallback:
            counter = fallback[0]

    return main, counter


def _venue_profile(stadium_no):
    profiles = {
        7: 0.020,
        1: 0.015,
        20: 0.015,
        22: 0.015,
        2: 0.015,
        5: 0.010,
        11: 0.010,
        14: 0.010,
        13: 0.005,
        17: 0.005,
        18: 0.005,
        24: -0.015,
        9: -0.010,
        16: -0.005,
        3: -0.005,
    }

    try:
        stadium_no = int(stadium_no)
    except Exception:
        return 0.0

    return float(
        profiles.get(stadium_no, 0.0)
    )


def _venue_axis_bonus(
    stadium_no,
    axis
):
    """
    会場 × 軸番号の弱い補正。

    補正値は小さくし、
    14.0%ベースの予想構造を
    大きく変えない。
    """

    try:
        stadium_no = int(stadium_no)
        axis = int(axis)
    except Exception:
        return 0.0

    axis_profiles = {
        # 桐生
        # 外枠軸を少し抑える
        1: {
            4: -0.008,
            5: -0.012,
            6: -0.012,
        },

        # 若松
        # 2号艇軸を少し抑える
        20: {
            2: -0.012,
        },

        # 蒲郡
        # 1号艇軸を少し強化
        7: {
            1: 0.010,
        },

        # 福岡
        # 1号艇軸を少し強化
        22: {
            1: 0.010,
        },

        # 芦屋
        # 1号艇軸を少し強化
        21: {
            1: 0.010,
        },

        # 津
        # 2・5号艇軸を少し抑える
        9: {
            2: -0.010,
            5: -0.010,
        },
    }

    return float(
        axis_profiles
        .get(stadium_no, {})
        .get(axis, 0.0)
    )


def _apply_venue_adjustment(
    ranked,
    stadium_no
):
    venue_bonus = _venue_profile(
        stadium_no
    )

    adjusted = []

    for item in ranked:
        combo = item[0]
        probability = float(item[1])
        raw_score = float(item[2])

        axis = int(combo[0])

        axis_bonus = venue_bonus

        if axis in (1, 2):
            axis_bonus *= 0.70
        elif axis in (3, 4, 5, 6):
            axis_bonus *= 0.85

        # 今回の実験部分
        venue_axis_bonus = _venue_axis_bonus(
            stadium_no,
            axis
        )

        adjusted_score = (
            raw_score
            + axis_bonus
            + venue_axis_bonus
        )

        adjusted.append((
            combo,
            probability,
            adjusted_score
        ))

    adjusted.sort(
        key=lambda item: (
            item[2],
            item[1]
        ),
        reverse=True
    )

    return adjusted


def _select_hole(
    ranked,
    main,
    counter,
    first_score,
    third_score
):
    main_combo = main[0]
    counter_combo = counter[0]

    candidates = [
        item
        for item in ranked
        if (
            item[0] != main_combo
            and item[0] != counter_combo
        )
    ]

    if not candidates:
        return ranked[1]

    main_axis = int(
        main_combo[0]
    )

    candidate_rows = []

    for item in candidates:
        combo = item[0]

        raw_score = float(item[2])

        alternative_axis = int(
            combo[0]
        )

        second_boat = int(combo[1])
        third_boat = int(combo[2])

        axis_score = float(
            first_score[alternative_axis]
        )

        third_score_value = float(
            third_score[third_boat]
        )

        diversity_bonus = 0.0

        if alternative_axis != main_axis:
            diversity_bonus = 0.025

        third_boat_bonus = 0.0

        if third_boat == 2:
            third_boat_bonus = 0.018

        third_fit_bonus = 0.035 * float(
            np.clip(
                first_score[third_boat]
                - first_score[second_boat],
                -0.20,
                0.20
            )
        )

        third_strength_bonus = (
            0.035 * third_score_value
        )

        hole_score = (
            raw_score
            + diversity_bonus
            + 0.10 * axis_score
            + third_boat_bonus
            + third_fit_bonus
            + third_strength_bonus
        )

        candidate_rows.append((
            float(hole_score),
            item
        ))

    candidate_rows.sort(
        key=lambda item: (
            item[0],
            float(item[1][2])
        ),
        reverse=True
    )

    return candidate_rows[0][1]


def predict(df, stadium_no=None):
    if not isinstance(df, pd.DataFrame):
        raise ValueError(
            "出走表データが不正です。"
        )

    if not (3 <= len(df) <= 6):
        raise ValueError(
            "3〜6艇分の出走表が必要です。"
        )

    boats_series = pd.to_numeric(
        df["boat"],
        errors="coerce"
    )

    if boats_series.isna().any():
        raise ValueError(
            "艇番データが不正です。"
        )

    active_boats = tuple(
        sorted(
            set(
                boats_series.astype(int)
            )
        )
    )

    if not (3 <= len(active_boats) <= 6):
        raise ValueError(
            "予想対象艇数が不正です。"
        )

    if not all(
        1 <= boat <= 6
        for boat in active_boats
    ):
        raise ValueError(
            "艇番が1〜6になっていません。"
        )

    x = _prepare(df)

    first_score = dict(
        zip(
            x["boat"].astype(int),
            x["first_score"].astype(float)
        )
    )

    second_score = dict(
        zip(
            x["boat"].astype(int),
            x["second_score"].astype(float)
        )
    )

    third_score = dict(
        zip(
            x["boat"].astype(int),
            x["third_score"].astype(float)
        )
    )

    combos = []

    for a, b, c in itertools.permutations(
        active_boats,
        3
    ):
        score = _combo_score(
            a,
            b,
            c,
            first_score,
            second_score,
            third_score
        )

        combos.append(
            ((a, b, c), score)
        )

    if not combos:
        raise ValueError(
            "3連単候補を生成できません。"
        )

    raw_scores = np.array(
        [
            score
            for _, score in combos
        ],
        dtype=float
    )

    probabilities = _softmax(
        raw_scores,
        temperature=0.075
    )

    ranked = sorted(
        [
            (
                combo,
                float(probability),
                float(score)
            )
            for (combo, score),
            probability
            in zip(
                combos,
                probabilities
            )
        ],
        key=lambda item: item[1],
        reverse=True
    )

    ranked = _apply_venue_adjustment(
        ranked,
        stadium_no
    )

    main, counter = _select_main_counter(
        ranked,
        first_score,
        second_score,
        third_score
    )

    hole = _select_hole(
        ranked,
        main,
        counter,
        first_score,
        third_score
    )

    used = {
        main[0],
        counter[0]
    }

    if hole[0] in used:
        alternatives = [
            item
            for item in ranked
            if item[0] not in used
        ]

        if alternatives:
            hole = alternatives[0]

    if (
        main[0] == counter[0]
        or main[0] == hole[0]
        or counter[0] == hole[0]
    ):
        unique = []

        for item in [
            main,
            counter,
            hole
        ]:
            if item[0] not in [
                u[0] for u in unique
            ]:
                unique.append(item)

        for item in ranked:
            if len(unique) >= 3:
                break

            if item[0] not in [
                u[0] for u in unique
            ]:
                unique.append(item)

        if len(unique) >= 3:
            main = unique[0]
            counter = unique[1]
            hole = unique[2]

    first_values = [
        first_score[boat]
        for boat in active_boats
    ]

    first_probabilities = _softmax(
        first_values,
        temperature=0.10
    )

    first_ranking = sorted(
        zip(
            active_boats,
            first_probabilities
        ),
        key=lambda item: item[1],
        reverse=True
    )

    axis = int(
        main[0][0]
    )

    axis_rank = [
        boat
        for boat, _
        in first_ranking
    ]

    axis_position = (
        axis_rank.index(axis)
        if axis in axis_rank
        else 0
    )

    axis_top3_probability = float(
        sum(
            probability
            for boat, probability
            in first_ranking[:3]
        )
    )

    if axis_position < 3:
        axis_top3_probability = float(
            sum(
                probability
                for boat, probability
                in first_ranking[:3]
            )
        )

    if len(first_ranking) >= 2:
        margin = float(
            first_ranking[0][1]
            - first_ranking[1][1]
        )
    else:
        margin = 0.0

    confidence = (
        62.0
        + margin * 220.0
    )

    confidence = min(
        95.0,
        max(55.0, confidence)
    )

    tickets = [
        {
            "label": "本線",
            "combo": main[0],
            "prob": float(main[1])
        },
        {
            "label": "対抗",
            "combo": counter[0],
            "prob": float(counter[1])
        },
        {
            "label": "穴",
            "combo": hole[0],
            "prob": float(hole[1])
        },
    ]

    return {
        "tickets": tickets,
        "ranking": ranked,
        "confidence": round(
            confidence,
            1
        ),
        "axis": axis,
        "axis_top3": axis_top3_probability,
        "all_combos": ranked,
        "df": x,
    }
