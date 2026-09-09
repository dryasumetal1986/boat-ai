import itertools

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier


FEATURES = [
    "枠",
    "展示進入",
    "全国勝率",
    "全国2連率",
    "全国3連率",
    "当地勝率",
    "当地2連率",
    "モーター2連率",
    "平均ST",
    "展示ST",
    "展示タイム",
    "場",
]


def _num(value, default=0.0):

    try:

        if value is None:
            return default

        text = str(value).strip()

        if text in (
            "",
            "-",
            "--",
            "None",
            "null",
        ):
            return default

        text = text.replace("%", "")
        text = text.replace("秒", "")

        return float(text)

    except Exception:

        return default


def _prepare_features(df):

    work = df.copy()

    for col in FEATURES:

        if col not in work.columns:
            work[col] = 0.0

        work[col] = pd.to_numeric(
            work[col],
            errors="coerce",
        ).fillna(0.0)

    return work[FEATURES]


def _ability_score(df):

    work = df.copy()

    for col in FEATURES:

        if col not in work.columns:
            work[col] = 0.0

        work[col] = pd.to_numeric(
            work[col],
            errors="coerce",
        ).fillna(0.0)

    score = np.zeros(len(work))

    score += (
        work["全国勝率"] * 0.28
        + work["全国2連率"] * 0.10
        + work["全国3連率"] * 0.06
    )

    score += (
        work["当地勝率"] * 0.13
        + work["当地2連率"] * 0.07
    )

    score += (
        work["モーター2連率"] * 0.12
    )

    return score


def _exhibition_score(df):

    work = df.copy()

    for col in [
        "枠",
        "展示進入",
        "平均ST",
        "展示ST",
        "展示タイム",
    ]:

        if col not in work.columns:
            work[col] = 0.0

        work[col] = pd.to_numeric(
            work[col],
            errors="coerce",
        ).fillna(0.0)

    score = np.zeros(len(work))

    exhibition_st = work["展示ST"]

    valid_st = exhibition_st[
        exhibition_st > 0
    ]

    if len(valid_st):

        score += (
            valid_st.mean()
            - exhibition_st
        ) * 35.0

    avg_st = work["平均ST"]

    valid_avg = avg_st[
        avg_st > 0
    ]

    if len(valid_avg):

        score += (
            valid_avg.mean()
            - avg_st
        ) * 18.0

    exhibition_time = work["展示タイム"]

    valid_time = exhibition_time[
        exhibition_time > 0
    ]

    if len(valid_time):

        # 展示タイムは小さいほど良い
        score += (
            valid_time.mean()
            - exhibition_time
        ) * 8.0

    score += (
        work["枠"]
        - work["展示進入"]
    ) * 1.8

    return score


def _course_score(df):

    work = df.copy()

    work["枠"] = pd.to_numeric(
        work["枠"],
        errors="coerce",
    ).fillna(0)

    work["展示進入"] = pd.to_numeric(
        work["展示進入"],
        errors="coerce",
    ).fillna(work["枠"])

    score = np.zeros(len(work))

    score += np.where(
        work["枠"] == 1,
        2.8,
        0.0,
    )

    score += np.where(
        work["枠"] == 2,
        0.8,
        0.0,
    )

    score += np.where(
        work["枠"] == 3,
        0.45,
        0.0,
    )

    score += np.where(
        work["枠"] >= 4,
        -0.10,
        0.0,
    )

    score += (
        work["枠"]
        - work["展示進入"]
    ) * 0.9

    return score


def _base_score(df):

    return (
        _ability_score(df)
        + _exhibition_score(df)
        + _course_score(df)
    )


def _machine_prob(current_df, history):

    if (
        history is None
        or history.empty
        or "1着" not in history.columns
    ):
        return None

    required = set(
        FEATURES + ["1着"]
    )

    if not required.issubset(
        history.columns
    ):
        return None

    train = history.copy()

    for col in FEATURES:

        train[col] = pd.to_numeric(
            train[col],
            errors="coerce",
        ).fillna(0.0)

    train["1着"] = pd.to_numeric(
        train["1着"],
        errors="coerce",
    ).fillna(0).astype(int)

    train = train[
        train["1着"].isin([0, 1])
    ]

    if len(train) < 100:
        return None

    if train["1着"].nunique() < 2:
        return None

    try:

        model = RandomForestClassifier(
            n_estimators=300,
            max_depth=8,
            min_samples_leaf=4,
            max_features="sqrt",
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )

        model.fit(
            train[FEATURES],
            train["1着"],
        )

        probabilities = model.predict_proba(
            _prepare_features(current_df)
        )

        classes = list(
            model.classes_
        )

        if 1 not in classes:
            return None

        return probabilities[
            :,
            classes.index(1),
        ]

    except Exception:

        return None


