import streamlit as st
import requests
import pandas as pd
from datetime import date

st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO",
    page_icon="🚤",
    layout="wide",
)

API_BASE = "https://boatraceopenapi.github.io/api/v1"

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
    24: "大村",
}


def get_number(value, default=0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


@st.cache_data(ttl=180)
def get_data(target_date):
    ymd = target_date.strftime("%Y%m%d")
    year = target_date.strftime("%Y")
    url = f"{API_BASE}/{year}/{ymd}.json"

    response = requests.get(
        url,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0"},
    )

    response.raise_for_status()
    return response.json()


def get_race(data, stadium_number, race_number):
    programs = data.get("programs", {})
    stadiums = programs.get("stadiums", {})

    stadium = stadiums.get(str(stadium_number))

    if not stadium:
        return None

    races = stadium.get("races", {})
    return races.get(str(race_number))


def make_table(race):
    racers = race.get("racers", {})
    preview = race.get("preview", {}).get("racers", {})

    rows = []

    for lane in range(1, 7):
        racer = racers.get(str(lane), {})
        info = preview.get(str(lane), {})

        if not racer:
            continue

        rows.append(
            {
                "枠": lane,
                "選手名": racer.get("name", "不明"),
                "級別": racer.get("rank_number", ""),
                "全国勝率": get_number(
                    racer.get("national_win_rate")
                ),
                "全国2連率": get_number(
                    racer.get("national_top_2_percent")
                ),
                "当地勝率": get_number(
                    racer.get("local_win_rate")
                ),
                "モーター2連率": get_number(
                    racer.get("motor_top_2_percent")
                ),
                "平均ST": get_number(
                    racer.get("average_start_timing")
                ),
                "展示タイム": get_number(
                    info.get("exhibition_time")
                ),
            }
        )

    return pd.DataFrame(rows)


def calculate_score(row):
    score = 0.0

    score += row["全国勝率"] * 10
    score += row["全国2連率"] * 0.25
    score += row["当地勝率"] * 5
    score += row["モーター2連率"] * 0.12

    st_time = row["平均ST"]

    if st_time > 0:
        if st_time <= 0.12:
            score += 12
        elif st_time <= 0.15:
            score += 8
        elif st_time <= 0.18:
            score += 4
        elif st_time >= 0.22:
            score -= 4

    lane = int(row["枠"])

    lane_bonus = {
        1: 20,
        2: 8,
        3: 6,
        4: 7,
        5: 2,
        6: -2,
    }

    score += lane_bonus.get(lane, 0)

    return score


st.title("🚤 やっちゃんの競艇AI予想 PRO")

st.write(
    "全国24場対応の競艇予想支援アプリです。"
)

st.warning(
    "⚠️ 非公式APIを利用しています。"
    "最新情報は必ず公式BOATRACEで確認してください。"
)


st.subheader("📅 レースを選択")

col1, col2, col3 = st.columns(3)

with col1:
    target_date = st.date_input(
        "開催日",
        value=date.today(),
        min_value=date(2026, 1, 1),
    )

with col2:
    stadium_name = st.selectbox(
        "競艇場",
        list(STADIUMS.values()),
    )

with col3:
    race_number = st.selectbox(
        "レース",
        list(range(1, 13)),
        format_func=lambda x: f"{x}R",
    )


stadium_number = 1

for number, name in STADIUMS.items():
    if name == stadium_name:
        stadium_number = number
        break


if st.button(
    "🚀 AI予想を実行",
    type="primary",
    use_container_width=True,
):

    with st.spinner("🚤 データを取得しています..."):

        try:
            data = get_data(target_date)

        except Exception as e:
            st.error(
                "データを取得できませんでした。"
            )

            st.info(
                "開催前、データ更新中、またはAPI側の"
                "一時的な問題の可能性があります。"
            )

            st.stop()

    race = get_race(
        data,
        stadium_number,
        race_number,
    )

    if race is None:
        st.error(
            "このレースのデータが見つかりません。"
        )

        st.info(
            "開催前またはAPI更新前の可能性があります。"
        )

        st.stop()

    df = make_table(race)

    if df.empty:
        st.error("出走表が取得できませんでした。")
        st.stop()

    preview = race.get("preview", {})

    wind_speed = preview.get("wind_speed", 0)
    wave_height = preview.get("wave_height", 0)
    wind_direction = preview.get(
        "wind_direction",
        "不明",
    )

    df["AIスコア"] = df.apply(
        calculate_score,
        axis=1,
    )

    max_score = df["AIスコア"].max()

    if max_score > 0:
        df["AI1着評価"] = (
            df["AIスコア"] / max_score * 100
        ).round(1)
    else:
        df["AI1着評価"] = 0.0

    df = df.sort_values(
        "AI1着評価",
        ascending=False,
    ).reset_index(drop=True)

    st.subheader(
        f"🏁 {stadium_name} {race_number}R"
    )

    info1, info2, info3 = st.columns(3)

    with info1:
        st.metric(
            "風速",
            f"{wind_speed} m",
        )

    with info2:
        st.metric(
            "風向",
            str(wind_direction),
        )

    with info3:
        st.metric(
            "波高",
            f"{wave_height} cm",
        )

    st.subheader("📋 AI評価")

    show_columns = [
        "枠",
        "選手名",
        "級別",
        "全国勝率",
        "全国2連率",
        "当地勝率",
        "モーター2連率",
        "平均ST",
        "展示タイム",
        "AI1着評価",
    ]

    st.dataframe(
        df[show_columns],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("🏆 AI注目選手")

    top = df.iloc[0]

    st.success(
        f"本命：{int(top['枠'])}号艇 "
        f"{top['選手名']}　"
        f"AI評価 {top['AI1着評価']:.1f}"
    )

    st.write("### 🥈 対抗")

    if len(df) >= 2:
        second = df.iloc[1]

        st.info(
            f"{int(second['枠'])}号艇 "
            f"{second['選手名']}　"
            f"AI評価 {second['AI1着評価']:.1f}"
        )

    st.write("### 🥉 穴候補")

    if len(df) >= 3:
        third = df.iloc[2]

        st.info(
            f"{int(third['枠'])}号艇 "
            f"{third['選手名']}　"
            f"AI評価 {third['AI1着評価']:.1f}"
        )

    st.subheader("🎯 推奨3連単")

    if len(df) >= 3:

        first = int(df.iloc[0]["枠"])
        second = int(df.iloc[1]["枠"])
        third = int(df.iloc[2]["枠"])

        st.write(
            f"**本線：{first}-{second}-{third}**"
        )

        st.write(
            f"押さえ：{first}-{third}-{second}"
        )

        st.write(
            f"穴：{second}-{first}-{third}"
        )

    st.divider()

    st.caption(
        "AI評価は独自計算による予想値です。"
        "的中や利益を保証するものではありません。"
    )

else:

    st.info(
        "競艇場とレースを選択して、"
        "「🚀 AI予想を実行」を押してください。"
    )

    st.write("### 対応競艇場")

    st.write(
        "・全国24場"
    )

    st.write(
        "・1R〜12R"
    )

    st.write(
        "・全国勝率"
    )

    st.write(
        "・当地勝率"
    )

    st.write(
        "・モーター成績"
    )

    st.write(
        "・平均ST"
    )

    st.write(
        "・展示タイム"
    )

    st.write(
        "・風速、風向、波高"
)
