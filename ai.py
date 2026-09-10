import itertools
import math

import numpy as np


def _norm(x):
    a = np.maximum(np.asarray(x, dtype=float), 0)
    s = a.sum()
    return a / s if s else np.ones(len(a)) / len(a)


def predict_race(race):
    scores = []

    for b in race["boats"]:
        boat = b["boat"]

        s = (
            b["rate"] * 4.2
            + b["local_rate"] * 1.8
            + b["motor"] * 0.8
            + b["course"] * 0.7
            + max(0, 7 - boat) * 1.2
        )

        if boat == 1:
            s += 8

        scores.append(max(s, 0.1))

    scores = np.array(scores, dtype=float)

    first_raw = np.exp(
        (scores + np.array([3, 0, 0, 0, 0, 0])) / 10
    )

    first_probs = _norm(first_raw)

    combos = list(
        itertools.permutations(range(1, 7), 3)
    )

    weights = []

    for a, b, c in combos:
        w = first_probs[a - 1] ** 1.60
        w *= first_probs[b - 1] ** 0.90
        w *= first_probs[c - 1] ** 0.65

        if a == 1:
            w *= 1.20

        if b in (2, 3):
            w *= 1.05

        if a in (5, 6) and first_probs[a - 1] < 0.12:
            w *= 0.85

        weights.append(w)

    probs = _norm(weights)

    joint = dict(
        zip(
            combos,
            map(float, probs)
        )
    )

    ranking = sorted(
        first_probs.keys(),
        key=first_probs.get,
        reverse=True
    )

    main, counter, hole = ranking[:3]

    confidence = max(
        55.0,
        min(
            90.0,
            55.0
            + (first_probs[main] - 1 / 6) * 75
        )
    )

    return {
        "scores": {
            i + 1: float(scores[i])
            for i in range(6)
        },
        "joint": joint,
        "first_probs": {
            i: float(first_probs[i - 1])
            for i in range(1, 7)
        },
        "ranking": ranking,
        "main": main,
        "counter": counter,
        "hole": hole,
        "confidence": confidence,
    }


def value_candidates(
    prediction,
    odds,
    min_prob=0.006,
    limit=8
):
    rows = []

    for combo, prob in prediction["joint"].items():

        odd = odds.get(combo)

        if odd is None or odd <= 0:
            continue

        if prob < min_prob:
            continue

        market_prob = 1.0 / odd

        edge = prob - market_prob

        ev = prob * odd - 1.0

        if ev <= 0:
            continue

        # -----------------------------------------
        # 的中率を最優先
        # EVは補助評価
        # -----------------------------------------
        #
        # EVの影響を最大35%相当に制限。
        # 150%以上のEVは、それ以上評価を膨らませない。
        #
        ev_boost = (
            min(max(ev, 0.0), 1.50)
            / 1.50
            * 0.35
        )

        score = prob * (1.0 + ev_boost)

        rows.append(
            {
                "combo": combo,
                "prob": float(prob),
                "odds": float(odd),
                "market_prob": float(market_prob),
                "edge": float(edge),
                "ev": float(ev),
                "score": float(score),
            }
        )

    # 的中率を最優先。
    # 近い場合にEVで比較。
    rows.sort(
        key=lambda x: (
            x["score"],
            x["prob"],
            x["ev"],
        ),
        reverse=True
    )

    return rows[:limit]
