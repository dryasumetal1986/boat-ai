# ai.py
# 🚤 やっちゃんの競艇AI予想PRO
# AI予想エンジン

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd


# =========================================================
# AI予想で使用する特徴量
# =========================================================

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


# =========================================================
# 数値変換
# =========================================================

def _num(
    value: Any,
    default: float = 0.0,
) -> float:

    try:
        if value is None:
            return default

        if value == "":
            return default

        value = float(value)

        if not np.isfinite(value):
            return default

        return value

    except Exception:
        return default


# =========================================================
# 0〜1へ正規化
# =========================================================

def _normalize(
    values: List[float],
) -> np.ndarray:

    arr = np.asarray(
        values,
        dtype=float,
    )

    if len(arr) == 0:
        return arr

    minimum = np.min(arr)
    maximum = np.max(arr)

    if maximum - minimum < 1e-9:
        return np.ones(len(arr)) * 0.5

    return (
        (arr - minimum)
        / (maximum - minimum)
    )


# =========================================================
# 枠評価
# =========================================================

def _lane_score(
    lane: float,
) -> float:

    lane = _num(lane, 0)

    scores = {
        1: 1.00,
        2: 0.82,
        3: 0.70,
        4: 0.62,
        5: 0.48,
        6: 0.38,
    }

    return scores.get(
        int(lane),
        0.5,
    )


# =========================================================
# 全国成績
# =========================================================

def _national_score(
    row: pd.Series,
) -> float:

    win = _num(
        row.get("全国勝率"),
    )

    top2 = _num(
        row.get("全国2連率"),
    )

    top3 = _num(
        row.get("全国3連率"),
    )

    # 勝率を中心に評価
    score = (
        win * 0.50
        + top2 * 0.30
        + top3 * 0.20
    )

    return score


# =========================================================
# 当地成績
# =========================================================

def _local_score(
    row: pd.Series,
) -> float:

    win = _num(
        row.get("当地勝率"),
    )

    top2 = _num(
        row.get("当地2連率"),
    )

    top3 = _num(
        row.get("当地3連率"),
    )

    return (
        win * 0.50
        + top2 * 0.30
        + top3 * 0.20
    )


# =========================================================
# モーター評価
# =========================================================

def _motor_score(
    row: pd.Series,
) -> float:

    return _num(
        row.get("モーター2連率"),
    )


# =========================================================
# ST評価
# =========================================================

def _st_score(
    row: pd.Series,
) -> float:

    avg_st = _num(
        row.get("平均ST"),
        0.20,
    )

    exhibition_st = _num(
        row.get("展示ST"),
        0.20,
    )

    # STは小さいほど高評価
    avg_score = max(
        0.0,
        1.0 - avg_st * 3.0,
    )

    exhibition_score = max(
        0.0,
        1.0 - exhibition_st * 3.0,
    )

    return (
        avg_score * 0.45
        + exhibition_score * 0.55
    )


# =========================================================
# 展示タイム評価
# =========================================================

def _exhibition_score(
    row: pd.Series,
    all_rows: pd.DataFrame,
) -> float:

    time = _num(
        row.get("展示タイム"),
        0.0,
    )

    if time <= 0:
        return 0.5

    times = [
        _num(x)
        for x in all_rows["展示タイム"].tolist()
        if _num(x) > 0
    ]

    if not times:
        return 0.5

    mean_time = float(
        np.mean(times)
    )

    # 展示タイムは小さいほど高評価
    diff = mean_time - time

    score = 0.5 + diff * 8.0

    return float(
        np.clip(
            score,
            0.0,
            1.0,
        )
    )


# =========================================================
# コース評価
# =========================================================

def _course_score(
    row: pd.Series,
) -> float:

    course = _num(
        row.get("展示進入"),
        row.get("枠", 1),
    )

    return _lane_score(course)


# =========================================================
# 個別選手スコア
# =========================================================

def _player_score(
    row: pd.Series,
    all_rows: pd.DataFrame,
) -> float:

    lane = _lane_score(
        row.get("枠")
    )

    course = _course_score(
        row
    )

    national = _national_score(
        row
    )

    local = _local_score(
        row
    )

    motor = _motor_score(
        row
    )

    st = _st_score(
        row
    )

    exhibition = _exhibition_score(
        row,
        all_rows,
    )

    # -----------------------------------------------------
    # 総合AIスコア
    # -----------------------------------------------------

    score = (
        lane * 25.0
        + course * 8.0
        + national * 2.5
        + local * 1.5
        + motor * 0.20
        + st * 10.0
        + exhibition * 12.0
    )

    return float(score)


# =========================================================
# 過去14日データによる補正
# =========================================================

