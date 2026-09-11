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
        return pd.Series(0.5, index=x.index)

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

    # 12.4%ベース
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

    exp_values = np.exp(scaled)
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

    return (
        0.045 * strength_gap
        + 0.025 * role
    )


def _select_main_counter(
    ranked,
    first_score,
    second_score,
    third_score,
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

    if original_axis != 5:

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

    axis = int(
        candidate_main[0][0]
    )

    same_axis = [
        item
        for item in ranked
        if int(item[0][0]) == axis
    ]

    if len(same_axis) < 2:

        if len(ranked) >= 2:
            return (
                candidate_main,
                ranked[1]
            )

        return (
            candidate_main,
            candidate_main
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
                "prob": float(probability),
                "raw_score": float(raw_score),
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
            candidate_main,
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
            if item[0] != main[0]
            and int(item[0][0]) == axis
        ]

        if fallback:
            counter = fallback[0]

    return (
        main,
        counter
    )


def _venue_profile(stadium_no):
    """
    会場別補正。
    
    強い会場を大きく優遇するのではなく、
    「同程度の候補なら少しだけ優先」するための
    非常に弱い補正。
    
    数値は今回の1000レース集計をもとにした実験値。
    """
    profiles = {
        # 3点的中率 上位
        7: 0.020,   # 蒲郡
        1: 0.015,   # 桐生
        20: 0.015,  # 若松
        22: 0.015,  # 福岡
        2: 0.015,   # 戸田

        # その他
        5: 0.010,   # 多摩川
        11: 0.010,  # びわこ
        14: 0.010,  # 鳴門
        13: 0.005,  # 尼崎
        18: 0.005,  # 宮島

        # 弱かった会場
        24: -0.015, # 大村
        9: -0.010,  # 津
        18: 0.005,  # 徳山は後述の実験では中立寄り
        16: -0.005, # 児島
        3: -0.005,  # 江戸川
    }

    try:
        stadium_no = int(stadium_no)
    except Exception:
        return 0.0

    return float(
        profiles.get(stadium_no, 0.0)
    )


def _apply_venue_adjustment(
    ranked,
    stadium_no,
):
    """
    会場補正はランキングを大きく崩さない。

    raw score が近い候補同士の場合だけ、
    会場傾向をわずかに反映する。
    """
    venue_bonus = _venue_profile(
        stadium_no
    )

    if abs(venue_bonus) < 1e-12:
        return ranked

    adjusted = []

    for item in ranked:
        combo = item[0]
        probability = float(item[1])
        raw_score = float(item[2])

        axis = int(combo[0])

        # 会場補正を全候補へ一律にかけず、
        # 1着軸側へ少しだけ反映。
        axis_bonus = venue_bonus

        if axis in (1, 2):
            axis_bonus *= 0.70
        elif axis in (3, 4, 5, 6):
            axis_bonus *= 0.85

        adjusted_score = (
            raw_score
            + axis_bonus
        )

        adjusted.append(
            (
                combo,
                probability,
                adjusted_score,
            )
        )

    adjusted.sort(
        key=lambda item: (
            item[2],
            item[1],
        ),
        reverse=True
    )

    return adjusted


def _select_hole(
    ranked,
    main,
    counter,
    first_score,
):
    main_combo = main[0]
    counter_combo = counter[0]

    # 本線・対抗を除外した全候補を対象。
    candidates = [
        item
        for item in ranked
        if item[0] != main_combo
        and item[0] != counter_combo
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
        alternative_axis = int(combo[0])

        axis_score = float(
            first_score[alternative_axis]
        )

        diversity_bonus = 0.0

        if alternative_axis != main_axis:
            diversity_bonus = 0.025

        hole_score = (
            raw_score
            + diversity_bonus
            + 0.10 * axis_score
        )

        candidate_rows.append(
            (
                float(hole_score),
                item,
            )
        )

    candidate_rows.sort(
        key=lambda item: (
            item[0],
            float(item[1][2]),
        ),
        reverse=True
    )

    return candidate_rows[0][1]


def predict(df, stadium_no=None):

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

    # 今回追加した変更はここだけ。
    # 会場補正を入れても、元のスコアから
    # 大きく離れた候補を無理に採用しない。
    ranked = _apply_venue_adjustment(
        ranked,
        stadium_no,
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
            for _,
            probability
            in first_ranking[:3]
        )
    )

    if axis_position < 3:
        axis_top3_probability = float(
            sum(
                probability
                for boat,
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
