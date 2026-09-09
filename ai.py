import math
from itertools import permutations

import numpy as np
import pandas as pd


# =========================================================
# 安全なfloat変換
# =========================================================

def safe_float(
    value,
    default=0.0
):

    try:

        if pd.isna(value):
            return default

        return float(value)

    except (
        TypeError,
        ValueError
    ):

        return default


# =========================================================
# 選手AIスコア
# =========================================================

def score(r):

    s = 0.0


    # =====================================================
    # 全国成績
    # =====================================================

    s += (
        safe_float(
            r.get("全国勝率")
        )
        * 10.0
    )

    s += (
        safe_float(
            r.get("全国2連率")
        )
        * 0.25
    )


    # =====================================================
    # 当地成績
    # =====================================================

    s += (
        safe_float(
            r.get("当地勝率")
        )
        * 5.0
    )


    # =====================================================
    # モーター
    # =====================================================

    s += (
        safe_float(
            r.get("モーター2連率")
        )
        * 0.12
    )


    # =====================================================
    # ST
    # =====================================================

    st_value = safe_float(
        r.get("平均ST")
    )

    if 0 < st_value <= 0.12:

        s += 12

    elif 0 < st_value <= 0.15:

        s += 8

    elif 0 < st_value <= 0.18:

        s += 4

    elif st_value >= 0.22:

        s -= 4


    # =====================================================
    # 枠番
    # =====================================================

    lane = int(
        safe_float(
            r.get("枠")
        )
    )

    lane_bonus = {

        1: 20.0,
        2: 8.0,
        3: 6.0,
        4: 7.0,
        5: 2.0,
        6: 0.0,

    }

    s += lane_bonus.get(
        lane,
        0.0
    )


    # =====================================================
    # 展示タイム
    # =====================================================

    exhibition = safe_float(
        r.get("展示タイム")
    )

    if 0 < exhibition <= 6.70:

        s += 6

    elif 0 < exhibition <= 6.75:

        s += 4

    elif 0 < exhibition <= 6.80:

        s += 2

    elif exhibition >= 6.90:

        s -= 2


    return round(
        s,
        2
    )


# =========================================================
# Softmax
# =========================================================

def softmax(values):

    array = np.asarray(
        values,
        dtype=float
    )

    if array.size == 0:

        return np.array(
            [],
            dtype=float
        )


    # NaN / inf対策

    array = np.nan_to_num(
        array,
        nan=0.0,
        posinf=100.0,
        neginf=-100.0
    )


    # オーバーフロー対策

    array = np.clip(
        array,
        -100,
        100
    )


    shifted = (
        array
        - np.max(array)
    )

    exp_values = np.exp(
        shifted
    )

    total = np.sum(
        exp_values
    )

    if total <= 0:

        return np.ones(
            array.size
        ) / array.size


    return (
        exp_values
        / total
    )


# =========================================================
# 過去成績補正
# =========================================================

def history_bonus(
    history,
    player_number,
    column,
    multiplier
):

    if history is None:

        return 0.0


    if history.empty:

        return 0.0


    if "選手番号" not in history.columns:

        return 0.0


    h = history[
        history["選手番号"].astype(str)
        == str(player_number)
    ]


    if h.empty:

        return 0.0


    if column not in h.columns:

        return 0.0


    rate = pd.to_numeric(
        h[column],
        errors="coerce"
    ).mean()


    if pd.isna(rate):

        return 0.0


    return (
        float(rate)
        * multiplier
    )


# =========================================================
# 3連単AI
# =========================================================

