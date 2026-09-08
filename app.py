import streamlit as st
import requests
import pandas as pd
from datetime import date, timedelta

st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO",
    page_icon="🚤",
    layout="wide"
)

API = "https://boatraceopenapi.github.io/api/v1"

STADIUMS = {
    1: "桐生", 2: "戸田", 3: "江戸川", 4: "平和島", 5: "多摩川",
    6: "浜名湖", 7: "蒲郡", 8: "常滑", 9: "津", 10: "三国",
    11: "びわこ", 12: "住之江", 13: "尼崎", 14: "鳴門", 15: "丸亀",
    16: "児島", 17: "宮島", 18: "徳山", 19: "下関", 20: "若松",
    21: "芦屋", 22: "福岡", 23: "唐津", 24: "大村"
}

# 競艇場ごとの水面特徴データベース
STADIUM_FEATURES = {
    "大村": {"in_rate": "極高", "water": "海水", "bonus_1": 15, "desc": "全国屈指のイン最強水面。1号艇の信頼度が非常に高い。"},
    "徳山": {"in_rate": "極高", "water": "海水", "bonus_1": 14, "desc": "イン強固。風の影響が少ない日は1号艇軸で安定。"},
    "芦屋": {"in_rate": "極高", "water": "淡水", "bonus_1": 14, "desc": "企画レースも多くイン利が突出。静水面。"},
    "下関": {"in_rate": "高", "water": "海水", "bonus_1": 12, "desc": "ナイター開催。海風の影響で満潮時は差しも決まる。"},
    "住之江": {"in_rate": "高", "water": "淡水", "bonus_1": 11, "desc": "競艇の聖地。工業用水で固く、インが手堅い。"},
    "戸田": {"in_rate": "極低", "water": "淡水", "bonus_1": -5, "desc": "全国一インが弱い狭小水面。3・4コースのまくり注意。"},
    "江戸川": {"in_rate": "低", "water": "汽水", "bonus_1": -3, "desc": "日本一の難水面。河川の波・流木・潮で波乱必至。"},
    "平和島": {"in_rate": "低", "water": "海水", "bonus_1": -2, "desc": "イン弱め。風と波の影響を受けやすく長穴が出やすい。"},
}

# デフォルト（標準水面）
DEFAULT_FEATURE = {"in_rate": "中", "water": "標準", "bonus_1": 5, "desc": "標準的な水面特性。"}

TECHNIQUES = {
    1: "逃げ", 2: "差し", 3: "まくり", 4: "まくり差し", 5: "抜き", 6: "恵まれ"
}

def num(x):
    try:
        return float(x)
    except:
        return 0

@st.cache_data(ttl=180)
def get_data(d):
    ymd = d.strftime("%Y%m%d")
    year = d.strftime("%Y")
    url = f"{API}/{year}/{ymd}.json"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.json()

def get_race(data, stadium, race_no):
    stadiums = data.get("programs", {}).get("stadiums", {})
    s = stadiums.get(str(stadium))
    if not s:
        return None
    races = s.get("races", {})
    return races.get(str(race_no))

def get_course_stats(target_date):
    stats = {}
    for day in range(1, 15):
        d = target_date - timedelta(days=day)
        if d < date(2026, 1, 1):
            continue
        try:
            data = get_data(d)
        except:
            continue
        stadiums = data.get("programs", {}).get("stadiums", {})
        for stadium in stadiums.values():
            races = stadium.get("races", {})
            for race in races.values():
                result = race.get("result", {})
                result_racers = result.get("racers", {})
                if not result_racers:
                    continue
                for racer in result_racers.values():
                    player_number = str(racer.get("number", ""))
                    course = racer.get("course_number")
                    place = racer.get("place_number")
                    if not player_number:
                        continue
                    try:
                        course = int(course)
                    except:
                        continue
                    if course < 1 or course > 6:
                        continue
                    key = (player_number, course)
                    if key not in stats:
                        stats[key] = {"出走": 0, "1着": 0}
                    stats[key]["出走"] += 1
                    try:
                        place = int(place)
                    except:
                        place = 0
                    if place == 1:
                        stats[key]["1着"] += 1
    return stats

def get_technique_stats(target_date):
    stats = {}
    for day in range(1, 15):
        d = target_date - timedelta(days=day)
        if d < date(2026, 1, 1):
            continue
        try:
            data = get_data(d)
        except:
            continue
        stadiums = data.get("programs", {}).get("stadiums", {})
        for stadium in stadiums.values():
            races = stadium.get("races", {})
            for race in races.values():
                result = race.get("result", {})
                racers = result.get("racers", {})
                if not racers:
                    continue
                for racer in racers.values():
                    player_number = str(racer.get("number", ""))
                    technique = racer.get("technique_number")
                    if not player_number:
                        continue
                    try:
                        technique = int(technique)
                    except:
                        continue
                    if technique < 1 or technique > 6:
                        continue
                    key = (player_number, technique)
                    if key not in stats:
                        stats[key] = 0
                    stats[key] += 1
    return stats

