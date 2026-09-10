import itertools
import math

import numpy as np


def _clip(value, low=0.0, high=1.0):
    return max(
        low,
        min(
            high,
            float(value),
        ),
    )


def _softmax(values, temperature=1.0):
    arr = np.asarray(
        values,
        dtype=float,
    )

    arr = np.nan_to_num(
        arr,
        nan=0.0,
        posinf=20.0,
        neginf=-20.0,
    )

    temperature = max(
        0.10,
        float(temperature),
    )

    arr = arr / temperature

    arr -= np.max(arr)

    exp = np.exp(
        np.clip(
            arr,
            -30,
            30,
        )
    )

    total = exp.sum()

    if total <= 0:
        return np.ones(
            len(arr)
        ) / len(arr)

    return exp / total


def _relative_low(
    value,
    values,
    default=0.5,
):
    """
    小さいほど良い指標を
    0〜1へ変換。

    ST・展示タイム用。
    """

    vals = [
        float(x)
        for x in values
        if float(x) > 0
    ]

    value = float(value)

    if value <= 0 or not vals:
        return default

    lo = min(vals)
    hi = max(vals)

    if hi <= lo:
        return default

    score = (
        (hi - value)
        / (hi - lo)
    )

    return _clip(score)


def _boat_score(
    boat,
    boats,
):
    """
    1艇の総合スコア。

    的中率重視なので、
    実績データを中心にする。

    EVはここでは一切使わない。
    """

    course = _clip(
        boat.get(
            "course_score",
            0.5,
        )
    )

    national_win = _clip(
        boat.get(
            "national_win_rate",
            0.0,
        ) / 10.0
    )

    national_top2 = _clip(
        boat.get(
            "national_top2",
            0.0,
        ) / 100.0
    )

    national_top3 = _clip(
        boat.get(
            "national_top3",
            0.0,
        ) / 100.0
    )

    local_win = _clip(
        boat.get(
            "local_win_rate",
            0.0,
        ) / 10.0
    )

    local_top2 = _clip(
        boat.get(
            "local_top2",
            0.0,
        ) / 100.0
    )

    local_top3 = _clip(
        boat.get(
            "local_top3",
            0.0,
        ) / 100.0
    )

    motor_top2 = _clip(
        boat.get(
            "motor_top2",
            0.0,
        ) / 100.0
    )

    motor_top3 = _clip(
        boat.get(
            "motor_top3",
            0.0,
        ) / 100.0
    )

    boat_top2 = _clip(
        boat.get(
            "boat_top2",
            0.0,
        ) / 100.0
    )

    boat_top3 = _clip(
        boat.get(
            "boat_top3",
            0.0,
        ) / 100.0
    )

    avg_st = boat.get(
        "average_start",
        0.0,
    )

    start_values = [
        x.get(
            "average_start",
            0.0,
        )
        for x in boats
    ]

    st_score = _relative_low(
        avg_st,
        start_values,
        default=0.5,
    )

    exhibition = boat.get(
        "exhibition_time",
        0.0,
    )

    exhibition_values = [
        x.get(
            "exhibition_time",
            0.0,
        )
        for x in boats
    ]

    exhibition_score = _relative_low(
        exhibition,
        exhibition_values,
        default=0.5,
    )

    direct_start = boat.get(
        "start_timing",
        0.0,
    )

    direct_values = [
        x.get(
            "start_timing",
            0.0,
        )
        for x in boats
    ]

    direct_score = _relative_low(
        direct_start,
        direct_values,
        default=0.5,
    )

    flying = boat.get(
        "flying_count",
        0,
    )

    late = boat.get(
        "late_count",
        0,
    )

    risk_penalty = (
        min(flying, 2) * 0.015
        + min(late, 2) * 0.010
    )

    score = (
        course * 0.22
        + national_win * 0.18
        + national_top2 * 0.11
        + national_top3 * 0.08
        + local_win * 0.10
        + local_top2 * 0.06
        + local_top3 * 0.04
        + motor_top2 * 0.06
        + motor_top3 * 0.04
        + boat_top2 * 0.025
        + boat_top3 * 0.015
        + st_score * 0.025
        + direct_score * 0.015
        + exhibition_score * 0.025
        - risk_penalty
    )

    return max(
        0.01,
        score * 10.0,
    )


def _plackett_luce(
    scores,
):
    """
    1着→2着→3着を順番に選ぶ
    Plackett-Luce型の3連単確率。

    単純な
    P1 × P2 × P3
    より順位関係を自然に扱える。
    """

    boats = sorted(
        scores.keys()
    )

    joint = {}

    for a, b, c in itertools.permutations(
        boats,
        3,
    ):
        remaining1 = [
            x
            for x in boats
            if x != a
        ]

        denom1 = sum(
            scores[x]
            for x in boats
        )

        if denom1 <= 0:
            continue

        p1 = (
            scores[a]
            / denom1
        )

        denom2 = sum(
            scores[x]
            for x in remaining1
        )

        if denom2 <= 0:
            continue

        p2 = (
            scores[b]
            / denom2
        )

        remaining2 = [
            x
            for x in remaining1
            if x != b
        ]

        denom3 = sum(
            scores[x]
            for x in remaining2
        )

        if denom3 <= 0:
            continue

        p3 = (
            scores[c]
            / denom3
        )

        joint[
            (a, b, c)
        ] = (
            p1 * p2 * p3
        )

    total = sum(
        joint.values()
    )

    if total > 0:
        for combo in joint:
            joint[combo] /= total

    return joint


