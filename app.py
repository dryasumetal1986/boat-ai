import streamlit as st
import pandas as pd

# ページ設定
st.set_page_config(page_title="競艇 AI 予想", page_icon="🚤", layout="centered")

st.title("🚤 競艇 AI 予想")
st.caption("独自モデルによるリアルタイム分析・資金配分ツール")

st.divider()

# --- 1. 条件設定 ---
st.subheader("⚙️ レース条件設定")

col1, col2 = st.columns(2)
with col1:
    venue = st.selectbox(
        "開催会場",
        ["桐生", "戸田", "江戸川", "平和島", "多摩川", "浜名湖", "蒲郡", "常滑", "津", "三国", "びわこ", "住之江", "尼崎", "鳴門", "丸亀", "児島", "宮島", "徳山", "下関", "若松", "芦屋", "福岡", "唐津", "大村"]
    )
with col2:
    race_num = st.selectbox("レース", [f"{i}R" for i in range(1, 13)])

# 予算設定
investment = st.number_input("投資合計金額 (円)", min_value=1000, value=5000, step=1000)

st.divider()

# --- 2. 予想実行ボタン ---
if st.button("🤖 AI予想 & 資金配分を計算", type="primary", use_container_width=True):
    st.success(f"【{venue} {race_num}】のAI解析が完了しました！")
    
    # --- 3. 出走表 & AIスコア表示 ---
    st.subheader("📋 出走表 & AI勝率スコア")
    
    # 擬似出走表データ（会場ごとにイン強さを少し可変）
    is_in_course_strong = venue in ["大村", "徳山", "芦屋", "下関"]
    
    racer_data = {
        "枠": ["1️⃣ 白", "2️⃣ 黒", "3️⃣ 赤", "4️⃣ 青", "5️⃣ 黄", "6️⃣ 緑"],
        "選手名": ["艇王 一郎", "競艇 二郎", "水上 三郎", "波乗り 四郎", "ターボ 五郎", "アウト 六郎"],
        "全国勝率": [7.45 if is_in_course_strong else 6.85, 6.20, 5.90, 6.50, 5.10, 4.80],
        "モータ2連率": ["45.2%", "38.1%", "41.0%", "52.3%", "33.0%", "29.5%"],
        "AI予測勝率": ["48.5%" if is_in_course_strong else "35.2%", "18.3%", "14.1%", "15.8%", "5.1%", "3.0%"]
    }
    
    df = pd.DataFrame(racer_data)
    st.dataframe(df, hide_index=True, use_container_width=True)

    st.divider()

    # --- 4. 買い目 & 推奨資金配分 ---
    st.subheader("🎯 推奨買い目 & 資金配分")
    st.caption(f"※総予算 {investment:,} 円に基づいた最適配分")

    # 資金配分計算（予算に応じて自動計算）
    b1_amount = int(investment * 0.4 // 100 * 100)
    b2_amount = int(investment * 0.3 // 100 * 100)
    b3_amount = int(investment * 0.2 // 100 * 100)
    b4_amount = int(investment * 0.1 // 100 * 100)

    bet_data = {
        "区分": ["本命 🔥", "本命 🔥", "対抗 ⚔️", "穴 ⚡"],
        "買い目（3連単）": ["1 - 2 - 4", "1 - 4 - 2", "1 - 3 - 2", "4 - 1 - 2"],
        "想定オッズ": ["8.5倍", "12.3倍", "18.0倍", "35.5倍"],
        "推奨購入額": [f"{b1_amount:,} 円", f"{b2_amount:,} 円", f"{b3_amount:,} 円", f"{b4_amount:,} 円"]
    }

    df_bet = pd.DataFrame(bet_data)
    st.table(df_bet)

    st.info("💡 **AIの助言:** インコースの信頼度が高いため、1号艇頭を軸にした資金配分が有効です。")