def make_table(race):
    racers = race.get("racers", {})
    preview = race.get("preview", {}).get("racers", {})
    rows = []
    for lane in range(1, 7):
        r = racers.get(str(lane), {})
        p = preview.get(str(lane), {})
        if not r:
            continue
        rows.append({
            "枠": lane,
            "選手名": r.get("name", "不明"),
            "選手番号": str(r.get("number", "")),
            "級別": r.get("rank_number", ""),
            "全国勝率": num(r.get("national_win_rate")),
            "全国2連率": num(r.get("national_top_2_percent")),
            "当地勝率": num(r.get("local_win_rate")),
            "モーター2連率": num(r.get("motor_top_2_percent")),
            "平均ST": num(r.get("average_start_timing")),
            "展示タイム": num(p.get("exhibition_time"))
        })
    return pd.DataFrame(rows)

def add_course_stats(df, stats):
    rates, starts = [], []
    for _, row in df.iterrows():
        player, course = str(row["選手番号"]), int(row["枠"])
        item = stats.get((player, course), {})
        start_count = item.get("出走", 0)
        win_count = item.get("1着", 0)
        rate = (win_count / start_count * 100) if start_count > 0 else 0
        rates.append(round(rate, 1))
        starts.append(start_count)
    df["コース1着率"] = rates
    df["コース出走数"] = starts
    return df

def add_technique_stats(df, stats):
    technique_names, technique_counts = [], []
    for _, row in df.iterrows():
        player = str(row["選手番号"])
        best_name, best_count = "なし", 0
        for number, name in TECHNIQUES.items():
            count = stats.get((player, number), 0)
            if count > best_count:
                best_count = count
                best_name = name
        technique_names.append(best_name)
        technique_counts.append(best_count)
    df["得意決まり手"] = technique_names
    df["決まり手回数"] = technique_counts
    return df

def technique_bonus(row):
    lane = int(row["枠"])
    technique = row["得意決まり手"]
    bonus = 0
    if lane == 1 and technique == "逃げ": bonus = 8
    elif lane == 2 and technique == "差し": bonus = 8
    elif lane in [3, 4] and technique in ["まくり", "まくり差し"]: bonus = 7
    elif lane == 5 and technique == "まくり差し": bonus = 5
    elif lane == 6 and technique == "まくり差し": bonus = 4
    return bonus

# 気象（風向き・風速）および会場特性に応じたAIスコア補正
def calculate_score(row, stadium_feat, weather_info):
    s = 0
    s += row["全国勝率"] * 10
    s += row["全国2連率"] * 0.25
    s += row["当地勝率"] * 5
    s += row["モーター2連率"] * 0.12

    st_time = row["平均ST"]
    if st_time > 0:
        if st_time <= 0.12: s += 12
        elif st_time <= 0.15: s += 8
        elif st_time <= 0.18: s += 4
        elif st_time >= 0.22: s -= 4

    lane = int(row["枠"])
    lane_bonus = {1: 20, 2: 8, 3: 6, 4: 7, 5: 2, 6: 0}
    s += lane_bonus.get(lane, 0)

    # 会場固有の1号艇補正
    if lane == 1:
        s += stadium_feat.get("bonus_1", 0)

    # 風・波の環境補正
    wind_speed = weather_info.get("wind_speed", 0)
    wind_dir = weather_info.get("wind_direction", "")

    if wind_speed >= 5:  # 強風時
        if lane in [2, 3, 4]: s += 5  # 波乱（まくり・差し）
    if "追い風" in wind_dir and lane in [1, 2]:
        s += 4  # 追い風はイン・差し有利
    elif "向かい風" in wind_dir and lane in [3, 4, 5]:
        s += 6  # 向かい風はダッシュまくり有利

    course_rate = row["コース1着率"]
    if course_rate >= 50: s += 12
    elif course_rate >= 40: s += 9
    elif course_rate >= 30: s += 6
    elif course_rate >= 20: s += 3
    elif course_rate > 0: s += 1

    s += technique_bonus(row)

    exhibition = row["展示タイム"]
    if exhibition > 0:
        if exhibition <= 6.70: s += 6
        elif exhibition <= 6.75: s += 4
        elif exhibition <= 6.80: s += 2
        elif exhibition >= 6.90: s -= 2

    return s

