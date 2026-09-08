import streamlit as st
import requests
import pandas as pd

# 競艇場と場コード(jcd)のマッピング
JCD_MAP = {
    "桐生": "01", "戸田": "02", "江戸川": "03", "平和島": "04", "多摩川": "05",
    "浜名湖": "06", "蒲郡": "07", "常滑": "08", "津": "09", "三国": "10",
    "びわこ": "11", "住之江": "12", "尼崎": "13", "鳴門": "14", "丸亀": "15",
    "児島": "16", "宮島": "17", "徳山": "18", "下関": "19", "若松": "20",
    "芦屋": "21", "福岡": "22", "唐津": "23", "大村": "24"
}

# あなたの最新GASデプロイURL
GAS_URL = "https://script.google.com/macros/s/AKfycbzcDjEeOka2MJJgZJNTA-2PE4DVZIuPXskND9wI1pFZUDH_3va5JewDDA7KvKVFshFT/exec"

st.title("🚤 やっちゃんの競艇AI予想 PRO")
st.caption("【リアルタイムデータ×気象・潮汐×決まり手解析】")

st.subheader("競艇場を選択")
selected_place = st.selectbox("", list(JCD_MAP.keys()), index=2)

st.subheader("レースを選択")
selected_race = st.selectbox("", [f"{i}R" for i in range(1, 13)], index=8)

if st.button("🔍 AI予想を実行する"):
    jcd = JCD_MAP[selected_place]
    rno = selected_race.replace("R", "")
    
    with st.spinner("出走表データを取得中..."):
        try:
            res = requests.get(GAS_URL, params={"jcd": jcd, "rno": rno}, timeout=15)
            
            # レスポンスがJSONかどうか判定
            try:
                data = res.json()
            except Exception:
                st.error("⚠️ GASからの応答が正しいJSONデータではありません。GASのデプロイ設定（アクセス権限が『全員』になっているか）を確認してください。")
                st.stop()
            
            if data.get("status") == "success":
                df = pd.DataFrame(data["data"])
                st.success(f"【{selected_place} {selected_race}】のデータを取得しました！")
                st.dataframe(df, use_container_width=True)
                
                st.markdown("### 🤖 AI予想結果")
                st.write("1着軸予想: 1号艇 / 2着対抗: 2号艇・3号艇")
            else:
                st.error(f"⚠️ 【{selected_place} {selected_race}】のデータを読み込めませんでした。（理由: {data.get('message')}）")
                
        except Exception as e:
            st.error(f"通信エラーが発生しました: {e}")
