import itertools

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier


# =========================================================
# AIで使う特徴量
# =========================================================
FEATURES = [
    "枠",
    "展示進入",
    "全国勝率",
    "全国2連率",
    "全国3連率",
    "当地勝率",
    "当地2連率",
    "モーター2連率",
    "平均ST",
    "展示ST",
    "展示タイム",
    "場",
]


# =========================================================
# 数値変換
# =========================================================
def _num(value, default=0.0):

    if value is None:
        return default

    try:
        text = str(value).strip()

        if text in (
            "",
            "-",
            "--",
            "None",
            "null",
        ):
            return default

        text = text.replace("%", "")
        text = text.replace("秒", "")

        return float(text)

    except Exception:
        return default


# =========================================================
# 特徴量を数値化
# =========================================================
def _prepare_features(df):

    work = df.copy()

    for col in FEATURES:

        if col not in work.columns:
            work[col] = 0.0

        work[col] = pd.to_numeric(
            work[col],
            errors="coerce",
        ).fillna(0.0)

    return work[FEATURES]


# =========================================================
# 基本能力スコア
# =========================================================
def _ability_score(df):

    work = df.copy()

    for col in FEATURES:

        if col not in work.columns:
            work[col] = 0.0

        work[col] = pd.to_numeric(
            work[col],
            errors="coerce",
        ).fillna(0.0)

    score = np.zeros(len(work))

    # 全国成績
    score += (
        work["全国勝率"] * 0.28
        + work["全国2連率"] * 0.10
        + work["全国3連率"] * 0.06
    )

    # 当地成績
    score += (
        work["当地勝率"] * 0.13
        + work["当地2連率"] * 0.07
    )

    # モーター
    score += (
        work["モーター2連率"] * 0.12
    )

    return score


# =========================================================
# 展示評価
# =========================================================
def _exhibition_score(df):

    work = df.copy()

    for col in [
        "枠",
        "展示進入",
        "平均ST",
        "展示ST",
        "展示タイム",
    ]:

        if col not in work.columns:
            work[col] = 0.0

        work[col] = pd.to_numeric(
            work[col],
            errors="coerce",
        ).fillna(0.0)

    score = np.zeros(len(work))

    # -----------------------------------------------------
    # 展示ST
    # 速いほどプラス
    # -----------------------------------------------------
    exhibition_st = work["展示ST"]

    valid_st = exhibition_st[
        exhibition_st > 0
    ]

    if len(valid_st) > 0:

        mean_st = valid_st.mean()

        score += (
            mean_st - exhibition_st
        ) * 35.0

    # -----------------------------------------------------
    # 平均ST
    # -----------------------------------------------------
    avg_st = work["平均ST"]

    valid_avg = avg_st[
        avg_st > 0
    ]

    if len(valid_avg) > 0:

        mean_avg = valid_avg.mean()

        score += (
            mean_avg - avg_st
        ) * 18.0

    # -----------------------------------------------------
    # 展示タイム
    # 速いほどプラス
    # -----------------------------------------------------
    exhibition_time = work[
        "展示タイム"
    ]

    valid_time = exhibition_time[
        exhibition_time > 0
    ]

    if len(valid_time) > 0:

        mean_time = valid_time.mean()

        score += (
            mean_time - exhibition_time
        ) * -8.0

    # -----------------------------------------------------
    # 展示進入
    # 枠より内側に入ればプラス
    # -----------------------------------------------------
    score += (
        work["枠"]
        - work["展示進入"]
    ) * 1.8

    return score


# =========================================================
# コース評価
# =========================================================
def _course_score(df):

    work = df.copy()

    work["枠"] = pd.to_numeric(
        work["枠"],
        errors="coerce",
    ).fillna(0)

    work["展示進入"] = pd.to_numeric(
        work["展示進入"],
        errors="coerce",
    ).fillna(
        work["枠"]
    )

    score = np.zeros(len(work))

    # 1号艇
    score += np.where(
        work["枠"] == 1,
        2.8,
        0.0,
    )

    # 2号艇
    score += np.where(
        work["枠"] == 2,
        0.8,
        0.0,
    )

    # 3号艇
    score += np.where(
        work["枠"] == 3,
        0.45,
        0.0,
    )

    # 4～6は少し控えめ
    score += np.where(
        work["枠"] >= 4,
        -0.10,
        0.0,
    )

    # 展示進入が内側なら評価
    score += (
        work["枠"]
        - work["展示進入"]
    ) * 0.9

    return score


