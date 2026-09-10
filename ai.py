import itertools
import math
import numpy as np
import pandas as pd


def _norm(v):
    v = np.asarray(v, dtype=float)

    if len(v) == 0:
        return v

    lo = np.nanmin(v)
    hi = np.nanmax(v)

    if hi - lo < 1e-9:
        return np.ones(len(v)) * 0.5

    return (v - lo) / (hi - lo)


def _softmax(scores, temp=1.0):
    x = np.asarray(scores, dtype=float) / temp
    x = x - np.max(x)

    e = np.exp(x)
    total = e.sum()

    if total <= 0:
        return np.ones(len(x)) / len(x)

    return e / total


def _col(df, name):
    if name not in df:
        return np.zeros(len(df))

    return (
        pd.to_numeric(
            df[name],
            errors="coerce"
        )
        .fillna(0)
        .values
    )


def _prepare(df):
    d = df.copy().reset_index(drop=True)

    cols = [
        "win_rate", "top2", "top3",
        "local_rate", "local_top2", "local_top3",
        "motor_top2", "motor_top3",
        "boat_top2", "boat_top3",
        "start", "exhibition",
    ]

    for c in cols:
        if c in d:
            d[c] = pd.to_numeric(
                d[c],
                errors="coerce"
            ).fillna(0)

    # パーセント表記を0～1へ
    for c in [
        "top2", "top3",
        "local_top2", "local_top3",
        "motor_top2", "motor_top3",
        "boat_top2", "boat_top3",
    ]:
        if c in d and d[c].max() > 1.5:
            d[c] = d[c] / 100.0

    return d


