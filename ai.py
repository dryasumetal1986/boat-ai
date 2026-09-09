# ai.py
# 🚤 やっちゃんの競艇AI予想PRO
# AI予想エンジン 完全版

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd


# =========================================================
# 数値変換
# =========================================================

def num(
    value: Any,
    default: float = 0.0,
) -> float:

    try:

        if value in (
            None,
            "",
        ):
            return default

        value = float(value)

        if not np.isfinite(value):
            return default

        return value

    except Exception:

        return default


# =========================================================
# 枠評価
# =========================================================

def lane_score(
    lane: int,
) -> float:

    return {
        1: 1.00,
        2: 0.86,
        3: 0.74,
        4: 0.63,
        5: 0.51,
        6: 0.42,
    }.get(
        int(lane),
        0.5,
    )


# =========================================================
# 選手成績
# =========================================================

def national_score(
    row: pd.Series,
) -> float:

    return (
        num(row.get("全国勝率")) * 0.50
        + num(row.get("全国2連率")) * 0.30
        + num(row.get("全国3連率")) * 0.20
    )


def local_score(
    row: pd.Series,
) -> float:

    return (
        num(row.get("当地勝率")) * 0.50
        + num(row.get("当地2連率")) * 0.30
        + num(row.get("当地3連率")) * 0.20
    )


# =========================================================
# モーター
# =========================================================

def motor_score(
    row: pd.Series,
) -> float:

    value = num(
        row.get(
            "モーター2連率"
        )
    )

    return min(
        max(
            value / 100.0,
            0.0,
        ),
        1.0,
    )


# =========================================================
# ST
# =========================================================

def st_score(
    row: pd.Series,
) -> float:

    avg_st = num(
        row.get(
            "平均ST"
        )
    )

    exhibition_st = num(
        row.get(
            "展示ST"
        )
    )

    if avg_st <= 0:
        avg_component = 0.5
    else:
        avg_component = np.clip(
            1.0 - avg_st * 3.0,
            0.0,
            1.0,
        )

    if exhibition_st <= 0:
        exhibition_component = 0.5
    else:
        exhibition_component = np.clip(
            1.0 - exhibition_st * 3.0,
            0.0,
            1.0,
        )

    return (
        avg_component * 0.4
        + exhibition_component * 0.6
    )


# =========================================================
# 展示タイム
# =========================================================

def exhibition_score(
    row: pd.Series,
    df: pd.DataFrame,
) -> float:

    current = num(
        row.get(
            "展示タイム"
        )
    )

    if current <= 0:
        return 0.5

    values = [
        num(x)
        for x in df[
            "展示タイム"
        ].tolist()
        if num(x) > 0
    ]

    if not values:
        return 0.5

    mean = float(
        np.mean(values)
    )

    # 小さいほど良い
    diff = mean - current

    score = (
        0.5
        + diff * 8.0
    )

    return float(
        np.clip(
            score,
            0.0,
            1.0,
        )
    )


# =========================================================
# 過去成績
# =========================================================

def history_bonus(
    boat: int,
    history: Any,
) -> float:

    if not history:
        return 0.0

    bonus = 0.0
    count = 0

    for item in history:

        if not isinstance(
            item,
            dict,
        ):
            continue

        result = item.get(
            "result",
            [],
        )

        if not isinstance(
            result,
            list,
        ):
            continue

        if len(result) < 3:
            continue

        count += 1

        if boat == result[0]:
            bonus += 2.0

        elif boat == result[1]:
            bonus += 1.2

        elif boat == result[2]:
            bonus += 0.6

    if count == 0:
        return 0.0

    return bonus / count


# =========================================================
# AI本体
# =========================================================

