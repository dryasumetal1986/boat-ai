import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import itertools
import re
import time

# ページ設定
st.set_page_config(page_title="やっちゃんの競艇AI予想", page_icon="🚤", layout="centered")

# --- カスタムCSS ---
st.markdown("""
    <style>
    .stApp {
        background-color: #F2F4F7;
    }
    h1, h2, h3, .stSubheader, p, span {
        color: #111111 !important;
    }
    </style>
""", unsafe_allow_html=True)

# 日付設定
JST = timezone(timedelta(hours=+9), 'JST')
now_jst = datetime.now(JST)
today_str = now_jst.strftime("%Y%m%d")
date_display = now_jst.strftime("%m月%d日")

VENUE_CODES = {
    "桐生": "01", "戸田": "02", "江戸川": "03", "平和島": "04", "多摩川": "05", "浜名湖": "06",
    "蒲郡": "07", "常滑": "08", "津": "09", "三国": "10", "びわこ": "11", "住之江": "12",
    "尼崎": "13", "鳴門": "14", "丸亀": "15", "児島": "16", "宮島": "17", "徳山": "18",
    "下関": "19", "若松": "20", "芦屋": "21", "福岡": "22", "唐津": "23", "大村": "24"
}

VENUE_CHARACTERISTICS = {
    "大村": {"water": "海水", "in_adj": 20, "makuri_adj": -5, "desc": "【海水/超イン最強】満潮時は1号艇独壇場。"},
    "徳山": {"water": "海水", "in_adj": 18, "makuri_adj": -4, "desc": "【海水/イン鉄板】満潮でイン信頼度さらに上昇。"},
    "芦屋": {"in_adj": 15, "water": "淡水", "makuri_adj": -3, "desc": "【淡水/イン圧倒】静水面でイン安定。"},
    "下関": {"water": "海水", "in_adj": 12, "makuri_adj": -2, "desc": "【海水/イン優位】ナイター・海水で安定感抜群。"},
    "住之江": {"water": "淡水", "in_adj": 10, "makuri_adj": -2, "desc": "【淡水/イン強力】硬い水面、イン逃げ主力。"},
    "尼崎": {"water": "淡水", "in_adj": 8, "makuri_adj": 0, "desc": "【淡水/静水面】フラットで実力通りの展開。"},
    "蒲郡": {"water": "淡水", "in_adj": 5, "makuri_adj": 0, "desc": "【淡水/ナイター】夜間の気温・気圧変化注意。"},
    "唐津": {"water": "淡水", "in_adj": 5, "makuri_adj": 0, "desc": "【淡水/広大水面】ピット離れ重要。"},
    "津": {"water": "淡水", "in_adj": 3, "makuri_adj": 2, "desc": "【淡水/風注意】強風時の波乱注意。"},
    "丸亀": {"water": "海水", "in_adj": 3, "makuri_adj": 1, "desc": "【海水/潮影響】満潮でイン有利、干潮でまくり。"},
    "若松": {"water": "海水", "in_adj": 3, "makuri_adj": 1, "desc": "【海水/洞海湾】風と潮の組み合わせ重要。"},
    "常滑": {"water": "海水", "in_adj": 0, "makuri_adj": 2, "desc": "【海水/風影響】風向きでカド一撃。"},
    "宮島": {"water": "海水", "in_adj": 0, "makuri_adj": 3, "desc": "【海水/潮汐激甚】干満差大きく満潮イン・干潮まくり顕著。"},
    "児島": {"water": "海水", "in_adj": 0, "makuri_adj": 2, "desc": "【海水/潮干満】干潮時のダッシュまくり警戒。"},
    "三国": {"water": "淡水", "in_adj": -3, "makuri_adj": 3, "desc": "【淡水/強風注意】風向きでイン流されやすい。"},
    "浜名湖": {"water": "汽水", "in_adj": -5, "makuri_adj": 4, "desc": "【汽水/広大】潮と風でセンターまくり差し決定。"},
    "多摩川": {"water": "淡水", "in_adj": -5, "makuri_adj": 4, "desc": "【淡水/日本一静水面】全速ターン決定、差し有効。"},
    "桐生": {"water": "淡水", "in_adj": -5, "makuri_adj": 5, "desc": "【淡水/高標高】出足鈍りダッシュ旋回頻出。"},
    "びわこ": {"water": "淡水", "in_adj": -8, "makuri_adj": 6, "desc": "【淡水/ウネリ難所】1M狭くイン流されやすい。"},
    "鳴門": {"water": "海水", "in_adj": -8, "makuri_adj": 6, "desc": "【海水/激流】潮と狭い1Mで波乱多発。"},
    "福岡": {"water": "汽水", "in_adj": -10, "makuri_adj": 7, "desc": "【汽水/博多うねり】1M難所、2差し・3まくり差し。"},
    "江戸川": {"water": "海水", "in_adj": -12, "makuri_adj": 8, "desc": "【海水/超難水面】潮流と風のダブルパンチ。"},
    "平和島": {"water": "海水", "in_adj": -12, "makuri_adj": 8, "desc": "【海水/イン難】バック伸び勝負、差し有利。"},
    "戸田": {"water": "淡水", "in_adj": -15, "makuri_adj": 10, "desc": "【淡水/イン弱点No.1】1M超狭くセンターまくり炸裂。"}
}