# =========================================================
# 総合スコア
# =========================================================
def _base_score(df):

    ability = _ability_score(df)

    exhibition = _exhibition_score(df)

    course = _course_score(df)

    # -----------------------------------------------------
    # 能力
    # -----------------------------------------------------
    total = (
        ability * 1.0
        + exhibition * 1.0
        + course * 1.0
    )

    return total


# =========================================================
# 機械学習による1着確率
# =========================================================
def _machine_prob(
    current_df,
    history,
):

    if (
        history is None
        or history.empty
        or "1着" not in history.columns
    ):
        return None

    required = set(
        FEATURES + ["1着"]
    )

    if not required.issubset(
        set(history.columns)
    ):
        return None

    train = history.copy()

    for col in FEATURES:

        train[col] = pd.to_numeric(
            train[col],
            errors="coerce",
        ).fillna(0.0)

    train["1着"] = pd.to_numeric(
        train["1着"],
        errors="coerce",
    ).fillna(0).astype(int)

    # 学習データ不足
    if len(train) < 100:
        return None

    # 1着/非1着の両方が必要
    if train["1着"].nunique() < 2:
        return None

    X = train[FEATURES]
    y = train["1着"]

    X_now = _prepare_features(
        current_df
    )

    try:

        model = RandomForestClassifier(
            n_estimators=400,
            max_depth=8,
            min_samples_leaf=4,
            max_features="sqrt",
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )

        model.fit(X, y)

        probabilities = (
            model.predict_proba(X_now)
        )

        classes = list(
            model.classes_
        )

        if 1 not in classes:
            return None

        index = classes.index(1)

        return probabilities[:, index]

    except Exception:
        return None


