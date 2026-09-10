import itertools

import numpy as np
import pandas as pd


# =========================================================
# 基本ユーティリティ
# =========================================================

def _clip(value, low=0.0, high=1.0):
    try:
        return float(np.clip(float(value), low, high))
    except Exception:
        return low


def _col(df, name, default=0.0):
    if name in df.columns:
        return pd.to_numeric(df[name], errors="coerce").fillna(default)
    return pd.Series(default, index=df.index, dtype=float)


def combo_text(combo):
    return "-".join(str(int(x)) for x in combo)


# =========================================================
# 各艇の評価値
# =========================================================

def _first_score(row):
    win_n = _clip(row.get("national_win_rate", 0))
    win_l = _clip(row.get("local_win_rate", 0))
    top2_n = _clip(row.get("national_top_2_percent", 0))
    top2_l = _clip(row.get("local_top_2_percent", 0))
    motor2 = _clip(row.get("motor_top_2_percent", 0))
    boat2 = _clip(row.get("boat_top_2_percent", 0))

    st = _clip(row.get("average_start_timing", 0), 0, 1)

    # 展示タイム
    exh = _clip(row.get("_exhibition_score", 0), 0, 1)

    course = _clip(row.get("_course_score", 0), 0.4, 1.0)

    score = (
        0.22 * win_n
        + 0.13 * win_l
        + 0.13 * top2_n
        + 0.08 * top2_l
        + 0.10 * motor2
        + 0.06 * boat2
        + 0.12 * st
        + 0.10 * exh
        + 0.06 * course
    )

    return float(score)


def _second_score(row):
    top2_n = _clip(row.get("national_top_2_percent", 0))
    top2_l = _clip(row.get("local_top_2_percent", 0))
    top3_n = _clip(row.get("national_top_3_percent", 0))
    top3_l = _clip(row.get("local_top_3_percent", 0))
    motor2 = _clip(row.get("motor_top_2_percent", 0))
    motor3 = _clip(row.get("motor_top_3_percent", 0))
    boat2 = _clip(row.get("boat_top_2_percent", 0))
    st = _clip(row.get("average_start_timing", 0), 0, 1)

    # 今回の実験：
    # 2着評価にも展示タイムを少し追加。
    # その分、全国2連率を少しだけ下げる。
    exh = _clip(row.get("_exhibition_score", 0), 0, 1)

    score = (
        0.16 * top2_n
        + 0.14 * top2_l
        + 0.16 * top3_n
        + 0.10 * top3_l
        + 0.14 * motor2
        + 0.08 * motor3
        + 0.10 * boat2
        + 0.08 * st
        + 0.04 * exh
    )

    return float(score)


def _third_score(row):
    top3_n = _clip(row.get("national_top_3_percent", 0))
    top3_l = _clip(row.get("local_top_3_percent", 0))
    motor3 = _clip(row.get("motor_top_3_percent", 0))
    boat3 = _clip(row.get("boat_top_3_percent", 0))
    top2_n = _clip(row.get("national_top_2_percent", 0))
    top2_l = _clip(row.get("local_top_2_percent", 0))
    st = _clip(row.get("average_start_timing", 0), 0, 1)
    exh = _clip(row.get("_exhibition_score", 0), 0, 1)

    # 今回の実験：
    # 3着評価にも展示タイムを少し追加。
    # その分、全国3連率を少しだけ下げる。
    score = (
        0.14 * top3_n
        + 0.14 * top3_l
        + 0.16 * motor3
        + 0.12 * boat3
        + 0.12 * top2_n
        + 0.10 * top2_l
        + 0.10 * st
        + 0.12 * exh
    )

    return float(score)


# =========================================================
# 展示タイム・進入コース
# =========================================================

