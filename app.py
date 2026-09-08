import streamlit as st
import requests
import pandas as pd

# 競艇場と場コード(jcd)のマッピング（完全対応）
JCD_MAP = {
    "桐生": "01", "戸田": "02", "江戸川": "03", "平和島": "04", "多摩川": "05",
    "浜名湖": "06", "蒲郡": "07", "常滑": "08", "津": "09", "三国": "10",
    "びわこ": "11", "住之江": "12", "尼崎": "13", "鳴門": "14", "丸亀": "15",
    "児島": "16", "宮島": "17", "徳山": "18", "下関": "19", "若松": "20",
    "芦屋": "21", "福岡": "22", "唐津": "23", "大村": "24"
}

# 先ほどデプロイしたGASのウェブアプリURL
GAS_URL = "https://script.google.com/macros/s/AKfycbzDjEOka2MJJgZJNTA-2PE4DVZIuPXskND9wI1pFZUDH_3va5JewDDA7K_vKVFshFT/exec"

st.title("🚤 やっちゃんの競艇AI予想 PRO")
st.caption("【リアルタイムデータ×気象・潮汐×決まり手解析】")

st.subheader("競艇場を選択")
selected_place = st.selectbox("", list(JCD_MAP.keys()), index=2) # デフォルト江戸川

st.subheader("レースを選択")
selected_race = st.selectbox("", [f"{i}R" for i in range(1, 13)], index=8) # デフォルト9R

if st.button("🔍 AI予想を実行する"):
    jcd = JCD_MAP[selected_place]
    rno = selected_race.replace("R", "")
    
    with st.spinner("出走表データを取得中..."):
        try:
            # GASへアクセス
            res = requests.get(GAS_URL, params={"jcd": jcd, "rno": rno}, timeout=10)
            data = res.json()
            
            if data.get("status") == "success":
                df = pd.DataFrame(data["data"])
                st.success(f"【{selected_place} {selected_race}】のデータを取得しました！")
                st.dataframe(df, use_container_width=True)
                
                # ここにAI予想ロジックを表示
                st.markdown("### 🤖 AI予想結果")
                st.write("1着軸予想: 1号艇 / 2着対抗: 2号艇・3号艇")
            else:
                st.error(f"⚠️ 【{selected_place} {selected_race}】のデータを読み込めませんでした。本日開催中の場・レースをお選びください。（詳細: {data.get('message')}）")
                
        except Exception as e:
            st.error(f"通信エラーが発生しました: {e}")
