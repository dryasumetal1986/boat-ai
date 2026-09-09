import itertools

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier


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


def _num(x, default=0.0):
    try:
        if x is None:
            return default

        return float(
            str(x)
            .replace("%", "")
            .replace(",", "")
            .strip()
        )
    except:
        return default


def _model():
    return RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced_subsample",
    )


def _prepare(history):

    if history is None:
        return None

    df = (
        history.copy()
        if isinstance(history, pd.DataFrame)
        else pd.DataFrame(history)
    )

    if df.empty:
        return None

    for c in FEATURES + ["1着", "2着", "3着"]:
        if c not in df.columns:
            df[c] = 0

    for c in FEATURES:
        df[c] = df[c].apply(_num)

    for c in ["1着", "2着", "3着"]:
        df[c] = df[c].apply(_num)

    df = df.replace(
        [np.inf, -np.inf],
        np.nan
    ).fillna(0)

    if len(df) < 30:
        return None

    return df


def _train(history):

    df = _prepare(history)

    if df is None:
        return None

    X = df[FEATURES]
    models = {}

    for target in ["1着", "2着", "3着"]:

        y = df[target].astype(int)

        if y.nunique() < 2:
            return None

        m = _model()
        m.fit(X, y)
        models[target] = m

    return models


def _prob(model, row):

    try:
        p = model.predict_proba(
            row[FEATURES]
        )[0]

        classes = list(
            model.classes_
        )

        if 1 in classes:
            return float(
                p[classes.index(1)]
            )

    except:
        pass

    return 0.0


# =========================================================
# フォールバック
# =========================================================

def _fallback(df):

    work = df.copy()

    scores = []

    for _, r in work.iterrows():

        s = (
            _num(r.get("全国勝率")) * 10
            + _num(r.get("全国2連率")) * 0.25
            + _num(r.get("当地勝率")) * 5
            + _num(r.get("モーター2連率")) * 0.12
        )

        lane = int(
            _num(r.get("枠"))
        )

        s += {
            1: 20,
            2: 8,
            3: 6,
            4: 7,
            5: 2,
            6: 0,
        }.get(lane, 0)

        ex = _num(
            r.get("展示タイム")
        )

        if ex > 0:
            s += max(
                0,
                (6.90 - ex) * 10
            )

        st = _num(
            r.get("展示ST")
        )

        if st > 0:
            s += max(
                0,
                (0.15 - st) * 20
            )

        scores.append(
            max(s, 0.01)
        )

    work["_score"] = scores

    lane_score = dict(
        zip(
            work["枠"].astype(int),
            work["_score"]
        )
    )

    results = []

    for combo in itertools.permutations(
        work["枠"].astype(int),
        3
    ):

        p = (
            lane_score[combo[0]]
            * lane_score[combo[1]]
            * lane_score[combo[2]]
        )

        results.append({
            "3連単":
                f"{combo[0]}-{combo[1]}-{combo[2]}",
            "raw": p,
        })

    result = pd.DataFrame(results)

    total = result["raw"].sum()

    result["AI確率"] = (
        result["raw"] / total * 100
    )

    result = result.sort_values(
        "AI確率",
        ascending=False
    ).reset_index(drop=True)

    result["AI順位"] = (
        result.index + 1
    )

    result["信頼度"] = (
        result["AI確率"]
        / result["AI確率"].max()
        * 100
    )

    # 枠別確率
    total_score = sum(scores)

    boat_probs = {}

    for lane, s in lane_score.items():
        boat_probs[lane] = (
            s / total_score
        )

    result["AI確率"] = result[
        "AI確率"
    ].round(2)

    result["信頼度"] = result[
        "信頼度"
    ].round(1)

    result["1着AI"] = 0.0
    result["2着AI"] = 0.0
    result["3着AI"] = 0.0

    return (
        result[
            [
                "AI順位",
                "3連単",
                "AI確率",
                "信頼度",
                "1着AI",
                "2着AI",
                "3着AI",
            ]
        ],
        boat_probs
    )


