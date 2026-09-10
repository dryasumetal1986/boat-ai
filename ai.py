import itertools
import numpy as np
import pandas as pd

BOATS = tuple(range(1, 7))


def _norm(series, higher=True):
    x = pd.to_numeric(series, errors="coerce").fillna(0.0).astype(float)
    lo, hi = float(x.min()), float(x.max())

    if hi - lo < 1e-9:
        return pd.Series(0.5, index=x.index)

    z = (x - lo) / (hi - lo)
    return z if higher else 1.0 - z


def _prepare(df):
    x = df.copy().sort_values("boat").reset_index(drop=True)

    x["win_n"] = _norm(x["national_win_rate"])
    x["win_l"] = _norm(x["local_win_rate"])
    x["top2_n"] = _norm(x["national_top_2_percent"])
    x["top3_n"] = _norm(x["national_top_3_percent"])
    x["top2_l"] = _norm(x["local_top_2_percent"])
    x["top3_l"] = _norm(x["local_top_3_percent"])
    x["motor2"] = _norm(x["motor_top_2_percent"])
    x["motor3"] = _norm(x["motor_top_3_percent"])
    x["boat2"] = _norm(x["boat_top_2_percent"])
    x["boat3"] = _norm(x["boat_top_3_percent"])
    x["st"] = _norm(x["average_start_timing"], higher=False)

    ex = pd.to_numeric(x["exhibition_time"], errors="coerce")
    valid_ex = ex[ex > 0]

    if len(valid_ex):
        ex_median = valid_ex.median()
    else:
        ex_median = 1.0

    ex_filled = ex.replace(0, np.nan).fillna(ex_median)
    x["exh"] = _norm(ex_filled, higher=False)

    course = pd.to_numeric(
        x["course_number"],
        errors="coerce"
    ).fillna(x["boat"])

    x["course"] = (
        1.0 - (course - 1) / 10.0
    ).clip(0.4, 1.0)

    x["first_score"] = (
        0.24 * x["win_n"]
        + 0.13 * x["win_l"]
        + 0.13 * x["top2_n"]
        + 0.08 * x["top2_l"]
        + 0.10 * x["motor2"]
        + 0.06 * x["boat2"]
        + 0.12 * x["st"]
        + 0.08 * x["exh"]
        + 0.06 * x["course"]
    )

    x["second_score"] = (
        0.18 * x["top2_n"]
        + 0.14 * x["top2_l"]
        + 0.16 * x["top3_n"]
        + 0.10 * x["top3_l"]
        + 0.14 * x["motor2"]
        + 0.08 * x["motor3"]
        + 0.10 * x["boat2"]
        + 0.10 * x["st"]
    )

    x["third_score"] = (
        0.18 * x["top3_n"]
        + 0.14 * x["top3_l"]
        + 0.16 * x["motor3"]
        + 0.12 * x["boat3"]
        + 0.12 * x["top2_n"]
        + 0.10 * x["top2_l"]
        + 0.10 * x["st"]
        + 0.08 * x["exh"]
    )

    return x


def _softmax(values, temperature=0.12):
    a = np.asarray(values, dtype=float) / temperature

    if len(a) == 0:
        return np.array([])

    a -= np.max(a)
    e = np.exp(a)

    return e / max(e.sum(), 1e-12)


def _base_combo_score(a, b, c, first_score, second_score, third_score):
    score = (
        1.00 * first_score[a]
        + 0.72 * second_score[b]
        + 0.58 * third_score[c]
    )

    if a == 1:
        score += 0.055
    elif a == 2:
        score += 0.025

    if b == 1:
        score += 0.020

    return float(score)


