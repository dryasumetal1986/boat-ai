import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import json

# --- ページ基本設定 ---
st.set_page_config(page_title="やっちゃんの競艇AI予想", page_icon="🚤", layout="centered")

# --- カスタムCSS ---
st.markdown("""
<style>
    .stApp { background-color: #f8fafc; color: #1e293b; }
    .main-title {
        font-size: 24px;
        font-weight: 800;
        color: #0284c7;
        text-align: center;
        margin-top: 10px;
        margin-bottom: 20px;
    }
    .predict-btn button {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
        color: white !important;
        font-weight: bold !important;
        font-size: 16px !important;
        border-radius: 10px !important;
        height: 48px !important;
        border: none !important;
        margin-top: 10px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🚤 やっちゃんの競艇AI予想</div>', unsafe_allow_html=True)

# --- 競艇場コードマップ ---
VENUES_MAP = {
    '桐生': '01', '戸田': '02', '江戸川': '03', '平和島': '04', '多摩川': '05',
    '浜名湖': '06', '蒲郡': '07', '常滑': '08', '津': '09', '三国': '10',
    'びわこ': '11', '住之江': '12', '尼崎': '13', '鳴門': '14', '丸亀': '15',
    '児島': '16', '宮島': '17', '徳山': '18', '下関': '19', '若松': '20',
    '芦屋': '21', '福岡': '22', '唐津': '23', '大村': '24'
}

def fetch_real_boatrace_data_via_proxy(venue_name, race_num):
    """プロキシAPI経由で公式出走表をIPブロック回避して取得する"""
    jcd = VENUES_MAP.get(venue_name, '01')
    rno = race_num.replace('R', '')
    target_url = f"https://www.boatrace.jp/owpc/pc/race/racelist?rno={rno}&jcd={jcd}"
    
    # クラウドサーバーからのIPブロックを回避するプロキシURL
    proxy_url = f"https://api.allorigins.win/get?url={requests.utils.quote(target_url)}"

    try:
        res = requests.get(proxy_url, timeout=10)
        if res.status_code == 200:
            json_data = res.json()
            html_content = json_data.get('contents', '')
            
            if html_content and ('is-fs' in html_content or 'is-pck12' in html_content):
                soup = BeautifulSoup(html_content, 'html.parser')
                tbodies = soup.find_all('tbody', class_=lambda x: x and ('is-fs' in x or 'is-pck12' in x))
                
                data = []
                for i in range(min(6, len(tbodies))):
                    tbody = tbodies[i]
                    b_num = i + 1
                    
                    # 1. 選手名取得
                    name_div = tbody.find('div', class_='is-name')
                    if name_div and name_div.find('a'):
                        raw_name = name_div.find('a').text
                        name = re.sub(r'[\s\u3000]+', '', raw_name)
                    else:
                        name = f"選手{b_num}"
                    
                    # 2. 級別取得
                    class_span = tbody.find('span', class_='is-class')
                    rank = class_span.text.strip() if class_span else "B1"
                    
                    # 3. 勝率・モーター2連率の抽出
                    tds = tbody.find_all('td')
                    all_text = " ".join([td.text.strip() for td in tds])
                    
                    win_rate = "0.00"
                    motor_2ren = "0.0%"
                    
                    rates = re.findall(r'\d\.\d{2}', all_text)
                    if len(rates) >= 1:
                        win_rate = rates[0]
                    
                    motor_match = re.findall(r'\d+\.\d{2}%|\d+\.\d+%', all_text)
                    if len(motor_match) >= 3:
                        motor_2ren = motor_match[2]
                    elif len(motor_match) >= 1:
                        motor_2ren = motor_match[0]

                    w_num = float(win_rate) if win_rate != "0.00" else 4.5
                    m_num = float(motor_2ren.replace('%', '')) if motor_2ren != "0.0%" else 30.0
                    
                    # AI予測スコア計算
                    score = (w_num * 7.5) + (m_num * 0.2) + (18 if b_num == 1 else 8 if b_num == 2 else 0) + (10 if rank == 'A1' else 5 if rank == 'A2' else 0)
                    
                    data.append({
                        '艇番': b_num,
                        '選手名': name,
                        '級別': rank,
                        '全国勝率': win_rate,
                        'モーター2連率': motor_2ren,
                        'AI予測スコア': round(score, 1)
                    })
                
                if len(data) == 6:
                    df = pd.DataFrame(data)
                    df = df.sort_values(by='AI予測スコア', ascending=False).reset_index(drop=True)
                    marks = ['◎', '○', '▲', '△', '注', '–']
                    df.insert(0, '印', marks[:len(df)])
                    return df
    except Exception:
        return None

    return None

# --- レース選択フォーム ---
col1, col2 = st.columns(2)
with col1:
    selected_venue = st.selectbox("競艇場を選択", list(VENUES_MAP.keys()), key="v_select")
with col2:
    selected_race = st.selectbox("レースを選択", [f"{i}R" for i in range(1, 13)], key="r_select")

st.markdown('<div class="predict-btn">', unsafe_allow_html=True)
predict_clicked = st.button("🔮 AI予想を実行する", use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- 結果表示 ---
if predict_clicked:
    with st.spinner(f"🌐 【{selected_venue} {selected_race}】公式データをプロキシ取得中..."):
        df_result = fetch_real_boatrace_data_via_proxy(selected_venue, selected_race)
        
        if df_result is not None and not df_result.empty:
            st.success(f"✅ 【{selected_venue} {selected_race}】公式データ取得成功！")
            
            st.dataframe(
                df_result[['印', '艇番', '選手名', '級別', '全国勝率', 'モーター2連率', 'AI予測スコア']], 
                use_container_width=True,
                hide_index=True
            )
            
            t1 = df_result.iloc[0]
            t2 = df_result.iloc[1]
            t3 = df_result.iloc[2]
            
            st.info(
                f"🎯 **【{selected_venue} {selected_race}】 AIおすすめ買い目**\n\n"
                f"• **本命（3連単）:** {t1['艇番']} - {t2['艇番']} - {t3['艇番']}\n"
                f"• **押さえ（3連単）:** {t1['艇番']} - {t3['艇番']} - {t2['艇番']}\n"
                f"• **注目軸選手:** {t1['艇番']}号艇 **{t1['選手名']}** （{t1['級別']} / 勝率: {t1['全国勝率']}）"
            )
        else:
            st.error(f"❌ 【{selected_venue} {selected_race}】の公式番組表を取得できませんでした。本日開催されている場（例：びわこ等）を選択してお試しください。")

st.caption("※「やっちゃんの競艇AI予想」公式システム")
