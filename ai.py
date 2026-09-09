import math

import numpy as np
import pandas as pd


def _num(value, default=0.0):
    try:
        if value is None:
            return default

        if isinstance(value, bool):
            return default

        text = str(value).strip()

        if text == "":
            return default

        return float(
            text.replace("%", "").replace(",", "")
        )

    except Exception:
        return default


def _safe_df(value):
    """
    historyがDataFrame / list / dict / Noneのどれでも
    DataFrameに統一する。
    """

    if value is None:
        return pd.DataFrame()

    if isinstance(value, pd.DataFrame):
        return value.copy()

    if isinstance(value, list):
        try:
            return pd.DataFrame(value)
        except Exception:
            return pd.DataFrame()

    if isinstance(value, dict):
        try:
            return pd.DataFrame(value)
        except Exception:
            return pd.DataFrame()

    return pd.DataFrame()


def _find_column(df, names):
    if df is None or df.empty:
        return None

    for name in names:
        if name in df.columns:
            return name

    return None


def history_bonus(history, boat):
    """
    過去成績による補正。
    """

    df = _safe_df(history)

    if df.empty:
        return 0.0

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

    if boat_col is None or place_col is None:
        return 0.0

    values = []

    for _, row in df.iterrows():
        try:
            row_boat = int(
                _num(row.get(boat_col), -1)
            )

            if row_boat != int(boat):
                continue

            place = _num(
                row.get(place_col),
                99,
            )

            if place <= 1:
                values.append(1.0)
            elif place <= 2:
                values.append(0.65)
            elif place <= 3:
                values.append(0.4)
            elif place <= 4:
                values.append(0.1)
            else:
                values.append(-0.2)

        except Exception:
            continue

    if not values:
        return 0.0

    return float(np.mean(values)) * 8.0


def exhibition_score(row):
    """
    展示タイム・展示ST・展示進入から補正。
    """

    score = 0.0

    exhibition_time = _num(
        row.get("展示タイム"),
        0,
    )

    if exhibition_time > 0:
        # 一般的な展示タイム帯からの相対評価
        if exhibition_time <= 6.70:
            score += 5.0
        elif exhibition_time <= 6.75:
            score += 3.5
        elif exhibition_time <= 6.80:
            score += 2.0
        elif exhibition_time <= 6.85:
            score += 0.5
        elif exhibition_time >= 6.95:
            score -= 2.0

    exhibition_st = _num(
        row.get("展示ST"),
        0,
    )

    if exhibition_st != 0:
        if exhibition_st <= 0.10:
            score += 4.0
        elif exhibition_st <= 0.13:
            score += 2.5
        elif exhibition_st <= 0.16:
            score += 1.0
        elif exhibition_st >= 0.20:
            score -= 1.5

    course = _num(
        row.get("展示進入"),
        row.get("枠", 0),
    )

    if course == 1:
        score += 4.0
    elif course == 2:
        score += 1.5
    elif course == 3:
        score += 0.8
    elif course >= 5:
        score -= 0.5

    return score


def calculate_boat_score(row, history, stadium_number):
    """
    1艇ごとの総合AIスコア。
    """

    score = 0.0

    national_win = _num(
        row.get("全国勝率"),
        0,
    )

    national_2 = _num(
        row.get("全国2連率"),
        0,
    )

    national_3 = _num(
        row.get("全国3連率"),
        0,
    )

    local_win = _num(
        row.get("当地勝率"),
        0,
    )

    local_2 = _num(
        row.get("当地2連率"),
        0,
    )

    local_3 = _num(
        row.get("当地3連率"),
        0,
    )

    motor_2 = _num(
        row.get("モーター2連率"),
        0,
    )

    motor_3 = _num(
        row.get("モーター3連率"),
        0,
    )

    average_st = _num(
        row.get("平均ST"),
        0,
    )

    # 全国成績
    score += national_win * 3.2
    score += national_2 * 0.055
    score += national_3 * 0.035

    # 当地成績
    score += local_win * 1.8
    score += local_2 * 0.035
    score += local_3 * 0.025

    # モーター
    score += motor_2 * 0.035
    score += motor_3 * 0.02

    # ST
    if average_st > 0:
        if average_st <= 0.12:
            score += 5.0
        elif average_st <= 0.15:
            score += 3.0
        elif average_st <= 0.18:
            score += 1.0
        elif average_st >= 0.22:
            score -= 2.0

    # コース
    boat = int(
        _num(
            row.get("枠"),
            0,
        )
    )

    if boat == 1:
        score += 12.0
    elif boat == 2:
        score += 5.0
    elif boat == 3:
        score += 3.0
    elif boat == 4:
        score += 2.0
    elif boat == 5:
        score -= 1.0
    elif boat == 6:
        score -= 2.0

    score += exhibition_score(row)

    score += history_bonus(
        history,
        boat,
    )

    # 場番号による微調整
    try:
        stadium = int(stadium_number)

        if stadium in {1, 7, 13, 19, 24} and boat == 1:
            score += 1.0

    except Exception:
        pass

    return float(score)


def _softmax(values, temperature=1.0):
    arr = np.array(
        values,
        dtype=float,
    )

    if arr.size == 0:
        return []

    arr = arr / max(
        float(temperature),
        0.01,
    )

    arr = arr - np.max(arr)

    exp_values = np.exp(
        np.clip(arr, -50, 50)
    )

    total = exp_values.sum()

    if total <= 0:
        return [
            1.0 / len(arr)
            for _ in arr
        ]

    return (
        exp_values / total
    ).tolist()


