import re
import requests
import streamlit as st
import pandas as pd
from datetime import date
from bs4 import BeautifulSoup

import data
from ai import score, tri_ai


STADIUMS = {
    1:"桐生",2:"戸田",3:"江戸川",4:"平和島",5:"多摩川",6:"浜名湖",
    7:"蒲郡",8:"常滑",9:"津",10:"三国",11:"びわこ",12:"住之江",
    13:"尼崎",14:"鳴門",15:"丸亀",16:"児島",17:"宮島",18:"徳山",
    19:"下関",20:"若松",21:"芦屋",22:"福岡",23:"唐津",24:"大村"
}

st.set_page_config(
    page_title="競艇AI予想",
    page_icon="🚤",
    layout="wide"
)

st.title("🚤 競艇AI予想")


def num(x, default=0):
    try:
        return float(
            str(x)
            .replace(",", "")
            .replace("%", "")
            .replace("秒", "")
            .strip()
        )
    except:
        return default


def req(url):
    r = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20
    )
    r.raise_for_status()
    return r.text


# =========================================================
# 公式 出走表
# =========================================================

@st.cache_data(ttl=120)
def official_racelist(sno, rno, td):

    url = (
        "https://www.boatrace.jp/owpc/pc/race/racelist"
        f"?rno={rno}"
        f"&jcd={int(sno):02d}"
        f"&hd={td:%Y%m%d}"
    )

    try:
        html = req(url)
    except:
        return {}

    soup = BeautifulSoup(html, "html.parser")
    result = {}

    # 出走表の各行を探す
    for tr in soup.find_all("tr"):

        cells = [
            x.get_text(" ", strip=True)
            for x in tr.find_all(["th", "td"])
        ]

        if len(cells) < 8:
            continue

        # 先頭に1～6の艇番がある行だけ
        lane = None

        for x in cells[:3]:
            if re.fullmatch(r"[1-6]", x):
                lane = int(x)
                break

        if lane is None:
            continue

        text = " ".join(cells)

        # 数値を抽出
        values = re.findall(
            r"\d+(?:\.\d+)?",
            text
        )

        if len(values) < 8:
            continue

        # 典型的な出走表の並び
        #
        # 枠
        # 選手番号
        # 級別
        # 体重
        # 全国勝率
        # 全国2連率
        # 当地勝率
        # 当地2連率
        # モーター2連率
        # ボート2連率
        # 平均ST
        #

        try:
            # 文字列として扱うため、cellsから
            # 小数値だけを抽出
            decimals = []

            for x in cells:
                m = re.search(
                    r"(\d+\.\d+)",
                    x
                )
                if m:
                    decimals.append(float(m.group(1)))

            if len(decimals) < 6:
                continue

            # 6艇の出走表では概ねこの順序
            # 体重の次から成績値が並ぶ
            result[lane] = {
                "全国勝率": decimals[0],
                "全国2連率": decimals[1],
                "当地勝率": decimals[2],
                "当地2連率": decimals[3],
                "モーター2連率": decimals[4],
                "ボート2連率": decimals[5],
                "平均ST": decimals[6] if len(decimals) > 6 else 0,
            }

        except:
            pass

    return result


# =========================================================
# 公式 直前情報
# =========================================================

@st.cache_data(ttl=120)
def official_before(sno, rno, td):

    url = (
        "https://www.boatrace.jp/owpc/pc/race/beforeinfo"
        f"?rno={rno}"
        f"&jcd={int(sno):02d}"
        f"&hd={td:%Y%m%d}"
    )

    try:
        html = req(url)
    except:
        return {}

    soup = BeautifulSoup(html, "html.parser")
    result = {}

    for tr in soup.find_all("tr"):

        cells = [
            x.get_text(" ", strip=True)
            for x in tr.find_all(["th", "td"])
        ]

        if not cells:
            continue

        lane = None

        for x in cells[:3]:
            if re.fullmatch(r"[1-6]", x):
                lane = int(x)
                break

        if lane is None:
            continue

        text = " ".join(cells)

        nums = re.findall(
            r"\d+\.\d+",
            text
        )

        exhibition = 0

        for x in nums:
            f = float(x)

            # 展示タイム
            if 6.0 <= f <= 8.0:
                exhibition = f
                break

        st_value = 0

        for x in nums:
            f = float(x)

            if 0 < f <= 0.60:
                st_value = f
                break

        result[lane] = {
            "展示タイム": exhibition,
            "展示ST": st_value,
            "展示進入": lane
        }

    return result


# =========================================================
# 選手データ作成
# =========================================================

