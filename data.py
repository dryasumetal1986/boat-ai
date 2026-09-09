import requests
import streamlit as st
from datetime import date, timedelta
from bs4 import BeautifulSoup
import re


# =========================================================
# Boatrace Open API
# =========================================================

API = "https://boatraceopenapi.github.io/api/v1"


@st.cache_data(ttl=180)
def get_data(d):

    u = f"{API}/{d:%Y/%Y%m%d}.json"

    r = requests.get(
        u,
        timeout=20
    )

    r.raise_for_status()

    return r.json()


# =========================================================
# 共通
# =========================================================

def racers(x):

    if isinstance(x, list):
        return x

    if isinstance(x, dict):
        return list(x.values())

    return []


def pmap(race):

    out = {}

    for p in racers(
        race.get(
            "preview",
            {}
        ).get(
            "racers",
            {}
        )
    ):

        e = p.get("entry_number")
        c = p.get("course_number")

        if e is not None:
            out[str(e)] = p

        if c is not None:
            out.setdefault(
                str(c),
                p
            )

    return out


def get_race(data, sno, rno):

    s = (
        data
        .get("programs", {})
        .get("stadiums", {})
        .get(str(sno))
    )

    if not s:
        return None

    return (
        s
        .get("races", {})
        .get(str(rno))
    )


# =========================================================
# 過去14日
# =========================================================

@st.cache_data(ttl=3600)
def history14(td):

    rows = []

    for i in range(1, 15):

        d = td - timedelta(days=i)

        if d < date(2026, 1, 1):
            continue

        try:
            data = get_data(d)

        except Exception:
            continue

        for sno, s in (
            data
            .get("programs", {})
            .get("stadiums", {})
            .items()
        ):

            for rno, race in (
                s
                .get("races", {})
                .items()
            ):

                rr = (
                    race
                    .get("result", {})
                    .get("racers", {})
                )

                places = {}

                for x in racers(rr):

                    p = str(
                        x.get(
                            "place_number",
                            ""
                        )
                    )

                    if p in ["1", "2", "3"]:

                        places[p] = str(
                            x.get(
                                "number",
                                ""
                            )
                        )

                if "1" not in places:
                    continue

                rs = race.get(
                    "racers",
                    {}
                )

                if not isinstance(rs, dict):
                    continue

                preview = (
                    race
                    .get("preview", {})
                    .get("racers", {})
                )

                if not isinstance(
                    preview,
                    dict
                ):
                    preview = {}

                for lane in range(1, 7):

                    r = rs.get(
                        str(lane),
                        {}
                    )

                    if not r:
                        continue

                    no = str(
                        r.get(
                            "number",
                            ""
                        )
                    )

                    p = preview.get(
                        str(lane),
                        {}
                    )

                    course = (
                        p.get("course_number")
                        or r.get("course_number")
                        or lane
                    )

                    try:
                        course = int(course)

                    except Exception:
                        course = lane

                    rows.append({

                        "日付": d,

                        "場": int(sno),

                        "レース": int(rno),

                        "枠": lane,

                        "コース": course,

                        "選手番号": no,

                        "1着": int(
                            no == places.get("1")
                        ),

                        "2着": int(
                            no == places.get("2")
                        ),

                        "3着": int(
                            no == places.get("3")
                        )
                    })

    return rows


# =========================================================
# 3連単オッズ取得
# =========================================================

ODDS_URL = (
    "https://www.boatrace.jp/"
    "owpc/pc/race/odds3t"
)


