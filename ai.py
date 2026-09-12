import itertools
import numpy as np
import pandas as pd


BOATS = (1, 2, 3, 4, 5, 6)


def combo_text(combo):
    return "-".join(str(x) for x in combo)


def _norm_series(s):
    s = pd.to_numeric(s, errors="coerce").fillna(0.0)
    mn = float(s.min())
    mx = float(s.max())
    if mx - mn < 1e-9:
        return pd.Series(0.5, index=s.index)
    return (s - mn) / (mx - mn)


def _prepare(df):
    x = df.copy()

    for col in [
        "win_n",
        "win_l",
        "top2_n",
        "top3_n",
        "top2_l",
        "top3_l",
        "motor2",
        "motor3",
        "boat2",
        "boat3",
    ]:
        x[col] = _norm_series(x[col])

    st_raw = pd.to_numeric(
        x.get("average_start_timing", 0),
        errors="coerce"
    ).fillna(0.0)

    # STは速いほど高評価
    st_max = float(st_raw.max())
    st_min = float(st_raw.min())

    if st_max - st_min < 1e-9:
        x["st"] = 0.5
    else:
        x["st"] = 1.0 - (st_raw - st_min) / (st_max - st_min)

    # 展示タイム0は有効値の中央値で補完
    exh_raw = pd.to_numeric(
        x.get("exhibition_time", 0),
        errors="coerce"
    ).fillna(0.0)

    valid_exh = exh_raw[exh_raw > 0]

    if len(valid_exh) > 0:
        median_exh = float(valid_exh.median())
    else:
        median_exh = 0.0

    exh_raw = exh_raw.mask(exh_raw <= 0, median_exh)

    exh_max = float(exh_raw.max())
    exh_min = float(exh_raw.min())

    if exh_max - exh_min < 1e-9:
        x["exh"] = 0.5
    else:
        # 展示タイムは速いほど高評価
        x["exh"] = 1.0 - (exh_raw - exh_min) / (
            exh_max - exh_min
        )

    # 進入コース
    course = pd.to_numeric(
        x.get("course_number", x.get("entry_number", 1)),
        errors="coerce"
    ).fillna(1.0)

    x["course"] = (
        1.0 - (course - 1.0) / 10.0
    ).clip(0.4, 1.0)

    # 1着スコア
    x["first_score"] = (
        0.22 * x["win_n"]
        + 0.13 * x["win_l"]
        + 0.13 * x["top2_n"]
        + 0.08 * x["top2_l"]
        + 0.10 * x["motor2"]
        + 0.06 * x["boat2"]
        + 0.12 * x["st"]
        + 0.10 * x["exh"]
        + 0.06 * x["course"]
    )

    # 2着スコア
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

    # 3着スコア
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


def _softmax(scores, temp=0.075):
    arr = np.asarray(scores, dtype=float)

    if len(arr) == 0:
        return np.array([])

    temp = max(float(temp), 0.001)

    z = arr / temp
    z -= np.max(z)

    e = np.exp(z)
    total = e.sum()

    if total <= 0:
        return np.ones(len(arr)) / len(arr)

    return e / total


def _combo_score(row_map, combo):
    a, b, c = combo

    return (
        row_map[a]["first_score"] * 1.00
        + row_map[b]["second_score"] * 0.72
        + row_map[c]["third_score"] * 0.58
        + (0.055 if a == 1 else 0.0)
        + (0.025 if a == 2 else 0.0)
        + (0.020 if b == 1 else 0.0)
    )


def _ordering_bonus(row_map, combo):
    a, b, c = combo

    second_score = row_map[b]["second_score"]
    third_score = row_map[c]["third_score"]

    strength_gap = np.clip(
        second_score - third_score,
        -0.30,
        0.30,
    )

    role_1 = np.clip(
        row_map[b]["second_score"]
        - row_map[c]["second_score"],
        -0.30,
        0.30,
    )

    role_2 = np.clip(
        row_map[c]["third_score"]
        - row_map[b]["third_score"],
        -0.30,
        0.30,
    )

    role = (role_1 + role_2) / 2.0

    return (
        0.045 * strength_gap
        + 0.025 * role
    )