def _ordering_signal(b, c, second_score, third_score):
    """
    2着・3着の順番を見るための軽い補正。

    大きく動かさず、
    「2着候補として強い艇」と
    「3着候補として強い艇」の役割差だけを見る。

    以前のpair compatibility実験より影響をかなり小さくする。
    """

    second_strength = float(second_score[b])
    third_strength = float(third_score[c])

    role_b = float(second_score[b] - third_score[b])
    role_c = float(third_score[c] - second_score[c])

    role_b = float(np.clip(role_b, -0.30, 0.30))
    role_c = float(np.clip(role_c, -0.30, 0.30))

    role = (role_b + role_c) / 2.0

    strength_gap = second_strength - third_strength
    strength_gap = float(np.clip(strength_gap, -0.30, 0.30))

    return (
        0.035 * strength_gap
        + 0.025 * role
    )


def _select_main_counter(
    ranked,
    first_score,
    second_score,
    third_score,
):
    """
    本線・対抗の2着3着順を再選択する。

    重要なのは「単純な順位入れ替え」ではなく、
    同じ軸を持つ候補群の中から、
    2着3着の順序まで含めて2本を選ぶこと。

    ただし過剰最適化を避けるため、
    元スコアを強く残したまま微調整する。
    """

    if not ranked:
        raise ValueError("予想候補がありません。")

    original_main = ranked[0]

    axis = original_main[0][0]

    same_axis = [
        item
        for item in ranked
        if item[0][0] == axis
    ]

    if len(same_axis) < 2:
        return original_main, ranked[1]

    # 元ランキング上位だけを対象にする。
    # 遠い候補まで拾うと3点的中率が崩れる可能性があるため。
    pool = same_axis[:10]

    adjusted = []

    for combo, prob, raw_score in pool:
        a, b, c = combo

        order_bonus = _ordering_signal(
            b,
            c,
            second_score,
            third_score,
        )

        adjusted_score = float(raw_score + order_bonus)

        adjusted.append(
            {
                "combo": combo,
                "prob": float(prob),
                "raw_score": float(raw_score),
                "adjusted_score": adjusted_score,
                "order_bonus": order_bonus,
            }
        )

    adjusted.sort(
        key=lambda z: (
            z["adjusted_score"],
            z["raw_score"],
        ),
        reverse=True,
    )

    main_candidate = adjusted[0]

    # 本線の相手は、単に2位を取るのではなく、
    # 本線との重複を避けつつ最も強い候補を選ぶ。
    counter_candidates = [
        item
        for item in adjusted
        if item["combo"] != main_candidate["combo"]
    ]

    if not counter_candidates:
        return original_main, ranked[1]

    counter_candidate = counter_candidates[0]

    main = (
        main_candidate["combo"],
        main_candidate["prob"],
        main_candidate["raw_score"],
    )

    counter = (
        counter_candidate["combo"],
        counter_candidate["prob"],
        counter_candidate["raw_score"],
    )

    # 微調整で元1位が大きく落ちる場合は、
    # 元ランキングを優先する安全装置。
    raw_main = float(original_main[2])

    if main_candidate["raw_score"] < raw_main - 0.045:
        main = original_main

        fallback = [
            item
            for item in ranked
            if item[0] != main[0]
            and item[0][0] == axis
        ]

        if fallback:
            counter = fallback[0]

    return main, counter


def _select_hole(
    ranked,
    main,
    first_score,
    second_score,
    third_score,
):
    """
    穴は現在のベスト版ロジックを維持。

    ・本線と違う1着艇を候補にする
    ・first_score上位を優先
    ・1号艇が僅差なら候補に残す
    ・各1着候補について最良の3連単を探す
    ・本線/対抗と重複させない
    """

    main_combo = main[0]
    main_axis = main_combo[0]

    non_axis_boats = [
        boat
        for boat in BOATS
        if boat != main_axis
    ]

    ranked_first = sorted(
        non_axis_boats,
        key=lambda b: first_score[b],
        reverse=True,
    )

    # 1号艇が非軸候補上位から外れていても、
    # 軸との差が小さい場合だけ穴候補へ追加。
    if 1 != main_axis and 1 not in ranked_first:
        if ranked_first:
            top_score = first_score[ranked_first[0]]
            if first_score[1] >= top_score - 0.08:
                ranked_first.append(1)

    candidate_rows = []

    for alternative_axis in ranked_first[:4]:
        candidates = [
            item
            for item in ranked
            if item[0][0] == alternative_axis
            and item[0] != main_combo
        ]

        if not candidates:
            continue

        best = candidates[0]

        candidate_score = (
            0.70 * first_score[alternative_axis]
            + 0.30 * best[2]
        )

        candidate_rows.append(
            (
                candidate_score,
                best,
            )
        )

    if not candidate_rows:
        fallback = [
            item
            for item in ranked
            if item[0] != main_combo
        ]

        if fallback:
            return fallback[0]

        return ranked[1]

    candidate_rows.sort(
        key=lambda z: z[0],
        reverse=True,
    )

    # 本線・対抗との重複を避ける。
    used = {main_combo}

    # counterはpredict側から渡されないため、
    # 同じfirst-axisの上位を避けるだけにする。
    for _, item in candidate_rows:
        if item[0] not in used:
            return item

    return candidate_rows[0][1]