def predict(df):
    """
    1着・2着・3着を別々に評価し、
    120通りの3連単を直接スコアリングする。
    """

    d = _prepare(df)

    if len(d) != 6:
        raise ValueError("6艇のデータが必要です")

    # -----------------------------
    # 基本データ
    # -----------------------------
    win = _col(d, "win_rate")
    local = _col(d, "local_rate")
    top2 = _col(d, "top2")
    top3 = _col(d, "top3")

    local2 = _col(d, "local_top2")
    local3 = _col(d, "local_top3")

    motor2 = _col(d, "motor_top2")
    motor3 = _col(d, "motor_top3")

    boat2 = _col(d, "boat_top2")
    boat3 = _col(d, "boat_top3")

    start = _col(d, "start")
    exhibition = _col(d, "exhibition")

    # -----------------------------
    # 0～1化
    # -----------------------------
    win_s = _norm(win)
    local_s = _norm(local)

    top2_s = _norm(top2)
    top3_s = _norm(top3)

    local2_s = _norm(local2)
    local3_s = _norm(local3)

    motor2_s = _norm(motor2)
    motor3_s = _norm(motor3)

    boat2_s = _norm(boat2)
    boat3_s = _norm(boat3)

    start_s = (
        1 - _norm(start)
        if np.any(start > 0)
        else np.ones(6) * 0.5
    )

    exhibition_s = (
        1 - _norm(exhibition)
        if np.any(exhibition > 0)
        else np.ones(6) * 0.5
    )

    # -----------------------------
    # コース補正
    # -----------------------------
    course_bonus = np.array([
        1.00,
        0.62,
        0.45,
        0.31,
        0.21,
        0.14
    ])

    # -----------------------------
    # ① 1着モデル
    # -----------------------------
    first_score = (
        2.00 * win_s +
        0.90 * local_s +
        0.80 * top2_s +
        0.55 * top3_s +
        0.70 * start_s +
        0.40 * exhibition_s +
        course_bonus
    )

    p1 = _softmax(
        first_score,
        temp=0.72
    )

    # -----------------------------
    # ② 2着モデル
    # -----------------------------
    second_score = (
        0.65 * win_s +
        0.85 * top2_s +
        0.55 * top3_s +
        0.65 * local2_s +
        0.45 * local3_s +
        0.50 * motor2_s +
        0.35 * boat2_s +
        0.35 * start_s +
        0.20 * exhibition_s +
        0.42 * course_bonus
    )

    # -----------------------------
    # ③ 3着モデル
    # -----------------------------
    third_score = (
        0.30 * win_s +
        0.50 * top2_s +
        0.80 * top3_s +
        0.55 * local2_s +
        0.75 * local3_s +
        0.45 * motor2_s +
        0.65 * motor3_s +
        0.30 * boat2_s +
        0.55 * boat3_s +
        0.25 * start_s +
        0.20 * exhibition_s +
        0.32 * course_bonus
    )

    # -----------------------------
    # ④ 120通りを計算
    # -----------------------------
    combos = []

    for a, b, c in itertools.permutations(range(6), 3):

        # 1着
        pa = p1[a]

        # 2着
        s2 = second_score.copy()
        s2[a] = -999

        # 1着艇が外なら1号艇の2着残りも少し評価
        if a != 0:
            s2[0] += 0.10

        # 1号艇が1着なら2～4号艇の2着を少し評価
        if a == 0:
            s2[1:4] += 0.06

        p2 = _softmax(
            s2,
            temp=0.82
        )

        pb = p2[b]

        # 3着
        s3 = third_score.copy()
        s3[a] = -999
        s3[b] = -999

        # 波乱時の1号艇残り目
        if a != 0 and b != 0:
            s3[0] += 0.08

        # 中間艇の3着残り目
        if c in (1, 2, 3):
            s3[c] += 0.035

        p3 = _softmax(
            s3,
            temp=0.88
        )

        pc = p3[c]

        probability = pa * pb * pc

        combos.append({
            "combo": (
                int(d.iloc[a]["boat"]),
                int(d.iloc[b]["boat"]),
                int(d.iloc[c]["boat"]),
            ),
            "prob": float(probability),
            "first_prob": float(pa),
        })

    # -----------------------------
    # ⑤ 全120通りを正規化
    # -----------------------------
    total = sum(x["prob"] for x in combos)

    if total > 0:
        for x in combos:
            x["prob"] /= total

    combos.sort(
        key=lambda x: x["prob"],
        reverse=True
    )

    # -----------------------------
    # ⑥ 本線
    # -----------------------------
    main = combos[0]

    # -----------------------------
    # ⑦ 対抗
    # 本線と完全に同じ展開に偏らない
    # -----------------------------
    counter = None

    for x in combos[1:]:
        same_first = (
            x["combo"][0] ==
            main["combo"][0]
        )

        same_second = (
            x["combo"][1] ==
            main["combo"][1]
        )

        if not (same_first and same_second):
            counter = x
            break

    if counter is None:
        counter = combos[1]

    # -----------------------------
    # ⑧ 穴
    # 別1着艇を優先
    # -----------------------------
    hole = None

    threshold = main["prob"] * 0.40

    for x in combos:
        if x["combo"] == main["combo"]:
            continue

        if x["combo"] == counter["combo"]:
            continue

        different_first = (
            x["combo"][0] !=
            main["combo"][0]
        )

        if (
            different_first
            and x["prob"] >= threshold
        ):
            hole = x
            break

    # 別1着候補が低すぎる場合は、
    # 4～6号艇を含む現実的な穴を採用
    if hole is None:
        for x in combos:
            if x["combo"] in (
                main["combo"],
                counter["combo"]
            ):
                continue

            if max(x["combo"]) >= 4:
                hole = x
                break

    if hole is None:
        hole = combos[2]

    # -----------------------------
    # ⑨ 1着ランキング
    # -----------------------------
    order = np.argsort(
        -p1
    )

    ranking = []

    for idx in order:
        ranking.append({
            "boat": int(d.iloc[idx]["boat"]),
            "name": d.iloc[idx]["name"],
            "prob": float(p1[idx]),
            "score": float(first_score[idx]),
        })

    # -----------------------------
    # ⑩ 信頼度
    # -----------------------------
    top_p = p1[order[0]]
    second_p = p1[order[1]]

    confidence = (
        50 +
        (top_p - second_p) * 250
    )

    confidence = max(
        45,
        min(95, confidence)
    )

    return {
        "tickets": {
            "main": main,
            "counter": counter,
            "hole": hole,
        },
        "ranking": ranking,
        "probabilities": p1,
        "confidence": float(confidence),
        "all_combos": combos,
            }
