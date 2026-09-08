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
    /* タイトルの見切れを防ぎ、スマホで自然に改行されるように設定 */
    h1 {
        font-size: 1.6rem !important;
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
        white-space: normal !important;
        line-height: 1.4 !important;
    }
    /* ボタン文字の見切れ防止 */
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
st.caption("全国勝率・モーター2連率・級別データを統合解析")

st.divider()

VENUE_CODES = {
    "桐生": "01", "戸田": "02", "江戸川": "03", "平和島": "04", "多摩川": "05", "浜名湖": "06",
    "蒲郡": "07", "常滑": "08", "津": "09", "三国": "10", "びわこ": "11", "住之江": "12",
    "尼崎": "13", "鳴門": "14", "丸亀": "15", "児島": "16", "宮島": "17", "徳山": "18",
    "下関": "19", "若松": "20", "芦屋": "21", "福岡": "22", "唐津": "23", "大村": "24"
}

# --- 公式サイトから詳細データ（選手、級別、勝率、モーター）をスクレイピング ---
def get_detailed_racers(jcd, rno, date_str):
    url = f"https://www.boatrace.jp/owpc/pc/race/racelist?rno={rno}&jcd={jcd}&hd={date_str}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            return None
            
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
            
            if not rank:
                continue
                
            name_el = tbody.find("div", class_="is-fs18")
            if not name_el:
                name_el = tbody.find("span", class_="is-fs18")
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
            
            if len(racers) == 6:
                break
                
        return pd.DataFrame(racers) if len(racers) == 6 else None
    except Exception:
        return None

# --- AIスコア＆期待値計算エンジン ---
def calculate_advanced_predictions(df, investment):
    course_base = {1: 45, 2: 25, 3: 20, 4: 15, 5: 10, 6: 5}
    rank_bonus = {"A1": 25, "A2": 15, "B1": 5, "B2": 0}
    
    scores = {}
    for _, row in df.iterrows():
        w = int(row["枠"])
        rank = row["級別"]
        win_rate = row["全国勝率"]
        motor = row["モーター2連率(%)"]
        
        total = course_base.get(w, 5) + rank_bonus.get(rank, 0) + (win_rate * 5) + (motor * 0.5)
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
        c, score = top_combos[i]
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

# --- 1. 条件設定 ---
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

# --- 2. 予想実行ボタン ---
if st.button("🤖 AI分析＆リアルタイム予想実行", type="primary", use_container_width=True):
    jcd = VENUE_CODES[venue]
    rno = race_num.replace("R", "")
    
    with st.spinner("出走表・勝率・モーターデータを統合分析中..."):
        df_racers = get_detailed_racers(jcd, rno, today_str)
    
    if df_racers is None or df_racers.empty:
        st.warning(f"⚠️ {date_display} の {venue} {race_num} の解析に失敗しました。開催状況またはレース番号をご確認ください。")
    else:
        st.success(f"【{venue} {race_num}】のデータ取得＆AI精密分析が完了しました！")
        
        df_display = df_racers.copy()
        df_display["枠"] = df_display["枠"].apply(lambda x: f"{x}号艇")
        
        st.subheader("📋 リアルタイム出走表 & 詳細データ")
        st.dataframe(df_display, hide_index=True, use_container_width=True)

        st.divider()

        df_bets = calculate_advanced_predictions(df_racers, investment)

        st.subheader("🎯 期待値AI推奨買い目 & 資金配分")
        st.table(df_bets)
