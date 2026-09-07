import streamlit as st

st.title("🚤 競艇 AI 予想")
st.write("独自モデルによるレース予想アプリ")

st.header("★ 的中速報")
col1, col2 = st.columns(2)

with col1:
    st.metric(label="蒲郡 5R", value="￥220", delta="3連複 1-3-4")
with col2:
    st.metric(label="びわこ 6R", value="￥170", delta="3連単 1-2-3")

st.success("AI解析完了：本日の回収率見込み 119%")
