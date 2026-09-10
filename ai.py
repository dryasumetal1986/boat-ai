import math

import numpy as np


def _f(value):
    try:
        return float(value)
    except Exception:
        return 0.0


def _score(racer):
    raw = racer.get("raw", {})
    number = racer["number"]

    score = 0.0

    # 全国成績
    score += _f(raw.get("national_win_rate")) * 2.2

    # 当地成績
    score += _f(raw.get("local_win_rate")) * 1.8

    # 全国2連対率
    score += _f(raw.get("national_top_2_percent")) * 0.06

    # 当地2連対率
    score += _f(raw.get("local_top_2_percent")) * 0.04

    # モーター2連対率
    score += _f(raw.get("motor_top_2_percent")) * 0.04

    # ボート2連対率
    score += _f(raw.get("boat_top_2_percent")) * 0.02

    # コース補正
    course_bonus = {
        1: 15.0,
        2: 8.0,
        3: 6.0,
        4: 4.0,
        5: 2.0,
        6: 0.0,
    }

    score += course_bonus.get(number, 0.0)

    return score


def _scores(racers):
    result = {}

    for racer in racers:
        result[racer["number"]] = _score(racer)

    return result


def _trifecta_distribution(scores):
    """
    6艇から3連単120通りを生成。

    各組み合わせを独立に作ったあと、
    120通り全体に対してsoftmaxを行うため、
    3連単確率の合計は必ず100%になる。

    さらに15%を均等分配して、
    極端な確率集中を少し抑える。
    """

    combinations = []

    for a in range(1, 7):
        for b in range(1, 7):
            if b == a:
                continue

            for c in range(1, 7):
                if c == a or c == b:
                    continue

                combinations.append((a, b, c))

    raw = {}

    t1 = 12.0
    t2 = 15.0
    t3 = 18.0

    for combo in combinations:
        a, b, c = combo

        value = (
            scores.get(a, 0.0) / t1
            + scores.get(b, 0.0) / t2
            + scores.get(c, 0.0) / t3
        )

        raw[combo] = value

    maximum = max(raw.values())

    weights = {
        combo: math.exp(value - maximum)
        for combo, value in raw.items()
    }

    total = sum(weights.values())

    if total <= 0:
        uniform = 1.0 / len(combinations)
        return {
            combo: uniform
            for combo in combinations
        }

    probabilities = {
        combo: weights[combo] / total
        for combo in combinations
    }

    # 極端な確率集中を抑える
    uniform = 1.0 / 120.0

    probabilities = {
        combo: probabilities[combo] * 0.85
        + uniform * 0.15
        for combo in combinations
    }

    # 最終的に誤差なく100%へ正規化
    total = sum(probabilities.values())

    return {
        combo: probabilities[combo] / total
        for combo in combinations
    }


def _first_probabilities(trifecta):
    """
    120通りの3連単確率から、
    1着艇別の確率を集計する。

    合計は100%になる。
    """

    result = {
        i: 0.0
        for i in range(1, 7)
    }

    for combo, probability in trifecta.items():
        first = combo[0]
        result[first] += probability

    total = sum(result.values())

    if total <= 0:
        return result

    return {
        boat: probability / total
        for boat, probability in result.items()
    }


def _confidence(probabilities):
    """
    6艇の1着確率分布のエントロピーから
    AI信頼度を算出。
    """

    values = np.array(
        list(probabilities.values()),
        dtype=float,
    )

    values = np.clip(
        values,
        1e-12,
        1.0,
    )

    entropy = -np.sum(
        values * np.log(values)
    )

    maximum = math.log(6)

    if maximum <= 0:
        certainty = 0.0
    else:
        certainty = 1.0 - (
            entropy / maximum
        )

    confidence = (
        0.55
        + certainty * 0.40
    )

    return float(
        np.clip(
            confidence,
            0.55,
            0.95,
        )
    )


def _candidates(trifecta, odds):
    """
    3連単120通りについて、

    - AI確率
    - 公式オッズ
    - 市場確率 = 1 / オッズ
    - EV
    - Edge

    を計算。

    EV:
        AI確率 × オッズ - 1

    Edge:
        AI確率 - 市場確率
    """

    result = []

    for combo, probability in trifecta.items():

        odd = odds.get(combo)

        item = {
            "combination": combo,
            "probability": probability,
            "odds": odd,
            "ev": None,
            "ev_rate": None,
            "market_probability": None,
            "edge": None,
        }

        if odd is not None and odd > 0:

            market_probability = 1.0 / odd

            ev = (
                probability * odd
                - 1.0
            )

            item["market_probability"] = (
                market_probability
            )

            item["ev"] = ev

            item["ev_rate"] = (
                ev * 100.0
            )

            item["edge"] = (
                probability
                - market_probability
            )

        result.append(item)

    if odds:
        result.sort(
            key=lambda x: (
                -999999999
                if x["ev"] is None
                else x["ev"]
            ),
            reverse=True,
        )
    else:
        result.sort(
            key=lambda x: x["probability"],
            reverse=True,
        )

    return result


def tri_ai(racers, odds=None):
    """
    メインAI。

    戻り値:
        scores
        probabilities
        ranking
        main
        counter
        hole
        confidence
        trifecta_probabilities
        trifecta_candidates
        odds
        odds_available
    """

    odds = odds or {}

    if not racers:
        return {
            "scores": {},
            "probabilities": {},
            "ranking": [],
            "main": None,
            "counter": None,
            "hole": None,
            "confidence": 0.55,
            "trifecta_probabilities": {},
            "trifecta_candidates": [],
            "odds": {},
            "odds_available": False,
        }

    scores = _scores(racers)

    ranking = sorted(
        scores.keys(),
        key=lambda x: scores[x],
        reverse=True,
    )

    trifecta = _trifecta_distribution(
        scores
    )

    probabilities = _first_probabilities(
        trifecta
    )

    main = (
        ranking[0]
        if ranking
        else None
    )

    counter = (
        ranking[1]
        if len(ranking) >= 2
        else None
    )

    hole = None

    if len(ranking) >= 3:

        remaining = [
            x
            for x in ranking
            if x not in (
                main,
                counter,
            )
        ]

        # 穴は残った艇の中で
        # 1着確率が最も高い艇
        hole = max(
            remaining,
            key=lambda x: probabilities.get(
                x,
                0.0,
            ),
        )

    confidence = _confidence(
        probabilities
    )

    candidates = _candidates(
        trifecta,
        odds,
    )

    return {
        "scores": scores,
        "probabilities": probabilities,
        "ranking": ranking,
        "main": main,
        "counter": counter,
        "hole": hole,
        "confidence": confidence,
        "trifecta_probabilities": trifecta,
        "trifecta_candidates": candidates,
        "odds": odds,
        "odds_available": len(odds) > 0,
    }
