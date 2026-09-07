import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import itertools

# ページ設定
st.set_page_config(page_title="やっちゃんの競艇AI予想ツール", page_icon="🚤", layout="centered")

# --- タイトルサイズ調整CSS ---
st.markdown("""
    <style>
    h1 {
        font-size: 1.8rem !important;
        line-height: 1.3 !important;
        padding-top: 0.5rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# タイトル表示
st.title("🚤 やっちゃんの競艇AI予想ツール")
st.caption("公式サイトからリアルタイム出走表を自動取得・AI分析")

st.divider()

VENUE_CODES = {
    "桐生": "01", "戸田": "02", "江戸川": "03", "平和島": "04", "多摩川": "05", "浜名湖": "06",
    "蒲郡": "07", "常滑": "08", "津": "09", "三国": "10", "びわこ": "11", "住之江": "12",
    "尼崎": "13", "鳴門": "14", "丸亀": "15", "児島": "16", "宮島": "17", "徳山": "18",
    "下関": "19", "若松": "20", "芦屋": "21", "福岡": "22", "唐津": "23", "大村": "24"
}

# --- 公式サイトからのデータ＆級別取得関数 ---
def get_race_list(jcd, rno, date_str):
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
        for idx, tbody in enumerate(tbodies):
            text = tbody.get_text(separator=" ", strip=True)
            words = text.split()
            
            # 級別(A1, A2, B1, B2)を探す
            for word in words:
                if word in ["A1", "A2", "B1", "B2"]:
                    i = words.index(word)
                    name = words[i-1] if i > 0 else "不明"
                    
                    racers.append({
                        "枠": len(racers) + 1,
                        "選手名": name,
                        "級別": word
                    })
                    break
            if len(racers) == 6:
                break
                
        return pd.DataFrame(racers) if len(racers) == 6 else None
    except Exception:
        return None

# --- AI予想スコア計算エンジン ---
def calculate_ai_predictions(df, investment):
    # コース基本スコア（インコース有利）
    course_scores = {1: 50, 2: 30, 3: 25, 4: 20, 5: 15, 6: 10}
    # 級別追加スコア
    rank_scores = {"A1": 30, "A2": 20, "B1": 10, "B2": 0}
    
    # 各艇の総合スコア計算
    scores = {}
    for _, row in df.iterrows():
        w = row["枠"]
        rank = row["級別"]
        score = course_scores.get(w, 10) + rank_scores.get(rank, 0)
        scores[w] = score
        
    # 全3連単（120通り）の組み合わせスコア計算
    boats = [1, 2, 3, 4, 5, 6]
    combos = list(itertools.permutations(boats, 3))
    
    combo_scores = []
    for c in combos:
        # 1着のスコアを重視する重み付け
        total_score = (scores[c[0]] * 1.5) + (scores[c[1]] * 1.0) + (scores[c[2]] * 0.7)
        combo_scores.append((c, total_score))
        
    # スコアが高い順にソート
    combo_scores.sort(key=lambda x: x[1], reverse=True)
    
    # 買い目の抽出 (本命2点、対抗1点、穴1点)
    top_combos = [combo_scores[0], combo_scores[1], combo_scores[2], combo_scores[5]]
    labels = ["本命 🔥", "本命 🔥", "対抗 ⚔️", "穴 ⚡"]
    ratios = [0.4, 0.3, 0.2, 0.1]
    
    bet_list = []
    for i in range(4):
        c, _ = top_combos[i]
        buy_str = f"{c[0]} - {c[1]} - {c[2]}"
        amount = int(investment * ratios[i] // 100 * 100)
        bet_list.append({
            "区分": labels[i],
            "買い目（3連単）": buy_str,
            "推奨購入額": f"{amount:,} 円"
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
    venue = st.selectbox("開催会場", list(VENUE_CODES.keys()), index=5)
with col2:
    race_num = st.selectbox("レース", [f"{i}R" for i in range(1, 13)])

investment = st.number_input("投資合計金額 (円)", min_value=1000, value=5000, step=1000)

st.divider()

# --- 2. 予想実行ボタン ---
if st.button("🤖 リアルタイム出走表を取得して予想", type="primary", use_container_width=True):
    jcd = VENUE_CODES[venue]
    rno = race_num.replace("R", "")
    
    with st.spinner("競艇公式サイトから出走表を取得中..."):
        df_racers = get_race_list(jcd, rno, today_str)
    
    if df_racers is None or df_racers.empty:
        st.warning(f"⚠️ {date_display} の {venue} {race_num} の自動解析に失敗しました。時間をおいて再試行するか、会場・レースをご確認ください。")
    else:
        st.success(f"【{venue} {race_num}】の出走表を取得・AI分析完了！")
        
        # 画面用表記の調整
        df_display = df_racers.copy()
        df_display["枠"] = df_display["枠"].apply(lambda x: f"{x}号艇")
        
        st.subheader("📋 リアルタイム出走表 (級別データ付)")
        st.dataframe(df_display, hide_index=True, use_container_width=True)

        st.divider()

        # AI計算による買い目生成
        df_bets = calculate_ai_predictions(df_racers, investment)

        st.subheader("🎯 リアルタイムAI推奨買い目 & 資金配分")
        st.table(df_bets)