def _venue_profile(stadium_no):
    return {
        7: 0.020,
        1: 0.015,
        20: 0.015,
        22: 0.015,
        2: 0.015,
        5: 0.010,
        11: 0.010,
        14: 0.010,
        13: 0.005,
        17: 0.005,
        18: 0.005,
        24: -0.015,
        9: -0.010,
        16: -0.005,
        3: -0.005,
    }.get(int(stadium_no or 0), 0.0)


def _apply_venue_adjustment(combo_scores, stadium_no):
    adj = _venue_profile(stadium_no)

    if abs(adj) < 1e-9:
        return combo_scores

    out = {}

    for combo, score in combo_scores.items():
        a, b, c = combo

        value = score

        if a == 1:
            value += adj
        elif a in (4, 5, 6):
            value -= adj * 0.35

        out[combo] = value

    return out


def _select_main_counter(
    combos,
    row_map,
    original_axis,
):
    same_axis = [
        combo for combo in combos
        if combo[0] == original_axis
    ]

    if not same_axis:
        same_axis = combos[:]

    # 5号艇を軸に近い候補として扱う既存ロジック
    if (
        original_axis != 5
        and 5 in row_map
    ):
        axis_gap = (
            row_map[original_axis]["first_score"]
            - row_map[5]["first_score"]
        )

        five_combos = [
            combo for combo in combos
            if combo[0] == 5
        ]

        if (
            axis_gap <= 0.025
            and five_combos
        ):
            best_five = max(
                five_combos,
                key=lambda c: _combo_score(row_map, c)
            )

            original_combos = [
                combo for combo in same_axis
            ]

            if original_combos:
                best_original = max(
                    original_combos,
                    key=lambda c: _combo_score(row_map, c)
                )

                if (
                    _combo_score(row_map, best_five)
                    >= _combo_score(row_map, best_original) - 0.035
                ):
                    same_axis.append(best_five)

    candidates = []

    for combo in same_axis:
        raw = _combo_score(row_map, combo)
        adjusted = raw + _ordering_bonus(
            row_map,
            combo
        )

        candidates.append(
            (adjusted, raw, combo)
        )

    candidates.sort(
        key=lambda x: x[0],
        reverse=True
    )

    if not candidates:
        return combos[0], combos[1]

    main = candidates[0][2]

    counter = None

    for _, _, combo in candidates[1:]:
        if combo != main:
            counter = combo
            break

    if counter is None:
        counter = combos[1]

    # 元の最有力候補を大きく下げない
    original_candidates = [
        combo for combo in combos
        if combo[0] == original_axis
    ]

    if original_candidates:
        original_best = max(
            original_candidates,
            key=lambda c: _combo_score(row_map, c)
        )

        main_raw = _combo_score(row_map, main)
        original_raw = _combo_score(
            row_map,
            original_best
        )

        if main_raw < original_raw - 0.045:
            main = original_best

    return main, counter


def _third_context_score(
    row_map,
    first_boat,
    second_boat,
    third_boat,
):
    """
    強い1-2着の組み合わせに対して、
    3着候補を再評価する実験用スコア。

    既存third_scoreを中心にしつつ、
    2着艇との相対関係と3着残り性能を少し加味する。
    """

    third = row_map[third_boat]

    base = third["third_score"]

    # 2着艇と3着候補の相対的な役割
    role_gap = (
        third["third_score"]
        - third["second_score"]
    )

    role_gap = float(
        np.clip(role_gap, -0.20, 0.20)
    )

    # 2着が強いほど、その後ろの3着候補を少し広く見る
    second_strength = row_map[second_boat]["second_score"]

    # 外枠だけを無条件に優遇しないため小さく調整
    course_value = third.get("course", 0.5)

    score = (
        base * 0.72
        + third["top2_n"] * 0.08
        + third["top2_l"] * 0.06
        + third["motor3"] * 0.05
        + third["boat3"] * 0.04
        + role_gap * 0.06
        + second_strength * 0.02
        + course_value * 0.01
    )

    # 1号艇・2号艇を候補から完全に消しすぎないための
    # 小さな残り目補正
    if third_boat == 2:
        score += 0.012

    if third_boat == 3:
        score += 0.006

    return float(score)


