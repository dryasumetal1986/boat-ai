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
    """
    6艇のAI評価と
    3連単120通りのAI確率を作成。
    """

    boats = race["boats"]

    scores = []

    for boat_data in boats:

        boat = boat_data["boat"]

        score = (
            boat_data["rate"] * 4.2
            + boat_data["local_rate"] * 1.8
            + boat_data["motor"] * 0.8
            + boat_data["course"] * 0.7
            + max(0, 7 - boat) * 1.2
        )

        if boat == 1:
            score += 8.0

        scores.append(max(score, 0.1))

    scores = np.asarray(scores, dtype=float)

    combos = list(
        itertools.permutations(
            range(1, 7),
            3,
        )
    )

    weights = []

    temp_first = 11.0
    temp_second = 9.5
    temp_third = 10.5

    for first, second, third in combos:

        weight = math.exp(
            scores[first - 1] / temp_first
            + scores[second - 1] / temp_second
            + scores[third - 1] / temp_third
        )

        weights.append(weight)

    probabilities = _normalize(weights)

    probabilities = (
        0.96 * probabilities
        + 0.04 / len(probabilities)
    )

    probabilities = _normalize(probabilities)

    joint = {
        combo: float(prob)
        for combo, prob in zip(
            combos,
            probabilities,
        )
    }

    first_probs = {
        i: 0.0
        for i in range(1, 7)
    }

    for combo, prob in joint.items():
        first_probs[combo[0]] += prob

    ranking = sorted(
        first_probs,
        key=first_probs.get,
        reverse=True,
    )

    main = ranking[0]
    counter = ranking[1]
    hole = ranking[2]

    confidence = (
        50.0
        + first_probs[main] * 100.0
    )

    confidence = max(
        55.0,
        min(95.0, confidence),
    )

    # 120通りの中で最も的中確率が高い3連単
    best_combo = max(
        joint,
        key=joint.get,
    )

    return {
        "scores": {
            i + 1: float(scores[i])
            for i in range(6)
        },

        "joint": joint,

        "first_probs": first_probs,

        "ranking": ranking,

        "main": main,

        "counter": counter,

        "hole": hole,

        "best_combo": best_combo,

        "best_combo_prob":
            float(joint[best_combo]),

        "confidence": confidence,
    }


def value_candidates(
    prediction,
    odds,
    min_prob=0.0075,
    limit=8,
):
    """
    的中率重視の3連単候補。

    基本評価：
        的中確率 70%
        期待値   30%

    超高配当だけで上位を独占しないよう
    オッズ過熱補正を入れる。
    """

    candidates = []

    joint = prediction["joint"]

    for combo, probability in joint.items():

        odd = odds.get(combo)

        if not odd:
            continue

        if odd <= 0:
            continue

        # 極端に低確率な買い目を除外
        if probability < min_prob:
            continue

        market_probability = 1.0 / odd

        ev = (
            probability * odd
            - 1.0
        )

        # プラス期待値だけ候補にする
        if ev <= 0:
            continue

        edge = (
            probability
            - market_probability
        )

        # -------------------------
        # 的中率スコア
        # -------------------------

        hit_score = probability

        # -------------------------
        # EVスコア
        #
        # 極端なEVを3.0で頭打ち
        # -------------------------

        ev_score = min(
            max(ev, 0.0),
            3.0,
        ) / 3.0

        # -------------------------
        # 高配当補正
        # -------------------------

        if odd <= 30:
            odds_factor = 1.00

        elif odd <= 50:
            odds_factor = 0.95

        elif odd <= 100:
            odds_factor = 0.88

        elif odd <= 200:
            odds_factor = 0.75

        elif odd <= 500:
            odds_factor = 0.60

        else:
            odds_factor = 0.45

        # -------------------------
        # 最終スコア
        #
        # 的中率70%
        # EV30%
        # -------------------------

        score = (
            hit_score * 0.70
            + ev_score
            * 0.30
            * odds_factor
        )

        candidates.append({
            "combo": combo,
            "prob": probability,
            "odds": odd,
            "ev": ev,
            "market_prob":
                market_probability,
            "edge": edge,
            "score": score,
            "hit_score": hit_score,
            "odds_factor": odds_factor,
        })

    candidates.sort(
        key=lambda x: (
            x["score"],
            x["prob"],
            x["ev"],
        ),
        reverse=True,
    )

    return candidates[:limit]