# --- 出走表データ取得 ---
def get_detailed_racers(jcd, rno, date_str, retries=2):
    url = f"https://www.boatrace.jp/owpc/pc/race/racelist?rno={rno}&jcd={jcd}&hd={date_str}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    for i in range(retries + 1):
        try:
            res = requests.get(url, headers=headers, timeout=8)
            if res.status_code == 200:
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
                    name = name_el.get_text(strip=True) if name_el else "選手名"
                    
                    floats = re.findall(r"\d+\.\d+", text)
                    national_win_rate = float(floats[0]) if len(floats) >= 1 else 5.00
                    local_win_rate = float(floats[1]) if len(floats) >= 2 else national_win_rate
                    motor_2ren = float(floats[2]) if len(floats) >= 3 else 30.00
                    
                    racers.append({
                        "枠": len(racers) + 1,
                        "選手名": name,
                        "級別": rank,
                        "全国勝率": national_win_rate,
                        "当地勝率": local_win_rate,
                        "モーター2連率(%)": motor_2ren
                    })
                    if len(racers) == 6: break
                if len(racers) == 6:
                    return pd.DataFrame(racers)
        except Exception:
            pass
        if i < retries:
            time.sleep(0.3)
    return None

# --- 直前情報＆展示タイム取得 ---
def get_before_info(jcd, rno, date_str, retries=2):
    url = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={rno}&jcd={jcd}&hd={date_str}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    info = {"wind_speed": 0, "wind_dir": "無風", "tenji": [6.80]*6, "tide": "平常"}
    
    for i in range(retries + 1):
        try:
            res = requests.get(url, headers=headers, timeout=8)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                
                weather_section = soup.find("div", class_="weather1")
                if weather_section:
                    w_text = weather_section.get_text()
                    m_speed = re.search(r"風速\s*(\d+)m", w_text)
                    if m_speed: info["wind_speed"] = int(m_speed.group(1))
                    
                    if "追い風" in w_text: info["wind_dir"] = "追い風"
                    elif "向かい風" in w_text: info["wind_dir"] = "向かい風"
                    elif "左横風" in w_text or "右横風" in w_text: info["wind_dir"] = "横風"
                    
                    if "満潮" in w_text or "上げ潮" in w_text: info["tide"] = "満潮/上げ潮 🌊"
                    elif "干潮" in w_text or "下げ潮" in w_text: info["tide"] = "干潮/下げ潮 ☀️"
                
                all_cells = soup.find_all(["td", "th", "div", "span"])
                found_times = []
                for cell in all_cells:
                    text = cell.get_text(strip=True)
                    if re.match(r"^6\.\d{2}$", text):
                        found_times.append(float(text))
                
                if len(found_times) >= 6:
                    info["tenji"] = found_times[:6]
                    return info
        except Exception:
            pass
        if i < retries:
            time.sleep(0.3)
    return info

