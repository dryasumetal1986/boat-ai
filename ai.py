import math
import itertools
import numpy as np
import pandas as pd


def _sigmoid(x):
    x = max(-10, min(10, x))
    return 1 / (1 + math.exp(-x))


def _norm(v):
    v = np.asarray(v, dtype=float)
    if len(v) == 0:
        return v
    lo, hi = np.nanmin(v), np.nanmax(v)
    if hi - lo < 1e-9:
        return np.ones(len(v)) * 0.5
    return (v - lo) / (hi - lo)


def _softmax(scores, temp=0.8):
    x = np.asarray(scores, dtype=float) / temp
    x -= np.max(x)
    e = np.exp(x)
    return e / e.sum()


def _col(df, name):
    if name not in df:
        return np.zeros(len(df))
    return pd.to_numeric(df[name], errors="coerce").fillna(0).values


def _prepare(df):
    d = df.copy()

    # 各項目を0～1へ
    for c in [
        "win_rate", "top2", "top3",
        "local_rate", "local_top2", "local_top3",
        "motor_top2", "motor_top3",
        "boat_top2", "boat_top3",
        "start", "exhibition"
    ]:
        if c in d:
            d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0)

    # 全国勝率などは実数値、率系は0～1に変換
    for c in [
        "top2", "top3",
        "local_top2", "local_top3",
        "motor_top2", "motor_top3",
        "boat_top2", "boat_top3"
    ]:
        if c in d:
            if d[c].max() > 1.5:
                d[c] = d[c] / 100.0

    return d


