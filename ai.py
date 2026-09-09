import numpy as np
import pandas as pd

from itertools import permutations
from sklearn.ensemble import RandomForestClassifier


# ============================================================
# AI特徴量
# ============================================================

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


# ============================================================
# 数値変換
# ============================================================

def to_float(value, default=0.0):

    try:
        if value is None:
            return default

        if pd.isna(value):
            return default

        return float(value)

    except Exception:
        return default


# ============================================================
# 旧AIスコア
# ============================================================

def score(r):

    s = 0.0

    s += to_float(r.get("全国勝率")) * 10
    s += to_float(r.get("全国2連率")) * 0.25
    s += to_float(r.get("当地勝率")) * 5
    s += to_float(r.get("モーター2連率")) * 0.12

    st = to_float(r.get("平均ST"))

    if 0 < st <= 0.12:
        s += 12
    elif 0 < st <= 0.15:
        s += 8
    elif 0 < st <= 0.18:
        s += 4
    elif st >= 0.22:
        s -= 4

    lane = int(
        to_float(r.get("枠"), 1)
    )

    lane_bonus = {
        1: 20,
        2: 8,
        3: 6,
        4: 7,
        5: 2,
        6: 0,
    }

    s += lane_bonus.get(lane, 0)

    ex = to_float(
        r.get("展示タイム")
    )

    if 0 < ex <= 6.70:
        s += 6
    elif 0 < ex <= 6.75:
        s += 4
    elif 0 < ex <= 6.80:
        s += 2
    elif ex >= 6.90:
        s -= 2

    exhibition_st = to_float(
        r.get("展示ST")
    )

    if 0 < exhibition_st <= 0.08:
        s += 10
    elif 0 < exhibition_st <= 0.10:
        s += 8
    elif 0 < exhibition_st <= 0.12:
        s += 6
    elif 0 < exhibition_st <= 0.15:
        s += 3
    elif exhibition_st >= 0.20:
        s -= 3

    exhibition_course = r.get(
        "展示進入",
        lane,
    )

    try:
        exhibition_course = int(
            exhibition_course
        )
    except Exception:
        exhibition_course = lane

    if exhibition_course < lane:
        s += 4

    elif exhibition_course > lane:
        s -= 2

    return round(s, 2)


# ============================================================
# 機械学習モデル
# ============================================================

def _make_model():

    return RandomForestClassifier(
        n_estimators=250,
        max_depth=12,
        min_samples_leaf=4,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced_subsample",
    )


# ============================================================
# 学習データ準備
# ============================================================

def prepare_training_data(history):

    if history is None:
        return None

    if len(history) == 0:
        return None

    df = pd.DataFrame(history).copy()

    required = FEATURES + [
        "1着",
        "2着",
        "3着",
    ]

    for column in required:

        if column not in df.columns:
            return None

    for column in FEATURES + [
        "1着",
        "2着",
        "3着",
    ]:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        ).fillna(0)

    return df


# ============================================================
# AI学習
# ============================================================

def train_ai(history):

    df = prepare_training_data(
        history
    )

    if df is None:
        return None

    # あまりに少ないデータでは学習しない
    if len(df) < 300:
        return None

    X = df[FEATURES]

    models = {}

    for place in [1, 2, 3]:

        target = df[f"{place}着"]

        # 0/1の両方が必要
        if target.nunique() < 2:
            continue

        model = _make_model()

        model.fit(
            X,
            target,
        )

        models[place] = model

    if len(models) != 3:
        return None

    return models


# ============================================================
# 各艇の着順確率
# ============================================================

def predict_boats(
    df,
    models,
):

    result = df.copy()

    X = result[FEATURES].copy()

    for column in FEATURES:

        X[column] = pd.to_numeric(
            X[column],
            errors="coerce",
        ).fillna(0)

    for place in [1, 2, 3]:

        model = models[place]

        probabilities = model.predict_proba(
            X
        )

        classes = list(
            model.classes_
        )

        if 1 in classes:

            index = classes.index(1)

            result[
                f"{place}着確率"
            ] = probabilities[:, index]

        else:

            result[
                f"{place}着確率"
            ] = 0.0

    return result


# ============================================================
# 3連単AI
# ============================================================

