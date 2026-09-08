import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import itertools
import re

# ページ設定
st.set_page_config(page_title="やっちゃんの競艇AI予想ツール", page_icon="🚤", layout="centered")

# --- スマホ表示最適化（見切れ防止） ---
st.markdown("""
    <style>
    h1 {
        font-size: 1.6rem !important;
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
        white-space: normal !important;
        line-height: 1.4 !important;
    }
    .stButton>button {
        white-space: normal !important;
        height: auto !important;
        padding-top: 10px !important;
        padding-bottom: 10px !important;
    }
    </style>
""", unsafe_allow_html=True)

# タイトル表示
st.title("🚤 やっちゃんの競艇AI予想ツール")
st.caption("会場補正・風向風速・展示タイム・勝率を統合解析")

st.divider()

VENUE_CODES = {
    "桐生": "01", "戸田": "02", "江戸川": "03", "平和島": "04", "多摩川": "05", "浜名湖": "06",
    "蒲郡": "07", "常滑": "08", "津": "09", "三国": "10", "びわこ": "11", "住之江": "12",
    "尼崎": "13", "鳴門": "14", "丸亀": "15", "児島": "16", "宮島": "17", "徳山": "18",
    "下関": "19", "若松": "20", "芦屋": "21", "福岡": "22", "唐津": "23", "大村": "24"
}

# 会場別イン強さ補正 (1号艇の加算/減算ポイント)
VENUE_IN_CORRECTION = {
    "大村": 15, "徳山": 15, "芦屋": 12, "下関": 10, "住之江": 8, "尼崎": 8,
    "津": 5, "丸亀": 5, "若松": 5, "唐津": 5, "蒲郡": 0, "常滑": 0,
    "宮島": 0, "児島": 0, "三国": -3, "びわこ": -5, "鳴門": -5,
    "多摩川": -5, "浜名湖": -5, "桐生": -5, "江戸川": -10, "平和島": -10, "戸田": -12
}

# --- 1. 出走表データ取得 ---
def get_detailed_racers(jcd, rno, date_str):
    url = f"https://www.boatrace.jp/owpc/pc/race/racelist?rno={rno}&jcd={jcd}&hd={date_str}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200: return None
        soup = BeautifulSoup(res.text, "html.parser")
        tbodies = soup.find_all("tbody")
        
        racers = []
        for tbody in tbodies:
            text = tbody.get_text(separator=" ", strip=True)
            words = text.split()
            rank = None
            for word in words:
                if word in ["A1", "A2", "B1", "B2"]:
                    rank = word
                    break
            if not rank: continue
                
            name_el = tbody.find("div", class_="is-fs18") or tbody.find("span", class_="is-fs18")
            name = name_el.get_text(strip=True) if name_el else "不明"
            
            floats = re.findall(r"\d+\.\d+", text)
            national_win_rate = float(floats[0]) if len(floats) >= 1 else 5.00
            motor_2ren = float(floats[2]) if len(floats) >= 3 else 30.00
            
            racers.append({
                "枠": len(racers) + 1,
                "選手名": name,
                "級別": rank,
                "全国勝率": national_win_rate,
                "モーター2連率(%)": motor_2ren
            })
            if len(racers) == 6: break
                
        return pd.DataFrame(racers) if len(racers) == 6 else None
    except Exception:
        return None

# --- 2. 直前情報（風速・風向・展示タイム）取得 ---
def get_before_info(jcd, rno, date_str):
    url = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={rno}&jcd={jcd}&hd={date_str}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    info = {"wind_speed": 0, "wind_dir": "無風", "tenji": [6.80]*6}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200: return info
        soup = BeautifulSoup(res.text, "html.parser")
        
        # 風速・風向
        weather_section = soup.find("div", class_="weather1")
        if weather_section:
            w_text = weather_section.get_text()
            m_speed = re.search(r"風速\s*(\d+)m", w_text)
            if m_speed:
                info["wind_speed"] = int(m_speed.group(1))
            
            if "追い風" in w_text: info["wind_dir"] = "追い風"
            elif "向かい風" in w_text: info["wind_dir"] = "向かい風"
            elif "左横風" in w_text or "右横風" in w_text: info["wind_dir"] = "横風"
            
        # 展示タイム
        tenji_list = []
        td_tenji = soup.find_all("td", class_="is-fs14")
        for td in td_tenji:
            val = td.get_text(strip=True)
            if re.match(r"^\d\.\d{2}$", val):
                tenji_list.append(float(val))
        if len(tenji_list) == 6:
            info["tenji"] = tenji_list
            
        return info
    except Exception:
        return info

