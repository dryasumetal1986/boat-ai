import itertools
import math
import numpy as np
import pandas as pd


def _safe(v):
    try:
        x = float(v)
        if math.isnan(x) or math.isinf(x):
            return 0.0
        return x
    except Exception:
        return 0.0


def _norm(series):
    s = pd.to_numeric(
        series,
        errors="coerce",
    ).fillna(0.0)

    if len(s) == 0:
        return s

    mn = s.min()
    mx = s.max()

    if mx - mn < 1e-9:
        return pd.Series(
            np.full(len(s), 0.5),
            index=s.index,
        )

    return (s - mn) / (mx - mn)


def _softmax(values):
    arr = np.array(values, dtype=float)

    if len(arr) == 0:
        return arr

    arr = arr - np.max(arr)
    exp = np.exp(arr)

    total = exp.sum()

    if total <= 0:
        return np.ones(len(arr)) / len(arr)

    return exp / total


def _feature_scores(df):
    d = df.copy()

    # 数値化
    cols = [
        "average_start_timing",
        "national_win_rate",
        "national_top_2_percent",
        "national_top_3_percent",
        "local_win_rate",
        "local_top_2_percent",
        "local_top_3_percent",
        "motor_top_2_percent",
        "motor_top_3_percent",
        "boat_top_2_percent",
        "boat_top_3_percent",
        "flying_count",
        "late_count",
        "start_timing",
        "exhibition_time",
    ]

    for c in cols:
        if c not in d.columns:
            d[c] = 0.0

        d[c] = pd.to_numeric(
            d[c],
            errors="coerce",
        ).fillna(0.0)

    # 艇番1の基本優位
    lane_bonus = {
        1: 1.00,
        2: 0.82,
        3: 0.70,
        4: 0.56,
        5: 0.43,
        6: 0.32,
    }

    d["lane_bonus"] = d["boat"].map(
        lane_bonus
    ).fillna(0.3)

    # 各指標を0～1化
    d["n_win"] = _norm(
        d["national_win_rate"]
    )
    d["n_top2"] = _norm(
        d["national_top_2_percent"]
    )
    d["n_top3"] = _norm(
        d["national_top_3_percent"]
    )

    d["l_win"] = _norm(
        d["local_win_rate"]
    )
    d["l_top2"] = _norm(
        d["local_top_2_percent"]
    )
    d["l_top3"] = _norm(
        d["local_top_3_percent"]
    )

    d["m_top2"] = _norm(
        d["motor_top_2_percent"]
    )
    d["m_top3"] = _norm(
        d["motor_top_3_percent"]
    )

    d["b_top2"] = _norm(
        d["boat_top_2_percent"]
    )
    d["b_top3"] = _norm(
        d["boat_top_3_percent"]
    )

    d["start"] = _norm(
        d["start_timing"]
    )

    # 展示タイムは速いほど良い
    ex = pd.to_numeric(
        d["exhibition_time"],
        errors="coerce",
    ).fillna(0.0)

    if ex.max() > ex.min():
        d["exhibition"] = 1 - (
            (ex - ex.min()) /
            (ex.max() - ex.min())
        )
    else:
        d["exhibition"] = 0.5

    # F/Lは少ないほど良い
    penalty = (
        d["flying_count"] * 0.08
        + d["late_count"] * 0.05
    )

    # 1着向けスコア
    d["first_score"] = (
        d["lane_bonus"] * 1.55
        + d["n_win"] * 1.30
        + d["n_top2"] * 0.65
        + d["l_win"] * 0.95
        + d["l_top2"] * 0.45
        + d["m_top2"] * 0.70
        + d["m_top3"] * 0.40
        + d["b_top2"] * 0.40
        + d["start"] * 0.55
        + d["exhibition"] * 0.35
        - penalty
    )

    # 2・3着向けスコア
    d["second_score"] = (
        d["lane_bonus"] * 0.75
        + d["n_top2"] * 1.05
        + d["n_top3"] * 0.90
        + d["l_top2"] * 0.75
        + d["l_top3"] * 0.75
        + d["m_top2"] * 0.70
        + d["m_top3"] * 0.65
        + d["b_top2"] * 0.35
        + d["b_top3"] * 0.35
        + d["start"] * 0.35
        + d["exhibition"] * 0.30
        - penalty * 0.65
    )

    d["third_score"] = (
        d["lane_bonus"] * 0.45
        + d["n_top3"] * 0.95
        + d["l_top3"] * 0.85
        + d["m_top3"] * 0.80
        + d["b_top3"] * 0.45
        + d["n_top2"] * 0.35
        + d["l_top2"] * 0.35
        + d["start"] * 0.25
        + d["exhibition"] * 0.25
        - penalty * 0.45
    )

    return d


