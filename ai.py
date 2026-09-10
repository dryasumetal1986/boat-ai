import itertools

import numpy as np
import pandas as pd


def _num(value, default=0.0):
    try:
        if value is None or isinstance(value, bool):
            return default

        text = str(value).strip()

        if not text:
            return default

        return float(
            text.replace("%", "").replace(",", "")
        )

    except Exception:
        return default


def _safe_df(value):
    if value is None:
        return pd.DataFrame()

    if isinstance(value, pd.DataFrame):
        return value.copy()

    try:
        return pd.DataFrame(value)
    except Exception:
        return pd.DataFrame()


def _find_column(df, names):
    if df is None or df.empty:
        return None

    for name in names:
        if name in df.columns:
            return name

    return None


def history_bonus(history, boat):
    df = _safe_df(history)

    if df.empty:
        return 0.0

    boat_col = _find_column(
        df,
        ["枠", "艇", "艇番", "boat_number", "entry_number"]
    )

    place_col = _find_column(
        df,
        ["着順", "着", "place_number", "result", "順位"]
    )

    if boat_col is None or place_col is None:
        return 0.0

    values = []

    for _, row in df.iterrows():
        try:
            b = int(_num(row.get(boat_col), -1))

            if b != int(boat):
                continue

            place = _num(row.get(place_col), 99)

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
            pass

    if not values:
        return 0.0

    return float(np.mean(values)) * 8.0


def exhibition_score(row):
    score = 0.0

    t = _num(row.get("展示タイム"))
    st = _num(row.get("展示ST"))
    course = _num(
        row.get("展示進入"),
        row.get("枠", 0)
    )

    if t > 0:
        if t <= 6.70:
            score += 5
        elif t <= 6.75:
            score += 3.5
        elif t <= 6.80:
            score += 2
        elif t <= 6.85:
            score += 0.5
        elif t >= 6.95:
            score -= 2

    if st != 0:
        if st <= 0.10:
            score += 4
        elif st <= 0.13:
            score += 2.5
        elif st <= 0.16:
            score += 1
        elif st >= 0.20:
            score -= 1.5

    if course == 1:
        score += 4
    elif course == 2:
        score += 1.5
    elif course == 3:
        score += 0.8
    elif course >= 5:
        score -= 0.5

    return score


def calculate_boat_score(row, history, stadium_number):
    score = 0.0

    score += _num(row.get("全国勝率")) * 3.2
    score += _num(row.get("全国2連率")) * 0.055
    score += _num(row.get("全国3連率")) * 0.035

    score += _num(row.get("当地勝率")) * 1.8
    score += _num(row.get("当地2連率")) * 0.035
    score += _num(row.get("当地3連率")) * 0.025

    score += _num(row.get("モーター2連率")) * 0.035
    score += _num(row.get("モーター3連率")) * 0.02

    st = _num(row.get("平均ST"))

    if st > 0:
        if st <= 0.12:
            score += 5
        elif st <= 0.15:
            score += 3
        elif st <= 0.18:
            score += 1
        elif st >= 0.22:
            score -= 2

    boat = int(_num(row.get("枠"), 0))

    score += {
        1: 12,
        2: 5,
        3: 3,
        4: 2,
        5: -1,
        6: -2,
    }.get(boat, 0)

    score += exhibition_score(row)
    score += history_bonus(history, boat)

    try:
        if int(stadium_number) in {1, 7, 13, 19, 24} and boat == 1:
            score += 1
    except Exception:
        pass

    return float(score)


def _softmax(values, temperature=1.0):
    arr = np.array(values, dtype=float)

    if arr.size == 0:
        return []

    arr = arr / max(float(temperature), 0.01)
    arr -= np.max(arr)

    exp_values = np.exp(
        np.clip(arr, -50, 50)
    )

    total = exp_values.sum()

    if total <= 0:
        return [1 / len(arr)] * len(arr)

    return (exp_values / total).tolist()


def hole_score(row):
    score = 0.0

    score += _num(row.get("モーター2連率")) * 0.08
    score += _num(row.get("モーター3連率")) * 0.04

    t = _num(row.get("展示タイム"))
    st = _num(row.get("展示ST"))
    boat = int(_num(row.get("枠"), 0))

    if t > 0:
        if t <= 6.75:
            score += 5
        elif t <= 6.80:
            score += 3

    if st > 0:
        if st <= 0.13:
            score += 4
        elif st <= 0.16:
            score += 2

    if boat in (4, 5, 6):
        score += 2.5

    return score


def _trifecta_probability(a, b, c, probs):
    pa = float(probs.get(a, 0))
    pb = float(probs.get(b, 0))
    pc = float(probs.get(c, 0))

    if min(pa, pb, pc) <= 0:
        return 0.0

    d2 = max(1.0 - pa, 1e-9)
    d3 = max(1.0 - pa - pb, 1e-9)

    return pa * (pb / d2) * (pc / d3)