def tri_ai(
    df: pd.DataFrame,
    history: Any = None,
    stadium_number: int = 0,
) -> Dict[str, Any]:

    if df is None or df.empty:
        raise ValueError(
            "AIに渡された選手データが空です。"
        )

    df = df.copy()

    # -----------------------------------------------------
    # 必須列
    # -----------------------------------------------------

    columns = [
        "枠",
        "展示進入",
        "全国勝率",
        "全国2連率",
        "全国3連率",
        "当地勝率",
        "当地2連率",
        "当地3連率",
        "モーター2連率",
        "平均ST",
        "展示ST",
        "展示タイム",
        "場",
    ]

    for column in columns:

        if column not in df.columns:

            if column == "枠":

                df[column] = range(
                    1,
                    len(df) + 1,
                )

            elif column == "展示進入":

                df[column] = df["枠"]

            else:

                df[column] = 0.0

    for column in columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        ).fillna(0.0)

    if stadium_number:
        df["場"] = stadium_number

    # -----------------------------------------------------
    # スコア
    # -----------------------------------------------------

    scores = {}

    for _, row in df.iterrows():

        boat = int(
            row["枠"]
        )

        lane = lane_score(
            boat
        )

        course = lane_score(
            int(
                row["展示進入"]
            )
        )

        national = national_score(
            row
        )

        local = local_score(
            row
        )

        motor = motor_score(
            row
        )

        st = st_score(
            row
        )

        exhibition = exhibition_score(
            row,
            df,
        )

        history = history_bonus(
            boat,
            history,
        )

        score = (

            lane * 30.0

            + course * 8.0

            + national * 2.0

            + local * 1.2

            + motor * 15.0

            + st * 12.0

            + exhibition * 15.0

            + history * 4.0
        )

        scores[boat] = float(
            score
        )

    # -----------------------------------------------------
    # ランキング
    # -----------------------------------------------------

    ranking = sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    main = ranking[0][0]

    counter = (
        ranking[1][0]
        if len(ranking) >= 2
        else main
    )

    # -----------------------------------------------------
    # 穴
    # -----------------------------------------------------

    hole_candidates = []

    for boat, score in ranking:

        if boat in (
            main,
            counter,
        ):
            continue

        row = df[
            df["枠"] == boat
        ].iloc[0]

        bonus = 0.0

        # 外枠
        if boat >= 4:
            bonus += 3.0

        # モーター
        bonus += (
            num(
                row["モーター2連率"]
            ) / 100.0
        ) * 8.0

        # 展示タイム
        bonus += (
            exhibition_score(
                row,
                df,
            )
            * 5.0
        )

        hole_candidates.append(
            (
                score + bonus,
                boat,
            )
        )

    if hole_candidates:

        hole_candidates.sort(
            reverse=True
        )

        hole = hole_candidates[0][1]

    else:

        hole = counter

    # -----------------------------------------------------
    # 確率
    # -----------------------------------------------------

    raw_scores = np.array(
        [
            max(
                0.01,
                score,
            )
            for _, score in ranking
        ],
        dtype=float,
    )

    shifted = (
        raw_scores
        - np.max(raw_scores)
    )

    exp_scores = np.exp(
        shifted / 10.0
    )

    probabilities = (
        exp_scores
        / exp_scores.sum()
    )

    boat_probs = {}

    for (
        (boat, _),
        probability,
    ) in zip(
        ranking,
        probabilities,
    ):

        boat_probs[
            int(boat)
        ] = float(
            probability
        )

    # -----------------------------------------------------
    # 自信度
    # -----------------------------------------------------

    if len(ranking) >= 2:

        first = ranking[0][1]
        second = ranking[1][1]

        gap = (
            first - second
        ) / max(
            abs(first),
            1.0,
        )

        confidence = (
            0.50
            + gap * 2.0
        )

    else:

        confidence = 0.50

    confidence = float(
        np.clip(
            confidence,
            0.50,
            0.95,
        )
    )

    # -----------------------------------------------------
    # 結果
    # -----------------------------------------------------

    return {
        "main": int(main),
        "counter": int(counter),
        "hole": int(hole),
        "confidence": confidence,
        "boat_probs": boat_probs,
        "scores": scores,
        "ranking": [
            int(boat)
            for boat, _ in ranking
        ],
    }