# --- AI分析ロジック ---
def calculate_predictions(df, venue, weather_info, investment):
    course_base = {1: 45, 2: 25, 3: 20, 4: 15, 5: 10, 6: 5}
    v_param = VENUE_CHARACTERISTICS.get(venue, {"water": "淡水", "in_adj": 0, "makuri_adj": 0, "desc": "標準水面"})
    
    tide_status = weather_info["tide"]
    tide_in_adj = 0
    tide_makuri_adj = 0
    
    if v_param["water"] in ["海水", "汽水"]:
        if "満潮" in tide_status:
            tide_in_adj = +6
            tide_makuri_adj = -4
        elif "干潮" in tide_status:
            tide_in_adj = -4
            tide_makuri_adj = +6
            
    course_base[1] += (v_param["in_adj"] + tide_in_adj)
    course_base[2] += (tide_in_adj * 0.5)
    course_base[3] += (v_param["makuri_adj"] + tide_makuri_adj) * 0.5
    course_base[4] += (v_param["makuri_adj"] + tide_makuri_adj) * 0.7
    
    rank_bonus = {"A1": 25, "A2": 15, "B1": 5, "B2": 0}
    w_speed = weather_info["wind_speed"]
    w_dir = weather_info["wind_dir"]
    wind_course_adj = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
    
    if w_speed >= 3:
        if w_dir == "追い風":
            wind_course_adj[1] -= (w_speed * 1.5)
            wind_course_adj[2] += (w_speed * 2.0)
            wind_course_adj[3] += (w_speed * 1.5)
        elif w_dir == "向かい風":
            wind_course_adj[1] -= (w_speed * 2.0)
            wind_course_adj[3] += (w_speed * 1.5)
            wind_course_adj[4] += (w_speed * 2.5)

    min_tenji = min(weather_info["tenji"])
    scores = {}
    attack_power = {}
    
    for idx, row in df.iterrows():
        w = int(row["枠"])
        rank = row["級別"]
        nat_win = row["全国勝率"]
        loc_win = row["当地勝率"]
        motor = row["モーター2連率(%)"]
        t_time = weather_info["tenji"][idx] if idx < len(weather_info["tenji"]) else 6.80
        
        tenji_score = max(0, (6.90 - t_time) * 30)
        if t_time == min_tenji: tenji_score += 10

        course_fitness = 0
        if w == 1: course_fitness = (nat_win * 3) + (loc_win * 2)
        elif w in [2, 3]: course_fitness = (nat_win * 3) + (motor * 0.2)
        elif w in [4, 5, 6]: course_fitness = (nat_win * 2.5) + tenji_score

        total = (course_base.get(w, 5) + wind_course_adj.get(w, 0) + 
                 rank_bonus.get(rank, 0) + (nat_win * 3) + (loc_win * 2) + 
                 (motor * 0.3) + tenji_score + course_fitness)
        
        scores[w] = total
        attack_power[w] = (nat_win * 2) + tenji_score + ((v_param["makuri_adj"] + tide_makuri_adj) * 2)
        
    combos = list(itertools.permutations([1, 2, 3, 4, 5, 6], 3))
    combo_scores = []
    center_attack = max(attack_power[3], attack_power[4])
    is_makuri_tenkai = (center_attack > attack_power[1] + 3) or (w_dir == "向かい風" and w_speed >= 4) or ("干潮" in tide_status and v_param["water"] in ["海水", "汽水"])
    
    for c in combos:
        eval_score = (scores[c[0]] * 1.6) + (scores[c[1]] * 1.0) + (scores[c[2]] * 0.6)
        if is_makuri_tenkai:
            if c[0] in [3, 4]: eval_score *= 1.3
            if c[1] in [2, 4, 5]: eval_score *= 1.15
        else:
            if c[0] == 1 and c[1] in [2, 3]: eval_score *= 1.25
        combo_scores.append((c, eval_score))
        
    combo_scores.sort(key=lambda x: x[1], reverse=True)
    
    top_combos = [combo_scores[0], combo_scores[1], combo_scores[2], combo_scores[5]]
    labels = ["本命 🔥", "本命 🔥", "対抗 ⚔️", "潮位穴 ⚡"]
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
        
    tenkai_msg = "⚡ 潮位・干潮まくり展開警戒" if is_makuri_tenkai else "🎯 満潮・イン堅調展開"
    return pd.DataFrame(bet_list), tenkai_msg, v_param["desc"]

# --- メイン画面構成 ---
st.title("🚤 やっちゃんの競艇AI予想")
st.caption(f"日付: {date_display}")

st.subheader("📍 レースを選択してください")

selected_v = st.selectbox("会場を選択", list(VENUE_CODES.keys()))

col_r, col_m = st.columns(2)
with col_r:
    race_num = st.selectbox("レースを選択", [f"{i}R" for i in range(1, 13)])
with col_m:
    investment = st.number_input("投資金額 (円)", min_value=1000, value=5000, step=1000)

# --- 予想実行 ---
if st.button(f"🚀 {selected_v} {race_num} をAI予想する", type="primary", use_container_width=True):
    jcd = VENUE_CODES[selected_v]
    rno = race_num.replace("R", "")
    
    with st.spinner("出走表・展示・水面・潮位情報を取得中..."):
        df_racers = get_detailed_racers(jcd, rno, today_str, retries=2)
        weather_info = get_before_info(jcd, rno, today_str, retries=2)
    
    if df_racers is None or df_racers.empty:
        st.error(f"❌ {selected_v} {race_num} の出走表を取得できませんでした。まだ開催前か、締め切り後の可能性があります。")
    else:
        df_bets, tenkai_msg, v_desc = calculate_predictions(df_racers, selected_v, weather_info, investment)
        
        st.info(f"🏟️ **会場特性**: {v_desc}\n\n🌀 **コンディション**: {weather_info['wind_dir']} {weather_info['wind_speed']}m / {weather_info['tide']}")
        
        df_display = df_racers.copy()
        df_display["枠"] = df_display["枠"].apply(lambda x: f"{x}号艇")
        df_display["展示タイム"] = weather_info["tenji"]
        
        st.subheader("📋 出走表・展示")
        st.dataframe(df_display, hide_index=True, use_container_width=True)

        st.subheader("🎯 AI推奨買い目")
        st.caption(f"展開予測: **{tenkai_msg}**")
        st.table(df_bets)
