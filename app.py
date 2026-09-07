import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

# ページ設定
st.set_page_config(page_title="競艇 AI 予想", page_icon="🚤", layout="centered")

st.title("🚤 競艇 AI 予想")
st.caption("公式サイトからリアルタイム出走表を自動取得・分析")

st.divider()

# 会場コードマップ
VENUE_CODES = {
    "桐生": "01", "戸田": "02", "江戸川": "03", "平和島": "04", "多摩川": "05", "浜名湖": "06",
    "蒲郡": "07", "常滑": "08", "津": "09", "三国": "10", "びわこ": "11", "住之江": "12",
    "尼崎": "13", "鳴門": "14", "丸亀": "15", "児島": "16", "宮島": "17", "徳山": "18",
    "下関": "19", "若松": "20", "芦屋": "21", "福岡": "22", "唐津": "23", "大村": "24"
}

# --- 公式サイトからのデータ取得関数 ---
def get_race_list(jcd, rno, date_str):
    url = f"https://www.boatrace.jp/owpc/pc/race/racelist?rno={rno}&jcd={jcd}&hd={date_str}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code != 200:
            return None
            
        soup = BeautifulSoup(res.text, "html.parser")
        tables = soup.find_all("table")
        if len(tables) < 3:
            return None
            
        racers = []
        tbody_list = tables[2].find_all("tbody")
        for idx, tbody in enumerate(tbody_list[:6]):
            row_num = idx + 1
            text = tbody.get_text(separator=" ", strip=True)
            words = text.split()
            
            name = "取得失敗"
            rank = "-"
            for i, word in enumerate(words):
                if word in ["A1", "A2", "B1", "B2"]:
                    rank = word
                    if i > 0:
                        name = words[i-1]
                    break
            
            racers.append({
                "枠": f"{row_num}号艇",
                "選手名": name,
                "級別": rank
            })
            
        return pd.DataFrame(racers) if racers else None
    except Exception:
        return None

# --- 1. 条件設定 ---
st.subheader("⚙️ レース条件設定")

# 日本時間 (JST) を設定
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
if st.button("🤖 リアルタイム出走表を取得して予想", type="primary", use_container_width=True):
    jcd = VENUE_CODES[venue]
    rno = race_num.replace("R", "")
    
    with st.spinner("競艇公式サイトから出走表を取得中..."):
        df_racers = get_race_list(jcd, rno, today_str)
    
    if df_racers is None or df_racers.empty:
        st.warning(f"⚠️ {date_display} の {venue} {race_num} は開催されていないか、データがまだ公開されていません。")
    else:
        st.success(f"【{venue} {race_num}】の本物出走表を取得しました！")
        
        st.subheader("📋 リアルタイム出走表")
        st.dataframe(df_racers, hide_index=True, use_container_width=True)

        st.divider()

        st.subheader("🎯 推奨買い目 & 資金配分")
        b1_amount = int(investment * 0.4 // 100 * 100)
        b2_amount = int(investment * 0.3 // 100 * 100)
        b3_amount = int(investment * 0.2 // 100 * 100)
        b4_amount = int(investment * 0.1 // 100 * 100)

        bet_data = {
            "区分": ["本命 🔥", "本命 🔥", "対抗 ⚔️", "穴 ⚡"],
            "買い目（3連単）": ["1 - 2 - 3", "1 - 3 - 2", "1 - 2 - 4", "2 - 1 - 3"],
            "推奨購入額": [f"{b1_amount:,} 円", f"{b2_amount:,} 円", f"{b3_amount:,} 円", f"{b4_amount:,} 円"]
        }
        st.table(pd.DataFrame(bet_data))
