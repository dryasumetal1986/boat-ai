import itertools
import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestClassifier


# =========================================================
# 学習に使う項目
# =========================================================

FEATURES = [
    "枠",
    "展示進入",
    "全国勝率",
    "全国2連率",
    "当地勝率",
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
            value = value.replace("%", "")
            value = value.replace(" ", "")
            value = value.replace(",", "")

        return float(value)

    except Exception:
        return default


# =========================================================
# 学習用データを整える
# =========================================================

def prepare_training_data(history):
    if history is None:
        return None

    if not isinstance(history, pd.DataFrame):
        history = pd.DataFrame(history)

    if history.empty:
        return None

    df = history.copy()

    # 必須項目が無ければ作る
    for col in FEATURES:
        if col not in df.columns:
            df[col] = 0

    for col in ["1着", "2着", "3着"]:
        if col not in df.columns:
            df[col] = 0

    # 数値化
    for col in FEATURES:
        df[col] = df[col].apply(_num)

    for col in ["1着", "2着", "3着"]:
        df[col] = df[col].apply(_num)

    # 無効な行を削除
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.fillna(0)

    if len(df) < 30:
        return None

    return df


# =========================================================
# RandomForestモデル作成
# =========================================================

def create_model():
    return RandomForestClassifier(
        n_estimators=250,
        max_depth=12,
        min_samples_leaf=4,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced_subsample",
    )


# =========================================================
# AI学習
# =========================================================

def train_models(history):
    df = prepare_training_data(history)

    if df is None:
        return None

    X = df[FEATURES]

    models = {}

    for place in ["1着", "2着", "3着"]:
        y = df[place].astype(int)

        # 1種類しかない場合は学習不能
        if y.nunique() < 2:
            continue

        model = create_model()
        model.fit(X, y)

        models[place] = model

    if len(models) != 3:
        return None

    return models


# =========================================================
# 確率取得
# =========================================================

def _predict_probability(model, X):
    try:
        probabilities = model.predict_proba(X)

        classes = list(model.classes_)

        if 1 in classes:
            idx = classes.index(1)
            return float(probabilities[:, idx][0])

        return 0.0

    except Exception:
        return 0.0


# =========================================================
# 3連単AI
# =========================================================

def tri_ai(df, history=None):
    """
    過去データからRandomForestを学習して
    3連単120通りをAI予測する。
    """

    work = df.copy()

    # 必要な列を用意
    for col in FEATURES:
        if col not in work.columns:
            work[col] = 0

    for col in FEATURES:
        work[col] = work[col].apply(_num)

    # =====================================================
    # AIモデル学習
    # =====================================================

    models = train_models(history)

    # 学習できなかった場合
    if models is None:
        return fallback_prediction(work)

    # =====================================================
    # 各艇の1着・2着・3着確率
    # =====================================================

    X = work[FEATURES]

    first_prob = []
    second_prob = []
    third_prob = []

    for i in range(len(work)):
        Xi = X.iloc[[i]]

        first_prob.append(
            _predict_probability(models["1着"], Xi)
        )

        second_prob.append(
            _predict_probability(models["2着"], Xi)
        )

        third_prob.append(
            _predict_probability(models["3着"], Xi)
        )

    work["1着AI"] = first_prob
    work["2着AI"] = second_prob
    work["3着AI"] = third_prob

    # =====================================================
    # 120通り作成
    # =====================================================

    combinations = list(
        itertools.permutations(work["枠"].astype(int).tolist(), 3)
    )

    results = []

    for combo in combinations:

        first, second, third = combo

        r1 = work[work["枠"] == first].iloc[0]
        r2 = work[work["枠"] == second].iloc[0]
        r3 = work[work["枠"] == third].iloc[0]

        p1 = max(float(r1["1着AI"]), 0.000001)
        p2 = max(float(r2["2着AI"]), 0.000001)
        p3 = max(float(r3["3着AI"]), 0.000001)

        # 3連単確率
        probability = p1 * p2 * p3

        results.append(
            {
                "3連単": f"{first}-{second}-{third}",
                "1着": first,
                "2着": second,
                "3着": third,
                "AI確率_raw": probability,
                "1着AI": p1,
                "2着AI": p2,
                "3着AI": p3,
            }
        )

    result = pd.DataFrame(results)

    # =====================================================
    # 120通りを100%に正規化
    # =====================================================

    total = result["AI確率_raw"].sum()

    if total > 0:
        result["AI確率"] = (
            result["AI確率_raw"] / total * 100
        )
    else:
        result["AI確率"] = 0

    # =====================================================
    # 信頼度
    #
    # ※ 本当の的中確率ではなく、
    #    AI確率を見やすくした指標
    # =====================================================

    max_prob = result["AI確率"].max()

    if max_prob > 0:
        result["信頼度"] = (
            result["AI確率"] / max_prob * 100
        )
    else:
        result["信頼度"] = 0

    result = result.sort_values(
        "AI確率",
        ascending=False
    ).reset_index(drop=True)

    result["AI順位"] = (
        result.index + 1
    )

    # 表示用に丸める
    result["AI確率"] = result["AI確率"].round(2)
    result["信頼度"] = result["信頼度"].round(1)

    result["1着AI"] = (
        result["1着AI"] * 100
    ).round(2)

    result["2着AI"] = (
        result["2着AI"] * 100
    ).round(2)

    result["3着AI"] = (
        result["3着AI"] * 100
    ).round(2)

    return result[
        [
            "AI順位",
            "3連単",
            "AI確率",
            "信頼度",
            "1着AI",
            "2着AI",
            "3着AI",
        ]
    ]


# =========================================================
# 学習できない場合の予備予測
# =========================================================

def fallback_prediction(df):

    scores = []

    for _, r in df.iterrows():

        score = (
            _num(r.get("全国勝率")) * 10
            + _num(r.get("全国2連率")) * 0.25
            + _num(r.get("当地勝率")) * 5
            + _num(r.get("モーター2連率")) * 0.12
        )

        lane = int(_num(r.get("枠")))

        lane_bonus = {
            1: 20,
            2: 8,
            3: 6,
            4: 7,
            5: 2,
            6: 0,
        }

        score += lane_bonus.get(lane, 0)

        exhibition_time = _num(
            r.get("展示タイム")
        )

        if exhibition_time > 0:
            score += max(
                0,
                (6.90 - exhibition_time) * 10
            )

        scores.append(score)

    df = df.copy()
    df["_score"] = scores

    # 簡易的に順位から確率を作る
    df = df.sort_values(
        "_score",
        ascending=False
    ).reset_index(drop=True)

    total = df["_score"].sum()

    if total <= 0:
        total = 1

    # 3連単
    results = []

    for combo in itertools.permutations(
        df["枠"].astype(int).tolist(),
        3
    ):

        r1 = df[df["枠"] == combo[0]].iloc[0]
        r2 = df[df["枠"] == combo[1]].iloc[0]
        r3 = df[df["枠"] == combo[2]].iloc[0]

        s1 = max(r1["_score"], 0.01)
        s2 = max(r2["_score"], 0.01)
        s3 = max(r3["_score"], 0.01)

        p = s1 * s2 * s3

        results.append(
            {
                "3連単": f"{combo[0]}-{combo[1]}-{combo[2]}",
                "AI確率_raw": p,
            }
        )

    result = pd.DataFrame(results)

    result["AI確率"] = (
        result["AI確率_raw"]
        / result["AI確率_raw"].sum()
        * 100
    )

    result["信頼度"] = (
        result["AI確率"]
        / result["AI確率"].max()
        * 100
    )

    result = result.sort_values(
        "AI確率",
        ascending=False
    ).reset_index(drop=True)

    result["AI順位"] = result.index + 1

    result["AI確率"] = result["AI確率"].round(2)
    result["信頼度"] = result["信頼度"].round(1)

    result["1着AI"] = 0.0
    result["2着AI"] = 0.0
    result["3着AI"] = 0.0

    return result[
        [
            "AI順位",
            "3連単",
            "AI確率",
            "信頼度",
            "1着AI",
            "2着AI",
            "3着AI",
        ]
    ]


# =========================================================
# 旧コード互換用 score
# =========================================================

def score(r):

    value = (
        _num(r.get("全国勝率")) * 10
        + _num(r.get("全国2連率")) * 0.25
        + _num(r.get("当地勝率")) * 5
        + _num(r.get("モーター2連率")) * 0.12
    )

    lane = int(_num(r.get("枠")))

    lane_bonus = {
        1: 20,
        2: 8,
        3: 6,
        4: 7,
        5: 2,
        6: 0,
    }

    value += lane_bonus.get(lane, 0)

    exhibition_time = _num(
        r.get("展示タイム")
    )

    if exhibition_time > 0:
        value += max(
            0,
            (6.90 - exhibition_time) * 10
        )

    exhibition_st = _num(
        r.get("展示ST")
    )

    if exhibition_st > 0:
        value += max(
            0,
            (0.15 - exhibition_st) * 20
        )

    return value