# --- UI実装 ---
st.title("🚤 やっちゃんの競艇AI予想 PRO")
st.write("【リアルタイム気象データ×会場水面特性×過去データAI解析】")

st.subheader("📅 レースを選択")
c1, c2, c3 = st.columns(3)

with c1:
    target_date = st.date_input("開催日", value=date.today(), min_value=date(2026, 1, 1))
with c2:
    stadium_name = st.selectbox("競艇場", list(STADIUMS.values()))
with c3:
    race_no = st.selectbox("レース", list(range(1, 13)), format_func=lambda x: f"{x}R")

stadium_no = [n for n, name in STADIUMS.items() if name == stadium_name][0]

if st.button("🚀 AI予想を実行", type="primary"):
    try:
        with st.spinner("🚤 レースデータ取得中..."):
            data = get_data(target_date)
    except Exception as e:
        st.error("データ取得に失敗しました")
        st.code(str(e))
        st.stop()

    race = get_race(data, stadium_no, race_no)
    if race is None:
        st.error("このレースのデータがありません")
        st.stop()

    df = make_table(race)
    if df.empty:
        st.error("出走表がありません")
        st.stop()

    # 会場・気象データの抽出
    stadium_feat = STADIUM_FEATURES.get(stadium_name, DEFAULT_FEATURE)
    preview_data = race.get("preview", {})
    weather_info = {
        "wind_speed": num(preview_data.get("wind_speed", 0)),
        "wind_direction": preview_data.get("wind_direction_name", "無風"),
        "wave_height": num(preview_data.get("wave_height", 0)),
        "weather": preview_data.get("weather_name", "不明")
    }

    # 気象・会場特徴パネル表示
    st.info(f"🏟️ **{stadium_name} 特徴**: {stadium_feat['desc']} （イン強度: {stadium_feat['in_rate']} / 水質: {stadium_feat['water']}）")
    w_col1, w_col2, w_col3, w_col4 = st.columns(4)
    w_col1.metric("天候", weather_info["weather"])
    w_col2.metric("風向", weather_info["wind_direction"])
    w_col3.metric("風速", f"{weather_info['wind_speed']} m")
    w_col4.metric("波高", f"{weather_info['wave_height']} cm")

    with st.spinner("📊 過去14日分を分析中..."):
        course_stats = get_course_stats(target_date)
        technique_stats = get_technique_stats(target_date)

    df = add_course_stats(df, course_stats)
    df = add_technique_stats(df, technique_stats)
    df["決まり手補正"] = df.apply(technique_bonus, axis=1)
    
    # 風速・会場特性を反映したAIスコア計算
    df["AIスコア"] = df.apply(lambda row: calculate_score(row, stadium_feat, weather_info), axis=1)

    maximum = df["AIスコア"].max()
    df["AI1着評価"] = (df["AIスコア"] / maximum * 100).round(1) if maximum > 0 else 0
    df = df.sort_values("AI1着評価", ascending=False).reset_index(drop=True)

    st.subheader(f"📋 {stadium_name} {race_no}R AI評価結果")
    columns = [
        "枠", "選手名", "級別", "全国勝率", "当地勝率", "モーター2連率",
        "平均ST", "展示タイム", "コース1着率", "得意決まり手", "決まり手補正", "AI1着評価"
    ]
    st.dataframe(df[columns], use_container_width=True, hide_index=True)

    st.subheader("🏆 AI注目選手")
    top = df.iloc[0]
    st.success(f"本命: **{int(top['枠'])}号艇 {top['選手名']}** (コース1着率 {top['コース1着率']}% / 得意決まり手: {top['得意決まり手']} / AI評価: {top['AI1着評価']})")

    if len(df) >= 2:
        second = df.iloc[1]
        st.info(f"対抗: **{int(second['枠'])}号艇 {second['選手名']}** (得意決まり手: {second['得意決まり手']})")
    if len(df) >= 3:
        third = df.iloc[2]
        st.info(f"穴目: **{int(third['枠'])}号艇 {third['選手名']}** (得意決まり手: {third['得意決まり手']})")

    if len(df) >= 3:
        a, b, c = int(df.iloc[0]["枠"]), int(df.iloc[1]["枠"]), int(df.iloc[2]["枠"])
        st.subheader("🎯 推奨3連単")
        st.write(f"本線: **{a}-{b}-{c}**")
        st.write(f"押さえ: **{a}-{c}-{b}**")
        st.write(f"穴目: **{b}-{a}-{c}**")

    st.divider()
    st.caption("AI評価は会場特性・展示気象データを含む独自計算による予想値です。")
