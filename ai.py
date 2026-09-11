import itertools
import numpy as np
import pandas as pd


BOATS = (1, 2, 3, 4, 5, 6)


def combo_text(combo):
    """3連単の組み合わせを表示用文字列にする。"""
    return "-".join(
        str(int(x))
        for x in combo
    )


def _norm_series(
    series,
    higher=True
):
    x = pd.to_numeric(
        series,
        errors="coerce"
    ).fillna(
        0.0
    ).astype(float)

    lo = float(
        x.min()
    )

    hi = float(
        x.max()
    )

    if hi - lo < 1e-12:
        return pd.Series(
            0.5,
            index=x.index
        )

    z = (
        x - lo
    ) / (
        hi - lo
    )

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

    if len(
        valid_exhibition
    ) > 0:

        exhibition_median = float(
            valid_exhibition.median()
        )

    else:

        exhibition_median = 1.0

    exhibition = (
        exhibition
        .replace(
            0,
            np.nan
        )
        .fillna(
            exhibition_median
        )
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
        - (
            course - 1.0
        ) / 10.0
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


def _softmax(
    values,
    temperature=0.075
):
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

    scaled = (
        values / temperature
    )

    scaled -= np.max(
        scaled
    )

    exp_values = np.exp(
        scaled
    )

    total = exp_values.sum()

    if total <= 0:

        return np.ones(
            len(values)
        ) / len(values)

    return (
        exp_values / total
    )


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

    return float(
        score
    )


def _ordering_bonus(
    second_boat,
    third_boat,
    second_score,
    third_score,
):
    second_strength = float(
        second_score[
            second_boat
        ]
    )

    third_strength = float(
        third_score[
            third_boat
        ]
    )

    second_role = float(
        second_score[
            second_boat
        ]
        - third_score[
            second_boat
        ]
    )

    third_role = float(
        third_score[
            third_boat
        ]
        - second_score[
            third_boat
        ]
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


def _select_three_tickets(
    ranked,
    first_score,
):
    """
    3点選択。

    基本はモデル順位。
    3点が同一買い目にならないようにする。
    """

    if not ranked:
        raise ValueError(
            "予想候補がありません。"
        )

    main = ranked[0]

    selected = [
        main
    ]

    counter = None

    for item in ranked:

        if item[0] == main[0]:
            continue

        counter = item
        break

    if counter is None:

        raise ValueError(
            "対抗候補を生成できません。"
        )

    selected.append(
        counter
    )

    main_axis = int(
        main[0][0]
    )

    counter_axis = int(
        counter[0][0]
    )

    hole = None

    for item in ranked:

        combo = item[0]

        if combo in [
            main[0],
            counter[0],
        ]:
            continue

        axis = int(
            combo[0]
        )

        if (
            main_axis == counter_axis
            and axis != main_axis
        ):

            hole = item
            break

    if hole is None:

        for item in ranked:

            if item[0] in [
                main[0],
                counter[0],
            ]:
                continue

            hole = item
            break

    if hole is None:

        raise ValueError(
            "穴候補を生成できません。"
        )

    selected.append(
        hole
    )

    unique = []

    for item in selected:

        if item[0] not in [
            row[0]
            for row in unique
        ]:

            unique.append(
                item
            )

    if len(unique) < 3:

        for item in ranked:

            if item[0] in [
                row[0]
                for row in unique
            ]:
                continue

            unique.append(
                item
            )

            if len(unique) >= 3:
                break

    if len(unique) < 3:

        raise ValueError(
            "3点を生成できません。"
        )

    return (
        unique[0],
        unique[1],
        unique[2],
    )


def _select_axis_first(
    ranked,
    first_score,
    current_main,
):
    """
    第2実験。

    1着艇だけを first_score で再評価する。

    3連単の候補順位を完全に無視するのではなく、
    first_score 1位の艇を軸候補として採用する。

    ただし、現在の本線より大幅に弱い場合は
    元の本線を維持する。

    変更幅を小さくして過学習を抑える。
    """

    if not ranked:
        return current_main

    if not first_score:
        return current_main

    first_ranking = sorted(
        first_score.items(),
        key=lambda item: (
            float(item[1]),
            -int(item[0]),
        ),
        reverse=True,
    )

    if not first_ranking:
        return current_main

    top_axis = int(
        first_ranking[0][0]
    )

    current_axis = int(
        current_main[0][0]
    )

    if top_axis == current_axis:
        return current_main

    current_first = float(
        first_score.get(
            current_axis,
            0.0
        )
    )

    top_first = float(
        first_score.get(
            top_axis,
            0.0
        )
    )

    first_gap = (
        top_first
        - current_first
    )

    # 1着専用スコアで明確に上なら候補を探す
    if first_gap < 0.035:
        return current_main

    top_candidates = [
        item
        for item in ranked
        if int(item[0][0]) == top_axis
    ]

    if not top_candidates:
        return current_main

    best_top = top_candidates[0]

    current_raw = float(
        current_main[2]
    )

    top_raw = float(
        best_top[2]
    )

    # 3連単としての強さを大きく犠牲にしない
    if top_raw < (
        current_raw - 0.035
    ):
        return current_main

    return best_top


def _venue_profile(
    stadium_no
):
    """
    会場別補正。

    17 = 宮島
    18 = 徳山
    """

    profiles = {

        # 3点的中率上位
        7: 0.020,
        1: 0.015,
        20: 0.015,
        22: 0.015,
        2: 0.015,

        # その他
        5: 0.010,
        11: 0.010,
        14: 0.010,
        13: 0.005,

        # 宮島
        17: 0.005,

        # 徳山
        18: 0.005,

        # 弱かった会場
        24: -0.015,
        9: -0.010,
        16: -0.005,
        3: -0.005,
    }

    try:

        stadium_no = int(
            stadium_no
        )

    except Exception:

        return 0.0

    return float(
        profiles.get(
            stadium_no,
            0.0
        )
    )


def _apply_venue_adjustment(
    ranked,
    stadium_no
):
    venue_bonus = _venue_profile(
        stadium_no
    )

    if abs(
        venue_bonus
    ) < 1e-12:

        return ranked

    adjusted = []

    for item in ranked:

        combo = item[0]

        probability = float(
            item[1]
        )

        raw_score = float(
            item[2]
        )

        axis = int(
            combo[0]
        )

        axis_bonus = venue_bonus

        if axis in (
            1,
            2
        ):

            axis_bonus *= 0.70

        elif axis in (
            3,
            4,
            5,
            6
        ):

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


def predict(
    df,
    stadium_no=None
):
    """
    3〜6艇に対応。
    """

    if not isinstance(
        df,
        pd.DataFrame
    ):

        raise ValueError(
            "出走表データが不正です。"
        )

    if not (
        3 <= len(df) <= 6
    ):

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

    if not (
        3 <= len(active_boats) <= 6
    ):

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

    x = _prepare(
        df
    )

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

    # =====================================================
    # 3連単候補生成
    # =====================================================

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
            third_score,
        )

        combos.append(
            (
                (a, b, c),
                score,
            )
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

    # =====================================================
    # 会場補正
    # =====================================================

    ranked = _apply_venue_adjustment(
        ranked,
        stadium_no,
    )

    # =====================================================
    # 3点選択
    # =====================================================

    main, counter, hole = (
        _select_three_tickets(
            ranked,
            first_score,
        )
    )

    # =====================================================
    # 第2実験
    #
    # 軸だけ first_score で再評価
    # =====================================================

    original_main = main

    main = _select_axis_first(
        ranked,
        first_score,
        main,
    )

    # =====================================================
    # 本線変更後の重複防止
    # =====================================================

    if main[0] == counter[0]:

        alternatives = [
            item
            for item in ranked
            if item[0] != main[0]
            and item[0] != hole[0]
        ]

        if alternatives:
            counter = alternatives[0]

    if main[0] == hole[0]:

        alternatives = [
            item
            for item in ranked
            if item[0] != main[0]
            and item[0] != counter[0]
        ]

        if alternatives:
            hole = alternatives[0]

    if counter[0] == hole[0]:

        alternatives = [
            item
            for item in ranked
            if item[0] != main[0]
            and item[0] != counter[0]
        ]

        if alternatives:
            hole = alternatives[0]

    # =====================================================
    # 最終3点重複防止
    # =====================================================

    selected = [
        main,
        counter,
        hole,
    ]

    unique = []

    for item in selected:

        if item[0] in [
            row[0]
            for row in unique
        ]:
            continue

        unique.append(
            item
        )

    if len(unique) < 3:

        for item in ranked:

            if item[0] in [
                row[0]
                for row in unique
            ]:
                continue

            unique.append(
                item
            )

            if len(unique) >= 3:
                break

    if len(unique) < 3:

        raise ValueError(
            "3点を生成できません。"
        )

    main = unique[0]
    counter = unique[1]
    hole = unique[2]

    # =====================================================
    # 1着確率
    # =====================================================

    first_values = [
        first_score[boat]
        for boat in active_boats
    ]

    first_probabilities = _softmax(
        first_values,
        temperature=0.10,
    )

    first_ranking = sorted(
        zip(
            active_boats,
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
        axis_rank.index(
            axis
        )
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

    # =====================================================
    # 信頼度
    # =====================================================

    if len(
        first_ranking
    ) >= 2:

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
        max(
            55.0,
            confidence
        )
    )

    tickets = [
        {
            "label": "本線",
            "combo": main[0],
            "prob": float(
                main[1]
            ),
        },
        {
            "label": "対抗",
            "combo": counter[0],
            "prob": float(
                counter[1]
            ),
        },
        {
            "label": "穴",
            "combo": hole[0],
            "prob": float(
                hole[1]
            ),
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
        "axis_top3": (
            axis_top3_probability
        ),
        "all_combos": ranked,
        "df": x,
    }