def make_trifecta_candidates(probs, odds=None, ranking=None):
    """
    実オッズがある場合:
      EV = AI確率 × オッズ - 1

    オッズがない場合:
      AI確率順の候補を返す。
    """

    odds = odds or {}
    ranking = ranking or list(range(1, 7))

    rank_map = {
        boat: i + 1
        for i, boat in enumerate(ranking)
    }

    results = []

    for combo in itertools.permutations(range(1, 7), 3):
        a, b, c = combo

        prob = _trifecta_probability(
            a, b, c, probs
        )

        odd = _num(odds.get(combo), 0)

        if odd > 0:
            ev = prob * odd - 1.0
            ev_percent = ev * 100
            expected_payout = prob * odd * 100
            score = ev
        else:
            ev = None
            ev_percent = None
            expected_payout = None
            score = prob

        results.append({
            "買い目": f"{a}-{b}-{c}",
            "組合せ": combo,
            "AI確率": prob * 100,
            "オッズ": odd if odd > 0 else None,
            "期待払戻": expected_payout,
            "EV": ev,
            "EV率": ev_percent,
            "スコア": score,
            "順位": (
                rank_map[a]
                + rank_map[b]
                + rank_map[c]
            ),
        })

    if odds:
        results.sort(
            key=lambda x: (
                x["EV"] is not None,
                x["EV"] if x["EV"] is not None else -999
            ),
            reverse=True
        )
    else:
        results.sort(
            key=lambda x: x["AI確率"],
            reverse=True
        )

    return results


def tri_ai(
    df,
    history=None,
    stadium_number=1,
    odds=None,
):
    data = _safe_df(df)

    if data.empty:
        raise ValueError("予想対象の艇データがありません。")

    data = data.reset_index(drop=True)

    if len(data) < 6:
        for boat in range(len(data) + 1, 7):
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

    for i, row in data.iterrows():
        boat = int(
            _num(row.get("枠"), i + 1)
        )

        scores[boat] = calculate_boat_score(
            row,
            history,
            stadium_number
        )

    score_values = [
        scores.get(boat, 0)
        for boat in range(1, 7)
    ]

    probabilities = _softmax(
        score_values,
        temperature=4.5
    )

    boat_probs = {
        boat: float(probabilities[boat - 1])
        for boat in range(1, 7)
    }

    ranking = sorted(
        range(1, 7),
        key=lambda boat: scores.get(boat, -999),
        reverse=True
    )

    main = ranking[0]
    counter = ranking[1]

    hole_values = {}

    for _, row in data.iterrows():
        boat = int(_num(row.get("枠"), 0))
        hole_values[boat] = hole_score(row)

    hole_candidates = sorted(
        range(1, 7),
        key=lambda boat: hole_values.get(
            boat, -999
        ),
        reverse=True
    )

    hole = next(
        (
            b for b in hole_candidates
            if b not in (main, counter)
        ),
        ranking[2]
    )

    top_prob = max(boat_probs.values())
    second_prob = sorted(
        boat_probs.values(),
        reverse=True
    )[1]

    spread = top_prob - second_prob

    confidence = min(
        0.99,
        max(
            0.50,
            0.55 + spread * 2.4
        )
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
            int(_num(x, 0)), 0
        )
    )

    result["_確率"] = result["枠"].apply(
        lambda x: boat_probs.get(
            int(_num(x, 0)), 0
        )
    )

    result = result.sort_values(
        "_AIスコア",
        ascending=False
    ).reset_index(drop=True)

    ranking_result = []

    for rank, boat in enumerate(
        ranking,
        start=1
    ):
        row = data[
            data["枠"].apply(
                lambda x: int(_num(x, -1))
            ) == boat
        ]

        name = (
            row.iloc[0]["選手名"]
            if not row.empty
            else f"{boat}号艇"
        )

        ranking_result.append({
            "順位": rank,
            "艇": boat,
            "選手名": name,
            "スコア": round(
                scores.get(boat, 0), 2
            ),
            "確率": round(
                boat_probs.get(boat, 0) * 100,
                1
            ),
        })

    candidates = make_trifecta_candidates(
        boat_probs,
        odds=odds,
        ranking=ranking,
    )

    return {
        "main": int(main),
        "counter": int(counter),
        "hole": int(hole),
        "boat_probs": boat_probs,
        "ranking": ranking,
        "ranking_result": ranking_result,
        "confidence": float(confidence),
        "confidence_percent": float(confidence * 100),
        "stars": int(stars),
        "scores": scores,
        "data": result,
        "trifecta_candidates": candidates,
        "odds": odds or {},
        "odds_available": bool(odds),
            }
