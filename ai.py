import itertools
import math
import numpy as np


def _normalize(values):
    arr = np.asarray(values, dtype=float)
    arr = np.maximum(arr, 0.0)
    total = arr.sum()

    if total <= 0:
        return np.ones(len(arr)) / len(arr)

    return arr / total


def predict_race(race):
    boats = race["boats"]

    scores = {}

    for b in boats:
        no = b["boat"]

        score = (
            b["rate"] * 4.2
            + b["local_rate"] * 1.8
            + b["motor"] * 0.8
            + b["course"] * 0.7
            + max(0, 7 - no) * 1.2
        )

        if no == 1:
            score += 8.0

        scores[no] = max(score, 0.1)

    # 1着評価
    raw = {}

    for no, score in scores.items():
        bonus = 3.0 if no == 1 else 0.0
        raw[no] = math.exp((score + bonus) / 10.0)

    first_values = _normalize(
        [raw[i] for i in range(1, 7)]
    )

    first_probs = {
        i: float(first_values[i - 1])
        for i in range(1, 7)
    }

    # 3連単120通り
    combos = list(
        itertools.permutations(range(1, 7), 3)
    )

    weights = []

    for first, second, third in combos:
        weight = (
            first_probs[first] ** 1.60
            * first_probs[second] ** 0.90
            * first_probs[third] ** 0.65
        )

        # インコース1着を少し優先
        if first == 1:
            weight *= 1.20

        # 2・3号艇の2着を少し優先
        if second in (2, 3):
            weight *= 1.05

        # 5・6号艇頭の暴走を抑制
        if first in (5, 6):
            if first_probs[first] < 0.12:
                weight *= 0.55

        weights.append(weight)

    probs = _normalize(weights)

    probs = (
        0.985 * probs
        + 0.015 / len(probs)
    )

    probs = _normalize(probs)

    joint = {
        combo: float(prob)
        for combo, prob in zip(combos, probs)
    }

    ranking = sorted(
        first_probs,
        key=first_probs.get,
        reverse=True,
    )

    main = ranking[0]
    counter = ranking[1]
    hole = ranking[2]

    # 本命を1着にした最有力買い目
    main_combos = {
        c: p
        for c, p in joint.items()
        if c[0] == main
    }

    main_best_combo = max(
        main_combos,
        key=main_combos.get,
    )

    best_combo = max(
        joint,
        key=joint.get,
    )

    # 信頼度
    # 1着確率だけで95%にならないようにする
    concentration = (
        first_probs[main] - 1 / 6
    )

    confidence = (
        55.0
        + concentration * 75.0
    )

    confidence = max(
        55.0,
        min(90.0, confidence),
    )

    return {
        "scores": scores,
        "joint": joint,
        "first_probs": first_probs,
        "ranking": ranking,
        "main": main,
        "counter": counter,
        "hole": hole,
        "best_combo": best_combo,
        "best_combo_prob": joint[best_combo],
        "main_best_combo": main_best_combo,
        "main_best_combo_prob":
            joint[main_best_combo],
        "confidence": confidence,
    }


def value_candidates(
    prediction,
    odds,
    min_prob=0.006,
    limit=8,
):
    """
    的中率を最優先した期待値候補。

    的中率 80%
    EV    20%

    高配当ほど補正を強くする。
    """

    raw = []

    for combo, prob in prediction["joint"].items():

        odd = odds.get(combo)

        if not odd or odd <= 0:
            continue

        if prob < min_prob:
            continue

        market_prob = 1.0 / odd

        ev = prob * odd - 1.0

        if ev <= 0:
            continue

        edge = prob - market_prob

        if odd <= 30:
            odds_factor = 1.00
        elif odd <= 50:
            odds_factor = 0.95
        elif odd <= 100:
            odds_factor = 0.85
        elif odd <= 200:
            odds_factor = 0.70
        elif odd <= 300:
            odds_factor = 0.55
        elif odd <= 500:
            odds_factor = 0.40
        else:
            odds_factor = 0.20

        # EVの暴走を抑える
        ev_score = min(
            max(ev, 0.0),
            2.0,
        ) / 2.0

        # 的中率を主役にする
        score = (
            prob * 0.80
            + ev_score
            * 0.20
            * odds_factor
        )

        raw.append({
            "combo": combo,
            "prob": prob,
            "odds": odd,
            "ev": ev,
            "market_prob": market_prob,
            "edge": edge,
            "score": score,
        })

    raw.sort(
        key=lambda x: (
            x["score"],
            x["prob"],
            x["edge"],
        ),
        reverse=True,
    )

    return raw[:limit]