@st.cache_data(ttl=60)
def get_odds(td, sno, rno):

    """
    BOATRACE公式サイトから
    3連単の購入前オッズを取得。

    戻り値:
        {
            "1-2-3": 4.5,
            "1-2-4": 8.2,
            ...
        }
    """

    params = {
        "jcd": f"{int(sno):02d}",
        "hd": td.strftime("%Y%m%d"),
        "rno": int(rno)
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/131.0 Safari/537.36"
        )
    }

    try:

        r = requests.get(
            ODDS_URL,
            params=params,
            headers=headers,
            timeout=15
        )

        r.raise_for_status()

    except Exception as e:

        raise RuntimeError(
            f"オッズ取得に失敗しました: {e}"
        )

    soup = BeautifulSoup(
        r.text,
        "html.parser"
    )

    odds = {}

    # -----------------------------------------------------
    # HTMLから「1-2-3」のような組合せとオッズを探す
    # -----------------------------------------------------

    text = soup.get_text(
        " ",
        strip=True
    )

    # 3連単表記のパターン
    pattern = re.compile(
        r"([1-6])\s*[-－]\s*"
        r"([1-6])\s*[-－]\s*"
        r"([1-6])"
    )

    matches = pattern.findall(text)

    for a, b, c in matches:

        combo = f"{a}-{b}-{c}"

        # 組み合わせの直後にある数字を探す
        idx = text.find(
            f"{a}-{b}-{c}"
        )

        if idx < 0:
            continue

        after = text[
            idx + len(combo):
            idx + len(combo) + 80
        ]

        nums = re.findall(
            r"\d+(?:\.\d+)?",
            after
        )

        if not nums:
            continue

        for n in nums:

            try:
                value = float(n)

            except Exception:
                continue

            # 0や異常な数値を除外
            if value <= 0:
                continue

            if value < 1:
                continue

            odds[combo] = value
            break

    # -----------------------------------------------------
    # 120通り揃わなかった場合
    # -----------------------------------------------------

    if len(odds) < 50:

        # HTMLのtableを直接読む
        try:

            tables = pd.read_html(
                r.text
            )

            for table in tables:

                for _, row in table.iterrows():

                    row_text = " ".join(
                        str(x)
                        for x in row.tolist()
                    )

                    m = pattern.search(
                        row_text
                    )

                    if not m:
                        continue

                    a, b, c = m.groups()

                    combo = (
                        f"{a}-{b}-{c}"
                    )

                    nums = re.findall(
                        r"\d+(?:\.\d+)?",
                        row_text
                    )

                    if not nums:
                        continue

                    for n in reversed(nums):

                        try:
                            value = float(n)

                        except Exception:
                            continue

                        if value >= 1:
                            odds[combo] = value
                            break

        except Exception:
            pass

    return odds

---

2. "ai.py" をオッズ対応にする

ここでは重要なので、AIスコアとオッズを分離します。

そして、

AI確率 × オッズ

を期待値として表示します。

:::writing{variant="document" id="74106" title="ai.py オッズ対応版"}

import pandas as pd
from itertools import permutations


# =========================================================
# 共通
# =========================================================

def safe_float(v, default=0.0):

    try:

        if pd.isna(v):
            return default

        return float(v)

    except Exception:

        return default


# =========================================================
# 選手AI
# =========================================================

def score(r):

    s = 0.0

    # --------------------------------
    # 選手能力
    # --------------------------------

    s += safe_float(
        r.get("全国勝率")
    ) * 8.0

    s += safe_float(
        r.get("全国2連率")
    ) * 0.20

    s += safe_float(
        r.get("当地勝率")
    ) * 4.0

    s += safe_float(
        r.get("モーター2連率")
    ) * 0.15

    # --------------------------------
    # ST
    # --------------------------------

    st = safe_float(
        r.get("平均ST")
    )

    if st > 0:

        st_score = (
            0.20 - st
        ) * 100

        st_score = max(
            -8,
            min(10, st_score)
        )

        s += st_score

    # --------------------------------
    # 枠
    # --------------------------------

    lane = int(
        safe_float(
            r.get("枠")
        )
    )

    s += {
        1: 18,
        2: 8,
        3: 6,
        4: 7,
        5: 3,
        6: 0
    }.get(lane, 0)

    # --------------------------------
    # 展示
    # --------------------------------

    ex = safe_float(
        r.get("展示タイム")
    )

    if ex > 0:

        ex_score = (
            6.80 - ex
        ) * 40

        ex_score = max(
            -5,
            min(8, ex_score)
        )

        s += ex_score

    return round(s, 2)


# =========================================================
# 相対特徴
# =========================================================

