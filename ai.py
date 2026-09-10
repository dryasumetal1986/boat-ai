import itertools

import numpy as np
import pandas as pd


BOATS = (1, 2, 3, 4, 5, 6)


def _to_num(series, default=0.0):
    return pd.to_numeric(
        series,
        errors="coerce"
    ).fillna(default).astype(float)


def _norm(series, higher=True):
    """
    6艇の中で0〜1に正規化する。
    higher=Falseなら値が小さいほど高評価。
    """

    x = _to_num(series)

    lo = float(x.min())
    hi = float(x.max())

    if hi - lo < 1e-9:
        return pd.Series(
            0.5,
            index=x.index
        )

    z = (x - lo) / (hi - lo)

    if not higher:
        z = 1.0 - z

    return z


def _prepare(df):
    """
    AI計算用データを作成。
    """

    x = (
        df.copy()
        .sort_values("boat")
        .reset_index(drop=True)
    )

    # 全国成績
    x["win_n"] = _norm(
        x["national_win_rate"]
    )

    x["top2_n"] = _norm(
        x["national_top_2_percent"]
    )

    x["top3_n"] = _norm(
        x["national_top_3_percent"]
    )

    # 当地成績
    x["win_l"] = _norm(
        x["local_win_rate"]
    )

    x["top2_l"] = _norm(
        x["local_top_2_percent"]
    )

    x["top3_l"] = _norm(
        x["local_top_3_percent"]
    )

    # モーター・ボート
    x["motor2"] = _norm(
        x["motor_top_2_percent"]
    )

    x["motor3"] = _norm(
        x["motor_top_3_percent"]
    )

    x["boat2"] = _norm(
        x["boat_top_2_percent"]
    )

    x["boat3"] = _norm(
        x["boat_top_3_percent"]
    )

    # 平均ST
    # STは小さいほど評価
    x["st"] = _norm(
        x["average_start_timing"],
        higher=False
    )

    # 展示タイム
    exhibition = _to_num(
        x["exhibition_time"]
    )

    valid = exhibition[
        exhibition > 0
    ]

    if len(valid) > 0:
        fill_value = float(
            valid.median()
        )
    else:
        fill_value = 1.0

    exhibition = exhibition.replace(
        0,
        np.nan
    ).fillna(fill_value)

    x["exh"] = _norm(
        exhibition,
        higher=False
    )

    # 進入コース
    course = _to_num(
        x["course_number"]
    )

    course = course.where(
        course > 0,
        x["boat"]
    )

    # 1コースを最も高く評価
    x["course"] = (
        1.0
        - (course - 1.0) / 10.0
    ).clip(
        0.4,
        1.0
    )

    # 1着評価
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

    # 2着評価
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

    # 3着評価
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


def _softmax(values, temperature=0.10):
    """
    スコアを確率へ変換。
    """

    values = np.asarray(
        values,
        dtype=float
    )

    temperature = max(
        float(temperature),
        0.001
    )

    scaled = values / temperature

    scaled -= np.max(
        scaled
    )

    exp_values = np.exp(
        scaled
    )

    total = exp_values.sum()

    if total <= 0:
        return np.ones(
            len(values)
        ) / len(values)

    return exp_values / total


def combo_text(combo):
    """
    3連単の組み合わせを表示用文字列に変換。

    例:
    (1, 2, 3) → "1-2-3"
    """

    if combo is None:
        return ""

    return "-".join(
        str(int(x))
        for x in combo
    )