def _select_hole(
    combos,
    row_map,
    main,
    counter,
):
    """
    既存の穴選択をベースにしながら、
    強い1-2着の組み合わせに対する
    3着救済候補を追加する。
    """

    used = {main, counter}

    # まず従来通り、未使用コンボから穴候補を選ぶ
    normal_candidates = [
        combo for combo in combos
        if combo not in used
    ]

    if not normal_candidates:
        return combos[2]

    normal_best = max(
        normal_candidates,
        key=lambda c: (
            _combo_score(row_map, c)
            + _ordering_bonus(row_map, c)
        )
    )

    normal_score = (
        _combo_score(row_map, normal_best)
        + _ordering_bonus(
            row_map,
            normal_best
        )
    )

    # 本線の1-2を固定した「3着救済候補」
    rescue_pool = []

    first_boat = main[0]
    second_boat = main[1]

    for third_boat in row_map:
        if third_boat in (first_boat, second_boat):
            continue

        combo = (
            first_boat,
            second_boat,
            third_boat,
        )

        if combo in used:
            continue

        context_score = _third_context_score(
            row_map,
            first_boat,
            second_boat,
            third_boat,
        )

        rescue_pool.append(
            (context_score, combo)
        )

    if not rescue_pool:
        return normal_best

    rescue_pool.sort(
        key=lambda x: x[0],
        reverse=True
    )

    rescue_score, rescue_combo = rescue_pool[0]

    # 穴を何でも1-2固定にするのではなく、
    # 通常候補との差が小さいときだけ救済。
    #
    # これにより13.7%版の骨格をなるべく維持する。
    #
    # さらに2号艇・3号艇の残り目を拾いやすくする。
    if rescue_combo[2] == 2:
        threshold = 0.018
    elif rescue_combo[2] == 3:
        threshold = 0.012
    else:
        threshold = 0.006

    if rescue_score >= normal_score - threshold:
        return rescue_combo

    return normal_best