def predict(df):
    """
    3連単3点を返す。

    本線:
        最も総合評価の高い組み合わせ

    対抗:
        本線と1着を共有しつつ、
        2・3着を入れ替え

    穴:
        別の1着シナリオも許可

    重要:
        ここで使う番号は必ず1～6号艇。
    """
    if df is None or df.empty:
        return None

    d = _feature_scores(df)

    # 艇番を1～6に矯正
    d["boat"] = pd.to_numeric(
        d["boat"],
        errors="coerce",
    )

    d = d[
        d["boat"].between(1, 6)
    ].copy()

    if len(d) != 6:
        return None

    d = d.sort_values(
        "boat"
    ).reset_index(drop=True)

    boats = d["boat"].astype(int).tolist()

    first_map = dict(
        zip(
            d["boat"].astype(int),
            d["first_score"],
        )
    )

    second_map = dict(
        zip(
            d["boat"].astype(int),
            d["second_score"],
        )
    )

    third_map = dict(
        zip(
            d["boat"].astype(int),
            d["third_score"],
        )
    )

    combos = []

    for a, b, c in itertools.permutations(
        boats,
        3,
    ):
        # 1着を強く評価
        score = (
            first_map[a] * 0.52
            + second_map[b] * 0.28
            + third_map[c] * 0.20
        )

        # 1号艇は基本的にやや優位
        if a == 1:
            score += 0.22

        # 2号艇は差し候補
        if a == 2:
            score += 0.10

        # 3～6の1着は少し抑える
        if a >= 4:
            score -= 0.05

        # 2着・3着の入れ替えを少し許容
        if b == 1:
            score += 0.08

        if c == 1:
            score += 0.04

        combos.append({
            "combo": (a, b, c),
            "score": float(score),
        })

    combo_scores = np.array([
        x["score"] for x in combos
    ])

    probs = _softmax(
        combo_scores * 1.15
    )

    for i, p in enumerate(probs):
        combos[i]["prob"] = float(p)

    combos.sort(
        key=lambda x: x["prob"],
        reverse=True,
    )

    # まず本線
    main = combos[0]

    # 対抗:
    # 本線と1着を共有し、順序を変える
    counter_candidates = [
        x for x in combos
        if x["combo"][0] == main["combo"][0]
        and x["combo"] != main["combo"]
    ]

    counter = (
        counter_candidates[0]
        if counter_candidates
        else combos[1]
    )

    # 穴:
    # 本線と違う1着を優先
    hole_candidates = [
        x for x in combos
        if x["combo"][0] != main["combo"][0]
        and x["combo"] != counter["combo"]
    ]

    # 上位の別1着から選ぶ
    hole = (
        hole_candidates[0]
        if hole_candidates
        else combos[2]
    )

    tickets = [
        {
            "label": "本線",
            "mark": "◎",
            "combo": main["combo"],
            "prob": main["prob"],
        },
        {
            "label": "対抗",
            "mark": "○",
            "combo": counter["combo"],
            "prob": counter["prob"],
        },
        {
            "label": "穴",
            "mark": "▲",
            "combo": hole["combo"],
            "prob": hole["prob"],
        },
    ]

    # 重複防止
    unique = []
    seen = set()

    for t in tickets:
        if t["combo"] not in seen:
            unique.append(t)
            seen.add(t["combo"])

    # 万一3点未満なら上位から補充
    for x in combos:
        if len(unique) >= 3:
            break

        if x["combo"] not in seen:
            unique.append({
                "label": "追加",
                "mark": "・",
                "combo": x["combo"],
                "prob": x["prob"],
            })
            seen.add(x["combo"])

    tickets = unique[:3]

    # 1着ランキング
    ranking_df = d.sort_values(
        "first_score",
        ascending=False,
    ).copy()

    ranking = []

    first_values = ranking_df[
        "first_score"
    ].values

    first_probs = _softmax(
        first_values * 1.35
    )

    for (_, row), prob in zip(
        ranking_df.iterrows(),
        first_probs,
    ):
        ranking.append({
            "boat": int(row["boat"]),
            "name": row["name"],
            "prob": float(prob),
            "score": float(
                row["first_score"]
            ),
        })

    # 信頼度
    top_prob = ranking[0]["prob"]

    confidence = (
        60
        + top_prob * 80
    )

    confidence = max(
        55,
        min(95, confidence),
    )

    return {
        "tickets": tickets,
        "ranking": ranking,
        "confidence": confidence,
        "all_combos": combos,
        "df": d,
    }


def combo_text(combo):
    return "-".join(
        str(int(x))
        for x in combo
    )