# =========================================================
# メインAI
# =========================================================

def tri_ai(df, history=None):

    work = df.copy()

    for c in FEATURES:
        if c not in work.columns:
            work[c] = 0

        work[c] = work[c].apply(_num)

    models = _train(history)

    if models is None:
        return _fallback(work)

    first = []
    second = []
    third = []

    for _, row in work.iterrows():

        first.append(
            _prob(
                models["1着"],
                row.to_frame().T
            )
        )

        second.append(
            _prob(
                models["2着"],
                row.to_frame().T
            )
        )

        third.append(
            _prob(
                models["3着"],
                row.to_frame().T
            )
        )

    work["1着AI"] = first
    work["2着AI"] = second
    work["3着AI"] = third

    pmap = {
        int(r["枠"]): (
            max(r["1着AI"], 0.000001)
            * max(r["2着AI"], 0.000001)
            * max(r["3着AI"], 0.000001)
        )
        for _, r in work.iterrows()
    }

    results = []

    for combo in itertools.permutations(
        work["枠"].astype(int),
        3
    ):

        r1 = work[
            work["枠"] == combo[0]
        ].iloc[0]

        r2 = work[
            work["枠"] == combo[1]
        ].iloc[0]

        r3 = work[
            work["枠"] == combo[2]
        ].iloc[0]

        p = (
            max(r1["1着AI"], 0.000001)
            * max(r2["2着AI"], 0.000001)
            * max(r3["3着AI"], 0.000001)
        )

        results.append({
            "3連単":
                f"{combo[0]}-{combo[1]}-{combo[2]}",
            "raw": p,
            "1着AI": r1["1着AI"],
            "2着AI": r2["2着AI"],
            "3着AI": r3["3着AI"],
        })

    result = pd.DataFrame(results)

    total = result["raw"].sum()

    result["AI確率"] = (
        result["raw"] / total * 100
    )

    result = result.sort_values(
        "AI確率",
        ascending=False
    ).reset_index(drop=True)

    result["AI順位"] = (
        result.index + 1
    )

    result["信頼度"] = (
        result["AI確率"]
        / result["AI確率"].max()
        * 100
    )

    # 枠別AI確率
    boat_probs = {}

    for _, r in work.iterrows():
        boat_probs[int(r["枠"])] = float(
            r["1着AI"]
        )

    total_boat = sum(
        boat_probs.values()
    )

    if total_boat > 0:
        boat_probs = {
            k: v / total_boat
            for k, v in boat_probs.items()
        }

    result["AI確率"] = result[
        "AI確率"
    ].round(2)

    result["信頼度"] = result[
        "信頼度"
    ].round(1)

    result["1着AI"] = (
        result["1着AI"] * 100
    ).round(2)

    result["2着AI"] = (
        result["2着AI"] * 100
    ).round(2)

    result["3着AI"] = (
        result["3着AI"] * 100
    ).round(2)

    return (
        result[
            [
                "AI順位",
                "3連単",
                "AI確率",
                "信頼度",
                "1着AI",
                "2着AI",
                "3着AI",
            ]
        ],
        boat_probs
    )


# =========================================================
# 選手スコア
# =========================================================

def score(r):

    value = (
        _num(r.get("全国勝率")) * 10
        + _num(r.get("全国2連率")) * 0.25
        + _num(r.get("当地勝率")) * 5
        + _num(r.get("モーター2連率")) * 0.12
    )

    lane = int(
        _num(r.get("枠"))
    )

    value += {
        1: 20,
        2: 8,
        3: 6,
        4: 7,
        5: 2,
        6: 0,
    }.get(lane, 0)

    ex = _num(
        r.get("展示タイム")
    )

    if ex > 0:
        value += max(
            0,
            (6.90 - ex) * 10
        )

    st = _num(
        r.get("展示ST")
    )

    if st > 0:
        value += max(
            0,
            (0.15 - st) * 20
        )

    return round(value, 2)