def tri_ai(
    df,
    history,
    odds=None
):

    if df is None or df.empty:

        return pd.DataFrame()


    if odds is None:

        odds = {}


    # =====================================================
    # 枠 → AIスコア
    # =====================================================

    scores = {}

    numbers = {}


    for _, row in df.iterrows():

        lane = int(
            safe_float(
                row.get("枠")
            )
        )

        scores[lane] = safe_float(
            row.get("学習AI")
        )

        numbers[lane] = str(
            row.get("選手番号", "")
        )


    lanes = sorted(
        scores.keys()
    )


    if len(lanes) < 3:

        return pd.DataFrame()


    # =====================================================
    # 120通り
    # =====================================================

    rows = []


    for a, b, c in permutations(
        lanes,
        3
    ):

        # -----------------------------------------------
        # 基本スコア
        # -----------------------------------------------

        total = (

            scores[a]

            + scores[b] * 0.72

            + scores[c] * 0.48

        )


        # -----------------------------------------------
        # 過去14日
        # -----------------------------------------------

        total += history_bonus(
            history,
            numbers[a],
            "1着",
            18
        )

        total += history_bonus(
            history,
            numbers[b],
            "2着",
            12
        )

        total += history_bonus(
            history,
            numbers[c],
            "3着",
            8
        )


        # -----------------------------------------------
        # 1着コース補正
        # -----------------------------------------------

        if a == 1:

            total += 4.0

        elif a in (3, 4):

            total += 1.0


        # -----------------------------------------------
        # 2着コース補正
        # -----------------------------------------------

        if b in (2, 3, 4):

            total += 1.0


        # -----------------------------------------------
        # 穴補正
        # -----------------------------------------------

        if c in (4, 5, 6):

            total += 0.5


        combo = (
            f"{a}-{b}-{c}"
        )


        rows.append({

            "3連単": combo,

            "AIスコア": round(
                total,
                2
            ),

        })


    result = pd.DataFrame(
        rows
    )


    # =====================================================
    # AI確率
    # =====================================================

    probabilities = softmax(
        result[
            "AIスコア"
        ].to_numpy()
    )


    result["AI確率"] = (
        probabilities
        * 100
    ).round(3)


    # =====================================================
    # オッズ
    # =====================================================

    def lookup_odds(combo):

        value = odds.get(
            combo
        )

        if value is None:

            return np.nan

        try:

            value = float(
                value
            )

            if value <= 0:

                return np.nan

            return value

        except (
            TypeError,
            ValueError
        ):

            return np.nan


    result["オッズ"] = result[
        "3連単"
    ].map(
        lookup_odds
    )


    # =====================================================
    # 市場確率
    #
    # 1 / オッズ
    # =====================================================

    result["市場確率"] = np.where(

        result["オッズ"].notna(),

        100.0
        / result["オッズ"],

        np.nan

    )


    result["市場確率"] = (
        result["市場確率"]
        .round(3)
    )


    # =====================================================
    # AI市場乖離
    # =====================================================

    result["AI乖離"] = np.where(

        result["市場確率"].notna(),

        result["AI確率"]
        - result["市場確率"],

        np.nan

    )


    result["AI乖離"] = (
        result["AI乖離"]
        .round(3)
    )


    # =====================================================
    # 期待値倍率
    #
    # AI確率 × オッズ
    #
    # 例:
    # AI確率 10%
    # オッズ 20倍
    #
    # 0.10 × 20 = 2.0倍
    # =====================================================

    result["期待値倍率"] = np.where(

        result["オッズ"].notna(),

        (
            result["AI確率"]
            / 100.0
        )
        * result["オッズ"],

        np.nan

    )


    result["期待値倍率"] = (
        result["期待値倍率"]
        .round(3)
    )


    # =====================================================
    # 信頼度
    # =====================================================

    result["信頼度"] = (
        result["AI確率"]
        .round(1)
    )


    # =====================================================
    # 穴度
    # =====================================================

    min_score = (
        result["AIスコア"]
        .min()
    )

    max_score = (
        result["AIスコア"]
        .max()
    )

    score_range = (
        max_score
        - min_score
    )


    if score_range <= 0:

        result["穴度"] = 0.0

    else:

        # AIスコアが低いほど穴度を高くする
        result["穴度"] = (

            (
                max_score
                - result["AIスコア"]
            )
            / score_range
            * 100

        ).round(1)


    # =====================================================
    # AIランキング
    #
    # オッズがない場合はAIスコア順
    # オッズがある場合は期待値を優先
    # =====================================================

    result["期待値ソート"] = (
        result["期待値倍率"]
        .fillna(-1)
    )


    result = result.sort_values(

        [
            "期待値ソート",
            "AI確率",
            "AIスコア"

        ],

        ascending=[
            False,
            False,
            False
        ]

    ).reset_index(
        drop=True
    )


    result.drop(
        columns=[
            "期待値ソート"
        ],
        inplace=True
    )


    return result
