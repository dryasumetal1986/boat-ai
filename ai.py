import itertools

import numpy as np


def _norm(x):
    a = np.maximum(np.asarray(x, dtype=float), 0)
    total = a.sum()

    if total <= 0:
        return np.ones(len(a)) / len(a)

    return a / total


def predict_race(race):
    scores = []

    for boat_data in race["boats"]:
        boat = boat_data["boat"]

        score = (
            boat_data["rate"] * 4.2
            + boat_data["local_rate"] * 1.8
            + boat_data["motor"] * 0.8
            + boat_data["course"] * 0.7
            + max(0, 7 - boat) * 1.2
        )

        if boat == 1:
            score += 8

        scores.append(max(score, 0.1))

    scores = np.array(
        scores,
        dtype=float
    )

    first_raw = np.exp(
        (
            scores
            + np.array(
                [3, 0, 0, 0, 0, 0],
                dtype=float
            )
        )
        / 10
    )

    first_probs_array = _norm(
        first_raw
    )

    # 1〜6号艇の辞書に変換
    first_probs = {
        boat: float(
            first_probs_array[boat - 1]
        )
        for boat in range(1, 7)
    }

    combos = list(
        itertools.permutations(
            range(1, 7),
            3
        )
    )

    weights = []

    for first, second, third in combos:

        weight = (
            first_probs[first] ** 1.60
        )

        weight *= (
            first_probs[second] ** 0.90
        )

        weight *= (
            first_probs[third] ** 0.65
        )

        if first == 1:
            weight *= 1.20

        if second in (2, 3):
            weight *= 1.05

        if (
            first in (5, 6)
            and first_probs[first] < 0.12
        ):
            weight *= 0.85

        weights.append(weight)

    combo_probs = _norm(
        weights
    )

    joint = {
        combo: float(prob)
        for combo, prob in zip(
            combos,
            combo_probs
        )
    }

    ranking = sorted(
        range(1, 7),
        key=lambda boat: first_probs[boat],
        reverse=True
    )

    main = ranking[0]
    counter = ranking[1]
    hole = ranking[2]

    confidence = (
        55.0
        + (
            first_probs[main]
            - 1 / 6
        ) * 75
    )

    confidence = max(
        55.0,
        min(
            90.0,
            confidence
        )
    )

    return {
        "scores": {
            boat: float(
                scores[boat - 1]
            )
            for boat in range(1, 7)
        },

        "joint": joint,

        "first_probs": first_probs,

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
    candidates = []

    for combo, prob in prediction["joint"].items():

        odd = odds.get(combo)

        if odd is None:
            continue

        if odd <= 0:
            continue

        if prob < min_prob:
            continue

        market_prob = 1.0 / odd

        edge = (
            prob
            - market_prob
        )

        ev = (
            prob * odd
            - 1.0
        )

        if ev <= 0:
            continue

        # -----------------------------------------
        # 的中率最優先
        # EVは補助評価
        # -----------------------------------------

        ev_boost = (
            min(
                max(ev, 0.0),
                1.50
            )
            / 1.50
            * 0.35
        )

        score = (
            prob
            * (1.0 + ev_boost)
        )

        candidates.append(
            {
                "combo": combo,
                "prob": float(prob),
                "odds": float(odd),
                "market_prob": float(
                    market_prob
                ),
                "edge": float(edge),
                "ev": float(ev),
                "score": float(score),
            }
        )

    candidates.sort(
        key=lambda x: (
            x["score"],
            x["prob"],
            x["ev"],
        ),
        reverse=True
    )

    return candidates[:limit]
