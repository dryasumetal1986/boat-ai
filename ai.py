import itertools
import numpy as np
import pandas as pd


BOATS = (1, 2, 3, 4, 5, 6)


def combo_text(combo):
    """3連単の組み合わせを表示用文字列にする。"""
    return "-".join(str(int(x)) for x in combo)


def _norm_series(series, higher=True):
    x = pd.to_numeric(
        series,
        errors="coerce"
    ).fillna(0.0).astype(float)

    lo = float(x.min())
    hi = float(x.max())

    if hi - lo < 1e-12:
        return pd.Series(
            0.5,
            index=x.index
        )

    z = (x - lo) / (hi - lo)

    if higher:
        return z

    return 1.0 - z


def _prepare(df):
    x = (
        df.copy()
        .sort_values("boat")
        .reset_index(drop=True)
    )

    x["win_n"] = _norm_series(
        x["national_win_rate"]
    )

    x["win_l"] = _norm_series(
        x["local_win_rate"]
    )

    x["top2_n"] = _norm_series(
        x["national_top_2_percent"]
    )

    x["top3_n"] = _norm_series(
        x["national_top_3_percent"]
    )

    x["top2_l"] = _norm_series(
        x["local_top_2_percent"]
    )

    x["top3_l"] = _norm_series(
        x["local_top_3_percent"]
    )

    x["motor2"] = _norm_series(
        x["motor_top_2_percent"]
    )

    x["motor3"] = _norm_series(
        x["motor_top_3_percent"]
    )

    x["boat2"] = _norm_series(
        x["boat_top_2_percent"]
    )

    x["boat3"] = _norm_series(
        x["boat_top_3_percent"]
    )

    x["st"] = _norm_series(
        x["average_start_timing"],
        higher=False
    )

    exhibition = pd.to_numeric(
        x["exhibition_time"],
        errors="coerce"
    )

    valid_exhibition = exhibition[
        exhibition > 0
    ]

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
        pd.to_numeric(
            x["boat"],
            errors="coerce"
        )
    )

    x["course"] = (
        1.0
        - (course - 1.0) / 10.0
    ).clip(
        0.4,
        1.0
    )

    x["first_score"] = (
        0.24 * x["win_n"]
        + 0.13 * x["win_l"]
        + 0.13 * x["top2_n"]
        + 0.08 * x["top2_l"]
        + 0.10 * x["motor2"]
        + 0.06 * x["boat2"]
        + 0.12 * x["st"]
        + 0.08 * x["exh"]
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
    values = np.asarray(
        values,
        dtype=float
    )

    if len(values) == 0:
        return np.array([])

    temperature = max(
        float(temperature),
        0.001
    )

    scaled = values / temperature
    scaled -= np.max(scaled)

    exp_values = np.exp(
        scaled
    )

    total = exp_values.sum()

    if total <= 0:
        return np.ones(
            len(values)
        ) / len(values)

    return exp_values / total


def _combo_score(
    a,
    b,
    c,
    first_score,
    second_score,
    third_score,
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
    third_score,
):
    """
    第1実験：
    2着・3着の「役割差」を少しだけ強める。

    軸選択・基本スコア・穴選択は変更しない。
    現行12.2%版との差を最小限にする。
    """

    second_strength = float(
        second_score[second_boat]
    )

    third_strength = float(
        third_score[third_boat]
    )

    # その艇自身が「2着向き」か
    second_role = float(
        second_score[second_boat]
        - third_score[second_boat]
    )

    # その艇自身が「3着向き」か
    third_role = float(
        third_score[third_boat]
        - second_score[third_boat]
    )

    second_role = float(
        np.clip(
            second_role,
            -0.30,
            0.30
        )
    )

    third_role = float(
        np.clip(
            third_role,
            -0.30,
            0.30
        )
    )

    # 2着艇の2着適性と
    # 3着艇の3着適性を評価
    role = (
        second_role
        + third_role
    ) / 2.0

    strength_gap = (
        second_strength
        - third_strength
    )

    strength_gap = float(
        np.clip(
            strength_gap,
            -0.30,
            0.30
        )
    )

    # 現行12.2%版：
    # 0.035 * strength_gap
    # + 0.025 * role
    #
    # 第1実験では「役割差」を少しだけ強める。
    return (
        0.035 * strength_gap
        + 0.032 * role
    )


def _select_main_counter(
    ranked,
    first_score,
    second_score,
    third_score,
):
    """
    今回12.2%版の本線・対抗ロジックを維持。
    """

    if not ranked:
        raise ValueError(
            "予想候補がありません。"
        )

    original_main = ranked[0]

    axis = int(
        original_main[0][0]
    )

    same_axis = [
        item
        for item in ranked
        if int(item[0][0]) == axis
    ]

    if len(same_axis) < 2:
        if len(ranked) >= 2:
            return (
                original_main,
                ranked[1]
            )

        return (
            original_main,
            original_main
        )

    pool = same_axis[:10]

    adjusted = []

    for combo, probability, raw_score in pool:

        _, second_boat, third_boat = combo

        bonus = _ordering_bonus(
            second_boat,
            third_boat,
            second_score,
            third_score,
        )

        adjusted_score = (
            float(raw_score)
            + float(bonus)
        )

        adjusted.append(
            {
                "combo": combo,
                "prob": float(
                    probability
                ),
                "raw_score": float(
                    raw_score
                ),
                "adjusted_score": adjusted_score,
            }
        )

    adjusted.sort(
        key=lambda item: (
            item["adjusted_score"],
            item["raw_score"],
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
        return (
            original_main,
            same_axis[1]
        )

    counter_candidate = (
        counter_candidates[0]
    )

    main = (
        main_candidate["combo"],
        main_candidate["prob"],
        main_candidate["raw_score"],
    )

    counter = (
        counter_candidate["combo"],
        counter_candidate["prob"],
        counter_candidate["raw_score"],
    )

    original_raw_score = float(
        original_main[2]
    )

    if (
        main_candidate["raw_score"]
        < original_raw_score - 0.045
    ):
        main = original_main

        fallback = [
            item
            for item in ranked
            if item[0] != main[0]
            and int(item[0][0]) == axis
        ]

        if fallback:
            counter = fallback[0]

    return (
        main,
        counter
    )


def _select_hole(
    ranked,
    main,
    counter,
    first_score,
):
    """
    前回ベストだった穴ロジック。
    今回も変更しない。
    """

    main_combo = main[0]
    counter_combo = counter[0]

    main_axis = int(
        main_combo[0]
    )

    non_axis_boats = [
        boat
        for boat in BOATS
        if boat != main_axis
    ]

    ranked_first = sorted(
        non_axis_boats,
        key=lambda boat: first_score[boat],
        reverse=True,
    )

    if (
        1 != main_axis
        and 1 not in ranked_first
        and ranked_first
    ):
        top_score = float(
            first_score[
                ranked_first[0]
            ]
        )

        if (
            float(first_score[1])
            >= top_score - 0.08
        ):
            ranked_first.append(1)

    candidate_rows = []

    for alternative_axis in ranked_first[:4]:

        candidates = [
            item
            for item in ranked
            if int(item[0][0])
            == int(alternative_axis)
            and item[0] != main_combo
            and item[0] != counter_combo
        ]

        if not candidates:
            continue

        best = candidates[0]

        candidate_score = (
            0.70
            * float(
                first_score[
                    alternative_axis
                ]
            )
            + 0.30
            * float(best[2])
        )

        candidate_rows.append(
            (
                candidate_score,
                best,
            )
        )

    if not candidate_rows:

        fallback = [
            item
            for item in ranked
            if item[0] != main_combo
            and item[0] != counter_combo
        ]

        if fallback:
            return fallback[0]

        return ranked[1]

    candidate_rows.sort(
        key=lambda item: item[0],
        reverse=True
    )

    for _, candidate in candidate_rows:

        if (
            candidate[0] != main_combo
            and candidate[0] != counter_combo
        ):
            return candidate

    return candidate_rows[0][1]


def predict(df):
    """
    6艇の出走表から
    本線・対抗・穴の3点を予想。
    """

    if (
        not isinstance(
            df,
            pd.DataFrame
        )
        or len(df) != 6
    ):
        raise ValueError(
            "6艇分の出走表が必要です。"
        )

    boats = pd.to_numeric(
        df["boat"],
        errors="coerce"
    )

    if boats.isna().any():
        raise ValueError(
            "艇番データが不正です。"
        )

    boats = set(
        boats.astype(int)
    )

    if boats != set(BOATS):
        raise ValueError(
            "艇番が1〜6になっていません。"
        )

    x = _prepare(df)

    first_score = dict(
        zip(
            x["boat"].astype(int),
            x["first_score"].astype(float),
        )
    )

    second_score = dict(
        zip(
            x["boat"].astype(int),
            x["second_score"].astype(float),
        )
    )

    third_score = dict(
        zip(
            x["boat"].astype(int),
            x["third_score"].astype(float),
        )
    )

    combos = []

    for a, b, c in itertools.permutations(
        BOATS,
        3
    ):

        score = _combo_score(
            a,
            b,
            c,
            first_score,
            second_score,
            third_score,
        )

        combos.append(
            (
                (a, b, c),
                score,
            )
        )

    raw_scores = np.array(
        [
            score
            for _, score in combos
        ],
        dtype=float,
    )

    probabilities = _softmax(
        raw_scores,
        temperature=0.075,
    )

    ranked = sorted(
        [
            (
                combo,
                float(probability),
                float(score),
            )
            for (
                combo,
                score
            ), probability
            in zip(
                combos,
                probabilities
            )
        ],
        key=lambda item: item[1],
        reverse=True,
    )

    main, counter = (
        _select_main_counter(
            ranked,
            first_score,
            second_score,
            third_score,
        )
    )

    hole = _select_hole(
        ranked,
        main,
        counter,
        first_score,
    )

    used = {
        main[0],
        counter[0],
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
            hole,
        ]:

            if item[0] not in [
                u[0]
                for u in unique
            ]:
                unique.append(item)

        for item in ranked:

            if len(unique) >= 3:
                break

            if item[0] not in [
                u[0]
                for u in unique
            ]:
                unique.append(item)

        if len(unique) >= 3:
            main = unique[0]
            counter = unique[1]
            hole = unique[2]

    first_values = [
        first_score[boat]
        for boat in BOATS
    ]

    first_probabilities = _softmax(
        first_values,
        temperature=0.10,
    )

    first_ranking = sorted(
        zip(
            BOATS,
            first_probabilities
        ),
        key=lambda item: item[1],
        reverse=True,
    )

    axis = int(
        first_ranking[0][0]
    )

    axis_top3_probability = float(
        sum(
            probability
            for _,
            probability
            in first_ranking[:3]
        )
    )

    margin = float(
        first_ranking[0][1]
        - first_ranking[1][1]
    )

    confidence = (
        62.0
        + margin * 220.0
    )

    confidence = min(
        95.0,
        max(
            55.0,
            confidence
        )
    )

    tickets = [
        {
            "label": "本線",
            "combo": main[0],
            "prob": float(main[1]),
        },
        {
            "label": "対抗",
            "combo": counter[0],
            "prob": float(counter[1]),
        },
        {
            "label": "穴",
            "combo": hole[0],
            "prob": float(hole[1]),
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
