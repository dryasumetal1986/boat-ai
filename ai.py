import itertools
import math

import numpy as np


def _normalize(values):
    """
    数値を合計1の確率に変換
    """

    arr = np.asarray(
        values,
        dtype=float,
    )

    arr = np.maximum(
        arr,
        0.0,
    )

    total = arr.sum()

    if total <= 0:
        return np.ones(
            len(arr)
        ) / len(arr)

    return arr / total


def predict_race(race):
    """
    6艇のAI評価と
    3連単120通りのAI確率を作成
    """

    boats = race["boats"]

    scores = []

    # -------------------------
    # 各艇のAIスコア
    # -------------------------

    for boat_data in boats:

        boat = boat_data["boat"]

        score = (
            boat_data["rate"] * 4.2
            + boat_data["local_rate"] * 1.8
            + boat_data["motor"] * 0.8
            + boat_data["course"] * 0.7
            + max(0, 7 - boat) * 1.2
        )

        # 1コースを少し重視
        if boat == 1:
            score += 8.0

        scores.append(
            max(score, 0.1)
        )

    scores = np.asarray(
        scores,
        dtype=float,
    )

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

    # 極端な穴がEVだけで
    # 上位を独占しないように
    # 着順ごとに温度を設定
    temp_first = 11.0
    temp_second = 9.5
    temp_third = 10.5

    for first, second, third in combos:

        weight = math.exp(
            scores[first - 1]
            / temp_first
            + scores[second - 1]
            / temp_second
            + scores[third - 1]
            / temp_third
        )

        weights.append(weight)

    probabilities = _normalize(
        weights
    )

    # -------------------------
    # 少量の確率フロア
    # -------------------------

    probabilities = (
        0.96 * probabilities
        + 0.04 / len(probabilities)
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
    # 1着確率
    # -------------------------

    first_probs = {
        1: 0.0,
        2: 0.0,
        3: 0.0,
        4: 0.0,
        5: 0.0,
        6: 0.0,
    }

    for combo, prob in joint.items():

        first = combo[0]

        first_probs[first] += prob

    # -------------------------
    # 1着AIランキング
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
    # AI信頼度
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

        "confidence": confidence,
    }


def value_candidates(
    prediction,
    odds,
    min_prob=0.01,
    limit=8,
):
    """
    実オッズを使った期待値候補。

    ただし、
    AI確率が1.0%未満の超低確率買い目は
    EVランキングから除外する。

    これにより、

    「AI確率0.5% × 2000倍」

    のような超穴だけが
    EV上位を独占するのを防ぐ。
    """

    candidates = []

    joint = prediction["joint"]

    for combo, probability in joint.items():

        odd = odds.get(combo)

        if not odd:
            continue

        if odd <= 0:
            continue

        # 低すぎるAI確率はEV候補から除外
        if probability < min_prob:
            continue

        # -------------------------
        # 期待値
        #
        # EV = AI確率 × オッズ - 1
        # -------------------------

        ev = (
            probability * odd
            - 1.0
        )

        if ev <= 0:
            continue

        # オッズから逆算した市場確率
        market_probability = (
            1.0 / odd
        )

        # AIと市場の確率差
        edge = (
            probability
            - market_probability
        )

        candidates.append({
            "combo": combo,

            "prob": probability,

            "odds": odd,

            "ev": ev,

            "market_prob":
                market_probability,

            "edge": edge,
        })

    # EVが高い順
    candidates.sort(
        key=lambda x: x["ev"],
        reverse=True,
    )

    return candidates[:limit]
