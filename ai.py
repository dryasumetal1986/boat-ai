import pandas as pd
from itertools import permutations


# =========================
# 選手基本AI
# =========================

def score(r):

    s = 0.0

    # 選手能力
    s += r["全国勝率"] * 10
    s += r["全国2連率"] * 0.25
    s += r["当地勝率"] * 5
    s += r["モーター2連率"] * 0.12

    # 平均ST
    st = r["平均ST"]

    if 0 < st <= 0.12:
        s += 12
    elif 0 < st <= 0.15:
        s += 8
    elif 0 < st <= 0.18:
        s += 4
    elif st >= 0.22:
        s -= 4

    # 枠
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
        0,
    )

    # 展示タイム
    ex = r["展示タイム"]

    if 0 < ex <= 6.70:
        s += 6
    elif 0 < ex <= 6.75:
        s += 4
    elif 0 < ex <= 6.80:
        s += 2
    elif ex >= 6.90:
        s -= 2

    # =========================
    # 展示ST
    # =========================

    exhibition_st = r.get(
        "展示ST",
        0,
    )

    try:
        exhibition_st = float(
            exhibition_st or 0
        )
    except Exception:
        exhibition_st = 0

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

    # =========================
    # 展示進入
    # =========================

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

    # 進入コースが枠より内側ならプラス
    if exhibition_course < lane:
        s += 4

    # 進入コースが外側なら少しマイナス
    elif exhibition_course > lane:
        s -= 2

    return round(
        s,
        2,
    )


# =========================
# 着順別補正
# =========================

def place_score(
    base,
    place,
):

    if place == 1:
        return base * 1.00

    if place == 2:
        return base * 0.72

    if place == 3:
        return base * 0.48

    return base


# =========================
# 過去データ補正
# =========================

def history_bonus(
    history,
    number,
    place,
):

    if history is None:
        return 0.0

    if history.empty:
        return 0.0

    if "選手番号" not in history.columns:
        return 0.0

    if place == 1:
        column = "1着"
        multiplier = 18

    elif place == 2:
        column = "2着"
        multiplier = 12

    else:
        column = "3着"
        multiplier = 8

    if column not in history.columns:
        return 0.0

    h = history[
        history["選手番号"]
        == str(number)
    ]

    if h.empty:
        return 0.0

    value = pd.to_numeric(
        h[column],
        errors="coerce",
    ).mean()

    if pd.isna(value):
        return 0.0

    return float(
        value * multiplier
    )


# =========================
# コース補正
# =========================

def course_bonus(
    lane,
    place,
):

    # 1号艇は1着を強化
    if lane == 1 and place == 1:
        return 5.0

    # 2〜4号艇は2着・3着を少し強化
    if lane in [2, 3, 4]:

        if place == 2:
            return 2.0

        if place == 3:
            return 1.5

    # 5・6号艇は1着を少し抑える
    if lane in [5, 6] and place == 1:
        return -1.5

    return 0.0


# =========================
# 展示ST補正
# =========================

def exhibition_st_bonus(
    row,
    place,
):

    value = row.get(
        "展示ST",
        0,
    )

    try:
        value = float(
            value or 0
        )
    except Exception:
        return 0.0

    if value <= 0:
        return 0.0

    # 展示STは1着評価を強めにする
    if place == 1:

        if value <= 0.08:
            return 7.0

        if value <= 0.10:
            return 5.0

        if value <= 0.12:
            return 3.0

        if value >= 0.20:
            return -3.0

    # 2着
    if place == 2:

        if value <= 0.10:
            return 3.0

        if value <= 0.12:
            return 2.0

    # 3着
    if place == 3:

        if value <= 0.12:
            return 1.5

    return 0.0


# =========================
# 展示進入補正
# =========================

def exhibition_course_bonus(
    row,
    place,
):

    lane = int(
        row["枠"]
    )

    course = row.get(
        "展示進入",
        lane,
    )

    try:
        course = int(course)
    except Exception:
        course = lane

    # 内に入った選手
    if course < lane:

        if place == 1:
            return 4.0

        if place == 2:
            return 2.5

        if place == 3:
            return 1.5

    # 外に出た選手
    if course > lane:

        if place == 1:
            return -2.0

        if place == 2:
            return -1.0

    return 0.0


# =========================
# 3連単AI
# =========================

def tri_ai(
    df,
    history,
):

    # -------------------------
    # 選手基本スコア
    # -------------------------

    scores = {}

    numbers = {}

    rows = {}

    for _, r in df.iterrows():

        lane = int(
            r["枠"]
        )

        scores[lane] = float(
            r["学習AI"]
        )

        numbers[lane] = str(
            r["選手番号"]
        )

        rows[lane] = r


    out = []


    # -------------------------
    # 120通り
    # -------------------------

    for a, b, c in permutations(
        scores,
        3,
    ):

        first = 0.0
        second = 0.0
        third = 0.0

        # =====================
        # 基本AI
        # =====================

        first += place_score(
            scores[a],
            1,
        )

        second += place_score(
            scores[b],
            2,
        )

        third += place_score(
            scores[c],
            3,
        )


        # =====================
        # 過去14日
        # =====================

        first += history_bonus(
            history,
            numbers[a],
            1,
        )

        second += history_bonus(
            history,
            numbers[b],
            2,
        )

        third += history_bonus(
            history,
            numbers[c],
            3,
        )


        # =====================
        # コース
        # =====================

        first += course_bonus(
            a,
            1,
        )

        second += course_bonus(
            b,
            2,
        )

        third += course_bonus(
            c,
            3,
        )


        # =====================
        # 展示ST
        # =====================

        first += exhibition_st_bonus(
            rows[a],
            1,
        )

        second += exhibition_st_bonus(
            rows[b],
            2,
        )

        third += exhibition_st_bonus(
            rows[c],
            3,
        )


        # =====================
        # 展示進入
        # =====================

        first += exhibition_course_bonus(
            rows[a],
            1,
        )

        second += exhibition_course_bonus(
            rows[b],
            2,
        )

        third += exhibition_course_bonus(
            rows[c],
            3,
        )


        # =====================
        # 1号艇の逃げ補正
        # =====================

        if a == 1:
            first += 4.0

        # 3・4号艇の攻め
        if a in [3, 4]:
            first += 1.0

        # 2〜4号艇の2着
        if b in [2, 3, 4]:
            second += 1.0


        # =====================
        # 合計
        # =====================

        total = (
            first
            + second
            + third
        )


        out.append({

            "3連単":
                f"{a}-{b}-{c}",

            "1着AI":
                round(
                    first,
                    2,
                ),

            "2着AI":
                round(
                    second,
                    2,
                ),

            "3着AI":
                round(
                    third,
                    2,
                ),

            "AIスコア":
                round(
                    total,
                    2,
                ),
        })


    result = pd.DataFrame(
        out
    )


    if result.empty:
        return result


    # =========================
    # AI順位
    # =========================

    result = result.sort_values(
        "AIスコア",
        ascending=False,
    ).reset_index(
        drop=True
    )


    # =========================
    # 信頼度
    # =========================

    minimum = result[
        "AIスコア"
    ].min()

    maximum = result[
        "AIスコア"
    ].max()


    if maximum > minimum:

        result["信頼度"] = (
            (
                result["AIスコア"]
                - minimum
            )
            / (
                maximum
                - minimum
            )
            * 100
        ).round(1)

    else:

        result["信頼度"] = 50.0


    return result