def hole_score(row):
    """
    穴候補向けの独立スコア。
    """

    score = 0.0

    motor = _num(
        row.get("モーター2連率"),
        0,
    )

    motor3 = _num(
        row.get("モーター3連率"),
        0,
    )

    exhibition = _num(
        row.get("展示タイム"),
        0,
    )

    st = _num(
        row.get("展示ST"),
        0,
    )

    boat = int(
        _num(
            row.get("枠"),
            0,
        )
    )

    score += motor * 0.08
    score += motor3 * 0.04

    if exhibition > 0:
        if exhibition <= 6.75:
            score += 5
        elif exhibition <= 6.80:
            score += 3

    if st > 0:
        if st <= 0.13:
            score += 4
        elif st <= 0.16:
            score += 2

    # 外枠は穴候補として少し評価
    if boat in (4, 5, 6):
        score += 2.5

    return score


def tri_ai(
    df,
    history=None,
    stadium_number=1,
):
    """
    メインAI。

    戻り値:
    {
        main,
        counter,
        hole,
        boat_probs,
        ranking,
        ranking_result,
        confidence,
        confidence_percent,
        stars,
        scores,
        data
    }
    """

    data = _safe_df(df)

    if data.empty:
        raise ValueError(
            "予想対象の艇データがありません。"
        )

    data = data.reset_index(drop=True)

    # 6艇に揃える
    if len(data) < 6:
        for boat in range(
            len(data) + 1,
            7,
        ):
            data.loc[len(data)] = {
                "枠": boat,
                "艇": boat,
                "艇番": boat,
                "entry_number": boat,
                "選手名": f"{boat}号艇",
            }

    if len(data) > 6:
        data = data.iloc[:6].copy()

    scores = {}

    for index, row in data.iterrows():
        boat = int(
            _num(
                row.get("枠"),
                index + 1,
            )
        )

        scores[boat] = calculate_boat_score(
            row,
            history,
            stadium_number,
        )

    score_values = [
        scores.get(boat, 0.0)
        for boat in range(1, 7)
    ]

    probabilities = _softmax(
        score_values,
        temperature=4.5,
    )

    boat_probs = {
        boat: float(
            probabilities[boat - 1]
        )
        for boat in range(1, 7)
    }

    ranking = sorted(
        range(1, 7),
        key=lambda boat: scores.get(
            boat,
            -999,
        ),
        reverse=True,
    )

    main = ranking[0]
    counter = ranking[1]

    # 穴候補は総合順位とは別に評価
    hole_values = {}

    for index, row in data.iterrows():
        boat = int(
            _num(
                row.get("枠"),
                index + 1,
            )
        )

        hole_values[boat] = (
            hole_score(row)
        )

    hole_candidates = sorted(
        range(1, 7),
        key=lambda boat: hole_values.get(
            boat,
            -999,
        ),
        reverse=True,
    )

    hole = hole_candidates[0]

    # 本命と同じになった場合は次候補
    if hole == main:
        for candidate in hole_candidates[1:]:
            if candidate != main:
                hole = candidate
                break

    top_prob = max(
        boat_probs.values()
    )

    second_prob = sorted(
        boat_probs.values(),
        reverse=True,
    )[1]

    spread = top_prob - second_prob

    confidence = min(
        0.99,
        max(
            0.50,
            0.55 + spread * 2.4,
        ),
    )

    confidence_percent = (
        confidence * 100
    )

    if confidence >= 0.88:
        stars = 5
    elif confidence >= 0.78:
        stars = 4
    elif confidence >= 0.68:
        stars = 3
    elif confidence >= 0.58:
        stars = 2
    else:
        stars = 1

    result = data.copy()

    result["_AIスコア"] = result["枠"].apply(
        lambda x: scores.get(
            int(_num(x, 0)),
            0.0,
        )
    )

    result["_確率"] = result["枠"].apply(
        lambda x: boat_probs.get(
            int(_num(x, 0)),
            0.0,
        )
    )

    result = result.sort_values(
        "_AIスコア",
        ascending=False,
    ).reset_index(drop=True)

    ranking_result = []

    for rank, boat in enumerate(
        ranking,
        start=1,
    ):
        row = data[
            data["枠"].apply(
                lambda x: int(
                    _num(x, -1)
                )
            )
            == boat
        ]

        name = (
            row.iloc[0]["選手名"]
            if not row.empty
            else f"{boat}号艇"
        )

        ranking_result.append(
            {
                "順位": rank,
                "艇": boat,
                "選手名": name,
                "スコア": round(
                    scores.get(
                        boat,
                        0.0,
                    ),
                    2,
                ),
                "確率": round(
                    boat_probs.get(
                        boat,
                        0.0,
                    ) * 100,
                    1,
                ),
            }
        )

    return {
        "main": int(main),
        "counter": int(counter),
        "hole": int(hole),
        "boat_probs": boat_probs,
        "ranking": ranking,
        "ranking_result": ranking_result,
        "confidence": float(confidence),
        "confidence_percent": float(
            confidence_percent
        ),
        "stars": int(stars),
        "scores": scores,
        "data": result,
    }
