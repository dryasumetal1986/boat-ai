import math
from typing import Any

import numpy as np
import pandas as pd


# =========================================================
# 数値変換
# =========================================================

def _num(value: Any, default: float = 0.0) -> float:
    """None / NaN / 文字列などを安全にfloatへ変換"""
    try:
        if value is None:
            return default

        if isinstance(value, str):
            value = value.replace("%", "").replace(",", "").strip()

        result = float(value)

        if math.isnan(result) or math.isinf(result):
            return default

        return result

    except Exception:
        return default


def _safe_df(data: Any) -> pd.DataFrame:
    """どんなhistory形式でもDataFrameへ統一"""
    if data is None:
        return pd.DataFrame()

    if isinstance(data, pd.DataFrame):
        return data.copy()

    if isinstance(data, list):
        try:
            return pd.DataFrame(data)
        except Exception:
            return pd.DataFrame()

    if isinstance(data, dict):
        try:
            return pd.DataFrame(data)
        except Exception:
            return pd.DataFrame()

    return pd.DataFrame()


# =========================================================
# 列名取得
# =========================================================

def _find_column(df: pd.DataFrame, candidates):
    """候補列から存在する列を探す"""
    if df is None or df.empty:
        return None

    for col in candidates:
        if col in df.columns:
            return col

    return None


# =========================================================
# 過去成績ボーナス
# =========================================================

def history_bonus(history: Any, boat_number: int) -> float:
    """
    過去成績から艇ごとのボーナスを計算。

    history は
      - pandas.DataFrame
      - list
      - dict
      - None
    のどれでもOK。

    ここが今回のTypeError対策の中心。
    """

    df = _safe_df(history)

    # 過去データが無い場合はゼロ
    if df.empty:
        return 0.0

    # -----------------------------------------
    # 枠 / 艇番号の列
    # -----------------------------------------

    boat_col = _find_column(
        df,
        [
            "枠",
            "艇",
            "艇番",
            "boat_number",
            "entry_number",
            "course_number",
        ],
    )

    if boat_col is None:
        return 0.0

    # -----------------------------------------
    # 着順の列
    # -----------------------------------------

    place_col = _find_column(
        df,
        [
            "着順",
            "着",
            "place_number",
            "result",
            "順位",
        ],
    )

    if place_col is None:
        return 0.0

    try:
        work = df.copy()

        work["_boat"] = pd.to_numeric(
            work[boat_col],
            errors="coerce",
        )

        work["_place"] = pd.to_numeric(
            work[place_col],
            errors="coerce",
        )

        work = work.dropna(subset=["_boat", "_place"])

        if work.empty:
            return 0.0

        work = work[work["_boat"] == int(boat_number)]

        if work.empty:
            return 0.0

        total = len(work)

        if total <= 0:
            return 0.0

        wins = int((work["_place"] == 1).sum())
        top2 = int((work["_place"] <= 2).sum())
        top3 = int((work["_place"] <= 3).sum())

        win_rate = wins / total
        top2_rate = top2 / total
        top3_rate = top3 / total

        # 過去成績ボーナス
        bonus = (
            win_rate * 2.5
            + top2_rate * 1.5
            + top3_rate * 1.0
        )

        return float(bonus)

    except Exception:
        return 0.0


# =========================================================
# 展示ボーナス
# =========================================================

def exhibition_score(
    df: pd.DataFrame,
    boat_number: int,
) -> float:

    if df is None or df.empty:
        return 0.0

    try:
        row = df.iloc[boat_number - 1]

    except Exception:
        return 0.0

    exhibition_time = _num(
        row.get("展示タイム", 0)
    )

    exhibition_st = _num(
        row.get("展示ST", 0)
    )

    all_times = [
        _num(x)
        for x in df.get("展示タイム", [])
    ]

    all_times = [
        x for x in all_times
        if x > 0
    ]

    all_st = [
        _num(x)
        for x in df.get("展示ST", [])
    ]

    all_st = [
        x for x in all_st
        if x > 0
    ]

    score = 0.0

    # 展示タイム
    if exhibition_time > 0 and all_times:
        mean_time = float(np.mean(all_times))

        # 平均より速いほどプラス
        score += (mean_time - exhibition_time) * 12.0

    # 展示ST
    if exhibition_st > 0 and all_st:
        mean_st = float(np.mean(all_st))

        # STは小さいほどプラス
        score += (mean_st - exhibition_st) * 8.0

    return float(score)


# =========================================================
# 選手・モーター・枠の総合スコア
# =========================================================

