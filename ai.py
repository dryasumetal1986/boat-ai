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
    AI計算用データを作成する。
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

    # モーター
    x["motor2"] = _norm(
        x["motor_top_2_percent"]
    )

    x["motor3"] = _norm(
        x["motor_top_3_percent"]
    )

    # ボート
    x["boat2"] = _norm(
        x["boat_top_2_percent"]
    )

    x["boat3"] = _norm(
        x["boat_top_3_percent"]
    )

    # 平均ST
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

    # 1コースを高評価
    x["course"] = (
        1.0
        - (course - 1.0) / 10.0
    ).clip(
        0.4,
        1.0
    )

    # ------------------------------------------------
    # 1着評価
    # ------------------------------------------------

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

    # ------------------------------------------------
    # 2着評価
    # ------------------------------------------------

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

    # ------------------------------------------------
    # 3着評価
    # ------------------------------------------------

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
    スコアを確率に変換する。
    """

    values = np.asarray(
        values,
        dtype=float
    )

    if len(values) == 0:
        return np.array([])

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
    3連単を表示用文字列に変換。

    例:
    (1, 2, 3) -> "1-2-3"
    """

    if combo is None:
        return ""

    return "-".join(
        str(int(x))
        for x in combo
    )


def _validate_df(df):
    """
    入力データを安全確認する。
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


def predict(df):
    """
    6艇の出走表から3連単3点を予想する。

    今回の改善点:

    1. 最有力軸と本線1着を一致させる
    2. 本線・対抗は軸を中心に組み立てる
    3. 穴は別1着展開を優先する
    4. 2着・3着の役割を少し明確にする
    5. 3点が同じような組み合わせになりすぎないようにする
    6. comboは必ず1〜6号艇
    7. combo_textとの互換性を維持
    """

    # ------------------------------------------------
    # 入力確認
    # ------------------------------------------------

    _validate_df(df)

    # ------------------------------------------------
    # AI用データ
    # ------------------------------------------------

    x = _prepare(df)

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

    # ------------------------------------------------
    # まず1着候補を決める
    # ------------------------------------------------

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

    # 最有力軸
    axis = int(
        first_ranking[0][0]
    )

    # 1着候補2位
    second_first_boat = int(
        first_ranking[1][0]
    )

    # 1着候補3位
    third_first_boat = int(
        first_ranking[2][0]
    )

    # ------------------------------------------------
    # 1着軸の信頼度関連
    # ------------------------------------------------

    axis_top3 = sum(
        prob
        for _, prob
        in first_ranking[:3]
    )

    margin = (
        first_ranking[0][1]
        - first_ranking[1][1]
    )

    # 表示上の信頼度。
    # 95%を超えないようにする。
    confidence = min(
        95.0,
        max(
            55.0,
            62.0 + margin * 220.0
        )
    )

    # ------------------------------------------------
    # 全120通りの3連単スコア
    #
    # ここでは確率計算用に全組み合わせを評価する。
    # ------------------------------------------------

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

        # ------------------------------------------------
        # 今回の改善
        #
        # 2着候補として強い艇は2着へ、
        # 3着候補として強い艇は3着へ、
        # 少しだけ優先する。
        #
        # 補正は小さくして、元のAIの順位を
        # 大きく壊さないようにする。
        # ------------------------------------------------

        second_role = (
            second_score[b]
            - third_score[b]
        )

        third_role = (
            third_score[c]
            - second_score[c]
        )

        score += (
            0.055 * second_role
        )

        score += (
            0.045 * third_role
        )

        # ------------------------------------------------
        # 1コースの優位性
        # ------------------------------------------------

        if a == 1:
            score += 0.055

        elif a == 2:
            score += 0.025

        # 2着1号艇
        if b == 1:
            score += 0.020

        # ------------------------------------------------
        # 軸との整合性
        #
        # 最有力軸を本線の1着候補として優先する。
        # ------------------------------------------------

        if a == axis:
            score += 0.065

        # 軸が2着の場合も少し残す
        if b == axis:
            score += 0.018

        # 軸が3着の場合も少し残す
        if c == axis:
            score += 0.008

        combinations.append(
            (
                (a, b, c),
                float(score)
            )
        )

    # ------------------------------------------------
    # 全組み合わせの確率
    # ------------------------------------------------

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

    # ------------------------------------------------
    # 軸を中心に2着・3着候補を評価
    # ------------------------------------------------

    same_axis_candidates = [
        item
        for item in ranked
        if item[0][0] == axis
    ]

    # 念のため空にならないようにする
    if not same_axis_candidates:
        same_axis_candidates = ranked

    # ------------------------------------------------
    # 本線
    #
    # 軸を1着固定。
    # 2着・3着は総合評価の高いもの。
    # ------------------------------------------------

    main = same_axis_candidates[0]

    # ------------------------------------------------
    # 対抗
    #
    # 本線と1着は同じ軸。
    # ただし2着・3着の組み合わせを変える。
    # ------------------------------------------------

    counter = None

    for item in same_axis_candidates[1:]:

        if item[0] == main[0]:
            continue

        # 本線と少なくとも2着か3着が違う
        if (
            item[0][1] != main[0][1]
            or item[0][2] != main[0][2]
        ):
            counter = item
            break

    if counter is None:

        for item in same_axis_candidates:

            if item[0] != main[0]:
                counter = item
                break

    if counter is None:
        counter = main

    # ------------------------------------------------
    # 穴
    #
    # ここは別展開。
    # 1着候補2位・3位を優先する。
    #
    # 「軸が絶対1着」ではないことを考慮し、
    # 穴だけは軸以外の1着を許可する。
    # ------------------------------------------------

    hole = None

    alternative_first_boats = [
        second_first_boat,
        third_first_boat,
    ]

    for alternative_boat in alternative_first_boats:

        candidates = [
            item
            for item in ranked
            if item[0][0] == alternative_boat
        ]

        for item in candidates:

            combo = item[0]

            # 本線・対抗と同一なら除外
            if combo == main[0]:
                continue

            if combo == counter[0]:
                continue

            hole = item
            break

        if hole is not None:
            break

    # ------------------------------------------------
    # 穴候補が取れない場合の安全処理
    # ------------------------------------------------

    if hole is None:

        for item in ranked:

            if item[0] == main[0]:
                continue

            if item[0] == counter[0]:
                continue

            if item[0][0] == axis:
                continue

            hole = item
            break

    if hole is None:

        for item in ranked:

            if item[0] != main[0]:

                hole = item
                break

    if hole is None:
        hole = ranked[2]

    # ------------------------------------------------
    # 3点
    # ------------------------------------------------

    tickets = [
        {
            "label": "本線",
            "combo": tuple(
                int(x)
                for x in main[0]
            ),
            "prob": float(
                main[1]
            ),
        },
        {
            "label": "対抗",
            "combo": tuple(
                int(x)
                for x in counter[0]
            ),
            "prob": float(
                counter[1]
            ),
        },
        {
            "label": "穴",
            "combo": tuple(
                int(x)
                for x in hole[0]
            ),
            "prob": float(
                hole[1]
            ),
        },
    ]

    # ------------------------------------------------
    # 最終安全確認
    # ------------------------------------------------

    for ticket in tickets:

        combo = ticket["combo"]

        # 3連単であること
        if len(combo) != 3:
            raise ValueError(
                "3連単の組み合わせが不正です。"
            )

        # 同じ艇が重複していないこと
        if len(set(combo)) != 3:
            raise ValueError(
                "3連単の艇番が重複しています。"
            )

        # 1〜6号艇だけであること
        if not all(
            1 <= int(boat) <= 6
            for boat in combo
        ):
            raise ValueError(
                "予想に1〜6以外の艇番が含まれています。"
            )

    # 本線は必ず軸1着
    if tickets[0]["combo"][0] != axis:
        raise ValueError(
            "本線の1着艇とAI最有力軸が一致していません。"
        )

    # 3点が完全に同一になっていないこと
    combo_set = {
        ticket["combo"]
        for ticket in tickets
    }

    if len(combo_set) < 3:

        for item in ranked:

            candidate = tuple(
                int(x)
                for x in item[0]
            )

            if candidate in combo_set:
                continue

            if len(combo_set) >= 3:
                break

            tickets[-1]["combo"] = candidate
            tickets[-1]["prob"] = float(
                item[1]
            )
            combo_set.add(candidate)

    # ------------------------------------------------
    # 結果
    # ------------------------------------------------

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
