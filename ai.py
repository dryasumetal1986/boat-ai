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
    6艇AI評価と3連単120通りを計算。

    的中率を最優先し、
    1着・2着・3着を別々に評価する。
    """

    boats = race["boats"]

    scores = {}

    for boat_data in boats:

        boat = boat_data["boat"]

        score = (
            boat_data["rate"] * 4.2
            + boat_data["local_rate"] * 1.8
            + boat_data["motor"] * 0.8
            + boat_data["course"] * 0.7
            + max(0, 7 - boat) * 1.2
        )

        # 1コース優位
        if boat == 1:
            score += 8.0

        scores[boat] = max(
            score,
            0.1,
        )

    # -------------------------
    # 1着確率
    # -------------------------

    first_raw = {}

    for boat, score in scores.items():

        bonus = 0.0

        if boat == 1:
            bonus = 3.0

        first_raw[boat] = math.exp(
            (score + bonus) / 10.0
        )

    first_probs = _normalize(
        list(first_raw.values())
    )

    first_probs = {
        boat: float(prob)
        for boat, prob in zip(
            first_raw.keys(),
            first_probs,
        )
    }

    # -------------------------
    # 3連単120通り
    # -------------------------

    combos = list(
        itertools.permutations(
            range(1, 7),
            3,
        )
    )

    weights = []

    for first, second, third in combos:

        # 1着を最重要
        first_score = (
            first_probs[first] ** 1.60
        )

        # 2着
        second_score = (
            first_probs[second] ** 0.90
        )

        # 3着
        third_score = (
            first_probs[third] ** 0.65
        )

        weight = (
            first_score
            * second_score
            * third_score
        )

        # 1号艇の1着をさらに少し優遇
        if first == 1:
            weight *= 1.20

        # 2号艇・3号艇の2着を少し優遇
        if second in (2, 3):
            weight *= 1.05

        # 5・6号艇の1着は
        # AI確率が十分高い場合だけ残す
        if first in (5, 6):
            if first_probs[first] < 0.12:
                weight *= 0.55

        weights.append(weight)

    probabilities = _normalize(
        weights
    )

    # 最低確率フロア
    probabilities = (
        0.985 * probabilities
        + 0.015 / len(probabilities)
    )

    probabilities = _normalize(
        probabilities
    )

    joint = {
        combo: float(prob)
        for combo, prob in zip(
            combos,
            probabilities,
        )
    }

    # -------------------------
    # 1着ランキング
    # -------------------------

    ranking = sorted(
        first_probs,
        key=first_probs.get,
        reverse=True,
    )

    main = ranking[0]
    counter = ranking[1]
    hole = ranking[2]

    # -------------------------
    # 本命を1着にした場合の
    # 最有力3連単
    # -------------------------

    main_combos = {
        combo: prob
        for combo, prob in joint.items()
        if combo[0] == main
    }

    main_best_combo = max(
        main_combos,
        key=main_combos.get,
    )

    # 全体最高確率
    best_combo = max(
        joint,
        key=joint.get,
    )

    # -------------------------
    # 信頼度
    # -------------------------

    confidence = (
        50.0
        + first_probs[main] * 100.0
    )

    confidence = max(
        55.0,
        min(
            95.0,
            confidence,
        ),
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
        "best_combo_prob":
            float(joint[best_combo]),
        "main_best_combo":
            main_best_combo,
        "main_best_combo_prob":
            float(joint[main_best_combo]),
        "confidence": confidence,
    }


def value_candidates(
    prediction,
    odds,
    min_prob=0.006,
    limit=8,
):
    """
    的中率最優先の期待値候補。

    高配当だけで上位を独占しない。
    """

    candidates = []

    joint = prediction["joint"]

    for combo, probability in joint.items():

        odd = odds.get(combo)

        if not odd or odd <= 0:
            continue

        if probability < min_prob:
            continue

        market_probability = 1.0 / odd

        ev = (
            probability * odd
            - 1.0
        )

        if ev <= 0:
            continue

        edge = (
            probability
            - market_probability
        )

        # -------------------------
        # 的中率
        # -------------------------

        hit_score = probability

        # -------------------------
        # EV
        # 高すぎるEVは頭打ち
        # -------------------------

        ev_score = min(
            max(ev, 0.0),
            2.0,
        ) / 2.0

        # -------------------------
        # オッズ補正
        # -------------------------

        if odd <= 30:
            odds_factor = 1.00

        elif odd <= 50:
            odds_factor = 0.97

        elif odd <= 100:
            odds_factor = 0.90

        elif odd <= 200:
            odds_factor = 0.78

        elif odd <= 300:
            odds_factor = 0.65

        elif odd <= 500:
            odds_factor = 0.50

        else:
            odds_factor = 0.30

        # -------------------------
        # 最終評価
        #
        # 的中率を強くする
        # -------------------------

        score = (
            hit_score * 0.80
            + ev_score
            * 0.20
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
        })

    candidates.sort(
        key=lambda x: (
            x["score"],
            x["prob"],
            x["edge"],
        ),
        reverse=True,
    )

    return candidates[:limit]