def _confidence(
    first_probs,
):
    ordered = sorted(
        first_probs.values(),
        reverse=True,
    )

    top = ordered[0]
    second = ordered[1]

    gap = max(
        0.0,
        top - second,
    )

    entropy = 0.0

    for p in ordered:
        if p > 0:
            entropy -= (
                p * math.log(p)
            )

    max_entropy = math.log(6)

    concentration = (
        1.0
        - entropy
        / max_entropy
    )

    value = (
        55.0
        + top * 35.0
        + gap * 80.0
        + concentration * 25.0
    )

    return max(
        55.0,
        min(
            95.0,
            value,
        ),
    )


def _select_three_tickets(
    joint,
    ranking,
):
    """
    3点を的中率優先で選ぶ。

    本線:
        AI確率1位

    対抗:
        AI確率2位

    穴:
        4〜6位の艇を最低1艇含む中で
        最も確率の高い組み合わせ

    EVは使用しない。
    """

    ordered = sorted(
        joint.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    if not ordered:
        return []

    main = ordered[0][0]

    counter = None

    for combo, prob in ordered:
        if combo != main:
            counter = combo
            break

    hole = None

    lower_boats = set(
        ranking[3:]
    )

    for combo, prob in ordered:
        if combo in {
            main,
            counter,
        }:
            continue

        if lower_boats.intersection(
            combo
        ):
            hole = combo
            break

    selected = []

    if main:
        selected.append(main)

    if counter:
        selected.append(counter)

    if hole:
        selected.append(hole)

    for combo, prob in ordered:
        if len(selected) >= 3:
            break

        if combo not in selected:
            selected.append(combo)

    return selected[:3]


def predict_race(race):
    boats = race.get(
        "boats",
        []
    )

    if len(boats) != 6:
        return {
            "main": 1,
            "counter": 2,
            "hole": 3,
            "confidence": 55.0,
            "first_probs": {
                i: 1 / 6
                for i in range(1, 7)
            },
            "ranking": list(
                range(1, 7)
            ),
            "scores": {
                i: 1.0
                for i in range(1, 7)
            },
            "joint": {},
            "tickets": [],
        }

    scores = {}

    for boat in boats:
        number = int(
            boat["boat"]
        )

        scores[number] = (
            _boat_score(
                boat,
                boats,
            )
        )

    raw_probs = _softmax(
        list(
            scores.values()
        ),
        temperature=0.75,
    )

    numbers = list(
        scores.keys()
    )

    first_probs = {
        boat: float(
            raw_probs[i]
        )
        for i, boat in enumerate(
            numbers
        )
    }

    ranking = sorted(
        numbers,
        key=lambda x: first_probs[x],
        reverse=True,
    )

    joint = _plackett_luce(
        scores
    )

    tickets = _select_three_tickets(
        joint,
        ranking,
    )

    main = (
        tickets[0]
        if len(tickets) > 0
        else (ranking[0], ranking[1], ranking[2])
    )

    counter = (
        tickets[1]
        if len(tickets) > 1
        else main
    )

    hole = (
        tickets[2]
        if len(tickets) > 2
        else main
    )

    confidence = _confidence(
        first_probs
    )

    return {
        "main": main[0],
        "counter": counter[0],
        "hole": hole[0],

        "confidence": float(
            confidence
        ),

        "first_probs": first_probs,

        "ranking": ranking,

        "scores": scores,

        "joint": joint,

        "tickets": tickets,
    }


def recommend_bets(
    prediction,
    odds=None,
):
    """
    本線・対抗・穴の3点。

    AI確率が最優先。
    オッズは表示用の補助情報だけ。

    EVで買い目を入れ替えない。
    """

    odds = odds or {}

    rows = []

    labels = [
        "本線",
        "対抗",
        "穴",
    ]

    tickets = prediction.get(
        "tickets",
        [],
    )

    for i, combo in enumerate(
        tickets[:3]
    ):
        prob = float(
            prediction["joint"].get(
                combo,
                0.0,
            )
        )

        odd = float(
            odds.get(
                combo,
                0.0,
            )
        )

        market_prob = (
            1.0 / odd
            if odd > 0
            else 0.0
        )

        ev = (
            prob * odd - 1.0
            if odd > 0
            else 0.0
        )

        rows.append(
            {
                "label": labels[i],
                "combo": combo,
                "prob": prob,
                "odds": odd,
                "market_prob": market_prob,
                "ev": ev,
            }
        )

    return rows


def value_candidates(
    prediction,
    odds,
    min_prob=0.0,
    limit=8,
):
    """
    互換用。

    旧UIから呼ばれても、
    AI確率順で返す。

    EVは選定条件にしない。
    """

    rows = []

    for combo, odd in (
        odds or {}
    ).items():

        prob = float(
            prediction["joint"].get(
                combo,
                0.0,
            )
        )

        if prob < min_prob:
            continue

        try:
            odd = float(odd)
        except Exception:
            continue

        if odd <= 0:
            continue

        rows.append(
            {
                "combo": combo,
                "odds": odd,
                "prob": prob,
                "market_prob": 1.0 / odd,
                "ev": (
                    prob * odd
                    - 1.0
                ),
                "edge": (
                    prob
                    - 1.0 / odd
                ),
                "score": prob,
            }
        )

    rows.sort(
        key=lambda x: x["prob"],
        reverse=True,
    )

    return rows[:limit]