def make_rows(race, sno, rno, td):

    racers = data.racers(
        race.get("racers")
        or race.get("entries")
        or race.get("entry")
        or []
    )

    official = official_racelist(
        sno,
        rno,
        td
    )

    before = official_before(
        sno,
        rno,
        td
    )

    rows = []

    for i, r in enumerate(racers):

        lane = data.val(
            r,
            [
                "entryNumber",
                "boatNumber",
                "courseNumber",
                "lane",
                "枠"
            ],
            i + 1
        )

        try:
            lane = int(float(lane))
        except:
            lane = i + 1

        stats = official.get(
            lane,
            {}
        )

        pre = before.get(
            lane,
            {}
        )

        name = data.val(
            r,
            [
                "racerName",
                "racer_name",
                "playerName",
                "player_name",
                "name",
                "選手名"
            ],
            "-"
        )

        number = data.val(
            r,
            [
                "racerNumber",
                "racer_number",
                "playerNumber",
                "player_number",
                "number",
                "選手番号"
            ],
            0
        )

        grade = data.val(
            r,
            [
                "grade",
                "racerClass",
                "racer_class",
                "class",
                "級別"
            ],
            "-"
        )

        rows.append({
            "枠": lane,
            "展示進入": pre.get(
                "展示進入",
                lane
            ),
            "選手名": name,
            "選手番号": number,
            "級別": grade,

            "全国勝率": stats.get(
                "全国勝率",
                0
            ),

            "全国2連率": stats.get(
                "全国2連率",
                0
            ),

            "当地勝率": stats.get(
                "当地勝率",
                0
            ),

            "モーター2連率": stats.get(
                "モーター2連率",
                0
            ),

            "平均ST": stats.get(
                "平均ST",
                0
            ),

            "展示ST": pre.get(
                "展示ST",
                0
            ),

            "展示タイム": pre.get(
                "展示タイム",
                0
            ),

            "場": sno
        })

    return rows


# =========================================================
# 入力
# =========================================================

c1, c2, c3 = st.columns(3)

with c1:
    td = st.date_input(
        "開催日",
        date.today()
    )

with c2:
    sno = st.selectbox(
        "競艇場",
        list(STADIUMS.keys()),
        format_func=lambda x: STADIUMS[x]
    )

with c3:
    rno = st.selectbox(
        "レース",
        range(1, 13),
        format_func=lambda x: f"{x}R"
    )


# =========================================================
# AI予想
# =========================================================

if st.button(
    "🤖 AI予想を実行",
    type="primary",
    use_container_width=True
):

    with st.spinner("データ取得・AI分析中..."):

        try:
            raw = data.get_data(td)

            race = data.get_race(
                raw,
                sno,
                rno
            )

            if race is None:
                st.error(
                    "レースデータが取得できませんでした。"
                )
                st.stop()

            rows = make_rows(
                race,
                sno,
                rno,
                td
            )

            df = pd.DataFrame(rows)

            if df.empty:
                st.error(
                    "選手データが取得できませんでした。"
                )
                st.stop()

            # AI用スコア
            df["学習AI"] = df.apply(
                score,
                axis=1
            )

            history = pd.DataFrame(
                data.history14(td)
            )

            result, boat_probs = tri_ai(
                df,
                history
            )

        except Exception as e:
            st.error(
                f"エラー：{e}"
            )
            st.stop()


    # =====================================================
    # レース
    # =====================================================

    st.subheader(
        f"🚤 {STADIUMS[sno]} {rno}R"
    )


    # =====================================================
    # 選手データ
    # =====================================================

    st.subheader("📋 選手データ")

    show = df[
        [
            "枠",
            "選手名",
            "選手番号",
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
    ].copy()

    st.dataframe(
        show,
        use_container_width=True,
        hide_index=True
    )


    # =====================================================
    # 3連単
    # =====================================================

    st.subheader("🏆 AI 3連単予想")

    if result is not None and not result.empty:

        show_result = result.copy()

        for col in [
            "AI確率",
            "信頼度",
            "1着AI",
            "2着AI",
            "3着AI"
        ]:
            if col in show_result:
                show_result[col] = pd.to_numeric(
                    show_result[col],
                    errors="coerce"
                ).round(2)

        st.dataframe(
            show_result.head(10),
            use_container_width=True,
            hide_index=True
        )

        x = result.iloc[0]

        st.success(
            f"🥇 本命：{x['3連単']} "
            f"AI確率 {float(x['AI確率']):.2f}%"
        )

        if len(result) >= 2:
            x = result.iloc[1]
            st.info(
                f"🥈 2番手：{x['3連単']} "
                f"{float(x['AI確率']):.2f}%"
            )

        if len(result) >= 3:
            x = result.iloc[2]
            st.info(
                f"🥉 3番手：{x['3連単']} "
                f"{float(x['AI確率']):.2f}%"
            )


    # =====================================================
    # 各着順AI
    # =====================================================

    st.subheader("🏆 各着順のAI評価")

    place_rows = []

    for lane in sorted(
        df["枠"].unique()
    ):

        lane = int(lane)

        first = result[
            result["3連単"].astype(str)
            .str.startswith(f"{lane}-")
        ]["1着AI"]

        second = result[
            result["3連単"].astype(str)
            .str.contains(f"-{lane}-")
        ]["2着AI"]

        third = result[
            result["3連単"].astype(str)
            .str.endswith(f"-{lane}")
        ]["3着AI"]

        racer = df[
            df["枠"] == lane
        ].iloc[0]

        place_rows.append({
            "枠": lane,
            "選手名": racer["選手名"],
            "選手番号": racer["選手番号"],
            "1着AI": round(
                first.max()
                if not first.empty
                else 0,
                2
            ),
            "2着AI": round(
                second.max()
                if not second.empty
                else 0,
                2
            ),
            "3着AI": round(
                third.max()
                if not third.empty
                else 0,
                2
            )
        })

    st.dataframe(
        pd.DataFrame(place_rows),
        use_container_width=True,
        hide_index=True
        )
