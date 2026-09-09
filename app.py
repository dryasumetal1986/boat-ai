import re
import requests
import streamlit as st
import pandas as pd
from datetime import date
from bs4 import BeautifulSoup

import data
from ai import score, tri_ai


STADIUMS = {
    1:"桐生", 2:"戸田", 3:"江戸川", 4:"平和島", 5:"多摩川",
    6:"浜名湖", 7:"蒲郡", 8:"常滑", 9:"津", 10:"三国",
    11:"びわこ", 12:"住之江", 13:"尼崎", 14:"鳴門",
    15:"丸亀", 16:"児島", 17:"宮島", 18:"徳山",
    19:"下関", 20:"若松", 21:"芦屋", 22:"福岡",
    23:"唐津", 24:"大村"
}

st.set_page_config(
    page_title="競艇AI予想",
    layout="wide"
)


# -------------------------
# 共通
# -------------------------

def val(d, keys, default=0):
    if not isinstance(d, dict):
        return default

    for k in keys:
        if k in d and d[k] is not None:
            return d[k]

    return default


def num(x, default=0):
    try:
        return float(
            str(x)
            .replace(",", "")
            .replace("%", "")
            .strip()
        )
    except:
        return default


def get_html(url):
    r = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20
    )
    r.raise_for_status()
    return r.text


# -------------------------
# 公式 出走表
# -------------------------

@st.cache_data(ttl=120)
def official_stats(sno, rno, td):

    url = (
        "https://www.boatrace.jp/owpc/pc/race/racelist"
        f"?rno={rno}&jcd={int(sno):02d}&hd={td:%Y%m%d}"
    )

    try:
        html = get_html(url)
    except:
        return {}

    soup = BeautifulSoup(html, "html.parser")
    result = {}

    for tr in soup.find_all("tr"):

        text = tr.get_text(" ", strip=True)

        # 1〜6の枠が含まれない行は無視
        lane = None
        for i in range(1, 7):
            if re.search(rf"\b{i}\b", text[:80]):
                lane = i
                break

        if lane is None:
            continue

        # 小数値を取得
        nums = re.findall(
            r"(?:\d+\.\d+|\.\d+)",
            text
        )

        nums = [num(x) for x in nums]

        # 勝率系は通常 0〜10程度
        rates = [
            x for x in nums
            if 0 < x <= 10
        ]

        if len(rates) < 3:
            continue

        result[lane] = {
            "全国勝率": rates[0],
            "全国2連率": rates[1],
            "当地勝率": rates[2],
            "モーター2連率": rates[4] if len(rates) > 4 else 0,
            "平均ST": rates[-1] if rates[-1] <= 1 else 0,
        }

    return result


# -------------------------
# 公式 展示情報
# -------------------------

@st.cache_data(ttl=120)
def official_before(sno, rno, td):

    url = (
        "https://www.boatrace.jp/owpc/pc/race/beforeinfo"
        f"?rno={rno}&jcd={int(sno):02d}&hd={td:%Y%m%d}"
    )

    try:
        html = get_html(url)
    except:
        return {}

    soup = BeautifulSoup(html, "html.parser")
    result = {}

    for tr in soup.find_all("tr"):

        text = tr.get_text(" ", strip=True)

        lane = None
        for i in range(1, 7):
            if re.search(rf"\b{i}\b", text[:60]):
                lane = i
                break

        if lane is None:
            continue

        nums = re.findall(
            r"(?:\d+\.\d+|\.\d+)",
            text
        )

        nums = [num(x) for x in nums]

        exhibition = 0
        exhibition_st = 0

        for x in nums:

            # 展示タイム
            if 6.0 <= x <= 8.0:
                if exhibition == 0:
                    exhibition = x

            # 展示ST
            if 0 < x <= 0.60:
                if exhibition_st == 0:
                    exhibition_st = x

        if exhibition or exhibition_st:
            result[lane] = {
                "展示タイム": exhibition,
                "展示ST": exhibition_st
            }

    return result


# -------------------------
# AI用データ作成
# -------------------------