def _history_bonus(
    boat_number: int,
    history: Any,
) -> float:

    if not history:
        return 0.0

    bonus = 0.0
    total = 0

    try:

        for item in history:

            if not isinstance(item, dict):
                continue

            result = item.get(
                "result",
                [],
            )

            if not isinstance(result, list):
                continue

            total += 1

            if boat_number in result[:3]:

                if len(result) > 0:
                    if boat_number == result[0]:
                        bonus += 2.5

                    elif boat_number == result[1]:
                        bonus += 1.5

                    elif boat_number == result[2]:
                        bonus += 0.8

    except Exception:
        return 0.0

    if total == 0:
        return 0.0

    return bonus / total * 10.0


# =========================================================
# 穴候補
# =========================================================

def _find_hole(
    df: pd.DataFrame,
    scores: Dict[int, float],
    main: int,
    counter: int,
) -> int:

    candidates = []

    for _, row in df.iterrows():

        boat = int(
            _num(
                row.get("枠"),
                0,
            )
        )

        if boat <= 0:
            continue

        if boat in (
            main,
            counter,
        ):
            continue

        score = scores.get(
            boat,
            0.0,
        )

        # 外枠を少し穴向きに評価
        if boat >= 4:
            score += 2.0

        # モーターが強い艇
        motor = _num(
            row.get("モーター2連率")
        )

        score += motor * 0.05

        # 展示ST
        exhibition_st = _num(
            row.get("展示ST")
        )

        if exhibition_st > 0:
            score += max(
                0.0,
                0.25 - exhibition_st,
            ) * 10

        candidates.append(
            (
                score,
                boat,
            )
        )

    if not candidates:

        return counter

    candidates.sort(
        reverse=True
    )

    return candidates[0][1]


# =========================================================
# 自信度
# =========================================================

def _confidence(
    sorted_scores: List[float],
) -> float:

    if len(sorted_scores) < 2:
        return 0.5

    first = sorted_scores[0]
    second = sorted_scores[1]

    if first <= 0:
        return 0.5

    gap = (
        first - second
    ) / first

    confidence = (
        0.55
        + gap * 2.5
    )

    return float(
        np.clip(
            confidence,
            0.50,
            0.98,
        )
    )


# =========================================================
# メインAI
# =========================================================

def tri_ai(
    df: pd.DataFrame,
    history: Any = None,
    stadium_number: int = 0,
) -> Dict[str, Any]:
    """
    競艇AI予想。

    必ず以下を返す:

        main
        counter
        hole
        confidence
        boat_probs
    """

    # -----------------------------------------------------
    # 入力チェック
    # -----------------------------------------------------

    if df is None:
        raise ValueError(
            "AIに渡されたデータがNoneです。"
        )

    if not isinstance(
        df,
        pd.DataFrame,
    ):
        df = pd.DataFrame(df)

    if df.empty:
        raise ValueError(
            "AIに渡された選手データが空です。"
        )

    # -----------------------------------------------------
    # 必要列を補完
    # -----------------------------------------------------

    required_columns = [
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

    for column in required_columns:

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

    # -----------------------------------------------------
    # 数値化
    # -----------------------------------------------------

    for column in required_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        ).fillna(0.0)

    # -----------------------------------------------------
    # 場番号
    # -----------------------------------------------------

    if stadium_number:

        df["場"] = stadium_number

    # -----------------------------------------------------
    # 1艇ずつスコア計算
    # -----------------------------------------------------

    scores: Dict[int, float] = {}

    for _, row in df.iterrows():

        boat = int(
            row["枠"]
        )

        score = _player_score(
            row,
            df,
        )

        # 過去成績補正
        score += _history_bonus(
            boat,
            history,
        )

        scores[boat] = float(
            score
        )

    # -----------------------------------------------------
    # スコア順
    # -----------------------------------------------------

    ranking = sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    if not ranking:
        raise ValueError(
            "AIスコアを計算できませんでした。"
        )

    main = ranking[0][0]

    if len(ranking) >= 2:
        counter = ranking[1][0]
    else:
        counter = main

    hole = _find_hole(
        df,
        scores,
        main,
        counter,
    )

    # -----------------------------------------------------
    # 確率化
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

    # Softmax
    shifted = (
        raw_scores
        - np.max(raw_scores)
    )

    exp_scores = np.exp(
        shifted / 8.0
    )

    probabilities = (
        exp_scores
        / np.sum(exp_scores)
    )

    boat_probs: Dict[int, float] = {}

    for (
        (boat, _),
        probability,
    ) in zip(
        ranking,
        probabilities,
    ):

        boat_probs[int(boat)] = float(
            probability
        )

    # -----------------------------------------------------
    # 自信度
    # -----------------------------------------------------

    confidence = _confidence(
        [
            score
            for _, score in ranking
        ]
    )

    # -----------------------------------------------------
    # 結果
    # -----------------------------------------------------

    return {
        "main": int(main),
        "counter": int(counter),
        "hole": int(hole),
        "confidence": float(confidence),
        "boat_probs": boat_probs,
        "scores": scores,
        "ranking": [
            boat
            for boat, _ in ranking
        ],
    }
