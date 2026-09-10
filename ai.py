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

    score += _f(raw.get("national_win_rate")) * 2.2
    score += _f(raw.get("local_win_rate")) * 1.8
    score += _f(raw.get("national_top_2_percent")) * 0.06
    score += _f(raw.get("local_top_2_percent")) * 0.04
    score += _f(raw.get("motor_top_2_percent")) * 0.04
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
    return {
        racer["number"]: _score(racer)
        for racer in racers
    }


def _trifecta_distribution(scores):
    combinations = []

    for a in range(1, 7):
        for b in range(1, 7):
            if b == a:
                continue

            for c in range(1, 7):
                if c == a or c == b:
                    continue

                combinations.append((a, b, c))

    t1 = 12.0
    t2 = 15.0
    t3 = 18.0

    raw = {}

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

    probabilities = {
        combo: weights[combo] / total
        for combo in combinations
    }

    # 極端なAI予想を少し緩和
    uniform = 1.0 / 120.0

    probabilities = {
        combo:
        probabilities[combo] * 0.85
        + uniform * 0.15
        for combo in combinations
    }

    total = sum(probabilities.values())

    return {
        combo: probabilities[combo] / total
        for combo in combinations
    }


def _first_probabilities(trifecta):
    result = {
        i: 0.0
        for i in range(1, 7)
    }

    for combo, probability in trifecta.items():
        result[combo[0]] += probability

    return result


def _confidence(probabilities):
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

        if odd and odd > 0:

            market_probability = 1.0 / odd

            ev = (
                probability * odd
                - 1.0
            )

            item["market_probability"] = (
                market_probability
            )

            item["ev"] = ev
            item["ev_rate"] = ev * 100.0

            item["edge"] = (
                probability
                - market_probability
            )

        result.append(item)

    if odds:
        result.sort(
            key=lambda x:
            -999999
            if x["ev"] is None
            else x["ev"],
            reverse=True,
        )
    else:
        result.sort(
            key=lambda x:
            x["probability"],
            reverse=True,
        )

    return result


def tri_ai(racers, odds=None):
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

    main = ranking[0] if ranking else None

    counter = (
        ranking[1]
        if len(ranking) >= 2
        else None
    )

    hole = None

    if len(ranking) >= 3:

        candidates = [
            x
            for x in ranking
            if x not in [main, counter]
        ]

        hole = max(
            candidates,
            key=lambda x:
            probabilities.get(x, 0.0),
        )

    confidence = _confidence(
        probabilities
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
        "trifecta_candidates": _candidates(
            trifecta,
            odds,
        ),
        "odds": odds,
        "odds_available": len(odds) > 0,
    }