def add_relative_features(df):

    df = df.copy()

    ex = pd.to_numeric(
        df["展示タイム"],
        errors="coerce"
    )

    valid = ex[ex > 0]

    if not valid.empty:

        best = valid.min()

        df["展示順位"] = (
            ex.rank(
                ascending=True,
                method="min"
            )
        )

        df["展示タイム差"] = (
            ex - best
        )

    else:

        df["展示順位"] = 4
        df["展示タイム差"] = 0

    return df


# =========================================================
# 過去14日
# =========================================================

def history_score(
    history,
    number
):

    if history is None:
        return 0.0

    if history.empty:
        return 0.0

    h = history[
        history["選手番号"].astype(str)
        == str(number)
    ]

    if h.empty:
        return 0.0

    score_value = 0.0

    # 1着率
    score_value += (
        h["1着"].mean() * 10
    )

    # 2着率
    score_value += (
        h["2着"].mean() * 5
    )

    # 3着率
    score_value += (
        h["3着"].mean() * 3
    )

    return score_value


# =========================================================
# 3連単AI
# =========================================================

def tri_ai(
    df,
    history,
    odds=None
):

    df = add_relative_features(df)

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

    rows = {
        int(r["枠"]):
        r

        for _, r in df.iterrows()
    }

    out = []

    # -----------------------------------------------------
    # 120通り
    # -----------------------------------------------------

    for a, b, c in permutations(
        scores,
        3
    ):

        ra = rows[a]
        rb = rows[b]
        rc = rows[c]

        s = 0.0

        # --------------------------------
        # 基本AI
        # --------------------------------

        s += scores[a] * 1.00
        s += scores[b] * 0.70
        s += scores[c] * 0.45

        # --------------------------------
        # 1着枠
        # --------------------------------

        if a == 1:
            s += 7

        elif a in [2, 3]:
            s += 3

        elif a in [5, 6]:
            s -= 1

        # --------------------------------
        # 2着
        # --------------------------------

        if b in [2, 3, 4]:
            s += 2

        # --------------------------------
        # 3着
        # --------------------------------

        if c in [2, 3, 4, 5]:
            s += 1

        # --------------------------------
        # 展示順位
        # --------------------------------

        ex_a = safe_float(
            ra.get("展示順位")
        )

        ex_b = safe_float(
            rb.get("展示順位")
        )

        ex_c = safe_float(
            rc.get("展示順位")
        )

        if ex_a == 1:
            s += 5

        elif ex_a == 2:
            s += 2

        if ex_b == 1:
            s += 2.5

        elif ex_b == 2:
            s += 1

        if ex_c == 1:
            s += 1.5

        # --------------------------------
        # 展示タイム差
        # --------------------------------

        s -= safe_float(
            ra.get("展示タイム差")
        ) * 20

        s -= safe_float(
            rb.get("展示タイム差")
        ) * 10

        s -= safe_float(
            rc.get("展示タイム差")
        ) * 5

        # --------------------------------
        # ST
        # --------------------------------

        sta = safe_float(
            ra.get("平均ST")
        )

        stb = safe_float(
            rb.get("平均ST")
        )

        stc = safe_float(
            rc.get("平均ST")
        )

        if 0 < sta <= .15:
            s += 4

        if 0 < stb <= .15:
            s += 2

        if 0 < stc <= .15:
            s += 1

        # --------------------------------
        # モーター
        # --------------------------------

        ma = safe_float(
            ra.get("モーター2連率")
        )

        mb = safe_float(
            rb.get("モーター2連率")
        )

        mc = safe_float(
            rc.get("モーター2連率")
        )

        if ma >= 45:
            s += 3

        elif ma >= 40:
            s += 1.5

        if mb >= 45:
            s += 1.5

        if mc >= 45:
            s += 1

        # --------------------------------
        # 過去14日
        # --------------------------------

        s += history_score(
            history,
            nums[a]
        ) * 1.5

        s += history_score(
            history,
            nums[b]
        )

        s += history_score(
            history,
            nums[c]
        ) * 0.6

        # --------------------------------
        # 組み合わせ
        # --------------------------------

        if a == 1 and b in [2, 3, 4]:
            s += 3

        if a in [2, 3] and b in [3, 4]:
            s += 1

        out.append({

            "3連単":
            f"{a}-{b}-{c}",

            "AIスコア":
            round(s, 2)

        })

    result = pd.DataFrame(out)

    # =====================================================
    # AIスコア → 確率
    # =====================================================

    # 単純なmin-maxではなく、
    # softmaxに近い変換を使用

    scores_series = (
        result["AIスコア"]
    )

    temperature = 8.0

    exp_score = (
        (scores_series - scores_series.max())
        / temperature
    ).apply(
        lambda x: __import__(
            "math"
        ).exp(x)
    )

    result["AI確率"] = (
        exp_score
        / exp_score.sum()
        * 100
    ).round(2)

    # =====================================================
    # オッズ
    # =====================================================

    if odds is None:
        odds = {}

    result["オッズ"] = (
        result["3連単"]
        .map(odds)
    )

    # =====================================================
    # 期待値
    #
    # AI確率(%) × オッズ ÷ 100
    # =====================================================

    result["期待値"] = (
        result["AI確率"]
        * pd.to_numeric(
            result["オッズ"],
            errors="coerce"
        )
        / 100
    ).round(3)

    # =====================================================
    # オッズがない場合の表示
    # =====================================================

    result["期待値"] = result[
        "期待値"
    ].fillna(0)

    # =====================================================
    # 穴度
    # =====================================================

    result["穴度"] = (
        result["オッズ"]
        .apply(
            lambda x:
            min(100, x / 2)
            if pd.notna(x)
            else 0
        )
        .round(1)
    )

    # =====================================================
    # AI順
    # =====================================================

    result = result.sort_values(
        "AI確率",
        ascending=False
    ).reset_index(
        drop=True
    )

    return result