def _prepare_features(df):
    work = df.copy()

    # 展示タイム：
    # 小さいほど良い。
    # レース内で相対評価する。
    exh = pd.to_numeric(
        work.get("exhibition_time", 0),
        errors="coerce",
    ).fillna(0.0)

    valid_exh = exh[exh > 0]

    if len(valid_exh) >= 2:
        best = float(valid_exh.min())
        worst = float(valid_exh.max())

        if worst > best:
            exhibition_score = 1.0 - (exh - best) / (worst - best)
            exhibition_score = exhibition_score.clip(0.0, 1.0)
        else:
            exhibition_score = pd.Series(
                0.5,
                index=work.index,
                dtype=float,
            )
    else:
        exhibition_score = pd.Series(
            0.5,
            index=work.index,
            dtype=float,
        )

    work["_exhibition_score"] = exhibition_score

    # 進入コース。
    # 1コースを高く評価し、外ほど少しずつ下げる。
    course = pd.to_numeric(
        work.get("course_number", work.get("boat", 1)),
        errors="coerce",
    ).fillna(work.get("boat", 1))

    course_score = 1.0 - (course - 1.0) / 10.0
    course_score = course_score.clip(0.4, 1.0)

    work["_course_score"] = course_score

    return work


# =========================================================
# 3連単コンボ評価
# =========================================================

def _combo_score(first, second, third, axis):
    score = (
        1.00 * first["first_score"]
        + 0.72 * second["second_score"]
        + 0.58 * third["third_score"]
    )

    # 内枠補正
    if axis == 1:
        score += 0.055
    elif axis == 2:
        score += 0.025

    # 1号艇が2着・3着に絡む場合の軽い補正
    if second["boat"] == 1 or third["boat"] == 1:
        score += 0.020

    return float(score)


def _make_rankings(df):
    rows = []

    for _, row in df.iterrows():
        boat = int(row["boat"])

        first = _first_score(row)
        second = _second_score(row)
        third = _third_score(row)

        rows.append(
            {
                "boat": boat,
                "first_score": first,
                "second_score": second,
                "third_score": third,
            }
        )

    return rows


# =========================================================
# 本線・対抗の並び補正
# =========================================================

def _ordering_bonus(axis_row, second_row, third_row):
    second_strength = (
        second_row["second_score"]
        + 0.55 * second_row["first_score"]
    )

    third_strength = (
        third_row["third_score"]
        + 0.40 * third_row["first_score"]
    )

    strength_gap = (
        second_strength
        - third_strength
    )

    second_role = (
        second_row["second_score"]
        - second_row["third_score"]
    )

    third_role = (
        third_row["third_score"]
        - third_row["second_score"]
    )

    role = second_role - third_role

    strength_gap = float(
        np.clip(strength_gap, -0.30, 0.30)
    )

    role = float(
        np.clip(role, -0.30, 0.30)
    )

    # 現在のベースラインC
    bonus = (
        0.045 * strength_gap
        + 0.025 * role
    )

    return float(bonus)


# =========================================================
# 本線・対抗選択
# =========================================================

