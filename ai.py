import math
import numpy as np


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _get_score(racer):
    raw = racer.get("raw", {})

    score = 0.0

    # APIに存在する可能性のある情報を利用
    for key, weight in [
        ("national_win_rate", 1.0),
        ("local_win_rate", 1.2),
        ("motor_second_rate", 0.8),
        ("boat_second_rate", 0.5),
    ]:
        value = raw.get(key)

        if value is not None:
            score += _safe_float(value) * weight

    # 既存APIの別名にも対応
    for key, weight in [
        ("national_win", 1.0),
        ("local_win", 1.2),
        ("motor_2ren", 0.8),
        ("boat_2ren", 0.5),
    ]:
        value = raw.get(key)

        if value is not None:
            score += _safe_float(value) * weight

    # コース有利
    number = racer.get("number", 0)

    course_bonus = {
        1: 16.0,
        2: 8.0,
        3: 6.0,
        4: 4.0,
        5: 2.0,
        6: 0.0,
    }

    score += course_bonus.get(number, 0.0)

    # 選手データが少ない場合でも順位差を作る
    score += max(0.0, 7.0 - number) * 0.7

    return score


def _make_scores(racers):
    result = {}

    for racer in racers:
        number = racer["number"]
        result[number] = _get_score(racer)

    # データがほぼ無い場合でも最低限のコース差を確保
    if len(result) >= 2:
        values = list(result.values())

        if max(values) - min(values) < 1.0:
            for number in result:
                result[number] += {
                    1: 6.0,
                    2: 3.0,
                    3: 2.0,
                    4: 1.0,
                    5: 0.5,
                    6: 0.0,
                }.get(number, 0.0)

    return result


def _softmax(values, temperature=10.0):
    keys = list(values.keys())

    arr = np.array(
        [values[k] for k in keys],
        dtype=float,
    )

    arr = arr / max(temperature, 0.1)

    arr -= np.max(arr)

    exp = np.exp(arr)

    total = exp.sum()

    if total <= 0:
        p = np.ones(len(keys)) / len(keys)
    else:
        p = exp / total

    return dict(zip(keys, p))


def _all_trifecta():
    result = []

    for a in range(1, 7):
        for b in range(1, 7):
            if b == a:
                continue

            for c in range(1, 7):
                if c == a or c == b:
                    continue

                result.append((a, b, c))

    return result


def _build_trifecta_distribution(scores):
    """
    120通りの3連単確率を直接生成する。

    1着・2着・3着で温度を変えて、
    その後120通りを正規化する。

    さらに15%を均等分布に混ぜて
    AIの過剰確信を抑える。
    """

    combinations = _all_trifecta()

    # 1着を最重要。
    # 2着、3着ほど少し平坦にする。
    t1 = 12.0
    t2 = 15.0
    t3 = 18.0

    raw_weights = {}

    for a, b, c in combinations:
        value = (
            scores.get(a, 0.0) / t1
            + scores.get(b, 0.0) / t2
            + scores.get(c, 0.0) / t3
        )

        raw_weights[(a, b, c)] = value

    max_value = max(raw_weights.values())

    weights = {}

    for combo, value in raw_weights.items():
        weights[combo] = math.exp(value - max_value)

    total = sum(weights.values())

    if total <= 0:
        base = 1.0 / len(combinations)
        probabilities = {
            combo: base
            for combo in combinations
        }
    else:
        probabilities = {
            combo: weights[combo] / total
            for combo in combinations
        }

    # 15%均等分布を混ぜる
    uniform = 1.0 / 120.0

    probabilities = {
        combo: (
            0.85 * probabilities[combo]
            + 0.15 * uniform
        )
        for combo in combinations
    }

    # 最終正規化
    total = sum(probabilities.values())

    probabilities = {
        combo: probabilities[combo] / total
        for combo in combinations
    }

    return probabilities


def _first_place_probabilities(trifecta_probabilities):
    result = {
        number: 0.0
        for number in range(1, 7)
    }

    for (a, b, c), probability in trifecta_probabilities.items():
        result[a] += probability

    return result


def _confidence(first_probs):
    values = np.array(
        list(first_probs.values()),
        dtype=float,
    )

    values = np.clip(values, 1e-12, 1.0)

    entropy = -np.sum(
        values * np.log(values)
    )

    max_entropy = math.log(6)

    certainty = 1.0 - (
        entropy / max_entropy
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


def make_trifecta_candidates(
    trifecta_probabilities,
    odds=None,
):
    candidates = []

    odds = odds or {}

    for combo, probability in trifecta_probabilities.items():
        odd = odds.get(combo)

        item = {
            "combination": combo,
            "probability": float(probability),
            "odds": odd,
        }

        if odd is not None and odd > 0:
            market_probability = 1.0 / odd

            ev = (
                probability * odd
            ) - 1.0

            item["market_probability"] = (
                market_probability
            )

            item["ev"] = ev
            item["ev_rate"] = ev * 100.0
            item["expected_return"] = (
                probability * odd * 100.0
            )

            item["edge"] = (
                probability
                - market_probability
            )

        else:
            item["market_probability"] = None
            item["ev"] = None
            item["ev_rate"] = None
            item["expected_return"] = None
            item["edge"] = None

        candidates.append(item)

    if odds:
        candidates.sort(
            key=lambda x: (
                -999999
                if x["ev"] is None
                else x["ev"]
            ),
            reverse=True,
        )
    else:
        candidates.sort(
            key=lambda x: x["probability"],
            reverse=True,
        )

    return candidates


def tri_ai(racers, odds=None):
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
            "odds": odds or {},
            "odds_available": bool(odds),
        }

    scores = _make_scores(racers)

    # 120通りから1着確率を算出
    trifecta_probabilities = (
        _build_trifecta_distribution(scores)
    )

    probabilities = (
        _first_place_probabilities(
            trifecta_probabilities
        )
    )

    ranking = sorted(
        scores.keys(),
        key=lambda x: scores[x],
        reverse=True,
    )

    main = ranking[0] if ranking else None
    counter = ranking[1] if len(ranking) >= 2 else None

    # 穴は本命・対抗と別にする
    hole = None

    if len(ranking) >= 3:
        remaining = ranking[2:]

        hole = max(
            remaining,
            key=lambda x: probabilities.get(
                x,
                0.0,
            ),
        )

    confidence = _confidence(probabilities)

    candidates = make_trifecta_candidates(
        trifecta_probabilities,
        odds=odds,
    )

    return {
        "scores": scores,
        "probabilities": probabilities,
        "ranking": ranking,
        "main": main,
        "counter": counter,
        "hole": hole,
        "confidence": confidence,
        "trifecta_probabilities": (
            trifecta_probabilities
        ),
        "trifecta_candidates": candidates,
        "odds": odds or {},
        "odds_available": bool(odds),
        }
