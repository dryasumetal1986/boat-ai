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


# =========================
# 数値化
# =========================

def _num(value):

    try:

        if value is None:
            return 0.0

        if pd.isna(value):
            return 0.0

        return float(value)

    except Exception:

        return 0.0


# =========================
# 特徴量
# =========================

def _prepare_features(df):

    work = df.copy()


    for col in FEATURES:

        if col not in work.columns:
            work[col] = 0


    for col in FEATURES:

        work[col] = pd.to_numeric(
            work[col],
            errors="coerce",
        ).fillna(0)


    return work[FEATURES].astype(float)


# =========================
# 選手能力
# =========================

def _ability_score(row):

    return (

        _num(row.get("全国勝率")) * 1.8

        + _num(row.get("全国2連率")) * 0.35

        + _num(row.get("全国3連率")) * 0.18

        + _num(row.get("当地勝率")) * 0.8

        + _num(row.get("当地2連率")) * 0.15

        + _num(row.get("モーター2連率")) * 0.08

    )


# =========================
# 展示
# =========================

def _exhibition_score(
    row,
    mean_time,
):

    score = 0.0


    exhibition_time = _num(
        row.get("展示タイム")
    )


    if exhibition_time > 0:

        score += (
            mean_time
            - exhibition_time
        ) * 8.0


    exhibition_st = _num(
        row.get("展示ST")
    )


    if exhibition_st > 0:

        score += (
            0.12
            - exhibition_st
        ) * 8.0


    return score


# =========================
# コース
# =========================

def _course_score(row):

    lane = int(
        _num(
            row.get(
                "展示進入",
                row.get("枠", 0),
            )
        )
    )


    if lane == 1:
        return 3.0

    if lane == 2:
        return 1.8

    if lane == 3:
        return 1.4

    if lane == 4:
        return 1.0

    if lane == 5:
        return 0.4

    if lane == 6:
        return 0.1

    return 0.0


# =========================
# 基礎スコア
# =========================

def _base_score(
    row,
    mean_time,
):

    return (

        _ability_score(row)

        + _exhibition_score(
            row,
            mean_time,
        )

        + _course_score(row)

    )


# =========================
# モーター
# =========================

def _machine_prob(row):

    motor = _num(
        row.get(
            "モーター2連率"
        )
    )

    return max(
        0.0,
        motor / 100.0,
    )


# =========================
# 正規化
# =========================

def _normalize(values):

    arr = np.asarray(
        values,
        dtype=float,
    )

    if len(arr) == 0:
        return arr


    arr = arr - arr.max()

    exp = np.exp(arr)

    total = exp.sum()


    if total <= 0:

        return np.ones(
            len(arr)
        ) / len(arr)


    return exp / total


# =========================
# 順位
# =========================

def _rank_scores(
    df,
    scores,
):

    order = np.argsort(
        -np.asarray(scores)
    )

    return order


# =========================
# 組み合わせ評価
# =========================

def _combination_score(
    combo,
    work,
):

    score = 0.0


    for pos, idx in enumerate(combo):

        row = work.iloc[idx]

        base = _num(
            row["_score"]
        )


        if pos == 0:
            score += base * 1.20

        elif pos == 1:
            score += base * 0.85

        else:
            score += base * 0.55


    return score


# =========================
# 実際の艇番
# =========================

def _combo_lanes(
    combo,
    work,
):

    result = []

    for idx in combo:

        lane = _num(
            work.iloc[idx].get(
                "艇番",
                work.iloc[idx].get(
                    "枠",
                    idx + 1,
                ),
            )
        )

        result.append(
            int(lane)
        )

    return result


# =========================
# 穴候補
# =========================

def _find_hole(
    work,
    ranked,
):

    # 人気上位を避けて
    # 中位〜下位から穴を探す

    candidates = ranked[2:]

    if len(candidates) == 0:
        candidates = ranked


    # モーター・展示を考慮
    best_idx = None
    best_score = -999999


    for idx in candidates:

        row = work.iloc[idx]

        score = (

            _num(
                row.get(
                    "モーター2連率"
                )
            ) * 0.5

            + _num(
                row.get(
                    "展示ST"
                )
            ) * -8.0

            + _num(
                row.get(
                    "展示タイム"
                )
            ) * -2.0

        )


        if score > best_score:

            best_score = score
            best_idx = idx


    return best_idx


# =========================
# AI予想
# =========================

def tri_ai(
    df,
    history=None,
):

    if df is None:
        return {
            "main": [],
            "counter": [],
            "hole": [],
            "boat_probs": {},
        }


    if len(df) != 6:

        return {
            "main": [],
            "counter": [],
            "hole": [],
            "boat_probs": {},
        }


    work = df.copy()


    # =========================
    # 平均展示タイム
    # =========================

    times = pd.to_numeric(
        work.get(
            "展示タイム",
            pd.Series(dtype=float),
        ),
        errors="coerce",
    )

    valid_times = times[
        times > 0
    ]


    if len(valid_times):

        mean_time = float(
            valid_times.mean()
        )

    else:

        mean_time = 0.0


    # =========================
    # スコア
    # =========================

    scores = []


    for _, row in work.iterrows():

        scores.append(
            _base_score(
                row,
                mean_time,
            )
            + _machine_prob(row) * 5
        )


    work["_score"] = scores


    # =========================
    # 確率
    # =========================

    probs = _normalize(
        scores
    )


    boat_probs = {}


    for idx, (_, row) in enumerate(
        work.iterrows()
    ):

        lane = int(
            _num(
                row.get(
                    "艇番",
                    row.get(
                        "枠",
                        idx + 1,
                    ),
                )
            )
        )

        boat_probs[lane] = float(
            probs[idx]
        )


    # =========================
    # 順位
    # =========================

    ranked = _rank_scores(
        work,
        scores,
    )


    # =========================
    # 3連単候補
    # =========================

    combinations = list(
        itertools.permutations(
            ranked[:5],
            3,
        )
    )


    scored_combos = []


    for combo in combinations:

        score = _combination_score(
            combo,
            work,
        )

        scored_combos.append(
            (
                score,
                combo,
            )
        )


    scored_combos.sort(
        reverse=True,
        key=lambda x: x[0],
    )


    if scored_combos:

        main_combo = (
            scored_combos[0][1]
        )

    else:

        main_combo = ranked[:3]


    # =========================
    # 対抗
    # =========================

    counter_combo = None


    for _, combo in scored_combos:

        if combo != main_combo:

            counter_combo = combo
            break


    if counter_combo is None:

        counter_combo = ranked[:3]


    # =========================
    # 穴
    # =========================

    hole_idx = _find_hole(
        work,
        ranked,
    )


    if hole_idx is None:

        hole_combo = ranked[-3:]

    else:

        others = [
            x
            for x in ranked
            if x != hole_idx
        ]

        others = others[:2]

        hole_combo = [
            hole_idx,
            *others,
        ]


    return {
        "main":
            _combo_lanes(
                main_combo,
                work,
            ),

        "counter":
            _combo_lanes(
                counter_combo,
                work,
            ),

        "hole":
            _combo_lanes(
                hole_combo,
                work,
            ),

        "boat_probs":
            boat_probs,
    }