def predict(df):
    """
    120通りの3連単を直接評価するAI。
    戻り値:
      tickets: 本線・対抗・穴
      ranking: 1着AI順位
      probabilities: 1着確率
      confidence: AI信頼度
      all_combos: 全120通り
    """
    d = _prepare(df).reset_index(drop=True)

    # ---------------------------------------------------------
    # ① 1着の強さ
    # ---------------------------------------------------------
    win = _col(d, "win_rate")
    local = _col(d, "local_rate")
    start = _col(d, "start")
    exhibition = _col(d, "exhibition")
    top2 = _col(d, "top2")
    top3 = _col(d, "top3")

    course = np.array([
        int(x) if str(x).isdigit() else i + 1
        for i, x in enumerate(d["boat"])
    ])

    # 勝率系
    win_s = _norm(win)
    local_s = _norm(local)
    top2_s = _norm(top2)
    top3_s = _norm(top3)

    # スタートは小さいほど良い
    start_s = 1 - _norm(start) if np.any(start > 0) else np.zeros(6)

    # 展示タイムも小さいほど良い
    ex_s = 1 - _norm(exhibition) if np.any(exhibition > 0) else np.zeros(6)

    # コース優位。ただしコースだけで決めない
    course_bonus = np.array([
        1.00, 0.58, 0.43, 0.30, 0.20, 0.14
    ])

    first_score = (
        2.00 * win_s +
        0.90 * local_s +
        0.80 * top2_s +
        0.55 * top3_s +
        0.65 * start_s +
        0.45 * ex_s +
        course_bonus
    )

    p1 = _softmax(first_score, 0.72)

    # ---------------------------------------------------------
    # ② 2着・3着用の基礎能力
    # ---------------------------------------------------------
    local2 = _col(d, "local_top2")
    local3 = _col(d, "local_top3")
    motor2 = _col(d, "motor_top2")
    motor3 = _col(d, "motor_top3")
    boat2 = _col(d, "boat_top2")
    boat3 = _col(d, "boat_top3")

    l2 = _norm(local2)
    l3 = _norm(local3)
    m2 = _norm(motor2)
    m3 = _norm(motor3)
    b2 = _norm(boat2)
    b3 = _norm(boat3)

    # 2着能力
    second_base = (
        0.70 * win_s +
        0.85 * top2_s +
        0.50 * top3_s +
        0.65 * l2 +
        0.45 * l3 +
        0.50 * m2 +
        0.35 * b2 +
        0.35 * start_s +
        0.18 * ex_s +
        0.45 * course_bonus
    )

    # 3着能力
    third_base = (
        0.35 * win_s +
        0.55 * top2_s +
        0.80 * top3_s +
        0.55 * l2 +
        0.75 * l3 +
        0.45 * m2 +
        0.65 * m3 +
        0.30 * b2 +
        0.55 * b3 +
        0.25 * start_s +
        0.20 * ex_s +
        0.32 * course_bonus
    )

    combos = []

    # ---------------------------------------------------------
    # ③ 120通りを直接計算
    # ---------------------------------------------------------
    for a, b, c in itertools.permutations(range(6), 3):

        # 1着確率
        pa = p1[a]

        # 1着がaになった場合の2着候補
        s2 = second_base.copy()

        # 1着艇そのものは除外
        s2[a] = -999

        # 強い1着艇がいる場合、内側艇の2着残りやすさを少し調整
        if a == 0:
            s2[1:] += 0.10 * course_bonus[1:]
        else:
            s2[0] += 0.10

        p2_all = _softmax(s2, 0.82)
        pb = p2_all[b]

        # 3着候補
        s3 = third_base.copy()
        s3[a] = -999
        s3[b] = -999

        # 1号艇が飛んだ場合、2～4号艇の残り目を少し評価
        if a != 0:
            s3[0] += 0.08

        # 2着艇とは別の艇が3着に来る構図を評価
        if c > 0 and c != a:
            s3[c] += 0.03

        p3_all = _softmax(s3, 0.88)
        pc = p3_all[c]

        # 3ポジションを掛け合わせる
        joint = pa * pb * pc

        combos.append({
            "combo": (
                int(d.iloc[a]["boat"]),
                int(d.iloc[b]["boat"]),
                int(d.iloc[c]["boat"])
            ),
            "prob": float(joint),
            "first_prob": float(pa),
        })

    # 全120通りを正規化
    total = sum(x["prob"] for x in combos)
    if total > 0:
        for x in combos:
            x["prob"] /= total

    combos.sort(key=lambda x: x["prob"], reverse=True)

    # ---------------------------------------------------------
    # ④ 3点選択
    # ---------------------------------------------------------
    main = combos[0]

    # 対抗：
    # 本線と同じ並びに偏りすぎないものを選択
    counter = None

    for x in combos[1:]:
        same_first = x["combo"][0] == main["combo"][0]
        same_second = x["combo"][1] == main["combo"][1]
        if not (same_first and same_second):
            counter = x
            break

    if counter is None:
        counter = combos[1]

    # 穴：
    # 「別の1着艇」を優先。
    # ただし確率が極端に低いものは避ける。
    hole = None
    threshold = main["prob"] * 0.42

    for x in combos:
        if x["combo"] == main["combo"]:
            continue
        if x["combo"] == counter["combo"]:
            continue

        different_first = x["combo"][0] != main["combo"][0]
        contains_lower = max(x["combo"]) >= 4

        if different_first and x["prob"] >= threshold:
            hole = x
            break

        if hole is None and contains_lower:
            hole = x

    if hole is None:
        hole = combos[2]

    # ---------------------------------------------------------
    # ⑤ 1着ランキング
    # ---------------------------------------------------------
    ranking_idx = np.argsort(-p1)

    ranking = []
    for idx in ranking_idx:
        ranking.append({
            "boat": int(d.iloc[idx]["boat"]),
            "name": d.iloc[idx]["name"],
            "prob": float(p1[idx]),
            "score": float(first_score[idx]),
        })

    # 信頼度
    top = p1[ranking_idx[0]]
    second = p1[ranking_idx[1]]

    confidence = 50 + (top - second) * 250
    confidence = max(45, min(95, confidence))

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
