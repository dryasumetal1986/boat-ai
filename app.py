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


def val(d, keys, default=0):
    if not isinstance(d, dict):
        return default
    for k in keys:
        if d.get(k) is not None:
            return d[k]
    return default


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


@st.cache_data(ttl=120)
def official_preview(sno, rno, td):
    try:
        url = (
            "https://www.boatrace.jp/owpc/pc/race/beforeinfo"
            f"?rno={rno}&jcd={int(sno):02d}&hd={td:%Y%m%d}"
        )

        r = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15
        )

        soup = BeautifulSoup(r.text, "html.parser")
        out = {}

        for tr in soup.find_all("tr"):
            cells = [
                x.get_text(" ", strip=True)
                for x in tr.find_all(["th", "td"])
            ]

            if not cells:
                continue

            lane = next(
                (
                    int(x) for x in cells
                    if re.fullmatch(r"[1-6]", x)
                ),
                None
            )

            if lane is None:
                continue

            text = " ".join(cells)

            times = re.findall(
                r"\d\.\d{2}",
                text
            )

            exhibition = next(
                (
                    float(x) for x in times
                    if 6.0 <= float(x) <= 8.0
                ),
                0
            )

            sts = re.findall(
                r"(?:F|L)?(\d\.\d{2})",
                text
            )

            st_value = next(
                (
                    float(x) for x in sts
                    if 0 <= float(x) <= 0.6
                ),
                0
            )

            out[lane] = {
                "展示タイム": exhibition,
                "展示ST": st_value,
                "展示進入": lane
            }

        return out

    except:
        return {}


def build_rows(race, sno, rno, td):

    racers = data.racers(
        race.get("racers")
        or race.get("entries")
        or race.get("entry")
        or []
    )

    preview = data.racers(
        race.get("preview")
        or race.get("exhibition")
        or []
    )

    pmap = {}

    for p in preview:
        no = val(
            p,
            ["racerNumber","playerNumber","number","選手番号"],
            None
        )
        try:
            pmap[int(float(no))] = p
        except:
            pass

    official = official_preview(
        sno,
        rno,
        td
    )

    rows = []

    for i, r in enumerate(racers):

        lane = val(
            r,
            ["entryNumber","boatNumber","courseNumber","枠","lane"],
            i + 1
        )

        try:
            lane = int(float(lane))
        except:
            lane = i + 1

        no = val(
            r,
            ["racerNumber","playerNumber","number","選手番号"],
            0
        )

        try:
            no = int(float(no))
        except:
            no = 0

        p = pmap.get(no, {})
        op = official.get(lane, {})

        def get(keys, default=0):
            return val(r, keys, default)

        def getp(keys, default=None):
            x = val(p, keys, default)
            return x if x is not None else default

        exhibition_time = getp(
            ["exhibitionTime","exhibition_time","exTime","time","展示タイム"],
            op.get("展示タイム", 0)
        )

        exhibition_st = getp(
            ["startTiming","exhibitionST","exhibitionSt","st","展示ST"],
            op.get("展示ST", 0)
        )

        exhibition_course = getp(
            ["courseNumber","entryNumber","course","展示進入"],
            op.get("展示進入", lane)
        )

        rows.append({
            "枠": lane,
            "展示進入": num(exhibition_course, lane),
            "選手名": get(
                ["racerName","playerName","name","選手名"],
                "-"
            ),
            "選手番号": no,
            "級別": get(
                ["grade","racerClass","class","級別"],
                "-"
            ),
            "全国勝率": num(get([
                "nationwideWinRate",
                "nationalWinRate",
                "winRate",
                "全国勝率"
            ])),
            "全国2連率": num(get([
                "nationwide2Rate",
                "national2Rate",
                "secondRate",
                "全国2連率"
            ])),
            "当地勝率": num(get([
                "localWinRate",
                "localRate",
                "placeWinRate",
                "当地勝率"
            ])),
            "モーター2連率": num(get([
                "motor2Rate",
                "motorSecondRate",
                "モーター2連率"
            ])),
            "平均ST": num(get([
                "averageST",
                "avgST",
                "averageStartTiming",
                "平均ST"
            ])),
            "展示ST": num(exhibition_st),
            "展示タイム": num(exhibition_time),
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
        list(STADIUMS),
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

    with st.spinner("AI分析中..."):

        try:
            all_data = data.get_data(td)
            race = data.get_race(
                all_data,
                sno,
                rno
            )

            if race is None:
                st.error("レースデータがありません。")
                st.stop()

            rows = build_rows(
                race,
                sno,
                rno,
                td
            )

            df = pd.DataFrame(rows)

            if df.empty:
                st.error("選手データが取得できませんでした。")
                st.stop()

            df["学習AI"] = df.apply(
                score,
                axis=1
            )

            history = pd.DataFrame(
                data.history14(td)
            )

            result = tri_ai(
                df,
                history
            )

        except Exception as e:
            st.error(
                f"AI予想でエラーが発生しました。\n\n{e}"
            )
            st.stop()


    # =====================================================
    # レース情報
    # =====================================================

    st.subheader(
        f"🚤 {STADIUMS[sno]} {rno}R"
    )


    # =====================================================
    # データ
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
        show.sort_values(
            "学習AI",
            ascending=False
        ),
        use_container_width=True,
        hide_index=True
    )


    # =====================================================
    # 3連単予想
    # =====================================================

    st.subheader("🏆 AI 3連単予想")

    if result is not None and not result.empty:

        display = result.copy()

        for col in [
            "AI確率",
            "信頼度",
            "1着AI",
            "2着AI",
            "3着AI"
        ]:
            if col in display:
                display[col] = pd.to_numeric(
                    display[col],
                    errors="coerce"
                ).round(2)

        st.dataframe(
            display.head(10),
            use_container_width=True,
            hide_index=True
        )

        best = result.iloc[0]

        st.success(
            f"🥇 本命：{best['3連単']}　"
            f"AI確率 {float(best['AI確率']):.2f}%"
        )

        if len(result) >= 2:
            x = result.iloc[1]
            st.info(
                f"🥈 2番手：{x['3連単']}　"
                f"{float(x['AI確率']):.2f}%"
            )

        if len(result) >= 3:
            x = result.iloc[2]
            st.info(
                f"🥉 3番手：{x['3連単']}　"
                f"{float(x['AI確率']):.2f}%"
            )


    # =====================================================
    # 各着順AI
    # =====================================================

    st.subheader("🏆 各着順のAI評価")

    place_rows = []

    for lane in sorted(df["枠"].unique()):

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
                first.max() if not first.empty else 0,
                2
            ),
            "2着AI": round(
                second.max() if not second.empty else 0,
                2
            ),
            "3着AI": round(
                third.max() if not third.empty else 0,
                2
            )
        })

    st.dataframe(
        pd.DataFrame(place_rows),
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# 過去レース検証
# =========================================================

st.divider()

st.subheader("📊 過去レース検証")

if st.button(
    "過去14日を検証",
    use_container_width=True
):

    with st.spinner(
        "過去データを取得中..."
    ):

        try:
            backtest = data.backtest_races(
                td,
                14
            )

            if backtest:
                st.dataframe(
                    pd.DataFrame(backtest),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.warning(
                    "過去レースのデータがありません。"
                )

        except Exception as e:

            st.error(
                f"検証エラー：{e}"
                )