def predict(df, stadium_no=None):
    if df is None or len(df) < 3:
        raise ValueError("予測対象の艇数が3艇未満です。")

    x = _prepare(df)

    # 枠番をキーにする
    if "entry_number" in x.columns:
        boats = pd.to_numeric(
            x["entry_number"],
            errors="coerce"
        )
    elif "boat_number" in x.columns:
        boats = pd.to_numeric(
            x["boat_number"],
            errors="coerce"
        )
    else:
        boats = pd.Series(
            range(1, len(x) + 1),
            index=x.index
        )

    x["_boat"] = boats.astype("Int64")

    x = x[
        x["_boat"].notna()
        & x["_boat"].isin(BOATS)
    ].copy()

    if len(x) < 3:
        raise ValueError("有効な艇番が3艇未満です。")

    x = x.drop_duplicates(
        subset=["_boat"],
        keep="first"
    )

    active_boats = [
        int(v) for v in x["_boat"].tolist()
    ]

    row_map = {}

    for _, row in x.iterrows():
        boat = int(row["_boat"])
        row_map[boat] = {
            "first_score": float(row["first_score"]),
            "second_score": float(row["second_score"]),
            "third_score": float(row["third_score"]),
            "top2_n": float(row["top2_n"]),
            "top2_l": float(row["top2_l"]),
            "top3_n": float(row["top3_n"]),
            "top3_l": float(row["top3_l"]),
            "motor2": float(row["motor2"]),
            "motor3": float(row["motor3"]),
            "boat2": float(row["boat2"]),
            "boat3": float(row["boat3"]),
            "st": float(row["st"]),
            "exh": float(row["exh"]),
            "course": float(row["course"]),
        }

    combos = list(
        itertools.permutations(
            active_boats,
            3
        )
    )

    raw_scores = {}

    for combo in combos:
        raw_scores[combo] = _combo_score(
            row_map,
            combo
        )

    # AI確率
    probs = _softmax(
        list(raw_scores.values()),
        temp=0.075
    )

    combo_prob = {
        combo: float(prob)
        for combo, prob in zip(
            raw_scores.keys(),
            probs
        )
    }

    # 会場補正
    adjusted_scores = _apply_venue_adjustment(
        raw_scores,
        stadium_no
    )

    ranked = sorted(
        combos,
        key=lambda c: (
            adjusted_scores[c]
            + _ordering_bonus(row_map, c)
        ),
        reverse=True
    )

    # 最有力軸
    axis = max(
        active_boats,
        key=lambda b: row_map[b]["first_score"]
    )

    main, counter = _select_main_counter(
        ranked,
        row_map,
        axis
    )

    hole = _select_hole(
        ranked,
        row_map,
        main,
        counter
    )

    tickets = [
        main,
        counter,
        hole,
    ]

    # 重複防止
    unique_tickets = []

    for combo in tickets:
        if combo not in unique_tickets:
            unique_tickets.append(combo)

    # 3点を維持
    for combo in ranked:
        if combo not in unique_tickets:
            unique_tickets.append(combo)

        if len(unique_tickets) >= 3:
            break

    tickets = unique_tickets[:3]

    # 確率
    ticket_data = []

    for combo in tickets:
        ticket_data.append({
            "combo": combo_text(combo),
            "probability": round(
                combo_prob.get(combo, 0.0) * 100,
                2
            ),
        })

    # 軸の1着確率
    first_values = np.array([
        row_map[b]["first_score"]
        for b in active_boats
    ])

    first_probs = _softmax(
        first_values,
        temp=0.075
    )

    first_prob_map = {
        boat: float(prob)
        for boat, prob in zip(
            active_boats,
            first_probs
        )
    }

    axis_first_probability = (
        first_prob_map.get(axis, 0.0) * 100
    )

    # 軸3着内確率
    top3_values = np.array([
        row_map[b]["second_score"]
        + row_map[b]["third_score"] * 0.75
        for b in active_boats
    ])

    top3_probs = _softmax(
        top3_values,
        temp=0.10
    )

    axis_top3_map = {
        boat: float(prob)
        for boat, prob in zip(
            active_boats,
            top3_probs
        )
    }

    axis_top3_probability = (
        axis_top3_map.get(axis, 0.0) * 100
    )

    # ランキング
    ranking = []

    for boat in sorted(
        active_boats,
        key=lambda b: row_map[b]["first_score"],
        reverse=True
    ):
        ranking.append({
            "boat": boat,
            "first_score": round(
                row_map[boat]["first_score"],
                4
            ),
            "second_score": round(
                row_map[boat]["second_score"],
                4
            ),
            "third_score": round(
                row_map[boat]["third_score"],
                4
            ),
        })

    # 信頼度
    top_scores = sorted(
        [
            row_map[b]["first_score"]
            for b in active_boats
        ],
        reverse=True
    )

    if len(top_scores) >= 2:
        gap = top_scores[0] - top_scores[1]
    else:
        gap = 0.0

    confidence = float(
        np.clip(
            65.0 + gap * 100.0,
            0.0,
            95.0
        )
    )

    return {
        "tickets": ticket_data,
        "ranking": ranking,
        "confidence": round(
            confidence,
            1
        ),
        "axis": axis,
        "axis_first": round(
            axis_first_probability,
            1
        ),
        "axis_top3": round(
            axis_top3_probability,
            1
        ),
        "all_combos": [
            {
                "combo": combo_text(combo),
                "probability": round(
                    combo_prob.get(combo, 0.0) * 100,
                    2
                ),
            }
            for combo in ranked
        ],
        "df": x,
            }
