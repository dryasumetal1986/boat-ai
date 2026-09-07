import streamlit as st

# タイトル
st.title("🚤 競艇 AI 予想")
st.write("独自モデルによるレース予想アプリ")

st.divider()

# サイドバーまたはメイン画面に会場選択を追加
st.header("⚙️ レース条件設定")

col1, col2 = st.columns(2)

with col1:
    # 会場選択
    venue = st.selectbox(
        "開催会場を選択",
        ["桐生", "戸田", "江戸川", "平和島", "多摩川", "浜名湖", "蒲郡", "常滑", "津", "三国", "びわこ", "住之江", "尼崎", "鳴門", "丸亀", "児島", "宮島", "徳山", "下関", "若松", "芦屋", "福岡", "唐津", "大村"]
    )

with col2:
    # レース番号選択
    race_num = st.selectbox(
        "レースを選択",
        [f"{i}R" for i in range(1, 13)]
    )

# 予想ボタン
if st.button("🤖 予想を計算する", type="primary"):
    st.success(f"{venue} {race_num} の予想結果を読み込みました！")
    
    st.subheader("📊 AI予想買い目")
    st.write("**本命（3連単）:** 1-2-3, 1-2-4")
    st.write("**穴目（3連単）:** 1-3-2, 2-1-3")