def predict(df):
    if not isinstance(df, pd.DataFrame) or len(df) != 6:
        raise ValueError("6艇分の出走表が必要です。")

    boats_series = pd.to_numeric(
        df["boat"],
        errors="coerce"
    ).astype(int)

    if set(boats_series) != set(BOATS):
        raise ValueError("艇番が1〜6になっていません。")

    x = _prepare(df)

    f = dict(
        zip(
            x["boat"].astype(int),
            x["first_score"],
        )
    )

    s = dict(
        zip(
            x["boat"].astype(int),
            x["second_score"],
        )
    )

    t = dict(
        zip(
            x["boat"].astype(int),
            x["third_score"],
        )
    )

    combos = []

    for a, b, c in itertools.permutations(BOATS, 3):
        score = _base_combo_score(
            a,
            b,
            c,
            f,
            s,
            t,
        )

        combos.append(
            (
                (a, b, c),
                float(score),
            )
        )

    raw = np.array(
        [score for _, score in combos],
        dtype=float,
    )

    probs = _softmax(
        raw,
        0.075,
    )

    ranked = sorted(
        [
            (
                combo,
                float(prob),
                score,
            )
            for (combo, score), prob
            in zip(combos, probs)
        ],
        key=lambda z: z[1],
        reverse=True,
    )

    # ---------------------------------
    # 本線・対抗
    # ---------------------------------
    main, counter = _select_main_counter(
        ranked,
        f,
        s,
        t,
    )

    # ---------------------------------
    # 穴
    # ---------------------------------
    hole = _select_hole(
        ranked,
        main,
        f,
        s,
        t,
    )

    # 穴が本線・対抗と同じになった場合の安全処理
    used_combos = {
        main[0],
        counter[0],
    }

    if hole[0] in used_combos:
        alternative_holes = [
            item
            for item in ranked
            if item[0] not in used_combos
            and item[0][0] != main[0][0]
        ]

        if alternative_holes:
            hole = alternative_holes[0]

    tickets = [
        {
            "label": "本線",
            "combo": main[0],
            "prob": main[1],
        },
        {
            "label": "対抗",
            "combo": counter[0],
            "prob": counter[1],
        },
        {
            "label": "穴",
            "combo": hole[0],
            "prob": hole[1],
        },
    ]

    # ---------------------------------
    # 軸評価
    # ---------------------------------
    first_probs = _softmax(
        [f[b] for b in BOATS],
        0.10,
    )

    first_rank = sorted(
        zip(BOATS, first_probs),
        key=lambda z: z[1],
        reverse=True,
    )

    axis = int(first_rank[0][0])

    axis_top3 = sum(
        p for _, p in first_rank[:3]
    )

    margin = (
        first_rank[0][1]
        - first_rank[1][1]
    )

    confidence = min(
        95.0,
        max(
            55.0,
            62.0 + margin * 220.0,
        ),
    )

    return {
        "tickets": tickets,
        "ranking": ranked,
        "confidence": round(
            confidence,
            1,
        ),
        "axis": axis,
        "axis_top3": float(axis_top3),
        "all_combos": ranked,
        "df": x,
    }