def _normalize(values):

    values = np.asarray(
        values,
        dtype=float,
    )

    values = np.nan_to_num(
        values,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    values = np.maximum(
        values,
        0.0001,
    )

    total = values.sum()

    if total <= 0:
        return np.ones(
            len(values)
        ) / len(values)

    return values / total


def _rank_scores(
    df,
    first_prob,
):

    base = _base_score(df)

    first = (
        base * 0.55
        + first_prob * 20.0
    )

    first += np.where(
        df["枠"].values == 1,
        2.0,
        0.0,
    )

    first_prob_final = _normalize(
        first
    )

    second = (
        base * 0.75
        + first_prob_final * 5.0
    )

    second += np.where(
        df["枠"].values == 2,
        0.75,
        0.0,
    )

    second += np.where(
        df["枠"].values == 3,
        0.45,
        0.0,
    )

    second_prob = _normalize(
        second
    )

    third = (
        base * 0.60
        + second_prob * 4.0
    )

    third += np.where(
        df["枠"].values <= 3,
        0.30,
        0.0,
    )

    third_prob = _normalize(
        third
    )

    return (
        first_prob_final,
        second_prob,
        third_prob,
    )


def _combination_score(
    a,
    b,
    c,
    first_prob,
    second_prob,
    third_prob,
    df,
):

    probability = (
        first_prob[a] ** 1.45
        * second_prob[b] ** 1.10
        * third_prob[c] ** 0.85
    )

    lane_a = int(
        _num(df.iloc[a]["枠"])
    )

    lane_b = int(
        _num(df.iloc[b]["枠"])
    )

    lane_c = int(
        _num(df.iloc[c]["枠"])
    )

    if lane_a == 1:
        probability *= 1.18

    if lane_b in (2, 3):
        probability *= 1.06

    if lane_c in (1, 2, 3):
        probability *= 1.04

    if (
        lane_a == 1
        and lane_b == 2
        and lane_c == 3
    ):
        probability *= 1.03

    return float(probability)


def _find_hole(
    combinations,
    main_combo,
    counter_combo,
    df,
):

    for combo, _ in combinations:

        if combo in (
            main_combo,
            counter_combo,
        ):
            continue

        first_lane = int(
            _num(
                df.iloc[
                    combo[0]
                ]["枠"]
            )
        )

        if first_lane >= 4:
            return combo

    for combo, _ in combinations:

        if combo not in (
            main_combo,
            counter_combo,
        ):
            return combo

    return main_combo


def _combo_lanes(
    combo,
    df,
):

    return [
        int(
            _num(
                df.iloc[i]["枠"]
            )
        )
        for i in combo
    ]


def tri_ai(
    df,
    history=None,
):

    work = df.copy()

    if len(work) != 6:
        raise ValueError(
            "6艇のデータが必要です。"
        )

    ml_prob = _machine_prob(
        work,
        history,
    )

    base = _base_score(work)

    base_prob = _normalize(
        np.maximum(
            base - base.min() + 0.5,
            0.01,
        )
    )

    if ml_prob is not None:

        ml_prob = _normalize(
            ml_prob
        )

        first_prob = (
            ml_prob * 0.70
            + base_prob * 0.30
        )

    else:

        first_prob = base_prob

    (
        first_prob,
        second_prob,
        third_prob,
    ) = _rank_scores(
        work,
        first_prob,
    )

    combinations = []

    for a, b, c in itertools.permutations(
        range(6),
        3,
    ):

        value = _combination_score(
            a,
            b,
            c,
            first_prob,
            second_prob,
            third_prob,
            work,
        )

        combinations.append(
            ((a, b, c), value)
        )

    combinations.sort(
        key=lambda x: x[1],
        reverse=True,
    )

    main_combo = combinations[0][0]

    counter_combo = None

    main_lanes = _combo_lanes(
        main_combo,
        work,
    )

    for combo, _ in combinations[1:]:

        combo_lanes = _combo_lanes(
            combo,
            work,
        )

        overlap = len(
            set(main_lanes)
            & set(combo_lanes)
        )

        if overlap <= 2:
            counter_combo = combo
            break

    if counter_combo is None:
        counter_combo = combinations[1][0]

    hole_combo = _find_hole(
        combinations,
        main_combo,
        counter_combo,
        work,
    )

    boat_probs = {}

    for i in range(6):

        lane = int(
            _num(
                work.iloc[i]["枠"]
            )
        )

        boat_probs[lane] = float(
            first_prob[i]
        )

    return {
        "main": _combo_lanes(
            main_combo,
            work,
        ),
        "counter": _combo_lanes(
            counter_combo,
            work,
        ),
        "hole": _combo_lanes(
            hole_combo,
            work,
        ),
        "boat_probs": boat_probs,
        }
