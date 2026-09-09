import pandas as pd
from itertools import permutations


# =========================
# 選手基本AI
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
    # 平均ST
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
    # 枠
    # =========================

    lane = int(r["枠"])

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
        0
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
        2
    )


# =========================
# 着順別スコア
# =========================

def place_score(
    base,
    place
):

    if place == 1:

        return base * 1.00

    if place == 2:

        return base * 0.72

    if place == 3:

        return base * 0.48

    return 0.0


# =========================
# 過去成績補正
# =========================

def history_bonus(
    history,
    number,
    place
):

    if history.empty:
        return 0.0

    h = history[
        history["選手番号"]
        == str(number)
    ]

    if h.empty:
        return 0.0


    column = {
        1: "1着",
        2: "2着",
        3: "3着",
    }.get(place)


    if column is None:
        return 0.0


    value = h[column].mean()

    if pd.isna(value):
        return 0.0


    multiplier = {
        1: 18,
        2: 12,
        3: 8,
    }[place]


    return float(
        value * multiplier
    )


# =========================
# 3連単AI
# =========================

def tri_ai(
    df,
    history
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
        3
    ):

        # -------------------------
        # 1着
        # -------------------------

        first_score = place_score(
            scores[a],
            1
        )


        # -------------------------
        # 2着
        # -------------------------

        second_score = place_score(
            scores[b],
            2
        )


        # -------------------------
        # 3着
        # -------------------------

        third_score = place_score(
            scores[c],
            3
        )


        s = (
            first_score
            + second_score
            + third_score
        )


        # =========================
        # 過去14日
        # =========================

        s += history_bonus(
            history,
            numbers[a],
            1
        )

        s += history_bonus(
            history,
            numbers[b],
            2
        )

        s += history_bonus(
            history,
            numbers[c],
            3
        )


        # =========================
        # 1着コース補正
        # =========================

        if a == 1:

            s += 4

        elif a in [3, 4]:

            s += 1


        # =========================
        # 2着コース補正
        # =========================

        if b in [2, 3, 4]:

            s += 1


        # =========================
        # 同じ艇は不可
        # =========================

        if len({
            a,
            b,
            c
        }) != 3:

            continue


        out.append({

            "3連単":
                f"{a}-{b}-{c}",

            "1着AI":
                round(
                    first_score,
                    2
                ),

            "2着AI":
                round(
                    second_score,
                    2
                ),

            "3着AI":
                round(
                    third_score,
                    2
                ),

            "AIスコア":
                round(
                    s,
                    2
                ),
        })


    df2 = pd.DataFrame(
        out
    )


    # =========================
    # AIスコア順
    # =========================

    df2 = df2.sort_values(
        "AIスコア",
        ascending=False
    ).reset_index(
        drop=True
    )


    # =========================
    # 信頼度
    # =========================

    if not df2.empty:

        min_score = (
            df2["AIスコア"].min()
        )

        max_score = (
            df2["AIスコア"].max()
        )


        if max_score > min_score:

            df2["信頼度"] = (
                (
                    df2["AIスコア"]
                    - min_score
                )
                / (
                    max_score
                    - min_score
                )
                * 100
            ).round(1)

        else:

            df2["信頼度"] = 50.0


    return df2