def calculate_boat_score(
    row: pd.Series,
    df: pd.DataFrame,
    history: Any,
    stadium_number: int = 1,
) -> float:

    boat = int(
        _num(
            row.get("枠", 1),
            1,
        )
    )

    # -----------------------------------------
    # 枠番
    # -----------------------------------------

    lane_bonus = {
        1: 5.0,
        2: 3.0,
        3: 2.2,
        4: 1.5,
        5: 0.8,
        6: 0.3,
    }

    score = lane_bonus.get(boat, 0.0)

    # -----------------------------------------
    # 全国成績
    # -----------------------------------------

    national_win = _num(
        row.get("全国勝率", 0)
    )

    national_top2 = _num(
        row.get("全国2連率", 0)
    )

    national_top3 = _num(
        row.get("全国3連率", 0)
    )

    score += national_win * 1.25
    score += national_top2 * 0.035
    score += national_top3 * 0.025

    # -----------------------------------------
    # 当地成績
    # -----------------------------------------

    local_win = _num(
        row.get("当地勝率", 0)
    )

    local_top2 = _num(
        row.get("当地2連率", 0)
    )

    local_top3 = _num(
        row.get("当地3連率", 0)
    )

    score += local_win * 0.8
    score += local_top2 * 0.025
    score += local_top3 * 0.018

    # -----------------------------------------
    # モーター
    # -----------------------------------------

    motor_top2 = _num(
        row.get("モーター2連率", 0)
    )

    motor_top3 = _num(
        row.get("モーター3連率", 0)
    )

    score += motor_top2 * 0.035
    score += motor_top3 * 0.020

    # -----------------------------------------
    # 平均ST
    # -----------------------------------------

    average_st = _num(
        row.get("平均ST", 0)
    )

    if average_st > 0:
        score += (0.20 - average_st) * 15.0

    # -----------------------------------------
    # 展示
    # -----------------------------------------

    score += exhibition_score(
        df,
        boat,
    )

    # -----------------------------------------
    # 過去14日などの履歴
    #
    # ★ historyがDataFrameでもOK
    # ★ listでもOK
    # ★ NoneでもOK
    # -----------------------------------------

    score += history_bonus(
        history,
        boat,
    )

    # -----------------------------------------
    # 場補正
    #
    # 極端な補正はせず微調整
    # -----------------------------------------

    stadium_adjust = {
        1: 0.15,
        2: 0.10,
        3: 0.05,
        4: 0.10,
        5: 0.00,
        6: 0.05,
        7: 0.05,
        8: 0.05,
        9: 0.10,
        10: 0.00,
        11: 0.05,
        12: 0.00,
        13: 0.05,
        14: 0.05,
        15: 0.05,
        16: 0.05,
        17: 0.05,
        18: 0.05,
        19: 0.05,
        20: 0.05,
        21: 0.05,
        22: 0.05,
        23: 0.05,
        24: 0.05,
    }

    score += stadium_adjust.get(
        int(stadium_number),
        0.0,
    )

    return float(score)


# =========================================================
# Softmax
# =========================================================

def _softmax(scores):

    values = np.asarray(
        scores,
        dtype=float,
    )

    if len(values) == 0:
        return []

    values = np.nan_to_num(
        values,
        nan=0.0,
        posinf=20.0,
        neginf=-20.0,
    )

    # 数値を安定させる
    values = values - np.max(values)

    exp_values = np.exp(
        np.clip(values, -50, 50)
    )

    total = np.sum(exp_values)

    if total <= 0 or not np.isfinite(total):
        return [
            1.0 / len(values)
            for _ in values
        ]

    probs = exp_values / total

    return [
        float(x)
        for x in probs
    ]


# =========================================================
# 穴候補スコア
# =========================================================

def hole_score(
    row: pd.Series,
    base_score: float,
) -> float:

    motor = _num(
        row.get("モーター2連率", 0)
    )

    motor3 = _num(
        row.get("モーター3連率", 0)
    )

    exhibition_time = _num(
        row.get("展示タイム", 0)
    )

    exhibition_st = _num(
        row.get("展示ST", 0)
    )

    score = base_score

    # モーターの強さ
    score += motor * 0.045
    score += motor3 * 0.025

    # 展示の上振れ
    if exhibition_time > 0:
        score += 0.5

    if exhibition_st > 0:
        score += max(
            0.0,
            0.20 - exhibition_st,
        ) * 8.0

    return float(score)


# =========================================================
# AI予想本体
# =========================================================