def make_rows(race, sno, rno, td):

    entries = (
        race.get("racers")
        or race.get("entries")
        or race.get("entry")
        or []
    )

    if isinstance(entries, dict):
        entries = list(entries.values())

    stats = official_stats(sno, rno, td)
    before = official_before(sno, rno, td)

    rows = []

    for i, racer in enumerate(entries):

        lane = num(
            val(
                racer,
                [
                    "entryNumber",
                    "boatNumber",
                    "courseNumber",
                    "枠",
                    "lane"
                ],
                i + 1
            )
        )

        lane = int(lane)

        s = stats.get(lane, {})
        b = before.get(lane, {})

        rows.append({
            "枠": lane,

            "展示進入": lane,

            "選手名": val(
                racer,
                ["racerName", "name", "選手名"],
                ""
            ),

            "選手番号": val(
                racer,
                [
                    "racerNumber",
                    "playerNumber",
                    "number",
                    "選手番号"
                ],
                ""
            ),

            "級別": val(
                racer,
                ["grade", "class", "級別"],
                ""
            ),

            "全国勝率": num(s.get("全国勝率", 0)),
            "全国2連率": num(s.get("全国2連率", 0)),
            "当地勝率": num(s.get("当地勝率", 0)),
            "モーター2連率": num(s.get("モーター2連率", 0)),
            "平均ST": num(s.get("平均ST", 0)),

            "展示ST": num(b.get("展示ST", 0)),
            "展示タイム": num(b.get("展示タイム", 0)),

            "場": int(sno)
        })

    return rows


# -------------------------
# 画面
# -------------------------

st.title("🚤 競艇AI予想")

col1, col2, col3 = st.columns(3)

with col1:
    td = st.date_input(
        "開催日",
        value=date.today()
    )

with col2:
    sno = st.selectbox(
        "競艇場",
        list(STADIUMS.keys()),
        format_func=lambda x: STADIUMS[x]
    )

with col3:
    rno = st.selectbox(
        "レース",
        range(1, 13),
        format_func=lambda x: f"{x}R"
    )


if st.button("AI予想を実行", type="primary"):

    with st.spinner("データ取得中..."):

        try:
            raw = data.get_data(td)
            race = data.get_race(raw, sno, rno)

            if race is None:
                st.error("レースデータが見つかりません。")
                st.stop()

            rows = make_rows(
                race,
                sno,
                rno,
                td
            )

            if not rows:
                st.error("選手データを取得できませんでした。")
                st.stop()

            df = pd.DataFrame(rows)

            # 学習AIスコア
            df["学習AI"] = df.apply(
                score,
                axis=1
            )

            # 過去データ
            try:
                history = pd.DataFrame(
                    data.history14(td)
                )
            except:
                history = pd.DataFrame()

            result, boat_probs = tri_ai(
                df,
                history
            )

        except Exception as e:
            st.error(f"エラー：{e}")
            st.stop()


    # -------------------------
    # 選手データ
    # -------------------------

    st.subheader("📋 選手データ")

    show_cols = [
        "枠",
        "選手名",
        "級別",
        "全国勝率",
        "全国2連率",
        "当地勝率",
        "モーター2連率",
        "平均ST",
        "展示ST",
        "展示タイム",
        "学習AI"
    ]

    show_cols = [
        c for c in show_cols
        if c in df.columns
    ]

    st.dataframe(
        df[show_cols],
        use_container_width=True,
        hide_index=True
    )


    # -------------------------
    # AI予想
    # -------------------------

    st.subheader("🤖 AI予想")

    st.dataframe(
        result,
        use_container_width=True,
        hide_index=True
    )


    # -------------------------
    # 枠別AI確率
    # -------------------------

    st.subheader("📊 枠別AI確率")

    prob_df = pd.DataFrame({
        "枠": list(range(1, 7)),
        "AI確率": [
            boat_probs.get(i, 0)
            for i in range(1, 7)
        ]
    })

    prob_df["AI確率"] = (
        prob_df["AI確率"] * 100
    ).round(1)

    st.bar_chart(
        prob_df.set_index("枠")
    )


    st.success("AI予想が完了しました。")
