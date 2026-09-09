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
    "当地勝率",
    "当地2連率",
    "モーター2連率",
    "平均ST",
    "展示ST",
    "展示タイム",
    "場",
]


# =========================================================
# 数値化
# =========================================================

def _num(value, default=0.0):
    try:
        if value is None:
            return default

        if isinstance(value, str):
            value = (
                value
                .replace("%", "")
                .replace("秒", "")
                .strip()
            )

        return float(value)
    except Exception:
        return default


# =========================================================
# 基本スコア
# =========================================================

def score(df):
    """
    6艇の総合スコア。
    """

    x = df.copy()

    # 欠損を0にする
    for col in FEATURES:
        if col not in x.columns:
            x[col] = 0.0

        x[col] = pd.to_numeric(
            x[col],
            errors="coerce",
        ).fillna(0.0)

    # -----------------------------------------------------
    # 各項目
    # -----------------------------------------------------

    x["AIスコア"] = 0.0

    # 全国勝率
    x["AIスコア"] += (
        x["全国勝率"] * 10.0
    )

    # 全国2連率
    x["AIスコア"] += (
        x["全国2連率"] * 0.35
    )

    # 当地勝率
    x["AIスコア"] += (
        x["当地勝率"] * 5.0
    )

    # 当地2連率
    x["AIスコア"] += (
        x["当地2連率"] * 0.20
    )

    # モーター
    x["AIスコア"] += (
        x["モーター2連率"] * 0.25
    )

    # 枠
    lane_bonus = {
        1: 5.0,
        2: 2.0,
        3: 1.0,
        4: 0.0,
        5: -0.5,
        6: -1.0,
    }

    x["AIスコア"] += (
        x["枠"].map(lane_bonus).fillna(0)
    )

    # 展示進入
    x["AIスコア"] += (
        (7 - x["展示進入"]) * 1.0
    )

    # 平均ST
    x["AIスコア"] += (
        (0.25 - x["平均ST"]) * 8.0
    )

    # 展示ST
    x["AIスコア"] += (
        (0.25 - x["展示ST"]) * 10.0
    )

    # 展示タイム
    valid_time = x["展示タイム"].replace(0, np.nan)

    if valid_time.notna().any():
        best_time = valid_time.min()

        x["AIスコア"] += (
            (best_time - valid_time.fillna(best_time))
            * 15.0
        )

    return x


# =========================================================
# AI特徴量
# =========================================================

def _prepare_features(df):
    x = df.copy()

    for col in FEATURES:
        if col not in x.columns:
            x[col] = 0.0

        x[col] = pd.to_numeric(
            x[col],
            errors="coerce",
        ).fillna(0.0)

    return x[FEATURES]


# =========================================================
# 機械学習
# =========================================================

def _machine_prob(df, history):
    """
    過去データが十分ならRandomForestで1着確率を作る。
    """
    if history is None:
        return None

    if not isinstance(history, pd.DataFrame):
        return None

    if history.empty:
        return None

    if "1着" not in history.columns:
        return None

    # 学習対象
    train = history.copy()

    # 必須特徴量
    for col in FEATURES:
        if col not in train.columns:
            train[col] = 0.0

        train[col] = pd.to_numeric(
            train[col],
            errors="coerce",
        ).fillna(0.0)

    train["1着"] = pd.to_numeric(
        train["1着"],
        errors="coerce",
    ).fillna(0).astype(int)

    # 0/1両方がないと学習できない
    if train["1着"].nunique() < 2:
        return None

    # 最低限のデータ量
    if len(train) < 100:
        return None

    X = train[FEATURES]
    y = train["1着"]

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=7,
        min_samples_leaf=3,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1,
    )

    try:
        model.fit(X, y)
    except Exception:
        return None

    current_x = _prepare_features(df)

    try:
        probabilities = model.predict_proba(current_x)

        classes = list(model.classes_)

        if 1 in classes:
            idx = classes.index(1)
            p = probabilities[:, idx]
        else:
            return None

        p = np.asarray(p, dtype=float)

        if np.all(p <= 0):
            return None

        # 1着確率として合計100%
        total = p.sum()

        if total <= 0:
            return None

        return p / total

    except Exception:
        return None


# =========================================================
# 予測
# =========================================================

def tri_ai(df, history=None):
    """
    3連単予想を作る。

    戻り値:
      result
      boat_probs
    """

    if not isinstance(df, pd.DataFrame):
        raise ValueError("dfがDataFrameではありません。")

    if len(df) != 6:
        raise ValueError(
            f"AIに渡された選手数が6人ではありません: {len(df)}"
        )

    # -----------------------------------------------------
    # 基本スコア
    # -----------------------------------------------------

    scored = score(df)

    heuristic = scored["AIスコア"].to_numpy(
        dtype=float
    )

    # -----------------------------------------------------
    # 機械学習確率
    # -----------------------------------------------------

    ml_prob = _machine_prob(
        df,
        history,
    )

    if ml_prob is not None:

        # ヒューリスティックも確率化
        h = heuristic - heuristic.max()

        exp_h = np.exp(
            np.clip(h, -20, 20)
        )

        h_prob = exp_h / exp_h.sum()

        # ML 70% + ルール30%
        boat_probs = (
            ml_prob * 0.70
            + h_prob * 0.30
        )

    else:

        h = heuristic - heuristic.max()

        exp_h = np.exp(
            np.clip(h, -20, 20)
        )

        boat_probs = exp_h / exp_h.sum()

    # -----------------------------------------------------
    # 100%に正規化
    # -----------------------------------------------------

    boat_probs = np.asarray(
        boat_probs,
        dtype=float,
    )

    boat_probs = boat_probs / boat_probs.sum()

    # -----------------------------------------------------
    # 3連単全組み合わせ
    # -----------------------------------------------------

    combos = []

    lanes = [1, 2, 3, 4, 5, 6]

    for a, b, c in itertools.permutations(lanes, 3):

        p = (
            boat_probs[a - 1]
            * boat_probs[b - 1]
            * boat_probs[c - 1]
        )

        # 進入・枠の補正
        if a == 1:
            p *= 1.15

        if b == 1:
            p *= 0.90

        combos.append(
            {
                "買い目": f"{a}-{b}-{c}",
                "確率": float(p),
            }
        )

    result = pd.DataFrame(combos)

    # -----------------------------------------------------
    # 確率を100%基準にする
    # -----------------------------------------------------

    total = result["確率"].sum()

    if total > 0:
        result["確率"] = (
            result["確率"] / total * 100
        )

    result = result.sort_values(
        "確率",
        ascending=False,
    ).reset_index(drop=True)

    # -----------------------------------------------------
    # 上位だけに順位を付ける
    # -----------------------------------------------------

    result["順位"] = (
        result.index + 1
    )

    # -----------------------------------------------------
    # 選手ごとの1着確率
    # -----------------------------------------------------

    boat_probs_df = pd.DataFrame(
        {
            "枠": lanes,
            "選手名": df["選手名"].tolist(),
            "1着確率": (
                boat_probs * 100
            ),
            "AIスコア": (
                scored["AIスコア"].to_numpy()
            ),
        }
    )

    return result, boat_probs_df