def tri_ai(
    df: pd.DataFrame,
    history: Any = None,
    stadium_number: int = 1,
):

    # -----------------------------------------
    # DataFrameへ統一
    # -----------------------------------------

    df = _safe_df(df)

    if df.empty:
        raise ValueError(
            "AI予想に必要な6艇のデータを取得できませんでした。"
        )

    # -----------------------------------------
    # 最大6艇
    # -----------------------------------------

    df = df.head(6).copy()

    # 6艇未満の場合でも落とさない
    while len(df) < 6:
        boat_no = len(df) + 1

        df.loc[len(df)] = {
            "枠": boat_no,
            "選手名": f"{boat_no}号艇",
            "全国勝率": 0,
            "全国2連率": 0,
            "全国3連率": 0,
            "当地勝率": 0,
            "当地2連率": 0,
            "当地3連率": 0,
            "モーター2連率": 0,
            "モーター3連率": 0,
            "平均ST": 0,
            "展示ST": 0,
            "展示タイム": 0,
            "展示進入": boat_no,
            "場": stadium_number,
        }

    # -----------------------------------------
    # 枠番を確実に設定
    # -----------------------------------------

    if "枠" not in df.columns:
        df["枠"] = range(
            1,
            len(df) + 1,
        )

    df["枠"] = pd.to_numeric(
        df["枠"],
        errors="coerce",
    ).fillna(
        pd.Series(
            range(1, len(df) + 1),
            index=df.index,
        )
    )

    # -----------------------------------------
    # 各艇スコア
    # -----------------------------------------

    scores = []

    for _, row in df.iterrows():

        score = calculate_boat_score(
            row=row,
            df=df,
            history=history,
            stadium_number=stadium_number,
        )

        scores.append(score)

    df["_AIスコア"] = scores

    # -----------------------------------------
    # 確率化
    # -----------------------------------------

    probabilities = _softmax(
        scores
    )

    df["_確率"] = probabilities

    # -----------------------------------------
    # ランキング
    # -----------------------------------------

    ranking_df = (
        df.sort_values(
            "_AIスコア",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    ranking = [
        int(
            _num(
                row.get("枠", i + 1),
                i + 1,
            )
        )
        for i, (_, row) in enumerate(
            ranking_df.iterrows()
        )
    ]

    # 重複除去
    ranking = list(
        dict.fromkeys(ranking)
    )

    # 1〜6を保証
    for boat in range(1, 7):
        if boat not in ranking:
            ranking.append(boat)

    ranking = ranking[:6]

    # -----------------------------------------
    # 本命
    # -----------------------------------------

    main = ranking[0]

    # -----------------------------------------
    # 対抗
    # -----------------------------------------

    counter = ranking[1]

    # -----------------------------------------
    # 穴
    #
    # 上位2艇以外から選択
    # -----------------------------------------

    hole_candidates = ranking[2:]

    best_hole = None
    best_hole_value = -999999.0

    for boat in hole_candidates:

        matches = df[
            pd.to_numeric(
                df["枠"],
                errors="coerce",
            ) == boat
        ]

        if matches.empty:
            continue

        row = matches.iloc[0]

        base = _num(
            row.get("_AIスコア", 0)
        )

        value = hole_score(
            row,
            base,
        )

        if value > best_hole_value:
            best_hole_value = value
            best_hole = boat

    if best_hole is None:
        best_hole = ranking[2]

    hole = int(best_hole)

    # -----------------------------------------
    # 確率辞書
    # -----------------------------------------

    boat_probs = {}

    for _, row in df.iterrows():

        boat = int(
            _num(
                row.get("枠", 1),
                1,
            )
        )

        prob = _num(
            row.get("_確率", 0),
            0,
        )

        boat_probs[boat] = prob

    # 0〜1に収める
    boat_probs = {
        boat: max(
            0.0,
            min(1.0, prob),
        )
        for boat, prob in boat_probs.items()
    }

    # 合計1に再調整
    total_prob = sum(
        boat_probs.values()
    )

    if total_prob > 0:
        boat_probs = {
            boat: prob / total_prob
            for boat, prob in boat_probs.items()
        }
    else:
        boat_probs = {
            boat: 1.0 / 6.0
            for boat in range(1, 7)
        }

    # -----------------------------------------
    # 信頼度
    # -----------------------------------------

    sorted_probs = sorted(
        boat_probs.values(),
        reverse=True,
    )

    top_prob = (
        sorted_probs[0]
        if sorted_probs
        else 1.0 / 6.0
    )

    second_prob = (
        sorted_probs[1]
        if len(sorted_probs) >= 2
        else 1.0 / 6.0
    )

    margin = max(
        0.0,
        top_prob - second_prob,
    )

    concentration = max(
        0.0,
        top_prob - (1.0 / 6.0),
    )

    confidence = (
        0.45
        + margin * 2.2
        + concentration * 1.2
    )

    confidence = max(
        0.35,
        min(0.98, confidence),
    )

    # -----------------------------------------
    # 星評価
    # -----------------------------------------

    if confidence >= 0.85:
        stars = 5
    elif confidence >= 0.72:
        stars = 4
    elif confidence >= 0.58:
        stars = 3
    elif confidence >= 0.45:
        stars = 2
    else:
        stars = 1

    # -----------------------------------------
    # 表示用ランキング
    # -----------------------------------------

    ranking_result = []

    for rank, boat in enumerate(
        ranking,
        start=1,
    ):
        ranking_result.append(
            {
                "順位": rank,
                "艇": boat,
                "確率": boat_probs.get(
                    boat,
                    0.0,
                ),
            }
        )

    # -----------------------------------------
    # 結果
    # -----------------------------------------

    return {
        "main": int(main),
        "counter": int(counter),
        "hole": int(hole),

        "boat_probs": boat_probs,

        "ranking": ranking,

        "ranking_result": ranking_result,

        "confidence": float(confidence),

        "confidence_percent": round(
            confidence * 100,
            1,
        ),

        "stars": stars,

        "scores": {
            int(
                _num(
                    row.get("枠", i + 1),
                    i + 1,
                )
            ): float(
                _num(
                    row.get("_AIスコア", 0),
                    0,
                )
            )
            for i, (_, row) in enumerate(
                df.iterrows()
            )
        },

        "data": df,
    }
