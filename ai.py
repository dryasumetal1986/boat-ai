import itertools

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier


# =========================
# AI特徴量
# =========================
FEATURES = [
    "枠",
    "展示進入",
    "全国勝率",
    "全国2連率",
    "当地勝率",
    "当地2連率",
    "モーター2連率",
    "平均ST",
    "展示ST",
    "展示タイム",
    "場",
]


# =========================
# 数値変換
# =========================
def _num(value, default=0.0):

    if value is None:
        return default

    try:
        text = str(value).strip()

        if text in ("", "-", "--", "None", "null"):
            return default

        text = text.replace("%", "")
        text = text.replace("秒", "")

        return float(text)

    except Exception:
        return default


# =========================
# 現在レースのスコア
# =========================
def score(df):

    work = df.copy()

    for col in FEATURES:

        if col not in work.columns:
            work[col] = 0.0

        work[col] = pd.to_numeric(
            work[col],
            errors="coerce",
        ).fillna(0.0)

    # =========================
    # 基本スコア
    # =========================

    s = (
        work["全国勝率"] * 0.24
        + work["全国2連率"] * 0.13
        + work["当地勝率"] * 0.10
        + work["当地2連率"] * 0.08
        + work["モーター2連率"] * 0.12
    )

    # ST
    s += (
        (0.20 - work["平均ST"])
        * 8.0
    )

    s += (
        (0.20 - work["展示ST"])
        * 8.0
    )

    # 展示タイム
    s += (
        (6.90 - work["展示タイム"])
        * 2.0
    )

    # 展示進入
    s += (
        (work["枠"] - work["展示進入"])
        * 0.8
    )

    # 1号艇の基本優位
    s += np.where(
        work["枠"] == 1,
        2.0,
        0.0,
    )

    return s


# =========================
# 特徴量作成
# =========================
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


# =========================
# 機械学習確率
# =========================
def _machine_prob(
    current_df,
    history,
):

    # 学習データがない場合
    if (
        history is None
        or history.empty
        or "1着" not in history.columns
    ):
        return None

    required = set(FEATURES + ["1着"])

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

    # 正例・負例が両方必要
    if train["1着"].nunique() < 2:
        return None

    X = train[FEATURES]
    y = train["1着"]

    X_now = _prepare_features(
        current_df
    )

    try:

        model = RandomForestClassifier(
            n_estimators=300,
            max_depth=7,
            min_samples_leaf=3,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )

        model.fit(X, y)

        probs = model.predict_proba(
            X_now
        )

        classes = list(
            model.classes_
        )

        if 1 not in classes:
            return None

        idx = classes.index(1)

        return probs[:, idx]

    except Exception:
        return None


# =========================
# AI予想
# =========================
def tri_ai(
    df,
    history=None,
):
    """
    3連単の
    本命・対抗・穴を返す。
    """

    work = df.copy()

    if len(work) != 6:
        raise ValueError(
            "6艇のデータが必要です。"
        )

    # =========================
    # ヒューリスティックスコア
    # =========================
    heuristic = score(work)

    heuristic = (
        heuristic
        - heuristic.min()
        + 0.01
    )

    heuristic_prob = (
        heuristic
        / heuristic.sum()
    )

    # =========================
    # ML確率
    # =========================
    machine_prob = _machine_prob(
        work,
        history,
    )

    if machine_prob is None:

        final_prob = np.asarray(
            heuristic_prob,
            dtype=float,
        )

    else:

        machine_prob = np.asarray(
            machine_prob,
            dtype=float,
        )

        if (
            len(machine_prob)
            != len(work)
        ):
            final_prob = np.asarray(
                heuristic_prob,
                dtype=float,
            )
        else:

            # ML 70%
            # ヒューリスティック 30%
            final_prob = (
                machine_prob * 0.70
                + heuristic_prob * 0.30
            )

    # =========================
    # 1号艇の基本優位
    # =========================
    for i in range(len(work)):

        lane = _num(
            work.iloc[i]["枠"]
        )

        if lane == 1:
            final_prob[i] *= 1.08

    # 正規化
    total = final_prob.sum()

    if total <= 0:
        final_prob = np.ones(6) / 6
    else:
        final_prob = (
            final_prob / total
        )

    # =========================
    # 3連単全組み合わせ
    # =========================
    combinations = []

    for combo in itertools.permutations(
        range(6),
        3,
    ):

        a, b, c = combo

        # 1着確率を強く反映
        p = (
            final_prob[a] ** 1.35
            * final_prob[b] ** 1.05
            * final_prob[c] ** 0.85
        )

        # 1号艇1着の基本優位
        if (
            _num(work.iloc[a]["枠"])
            == 1
        ):
            p *= 1.15

        combinations.append(
            (
                combo,
                float(p),
            )
        )

    combinations.sort(
        key=lambda x: x[1],
        reverse=True,
    )

    # =========================
    # 上位3つ
    # =========================
    predictions = []

    used = set()

    for combo, probability in combinations:

        text = "-".join(
            str(
                int(
                    _num(
                        work.iloc[i]["枠"]
                    )
                )
            )
            for i in combo
        )

        # 同じ予想を防止
        if text in used:
            continue

        used.add(text)

        predictions.append(text)

        if len(predictions) == 3:
            break

    while len(predictions) < 3:

        predictions.append(
            "予想なし"
        )

    # =========================
    # 確率辞書
    # =========================
    boat_probs = {}

    for i in range(len(work)):

        lane = int(
            _num(
                work.iloc[i]["枠"]
            )
        )

        boat_probs[lane] = float(
            final_prob[i]
        )

    return (
        predictions,
        boat_probs,
    )
