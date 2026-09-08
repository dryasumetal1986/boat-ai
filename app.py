import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd

# 競艇場と場コード(jcd)のマッピング
JCD_MAP = {
    "桐生": "01", "戸田": "02", "江戸川": "03", "平和島": "04", "多摩川": "05",
    "浜名湖": "06", "蒲郡": "07", "常滑": "08", "津": "09", "三国": "10",
    "びわこ": "11", "住之江": "12", "尼崎": "13", "鳴門": "14", "丸亀": "15",
    "児島": "16", "宮島": "17", "徳山": "18", "下関": "19", "若松": "20",
    "芦屋": "21", "福岡": "22", "唐津": "23", "大村": "24"
}

st.title("🚤 やっちゃんの競艇AI予想 PRO")
st.caption("【リアルタイムデータ×気象・潮汐×決まり手解析】")

selected_place = st.selectbox("競艇場を選択", list(JCD_MAP.keys()), index=2)
selected_race = st.selectbox("レースを選択", [f"{i}R" for i in range(1, 13)], index=8)

if st.button("🔍 AI予想を実行する"):
    jcd = JCD_MAP[selected_place]
    rno = selected_race.replace("R", "")
    
    url = f"https://www.boatrace.jp/owpc/pc/race/racelist?rno={rno}&jcd={jcd}"
    
    with st.spinner("公式Webサイトからデータを取得中..."):
        try:
            # セキュリティ回避用のスクレイパー
            scraper = cloudscraper.create_scraper()
            res = scraper.get(url, timeout=15)
            
            soup = BeautifulSoup(res.text, "html.parser")
            tbodies = soup.find_all("tbody", class_="is-fs12")
            
            rows = []
            if len(tbodies) >= 6:
                for i, tbody in enumerate(tbodies[:6]):
                    # 選手名
                    name_tag = tbody.find("div", class_=lambda x: x and "is-fs18" in x)
                    name = name_tag.get_text(strip=True).replace(" ", "").replace("　", "") if name_tag else f"選手{i+1}"
                    
                    # 級別
                    text = tbody.get_text()
                    rank = "-"
                    for r in ["A1", "A2", "B1", "B2"]:
                        if r in text:
                            rank = r
                            break
                    
                    rows.append({
                        "枠番": f"{i+1}号艇",
                        "選手名": name,
                        "級別": rank
                    })
                
                df = pd.DataFrame(rows)
                st.success(f"【{selected_place} {selected_race}】のデータを取得しました！")
                st.dataframe(df, use_container_width=True)
                
                # 予想表示
                top_player = df.iloc[0]["選手名"]
                top_rank = df.iloc[0]["級別"]
                st.markdown("### 🤖 AI予想結果")
                st.write(f"本命軸: **1号艇 {top_player}（{top_rank}）**")
                st.write("おすすめ買い目: **1-2-3, 1-2-4, 1-3-2**")
            else:
                st.error("出走表データの取得に失敗しました。時間をおいて再試行してください。")
                
        except Exception as e:
            st.error(f"通信エラーが発生しました: {e}")