def predict(df):
    """
    6艇の出走表から3連単3点を予想する。

    本線・対抗・穴の3点だけを返す。

    重要:
    comboは必ず1〜6号艇の数字。
    選手登録番号、モーター番号、
    ボート番号は使用しない。
    """

    if not isinstance(
        df,
        pd.DataFrame
    ):
        raise ValueError(
            "出走表データがDataFrameではありません。"
        )

    if len(df) != 6:
        raise ValueError(
            "6艇分の出走表が必要です。"
        )

    required = [
        "boat",
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
        "average_start_timing",
        "course_number",
        "exhibition_time",
    ]

    missing = [
        col
        for col in required
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            "AI計算に必要な項目がありません: "
            + ", ".join(missing)
        )

    boats = pd.to_numeric(
        df["boat"],
        errors="coerce"
    )

    if boats.isna().any():
        raise ValueError(
            "艇番に不正な値があります。"
        )

    boats = boats.astype(int)

    if set(boats) != set(BOATS):
        raise ValueError(
            "艇番が1〜6になっていません。"
        )

    x = _prepare(df)

    # 念のため最後にも確認
    if set(
        x["boat"].astype(int)
    ) != set(BOATS):
        raise ValueError(
            "AI内部の艇番が1〜6になっていません。"
        )

    first_score = dict(
        zip(
            x["boat"].astype(int),
            x["first_score"]
        )
    )

    second_score = dict(
        zip(
            x["boat"].astype(int),
            x["second_score"]
        )
    )

    third_score = dict(
        zip(
            x["boat"].astype(int),
            x["third_score"]
        )
    )

    # 全120通りの3連単を評価
    combinations = []

    for a, b, c in itertools.permutations(
        BOATS,
        3
    ):

        score = (
            1.00 * first_score[a]
            + 0.72 * second_score[b]
            + 0.58 * third_score[c]
        )

        # 1コースの基本的な優位性
        if a == 1:
            score += 0.055
        elif a == 2:
            score += 0.025

        # 2着1号艇も少し評価
        if b == 1:
            score += 0.020

        combinations.append(
            (
                (a, b, c),
                float(score)
            )
        )

    raw_scores = np.array(
        [
            score
            for combo, score
            in combinations
        ]
    )

    probabilities = _softmax(
        raw_scores,
        temperature=0.075
    )

    ranked = sorted(
        [
            (
                combo,
                float(prob),
                score
            )
            for (
                combo,
                score
            ), prob
            in zip(
                combinations,
                probabilities
            )
        ],
        key=lambda item: item[1],
        reverse=True
    )

    # 本線
    main = ranked[0]

    # 対抗
    counter = None

    for item in ranked[1:]:
        if item[0] != main[0]:
            counter = item
            break

    if counter is None:
        counter = ranked[1]

    # 穴
    # 本線・対抗とは違う1着艇を優先
    hole = None

    for item in ranked[1:]:

        if item[0] == main[0]:
            continue

        if item[0] == counter[0]:
            continue

        hole = item
        break

    if hole is None:

        for item in ranked[1:]:

            if item[0] != main[0]:
                hole = item
                break

    if hole is None:
        hole = ranked[2]

    tickets = [
        {
            "label": "本線",
            "combo": tuple(main[0]),
            "prob": float(main[1]),
        },
        {
            "label": "対抗",
            "combo": tuple(counter[0]),
            "prob": float(counter[1]),
        },
        {
            "label": "穴",
            "combo": tuple(hole[0]),
            "prob": float(hole[1]),
        },
    ]

    # 最有力軸
    first_prob_values = _softmax(
        [
            first_score[b]
            for b in BOATS
        ],
        temperature=0.10
    )

    first_ranking = sorted(
        zip(
            BOATS,
            first_prob_values
        ),
        key=lambda item: item[1],
        reverse=True
    )

    axis = int(
        first_ranking[0][0]
    )

    axis_top3 = sum(
        prob
        for _, prob
        in first_ranking[:3]
    )

    margin = (
        first_ranking[0][1]
        - first_ranking[1][1]
    )

    # 信頼度
    confidence = min(
        95.0,
        max(
            55.0,
            62.0 + margin * 220.0
        )
    )

    # 最終安全確認
    for ticket in tickets:

        combo = ticket["combo"]

        if len(combo) != 3:
            raise ValueError(
                "3連単の組み合わせが不正です。"
            )

        if len(set(combo)) != 3:
            raise ValueError(
                "3連単の艇番が重複しています。"
            )

        if not all(
            1 <= int(boat) <= 6
            for boat in combo
        ):
            raise ValueError(
                "予想に1〜6以外の艇番が含まれています。"
            )

    return {
        "tickets": tickets,
        "ranking": ranked,
        "confidence": round(
            confidence,
            1
        ),
        "axis": axis,
        "axis_top3": float(
            axis_top3
        ),
        "all_combos": ranked,
        "df": x,
        }