# --- 3. 風・展示データを取り入れた高度AI分析スコア計算 ---
def calculate_wind_and_tenji_predictions(df, venue, weather_info, investment):
    # 基本コーススコア
    course_base = {1: 45, 2: 25, 3: 20, 4: 15, 5: 10, 6: 5}
    
    # 1号艇に会場ごとの強さ補正を追加
    venue_adj = VENUE_IN_CORRECTION.get(venue, 0)
    course_base[1] += venue_adj
    
    rank_bonus = {"A1": 25, "A2": 15, "B1": 5, "B2": 0}
    
    # 風によるコース影響の補正値
    w_speed = weather_info["wind_speed"]
    w_dir = weather_info["wind_dir"]
    wind_course_adj = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
    
    if w_speed >= 3:
        if w_dir == "追い風":
            # 追い風：1号艇が流れやすく、2・3号艇の差し/まくり差しが効く
            wind_course_adj[1] -= (w_speed * 1.5)
            wind_course_adj[2] += (w_speed * 2.0)
            wind_course_adj[3] += (w_speed * 1.5)
        elif w_dir == "向かい風":
            # 向かい風：インがへこみやすく、3・4号艇のダッシュまくりが効く
            wind_course_adj[1] -= (w_speed * 2.0)
            wind_course_adj[3] += (w_speed * 1.5)
            wind_course_adj[4] += (w_speed * 2.5)

    # 展示タイムの最速（一番時計）判定
    min_tenji = min(weather_info["tenji"])
    
    scores = {}
    for idx, row in df.iterrows():
        w = int(row["枠"])
        rank = row["級別"]
        win_rate = row["全国勝率"]
        motor = row["モーター2連率(%)"]
        t_time = weather_info["tenji"][idx] if idx < len(weather_info["tenji"]) else 6.80
        
        # 展示タイム補正 (一番時計なら +10点、トップと差がないほど加点)
        tenji_score = max(0, (6.90 - t_time) * 30)
        if t_time == min_tenji:
            tenji_score += 10

        total = (course_base.get(w, 5) + wind_course_adj.get(w, 0) + 
                 rank_bonus.get(rank, 0) + (win_rate * 5) + (motor * 0.4) + tenji_score)
        scores[w] = total
        
    boats = [1, 2, 3, 4, 5, 6]
    combos = list(itertools.permutations(boats, 3))
    
    combo_scores = []
    for c in combos:
        eval_score = (scores[c[0]] * 1.6) + (scores[c[1]] * 1.0) + (scores[c[2]] * 0.6)
        combo_scores.append((c, eval_score))
        
    combo_scores.sort(key=lambda x: x[1], reverse=True)
    
    top_combos = [combo_scores[0], combo_scores[1], combo_scores[2], combo_scores[6]]
    labels = ["本命 🔥", "本命 🔥", "対抗 ⚔️", "中穴 ⚡"]
    ratios = [0.4, 0.3, 0.2, 0.1]
    
    bet_list = []
    for i in range(4):
        c, _ = top_combos[i]
        buy_str = f"{c[0]} - {c[1]} - {c[2]}"
        amount = int(investment * ratios[i] // 100 * 100)
        stars = "★★★★★" if i == 0 else ("★★★★☆" if i == 1 else "★★★☆☆")
        
        bet_list.append({
            "区分": labels[i],
            "買い目（3連単）": buy_str,
            "期待度": stars,
            "推奨金額": f"{amount:,} 円"
        })
        
    return pd.DataFrame(bet_list)

# --- 条件設定UI ---
st.subheader("⚙️ レース条件設定")

JST = timezone(timedelta(hours=+9), 'JST')
now_jst = datetime.now(JST)
today_str = now_jst.strftime("%Y%m%d")
date_display = now_jst.strftime("%m/%d")

st.info(f"📅 本日の日付: {date_display} (日本時間)")

col1, col2 = st.columns(2)
with col1:
    venue = st.selectbox("開催会場", list(VENUE_CODES.keys()), index=9)
with col2:
    race_num = st.selectbox("レース", [f"{i}R" for i in range(1, 13)])

investment = st.number_input("投資合計金額 (円)", min_value=1000, value=5000, step=1000)

st.divider()

# --- 予想実行 ---
if st.button("🤖 風速・水面・気象を考慮してAI予想実行", type="primary", use_container_width=True):
    jcd = VENUE_CODES[venue]
    rno = race_num.replace("R", "")
    
    with st.spinner("出走表・水面気象・展示タイムを分析中..."):
        df_racers = get_detailed_racers(jcd, rno, today_str)
        weather_info = get_before_info(jcd, rno, today_str)
    
    if df_racers is None or df_racers.empty:
        st.warning(f"⚠️ {date_display} の {venue} {race_num} の解析に失敗しました。開催状況またはレース番号をご確認ください。")
    else:
        st.success(f"【{venue} {race_num}】のデータ取得＆直前風速AI分析が完了しました！")
        
        # 気象・展示データの表示パネル
        w_speed = weather_info["wind_speed"]
        w_dir = weather_info["wind_dir"]
        st.info(f"🌀 **現地気象**: {w_dir} {w_speed}m / **会場特性**: {venue} (1枠補正: {VENUE_IN_CORRECTION.get(venue, 0):+}pt)")
        
        df_display = df_racers.copy()
        df_display["枠"] = df_display["枠"].apply(lambda x: f"{x}号艇")
        df_display["展示タイム"] = weather_info["tenji"]
        
        st.subheader("📋 出走表 & 展示タイムデータ")
        st.dataframe(df_display, hide_index=True, use_container_width=True)

        st.divider()

        df_bets = calculate_wind_and_tenji_predictions(df_racers, venue, weather_info, investment)

        st.subheader("🎯 直前風向・気象考慮のAI推奨買い目")
        st.table(df_bets)
