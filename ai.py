import math
import pandas as pd

from itertools import permutations


# =========================================================
# 選手個人AIスコア
# =========================================================

def score(r):

    s = 0.0

    # -----------------------------------------
    # 全国成績
    # -----------------------------------------

    s += r["全国勝率"] * 10.0

    s += r["全国2連率"] * 0.25

    # -----------------------------------------
    # 当地成績
    # -----------------------------------------

    s += r["当地勝率"] * 5.0

    # -----------------------------------------
    # モーター
    # -----------------------------------------

    s += r["モーター2連率"] * 0.12

    # -----------------------------------------
    # ST
    # -----------------------------------------

    st = r["平均ST"]

    if 0 < st <= 0.12:
        s += 12

    elif 0 < st <= 0.15:
        s += 8

    elif 0 < st <= 0.18:
        s += 4

    elif st >= 0.22:
        s -= 4

    # -----------------------------------------
    # コース補正
    # -----------------------------------------

    lane = int(r["枠"])

    course_bonus = {
        1: 20,
        2: 8,
        3: 6,
        4: 7,
        5: 2,
        6: 0
    }

    s += course_bonus.get(
        lane,
        0
    )

    # -----------------------------------------
    # 展示タイム
    # -----------------------------------------

    ex = r["展示タイム"]

    if 0 < ex <= 6.70:
        s += 6

    elif 0 < ex <= 6.75:
        s += 4

    elif 0 < ex <= 6.80:
        s += 2

    elif ex >= 6.90:
        s -= 2

    return round(
        s,
        2
    )


# =========================================================
# softmax
# =========================================================

def softmax(values):

    if not values:
        return []

    mx = max(values)

    exp_values = [
        math.exp(
            min(
                20,
                max(
                    -20,
                    x - mx
                )
            )
        )
        for x in values
    ]

    total = sum(
        exp_values
    )

    if total <= 0:
        return [
            1 / len(values)
            for _ in values
        ]

    return [
        x / total
        for x in exp_values
    ]


# =========================================================
# 3連単AI
# =========================================================

def tri_ai(
    df,
    history,
    odds=None
):

    scores = {
        int(r["枠"]):
        float(r["学習AI"])
        for _, r in df.iterrows()
    }

    nums = {
        int(r["枠"]):
        str(r["選手番号"])
        for _, r in df.iterrows()
    }

    out = []

    # -----------------------------------------
    # 全120通り
    # -----------------------------------------

    for a, b, c in permutations(
        scores,
        3
    ):

        s = (
            scores[a]
            + scores[b] * 0.72
            + scores[c] * 0.48
        )

        # -------------------------------------
        # 過去成績
        # -------------------------------------

        for lane, mul, col in [
            (a, 18, "1着"),
            (b, 12, "2着"),
            (c, 8, "3着")
        ]:

            player_no = nums[lane]

            h = history[
                history["選手番号"]
                == player_no
            ]

            if not h.empty:

                rate = h[col].mean()

                s += rate * mul

        # -------------------------------------
        # コース補正
        # -------------------------------------

        if a == 1:
            s += 4

        if a in [3, 4]:
            s += 1

        if b in [2, 3, 4]:
            s += 1

        # -------------------------------------
        # 3着穴補正
        # -------------------------------------

        if c in [4, 5, 6]:
            s += 0.5

        out.append({

            "3連単":
                f"{a}-{b}-{c}",

            "AIスコア":
                round(s, 2)

        })

    result = pd.DataFrame(
        out
    )

    # =====================================================
    # AI確率
    # =====================================================

    probs = softmax(
        result["AIスコア"].tolist()
    )

    result["AI確率"] = [
        round(
            p * 100,
            3
        )
        for p in probs
    ]

    # =====================================================
    # オッズ
    # =====================================================

    if odds is None:
        odds = {}

    result["オッズ"] = result[
        "3連単"
    ].map(
        lambda x:
        odds.get(x)
    )

    # =====================================================
    # 市場確率
    # =====================================================

    def market_probability(x):

        if x is None:
            return None

        try:

            x = float(x)

            if x <= 0:
                return None

            return round(
                100 / x,
                3
            )

        except Exception:
            return None

    result["市場確率"] = result[
        "オッズ"
    ].map(
        market_probability
    )

    # =====================================================
    # AIと市場の乖離
    # =====================================================

    def probability_gap(row):

        if pd.isna(
            row["市場確率"]
        ):
            return None

        return round(
            row["AI確率"]
            - row["市場確率"],
            3
        )

    result["AI乖離"] = result.apply(
        probability_gap,
        axis=1
    )

    # =====================================================
    # 期待値倍率
    #
    # AI確率 × オッズ
    # 100円投票に対する理論倍率
    # =====================================================

    def expected_value(row):

        if pd.isna(
            row["オッズ"]
        ):
            return None

        try:

            odds_value = float(
                row["オッズ"]
            )

            probability = (
                float(row["AI確率"])
                / 100
            )

            return round(
                probability
                * odds_value,
                3
            )

        except Exception:

            return None

    result["期待値倍率"] = result.apply(
        expected_value,
        axis=1
    )

    # =====================================================
    # 信頼度
    # =====================================================

    result["信頼度"] = result[
        "AI確率"
    ].round(1)

    # =====================================================
    # 穴度
    # =====================================================

    max_score = result[
        "AIスコア"
    ].max()

    min_score = result[
        "AIスコア"
    ].min()

    diff = max_score - min_score

    if diff <= 0:
        result["穴度"] = 0.0

    else:

        result["穴度"] = (
            (
                max_score
                - result["AIスコア"]
            )
            / diff
            * 100
        ).round(1)

    # =====================================================
    # 最終ランキング
    # =====================================================

    result = result.sort_values(
        [
            "期待値倍率",
            "AI確率",
            "AIスコア"
        ],
        ascending=[
            False,
            False,
            False
        ],
        na_position="last"
    ).reset_index(
        drop=True
    )

    return result
