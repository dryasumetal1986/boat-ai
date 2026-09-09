import pandas as pd
from itertools import permutations


# =========================
# 選手AIスコア
# =========================

def score(r):

    s = 0.0


    # 全国勝率
    s += r["全国勝率"] * 10


    # 全国2連率
    s += r["全国2連率"] * 0.25


    # 当地勝率
    s += r["当地勝率"] * 5


    # モーター2連率
    s += r["モーター2連率"] * 0.12


    # =========================
    # ST
    # =========================

    st = r["平均ST"]


    if 0 < st <= 0.12:

        s += 12

    elif 0 < st <= 0.15:

        s += 8

    elif 0 < st <= 0.18:

        s += 4

    elif st >= 0.22:

        s -= 4


    # =========================
    # コース
    # =========================

    lane = int(
        r["枠"]
    )


    lane_bonus = {
        1: 20,
        2: 8,
        3: 6,
        4: 7,
        5: 2,
        6: 0,
    }


    s += lane_bonus.get(
        lane,
        0,
    )


    # =========================
    # 展示タイム
    # =========================

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
        2,
    )


# =========================
# 3連単AI
# =========================

def tri_ai(
    df,
    history,
):

    scores = {
        int(r["枠"]): float(
            r["学習AI"]
        )
        for _, r in df.iterrows()
    }


    numbers = {
        int(r["枠"]): str(
            r["選手番号"]
        )
        for _, r in df.iterrows()
    }


    out = []


    # =========================
    # 120通り
    # =========================

    for a, b, c in permutations(
        scores,
        3,
    ):

        # 基本AI
        s = (
            scores[a]
            + scores[b] * 0.72
            + scores[c] * 0.48
        )


        # =========================
        # 過去14日成績
        # =========================

        for lane, mul, col in [
            (a, 18, "1着"),
            (b, 12, "2着"),
            (c, 8, "3着"),
        ]:

            if history.empty:
                continue


            h = history[
                history["選手番号"]
                == numbers[lane]
            ]


            if h.empty:
                continue


            s += (
                h[col].mean()
                * mul
            )


        # =========================
        # コース補正
        # =========================

        if a == 1:

            s += 4


        if a in [3, 4]:

            s += 1


        if b in [2, 3, 4]:

            s += 1


        # =========================
        # 3連単
        # =========================

        out.append(
            {
                "3連単": f"{a}-{b}-{c}",
                "AIスコア": round(
                    s,
                    2,
                ),
            }
        )


    return pd.DataFrame(
        out
    ).sort_values(
        "AIスコア",
        ascending=False,
    ).reset_index(
        drop=True
    )