def _select_main_counter(rankings):
    ranked_first = sorted(
        rankings,
        key=lambda x: x["first_score"],
        reverse=True,
    )

    if len(ranked_first) < 3:
        return None, None

    original_axis = ranked_first[0]

    # -----------------------------------------------------
    # 5号艇レスキュー
    # -----------------------------------------------------
    axis = original_axis

    boat5 = next(
        (x for x in rankings if x["boat"] == 5),
        None,
    )

    if (
        boat5 is not None
        and original_axis["boat"] != 5
    ):
        first_gap = (
            original_axis["first_score"]
            - boat5["first_score"]
        )

        best_boat5_raw = -999.0

        for second in rankings:
            if second["boat"] in {
                original_axis["boat"],
                5,
            }:
                continue

            for third in rankings:
                if third["boat"] in {
                    original_axis["boat"],
                    5,
                    second["boat"],
                }:
                    continue

                raw = _combo_score(
                    boat5,
                    second,
                    third,
                    5,
                )

                best_boat5_raw = max(
                    best_boat5_raw,
                    raw,
                )

        original_best_raw = -999.0

        for second in rankings:
            if second["boat"] == original_axis["boat"]:
                continue

            for third in rankings:
                if third["boat"] in {
                    original_axis["boat"],
                    second["boat"],
                }:
                    continue

                raw = _combo_score(
                    original_axis,
                    second,
                    third,
                    original_axis["boat"],
                )

                original_best_raw = max(
                    original_best_raw,
                    raw,
                )

        if (
            first_gap <= 0.025
            and best_boat5_raw >= original_best_raw - 0.035
        ):
            axis = boat5

    axis_boat = axis["boat"]

    same_axis = [
        x for x in rankings
        if x["boat"] != axis_boat
    ]

    same_axis = sorted(
        same_axis,
        key=lambda x: (
            x["second_score"]
            + 0.55 * x["first_score"]
        ),
        reverse=True,
    )[:10]

    candidates = []

    for second in same_axis:
        for third in same_axis:
            if second["boat"] == third["boat"]:
                continue

            raw = _combo_score(
                axis,
                second,
                third,
                axis_boat,
            )

            bonus = _ordering_bonus(
                axis,
                second,
                third,
            )

            adjusted = raw + bonus

            candidates.append(
                {
                    "combo": (
                        axis_boat,
                        second["boat"],
                        third["boat"],
                    ),
                    "raw": raw,
                    "adjusted": adjusted,
                }
            )

    if not candidates:
        return axis, None

    candidates.sort(
        key=lambda x: x["adjusted"],
        reverse=True,
    )

    main_candidate = candidates[0]

    # -----------------------------------------------------
    # 安全策
    # 元の最高評価から大きく離れた場合は戻す
    # -----------------------------------------------------
    original_candidates = []

    for second in same_axis:
        for third in same_axis:
            if second["boat"] == third["boat"]:
                continue

            raw = _combo_score(
                original_axis,
                second,
                third,
                original_axis["boat"],
            )

            original_candidates.append(
                {
                    "combo": (
                        original_axis["boat"],
                        second["boat"],
                        third["boat"],
                    ),
                    "raw": raw,
                }
            )

    original_candidates.sort(
        key=lambda x: x["raw"],
        reverse=True,
    )

    if original_candidates:
        original_best = original_candidates[0]

        if (
            main_candidate["raw"]
            < original_best["raw"] - 0.045
        ):
            axis = original_axis

            candidates = []

            for second in same_axis:
                for third in same_axis:
                    if second["boat"] == third["boat"]:
                        continue

                    raw = _combo_score(
                        axis,
                        second,
                        third,
                        axis["boat"],
                    )

                    bonus = _ordering_bonus(
                        axis,
                        second,
                        third,
                    )

                    candidates.append(
                        {
                            "combo": (
                                axis["boat"],
                                second["boat"],
                                third["boat"],
                            ),
                            "raw": raw,
                            "adjusted": raw + bonus,
                        }
                    )

            candidates.sort(
                key=lambda x: x["adjusted"],
                reverse=True,
            )

            main_candidate = candidates[0]

    # -----------------------------------------------------
    # 対抗
    # 本線とは2着・3着の並びを変える
    # -----------------------------------------------------
    counter_candidate = None

    for candidate in candidates:
        if (
            candidate["combo"]
            != main_candidate["combo"]
        ):
            counter_candidate = candidate
            break

    if counter_candidate is None:
        for candidate in candidates:
            if candidate["combo"] != main_candidate["combo"]:
                counter_candidate = candidate
                break

    return axis, (
        main_candidate,
        counter_candidate,
    )


# =========================================================
# 穴選択
# =========================================================

def _select_hole(rankings, axis):
    if axis is None:
        return None

    axis_boat = axis["boat"]

    non_axis = [
        x for x in rankings
        if x["boat"] != axis_boat
    ]

    if len(non_axis) < 2:
        return None

    ranked_first = sorted(
        non_axis,
        key=lambda x: x["first_score"],
        reverse=True,
    )

    # 代替軸候補は上位4艇
    alternative_axes = ranked_first[:4]

    candidates = []

    for alt_axis in alternative_axes:
        for second in rankings:
            if second["boat"] == alt_axis["boat"]:
                continue

            for third in rankings:
                if third["boat"] in {
                    alt_axis["boat"],
                    second["boat"],
                }:
                    continue

                raw = _combo_score(
                    alt_axis,
                    second,
                    third,
                    alt_axis["boat"],
                )

                first_score = alt_axis["first_score"]

                candidates.append(
                    {
                        "combo": (
                            alt_axis["boat"],
                            second["boat"],
                            third["boat"],
                        ),
                        "score": (
                            0.70 * first_score
                            + 0.30 * raw
                        ),
                    }
                )

    if not candidates:
        return None

    # 穴は本線・対抗と被らない候補を優先する
    candidates.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return candidates[0]


# =========================================================
# メイン予想
# =========================================================