# =========================================================
# 確率を正規化
# =========================================================
def _normalize(values):

    values = np.asarray(
        values,
        dtype=float,
    )

    values = np.nan_to_num(
        values,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    values = np.maximum(
        values,
        0.0001,
    )

    total = values.sum()

    if total <= 0:
        return np.ones(
            len(values)
        ) / len(values)

    return values / total


# =========================================================
# 順位別スコア
# =========================================================
def _rank_scores(
    df,
    first_prob,
):

    base = _base_score(df)

    # -----------------------------------------------------
    # 1着
    # -----------------------------------------------------
    first = (
        base * 0.55
        + first_prob * 20.0
    )

    # 1号艇のイン優位
    first += np.where(
        df["枠"].values == 1,
        2.0,
        0.0,
    )

    first_prob_final = _normalize(
        first
    )

    # -----------------------------------------------------
    # 2着
    #
    # 1着になりそうな艇は2着評価を少し下げ、
    # 1着候補の次に来る艇を評価する。
    # -----------------------------------------------------
    second = (
        base * 0.75
        + first_prob_final * 5.0
    )

    second += np.where(
        df["枠"].values == 2,
        0.75,
        0.0,
    )

    second += np.where(
        df["枠"].values == 3,
        0.45,
        0.0,
    )

    second_prob = _normalize(
        second
    )

    # -----------------------------------------------------
    # 3着
    # -----------------------------------------------------
    third = (
        base * 0.60
        + second_prob * 4.0
    )

    third += np.where(
        df["枠"].values <= 3,
        0.30,
        0.0,
    )

    third_prob = _normalize(
        third
    )

    return (
        first_prob_final,
        second_prob,
        third_prob,
    )


# =========================================================
# 3連単組み合わせ評価
# =========================================================
def _combination_score(
    a,
    b,
    c,
    first_prob,
    second_prob,
    third_prob,
    df,
):

    # 基本確率
    probability = (
        first_prob[a] ** 1.45
        * second_prob[b] ** 1.10
        * third_prob[c] ** 0.85
    )

    lane_a = int(
        _num(
            df.iloc[a]["枠"]
        )
    )

    lane_b = int(
        _num(
            df.iloc[b]["枠"]
        )
    )

    lane_c = int(
        _num(
            df.iloc[c]["枠"]
        )
    )

    # -----------------------------------------------------
    # 1着1号艇
    # -----------------------------------------------------
    if lane_a == 1:
        probability *= 1.18

    # -----------------------------------------------------
    # 2着2・3号艇
    # -----------------------------------------------------
    if lane_b in (2, 3):
        probability *= 1.06

    # -----------------------------------------------------
    # 3着は内枠を少し優遇
    # -----------------------------------------------------
    if lane_c in (1, 2, 3):
        probability *= 1.04

    # -----------------------------------------------------
    # 同じような評価の艇を過度に重ねない
    # -----------------------------------------------------
    if (
        lane_a == 1
        and lane_b == 2
        and lane_c == 3
    ):
        probability *= 1.03

    return float(
        probability
    )


# =========================================================
# 穴候補を探す
# =========================================================
def _find_hole(
    combinations,
    main_combo,
    counter_combo,
):

    # 本命・対抗と違う組み合わせを探す
    for combo, score in combinations:

        if combo == main_combo:
            continue

        if combo == counter_combo:
            continue

        # 4～6号艇が1着に入る組み合わせを
        # 穴候補として優先
        if combo[0] >= 3:
            return combo

    # なければ3番人気
    for combo, score in combinations:

        if combo not in (
            main_combo,
            counter_combo,
        ):
            return combo

    return main_combo


# =========================================================
# 表示用3連単
# =========================================================
def _combo_text(
    combo,
    df,
):

    return "-".join(
        str(
            int(
                _num(
                    df.iloc[i]["枠"]
                )
            )
        )
        for i in combo
    )


# =========================================================
# メインAI
# =========================================================
def tri_ai(
    df,
    history=None,
):

    work = df.copy()

    if len(work) != 6:
        raise ValueError(
            "6艇のデータが必要です。"
        )

    # =====================================================
    # MLによる1着確率
    # =====================================================
    ml_prob = _machine_prob(
        work,
        history,
    )

    # =====================================================
    # 基本スコア
    # =====================================================
    base = _base_score(work)

    base_prob = _normalize(
        np.maximum(
            base - base.min() + 0.5,
            0.01,
        )
    )

    # =====================================================
    # ML + ルール
    # =====================================================
    if ml_prob is not None:

        ml_prob = _normalize(
            ml_prob
        )

        first_prob = (
            ml_prob * 0.70
            + base_prob * 0.30
        )

    else:

        first_prob = base_prob

    # =====================================================
    # 順位別確率
    # =====================================================
    (
        first_prob,
        second_prob,
        third_prob,
    ) = _rank_scores(
        work,
        first_prob,
    )

    # =====================================================
    # 全120通りの3連単を評価
    # =====================================================
    combinations = []

    for a, b, c in itertools.permutations(
        range(6),
        3,
    ):

        value = _combination_score(
            a,
            b,
            c,
            first_prob,
            second_prob,
            third_prob,
            work,
        )

        combinations.append(
            (
                (a, b, c),
                value,
            )
        )

    combinations.sort(
        key=lambda x: x[1],
        reverse=True,
    )

    # =====================================================
    # 本命
    # =====================================================
    main_combo = combinations[0][0]

    # =====================================================
    # 対抗
    #
    # 本命と同じ1着を避けすぎず、
    # 近い有力パターンを選ぶ。
    # =====================================================
    counter_combo = None

    for combo, value in combinations[1:]:

        if combo == main_combo:
            continue

        # 完全同一は当然除外
        counter_combo = combo
        break

    if counter_combo is None:
        counter_combo = combinations[1][0]

    # =====================================================
    # 穴
    # =====================================================
    hole_combo = _find_hole(
        combinations,
        main_combo,
        counter_combo,
    )

    # =====================================================
    # 文字列化
    # =====================================================
    result = [
        _combo_text(
            main_combo,
            work,
        ),
        _combo_text(
            counter_combo,
            work,
        ),
        _combo_text(
            hole_combo,
            work,
        ),
    ]

    # =====================================================
    # 1着確率
    # =====================================================
    boat_probs = {}

    for i in range(6):

        lane = int(
            _num(
                work.iloc[i]["枠"]
            )
        )

        boat_probs[lane] = float(
            first_prob[i]
        )

    return (
        result,
        boat_probs,
            )
