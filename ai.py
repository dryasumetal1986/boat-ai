import itertools
import math

import numpy as np


def _norm(values):
    arr = np.asarray(values, dtype=float)

    arr = np.nan_to_num(
        arr,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    total = arr.sum()

    if total <= 0:
        return np.ones(len(arr)) / len(arr)

    return arr / total


def predict_race(race):
    boats = race["boats"]

    scores = {}

    for b in boats:
        boat = int(b["boat"])

        score = (
            float(b.get("win_rate", 0.0)) * 0.55
            + float(b.get("local_rate", 0.0)) * 0.20
            + float(b.get("motor_rate", 0.0)) * 0.10
            + float(b.get("course_score", 0.0)) * 0.15
        )

        scores[boat] = score

    # スコアが全艇ほぼ0の場合でも計算可能にする
    if max(scores.values()) <= 0:
        scores = {
            boat: 1.0
            for boat in range(1, 7)
        }

    # -------------------------
    # 1着確率
    # -------------------------

    raw_first = []

    for boat in range(1, 7):
        s = scores.get(boat, 0.0)

        raw_first.append(
            math.exp(
                min(
                    max(s / 10.0, -20),
                    20,
                )
            )
        )

    first_array = _norm(raw_first)

    first_probs = {
        boat: float(first_array[boat - 1])
        for boat in range(1, 7)
    }

    ranking = sorted(
        range(1, 7),
        key=lambda boat: first_probs[boat],
        reverse=True,
    )

    main = ranking[0]
    counter = ranking[1]
    hole = ranking[2]

    # -------------------------
    # 三連単確率
    # -------------------------

    combos = list(
        itertools.permutations(
            range(1, 7),
            3,
        )
    )

    joint_raw = []

    for a, b, c in combos:
        pa = first_probs[a]
        pb = first_probs[b]
        pc = first_probs[c]

        # 1着を少し強く評価しつつ、
        # 2・3着も考慮
        value = (
            pa ** 1.00
            * pb ** 0.90
            * pc ** 0.85
        )

        joint_raw.append(
            max(value, 1e-12)
        )

    joint_array = _norm(joint_raw)

    joint = {
        combo: float(prob)
        for combo, prob in zip(
            combos,
            joint_array,
        )
    }

    # -------------------------
    # 信頼度
    # -------------------------

    top = first_probs[ranking[0]]
    second = first_probs[ranking[1]]

    gap = max(
        0.0,
        top - second,
    )

    confidence = (
        58.0
        + top * 55.0
        + gap * 70.0
    )

    confidence = max(
        55.0,
        min(
            95.0,
            confidence,
        ),
    )

    return {
        "main": main,
        "counter": counter,
        "hole": hole,
        "confidence": float(confidence),
        "first_probs": first_probs,
        "ranking": ranking,
        "scores": scores,
        "joint": joint,
    }


def value_candidates(
    prediction,
    odds,
    min_prob=0.006,
    limit=8,
):
    """
    的中率を最優先。
    EVは補助評価として使用。

    prob       = AI的中確率
    market_prob= 1 / オッズ
    ev         = prob * odds - 1

    スコアはAI確率を主軸にし、
    EVが高い場合だけ限定的に加点する。
    """

    if not odds:
        return []

    rows = []

    joint = prediction["joint"]

    for combo, odd in odds.items():
        if combo not in joint:
            continue

        try:
            odd = float(odd)
        except Exception:
            continue

        if odd <= 0:
            continue

        prob = float(
            joint[combo]
        )

        if prob < min_prob:
            continue

        market_prob = 1.0 / odd

        ev = (
            prob * odd
            - 1.0
        )

        if ev <= 0:
            continue

        edge = (
            prob
            - market_prob
        )

        # EVの加点は限定
        # 極端な高配当だけで上位を
        # 独占しないようにする
        ev_capped = min(
            max(ev, 0.0),
            1.50,
        )

        ev_bonus = (
            ev_capped / 1.50
        ) * 0.35

        # AI確率を最優先
        score = (
            prob
            * (1.0 + ev_bonus)
        )

        rows.append(
            {
                "combo": combo,
                "odds": odd,
                "prob": prob,
                "market_prob": market_prob,
                "ev": ev,
                "edge": edge,
                "score": score,
            }
        )

    rows.sort(
        key=lambda x: (
            x["score"],
            x["prob"],
            x["ev"],
        ),
        reverse=True,
    )

    return rows[:limit]