def predict(df):
    if df is None or len(df) != 6:
        raise ValueError(
            "予想には6艇分のデータが必要です。"
        )

    work = _prepare_features(df)

    if "boat" not in work.columns:
        raise ValueError(
            "boat列がありません。"
        )

    work["boat"] = pd.to_numeric(
        work["boat"],
        errors="coerce",
    )

    work = work.dropna(
        subset=["boat"]
    ).copy()

    work["boat"] = work["boat"].astype(int)

    if set(work["boat"]) != {1, 2, 3, 4, 5, 6}:
        raise ValueError(
            "艇番1〜6が揃っていません。"
        )

    rankings = _make_rankings(work)

    axis, main_counter = _select_main_counter(
        rankings
    )

    if axis is None or main_counter is None:
        raise ValueError(
            "本線・対抗の生成に失敗しました。"
        )

    main_candidate, counter_candidate = (
        main_counter
    )

    if counter_candidate is None:
        counter_candidate = main_candidate

    hole_candidate = _select_hole(
        rankings,
        axis,
    )

    if hole_candidate is None:
        # 万一穴が作れない場合の安全な代替
        fallback = None

        for candidate in rankings:
            if candidate["boat"] != axis["boat"]:
                fallback = candidate
                break

        if fallback is None:
            raise ValueError(
                "穴候補の生成に失敗しました。"
            )

        others = [
            x for x in rankings
            if x["boat"] not in {
                axis["boat"],
                fallback["boat"],
            }
        ]

        others.sort(
            key=lambda x: x["third_score"],
            reverse=True,
        )

        if not others:
            raise ValueError(
                "穴候補の生成に失敗しました。"
            )

        hole_candidate = {
            "combo": (
                fallback["boat"],
                axis["boat"],
                others[0]["boat"],
            ),
            "score": (
                0.70 * fallback["first_score"]
                + 0.30 * others[0]["third_score"]
            ),
        }

    tickets = [
        {
            "label": "本線",
            "combo": tuple(
                int(x)
                for x in main_candidate["combo"]
            ),
            "score": float(
                main_candidate["adjusted"]
            ),
        },
        {
            "label": "対抗",
            "combo": tuple(
                int(x)
                for x in counter_candidate["combo"]
            ),
            "score": float(
                counter_candidate["adjusted"]
            ),
        },
        {
            "label": "穴",
            "combo": tuple(
                int(x)
                for x in hole_candidate["combo"]
            ),
            "score": float(
                hole_candidate["score"]
            ),
        },
    ]

    # 3点の重複防止
    used = set()
    clean_tickets = []

    for ticket in tickets:
        combo = ticket["combo"]

        if (
            len(combo) == 3
            and len(set(combo)) == 3
            and all(1 <= x <= 6 for x in combo)
            and combo not in used
        ):
            used.add(combo)
            clean_tickets.append(ticket)

    # 何らかの理由で3点未満になった場合は
    # 評価上位コンボから補完
    if len(clean_tickets) < 3:
        axis_boat = axis["boat"]
        all_candidates = []

        for first in rankings:
            for second in rankings:
                if first["boat"] == second["boat"]:
                    continue

                for third in rankings:
                    if third["boat"] in {
                        first["boat"],
                        second["boat"],
                    }:
                        continue

                    combo = (
                        first["boat"],
                        second["boat"],
                        third["boat"],
                    )

                    if combo in used:
                        continue

                    score = _combo_score(
                        first,
                        second,
                        third,
                        first["boat"],
                    )

                    all_candidates.append(
                        (score, combo)
                    )

        all_candidates.sort(
            key=lambda x: x[0],
            reverse=True,
        )

        for score, combo in all_candidates:
            if combo in used:
                continue

            clean_tickets.append(
                {
                    "label": (
                        "対抗"
                        if not any(
                            x["label"] == "対抗"
                            for x in clean_tickets
                        )
                        else "穴"
                    ),
                    "combo": combo,
                    "score": float(score),
                }
            )

            used.add(combo)

            if len(clean_tickets) >= 3:
                break

    # ラベルを必ず 本線・対抗・穴 に固定
    label_order = ["本線", "対抗", "穴"]

    for index, ticket in enumerate(clean_tickets[:3]):
        ticket["label"] = label_order[index]

    return {
        "axis": int(main_candidate["combo"][0]),
        "tickets": clean_tickets[:3],
                }