def tri_ai(
    df,
    history=None,
):

    df = df.copy()

    if df.empty:
        return pd.DataFrame()

    # --------------------------------------------------------
    # 機械学習
    # --------------------------------------------------------

    models = train_ai(
        history
    )

    if models is not None:

        df = predict_boats(
            df,
            models,
        )

        # MLの1着確率をAIスコアとして表示
        df["学習AI"] = (
            df["1着確率"] * 100
        ).round(2)

    else:

        # 学習できない場合は旧スコア
        df["学習AI"] = df.apply(
            score,
            axis=1,
        )

        for place in [1, 2, 3]:

            df[
                f"{place}着確率"
            ] = 0.0

    # --------------------------------------------------------
    # 枠 → 行
    # --------------------------------------------------------

    rows = {}

    for _, row in df.iterrows():

        lane = int(
            row["枠"]
        )

        rows[lane] = row

    lanes = sorted(
        rows.keys()
    )

    # --------------------------------------------------------
    # 120通り
    # --------------------------------------------------------

    output = []

    for a, b, c in permutations(
        lanes,
        3,
    ):

        ra = rows[a]
        rb = rows[b]
        rc = rows[c]

        # --------------------------------------------
        # 機械学習確率
        # --------------------------------------------

        if models is not None:

            p1 = float(
                ra["1着確率"]
            )

            p2 = float(
                rb["2着確率"]
            )

            p3 = float(
                rc["3着確率"]
            )

            # 3連単確率
            probability = (
                p1
                * p2
                * p3
            )

        else:

            # ----------------------------------------
            # fallback
            # ----------------------------------------

            s1 = max(
                float(ra["学習AI"]),
                0.1,
            )

            s2 = max(
                float(rb["学習AI"]),
                0.1,
            )

            s3 = max(
                float(rc["学習AI"]),
                0.1,
            )

            probability = (
                s1
                * s2
                * s3
            )

        # --------------------------------------------
        # 1号艇逃げ
        # --------------------------------------------

        if a == 1:
            probability *= 1.12

        # --------------------------------------------
        # 展示進入
        # --------------------------------------------

        try:

            course_a = int(
                ra.get(
                    "展示進入",
                    a,
                )
            )

            if course_a < a:
                probability *= 1.05

            elif course_a > a:
                probability *= 0.95

        except Exception:
            pass

        # --------------------------------------------
        # 3・4号艇攻め
        # --------------------------------------------

        if a in [3, 4]:
            probability *= 1.02

        # --------------------------------------------
        # 同一艇防止
        # permutationsで保証済み
        # --------------------------------------------

        output.append({

            "3連単":
                f"{a}-{b}-{c}",

            "1着AI":
                round(
                    float(
                        ra.get(
                            "1着確率",
                            0,
                        )
                    ) * 100,
                    2,
                ),

            "2着AI":
                round(
                    float(
                        rb.get(
                            "2着確率",
                            0,
                        )
                    ) * 100,
                    2,
                ),

            "3着AI":
                round(
                    float(
                        rc.get(
                            "3着確率",
                            0,
                        )
                    ) * 100,
                    2,
                ),

            "AI確率":
                probability,

        })

    result = pd.DataFrame(
        output
    )

    if result.empty:
        return result

    # ========================================================
    # 確率を120通り合計100%に正規化
    # ========================================================

    total = result[
        "AI確率"
    ].sum()

    if total > 0:

        result[
            "AI確率"
        ] = (
            result["AI確率"]
            / total
            * 100
        )

    else:

        result[
            "AI確率"
        ] = 0.0

    result[
        "AI確率"
    ] = result[
        "AI確率"
    ].round(2)

    # ========================================================
    # AIスコア
    # ========================================================

    result[
        "AIスコア"
    ] = (
        result["AI確率"] * 10
    ).round(2)

    # ========================================================
    # 信頼度
    #
    # 旧方式のmin-maxではなく、
    # 上位予想の確率を基準にする
    # ========================================================

    max_probability = result[
        "AI確率"
    ].max()

    if max_probability > 0:

        result[
            "信頼度"
        ] = (
            result["AI確率"]
            / max_probability
            * 100
        ).round(1)

    else:

        result[
            "信頼度"
        ] = 0.0

    # ========================================================
    # 順位
    # ========================================================

    result = result.sort_values(
        "AI確率",
        ascending=False,
    ).reset_index(
        drop=True
    )

    result.insert(
        0,
        "AI順位",
        range(
            1,
            len(result) + 1,
        ),
    )

    return result
