import itertools
import math


def _norm(values):
    arr = []
    for value in values:
        try:
            value = float(value)
        except Exception:
            value = 0.0
        if not math.isfinite(value):
            value = 0.0
        arr.append(max(value, 0.0))

    total = sum(arr)

    if total <= 0:
        return [1.0 / len(arr)] * len(arr)

    return [x / total for x in arr]


def _safe_float(value, default=0.0):
    try:
        value = float(value)
        if math.isfinite(value):
            return value
    except Exception:
        pass
    return default


def predict_race(race):
    """
    6艇の強さを計算し、
    1着確率と120通りの3連単確率を作る。

    今回は「期待値」ではなく
    AI的中確率を中心にする。
    """

    boats = race.get("boats", [])

    if len(boats) < 6:
        boats = list(boats)

    scores = {}

    for b in boats:
        boat = int(b.get("boat", 0))

        if boat < 1 or boat > 6:
            continue

        win_rate = _safe_float(
            b.get("win_rate", 0.0)
        )

        local_rate = _safe_float(
            b.get("local_rate", 0.0)
        )

        motor_rate = _safe_float(
            b.get("motor_rate", 0.0)
        )

        course_score = _safe_float(
            b.get("course_score", 0.0)
        )

        # --------------------------------
        # 基本AIスコア
        # --------------------------------
        #
        # 全国成績を中心に、
        # 当地・モーター・コースを加味。
        #
        score = (
            win_rate * 0.55
            + local_rate * 0.20
            + motor_rate * 0.10
            + course_score * 0.15
        )

        scores[boat] = score

    # 6艇すべて無い場合
    for boat in range(1, 7):
        if boat not in scores:
            scores[boat] = 0.0

    # 全艇ほぼ0なら
    # 1号艇を少し有利にする基本モデル
    if max(scores.values()) <= 0:
        scores = {
            1: 7.0,
            2: 4.5,
            3: 4.0,
            4: 3.5,
            5: 3.0,
            6: 2.5,
        }

    # --------------------------------
    # 1着確率
    # --------------------------------

    raw_first = []

    for boat in range(1, 7):
        score = scores[boat]

        # スコア差を極端にしない
        z = min(
            max(score / 10.0, -20.0),
            20.0,
        )

        raw_first.append(
            math.exp(z)
        )

    first_array = _norm(raw_first)

    first_probs = {
        boat: float(first_array[boat - 1])
        for boat in range(1, 7)
    }

    ranking = sorted(
        range(1, 7),
        key=lambda b: first_probs[b],
        reverse=True,
    )

    main = ranking[0]
    counter = ranking[1]
    hole = ranking[2]

    # --------------------------------
    # 3連単120通り
    # --------------------------------
    #
    # 1着・2着・3着の確率を組み合わせる。
    #
    # 同じ艇を重複させない。
    #

    combos = list(
        itertools.permutations(
            range(1, 7),
            3,
        )
    )

    joint_raw = []

    for a, b, c in combos:
        pa = first_probs[a]
        pb = first_probs[b]
        pc = first_probs[c]

        # 1着をやや強く評価
        value = (
            pa ** 1.00
            * pb ** 0.92
            * pc ** 0.86
        )

        joint_raw.append(
            max(value, 1e-15)
        )

    joint_array = _norm(joint_raw)

    joint = {
        combo: float(prob)
        for combo, prob in zip(
            combos,
            joint_array,
        )
    }

    # --------------------------------
    # 3連単ランキング
    # --------------------------------

    combo_ranking = sorted(
        joint.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    # --------------------------------
    # 信頼度
    # --------------------------------

    top = first_probs[ranking[0]]
    second = first_probs[ranking[1]]

    gap = max(
        0.0,
        top - second,
    )

    confidence = (
        55.0
        + top * 60.0
        + gap * 80.0
    )

    confidence = max(
        55.0,
        min(
            95.0,
            confidence,
        ),
    )

    return {
        "main": main,
        "counter": counter,
        "hole": hole,
        "confidence": float(confidence),
        "first_probs": first_probs,
        "ranking": ranking,
        "scores": scores,
        "joint": joint,
        "combo_ranking": combo_ranking,
    }


def _pick_three_bets(prediction):
    """
    的中率重視で3点を選ぶ。

    1. 本線
       → AI確率1位

    2. 対抗
       → 本線と異なる組み合わせから高確率

    3. 穴
       → 低順位艇を絡めつつ、
          AI確率が比較的高いもの

    EVは一切使わない。
    """

    ranking = prediction["ranking"]
    joint = prediction["joint"]

    combo_ranking = prediction.get(
        "combo_ranking"
    )

    if not combo_ranking:
        combo_ranking = sorted(
            joint.items(),
            key=lambda x: x[1],
            reverse=True,
        )

    # --------------------------------
    # 本線
    # --------------------------------

    main_combo = combo_ranking[0][0]

    # --------------------------------
    # 対抗
    # --------------------------------
    #
    # 本線と違う組み合わせの中から
    # 最もAI確率が高いもの。
    #

    counter_combo = None

    for combo, prob in combo_ranking:
        if combo != main_combo:
            counter_combo = combo
            break

    if counter_combo is None:
        counter_combo = main_combo

    # --------------------------------
    # 穴
    # --------------------------------
    #
    # AI順位4～6位の艇を最低1艇絡める。
    # ただし確率が低すぎる場合は
    # 無理に穴を作らない。
    #

    low_boats = set(
        ranking[3:]
    )

    hole_candidates = []

    for combo, prob in combo_ranking:
        if combo == main_combo:
            continue

        if combo == counter_combo:
            continue

        if any(
            boat in low_boats
            for boat in combo
        ):
            hole_candidates.append(
                (combo, prob)
            )

    if hole_candidates:
        # 上位確率を優先
        hole_combo = hole_candidates[0][0]
    else:
        # 万一候補がなければ3位
        hole_combo = None

        for combo, prob in combo_ranking:
            if combo not in {
                main_combo,
                counter_combo,
            }:
                hole_combo = combo
                break

        if hole_combo is None:
            hole_combo = main_combo

    return [
        main_combo,
        counter_combo,
        hole_combo,
    ]


def recommend_bets(prediction, odds=None):
    """
    的中率重視のおすすめ3点。

    oddsを渡した場合は表示用に付加するだけ。
    買い目順位にはEVを使用しない。
    """

    combos = _pick_three_bets(
        prediction
    )

    joint = prediction["joint"]

    result = []

    labels = [
        "本線",
        "対抗",
        "穴",
    ]

    for label, combo in zip(
        labels,
        combos,
    ):
        row = {
            "label": label,
            "combo": combo,
            "prob": float(
                joint.get(combo, 0.0)
            ),
            "odds": None,
            "market_prob": None,
            "edge": None,
        }

        if odds:
            odd = odds.get(combo)

            if odd is not None:
                try:
                    odd = float(odd)

                    if odd > 0:
                        row["odds"] = odd
                        row["market_prob"] = (
                            1.0 / odd
                        )
                        row["edge"] = (
                            row["prob"]
                            - row["market_prob"]
                        )
                except Exception:
                    pass

        result.append(row)

    return result


def value_candidates(
    prediction,
    odds,
    min_prob=0.006,
    limit=8,
):
    """
    旧UIとの互換用。

    ただし現在はEVを主軸にせず、
    AI確率順で返す。

    既存コードから呼ばれても
    動くように残している。
    """

    if not odds:
        return []

    joint = prediction["joint"]

    rows = []

    for combo, odd in odds.items():
        if combo not in joint:
            continue

        try:
            odd = float(odd)
        except Exception:
            continue

        if odd <= 0:
            continue

        prob = float(
            joint[combo]
        )

        if prob < min_prob:
            continue

        market_prob = 1.0 / odd

        ev = (
            prob * odd
            - 1.0
        )

        edge = (
            prob
            - market_prob
        )

        rows.append(
            {
                "combo": combo,
                "odds": odd,
                "prob": prob,
                "market_prob": market_prob,
                "ev": ev,
                "edge": edge,
                "score": prob,
            }
        )

    rows.sort(
        key=lambda x: (
            x["prob"],
            x["edge"],
        ),
        reverse=True,
    )

    return rows[:limit]