---

3. "app.py" を変更

ここが画面部分です。

オッズ取得 → AIと結合 → AIランキング＋期待値ランキングを追加します。

:::writing{variant="document" id="92647" title="app.py オッズ対応版"}

import streamlit as st
import pandas as pd

from datetime import date, datetime
from zoneinfo import ZoneInfo

from data import (
    get_data,
    get_race,
    history14,
    get_odds
)

from ai import (
    score,
    tri_ai
)


# =========================================================
# 競艇場
# =========================================================

STADIUMS = {

    1: "桐生",
    2: "戸田",
    3: "江戸川",
    4: "平和島",
    5: "多摩川",
    6: "浜名湖",
    7: "蒲郡",
    8: "常滑",
    9: "津",
    10: "三国",
    11: "びわこ",
    12: "住之江",
    13: "尼崎",
    14: "鳴門",
    15: "丸亀",
    16: "児島",
    17: "宮島",
    18: "徳山",
    19: "下関",
    20: "若松",
    21: "芦屋",
    22: "福岡",
    23: "唐津",
    24: "大村"
}


# =========================================================
# Streamlit
# =========================================================

st.set_page_config(

    page_title=
    "やっちゃんの競艇AI予想 PRO",

    page_icon="🚤",

    layout="wide"
)


st.title(
    "🚤 やっちゃんの競艇AI予想 PRO"
)

st.write(
    "展示タイム＋選手データ＋過去14日＋購入前オッズ"
)


# =========================================================
# 日付
# =========================================================

today = datetime.now(
    ZoneInfo("Asia/Tokyo")
).date()


c1, c2, c3 = st.columns(3)


with c1:

    td = st.date_input(
        "開催日",
        today,
        min_value=date(
            2026,
            1,
            1
        )
    )


with c2:

    name = st.selectbox(
        "競艇場",
        list(
            STADIUMS.values()
        )
    )


with c3:

    rno = st.selectbox(
        "レース",
        range(1, 13),
        format_func=
        lambda x:
        f"{x}R"
    )


sno = list(
    STADIUMS
)[
    list(
        STADIUMS.values()
    ).index(name)
]


# =========================================================
# 実行
# =========================================================

if st.button(
    "🚀 AI予想を実行",
    type="primary"
):

    # -----------------------------------------------------
    # レースデータ
    # -----------------------------------------------------

    try:

        data = get_data(td)

        race = get_race(
            data,
            sno,
            rno
        )

    except Exception as e:

        st.error(
            "データ取得に失敗しました"
        )

        st.code(str(e))

        st.stop()


    if race is None:

        st.error(
            "このレースのデータがありません"
        )

        st.stop()


    # -----------
