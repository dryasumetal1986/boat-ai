import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo

import data
from ai import tri_ai
import backtest


# =========================================================
# ページ設定
# =========================================================

st.set_page_config(
    page_title="やっちゃんの競艇AI予想PRO",
    page_icon="🚤",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# =========================================================
# 日本時間
# =========================================================

JST = ZoneInfo("Asia/Tokyo")
today = datetime.now(JST).date()
target_date = today.isoformat()


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
    <style>

    /* ---------------------------------
       全体
    --------------------------------- */

    .stApp {
        background: #f4f6f9;
        color: #111827;
    }

    .block-container {
        max-width: 720px !important;
        padding-top: 5.8rem !important;
        padding-bottom: 4rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    /* Streamlit上部バーとの重なり対策 */
    header[data-testid="stHeader"] {
        background: #0d1117;
    }

    /* ---------------------------------
       タイトル
    --------------------------------- */

    .pro-title {
        text-align: center;
        font-size: 29px;
        font-weight: 900;
        letter-spacing: -0.5px;
        color: #111827;
        margin: 0.2rem 0 0.35rem 0;
        white-space: nowrap;
    }

    .pro-subtitle {
        text-align: center;
        color: #6b7280;
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 1rem;
    }

    .today-badge {
        width: fit-content;
        margin: 0 auto 1.2rem auto;
        padding: 8px 16px;
        border-radius: 999px;
        background: #e8f1ff;
        border: 1px solid #c9dcff;
        color: #1558c0;
        font-weight: 800;
        font-size: 14px;
    }

    /* ---------------------------------
       カード
    --------------------------------- */

    .pro-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 20px;
        padding: 20px;
        margin: 14px 0;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    }

    .section-label {
        font-size: 13px;
        font-weight: 800;
        color: #64748b;
        margin-bottom: 5px;
    }

    /* ---------------------------------
       予想結果
    --------------------------------- */

    .result-card {
        background: #ffffff;
        border-radius: 20px;
        border: 1px solid #e5e7eb;
        padding: 20px;
        margin-top: 18px;
        box-shadow: 0 8px 25px rgba(15, 23, 42, 0.06);
    }

    .result-title {
        font-size: 20px;
        font-weight: 900;
        color: #111827;
        margin-bottom: 14px;
    }

    .prediction-row {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 14px 0;
        border-bottom: 1px solid #edf0f3;
    }

    .prediction-row:last-child {
        border-bottom: none;
    }

    .prediction-label {
        width: 70px;
        font-weight: 900;
        font-size: 14px;
    }

    .prediction-main {
        color: #1558c0;
    }

    .prediction-counter {
        color: #334155;
    }

    .prediction-hole {
        color: #dc2626;
    }

    .prediction-number {
        font-size: 23px;
        font-weight: 950;
        letter-spacing: 2px;
        color: #111827;
    }

    /* ---------------------------------
       信頼度
    --------------------------------- */

    .confidence-card {
        background: #111827;
        color: #ffffff;
        border-radius: 20px;
        padding: 18px 20px;
        margin-top: 16px;
        text-align: center;
    }

    .confidence-title {
        font-size: 13px;
        color: #cbd5e1;
        font-weight: 700;
        margin-bottom: 4px;
    }

    .confidence-stars {
        font-size: 24px;
        letter-spacing: 3px;
        font-weight: 900;
    }

    /* ---------------------------------
       ボート一覧
    --------------------------------- */

    .race-header {
        font-size: 21px;
        font-weight: 900;
        color: #111827;
        margin-bottom: 10px;
    }

    .boat-row {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 0;
        border-bottom: 1px solid #eef0f2;
    }

    .boat-row:last-child {
        border-bottom: none;
    }

    .boat-number {
        width: 34px;
        height: 34px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 9px;
        background: #111827;
        color: #ffffff;
        font-size: 15px;
        font-weight: 900;
    }

    .boat-name {
        font-size: 15px;
        font-weight: 750;
        color: #1f2937;
    }

    /* ---------------------------------
       Expander
    --------------------------------- */

    div[data-testid="stExpander"] {
        border: 1px solid #dfe4ea;
        border-radius: 20px;
        overflow: hidden;
        margin-top: 24px;
        background: #ffffff;
    }

    div[data-testid="stExpander"] summary {
        background: #111827;
        color: #ffffff !important;
        font-weight: 800;
    }

    div[data-testid="stExpander"] summary p {
        color: #ffffff !important;
    }

    /* ---------------------------------
       ボタン
    --------------------------------- */

    div.stButton > button {
        width: 100%;
        min-height: 58px;
        border-radius: 17px;
        border: none;
        background: #2457d6;
        color: #ffffff;
        font-size: 18px;
        font-weight: 900;
        box-shadow: 0 10px 22px rgba(36, 87, 214, 0.22);
    }

    div.stButton > button:hover {
        background: #1d4ed8;
        color: #ffffff;
    }

    /* ---------------------------------
       Selectbox
    --------------------------------- */

    div[data-baseweb="select"] > div {
        border-radius: 13px;
        border-color: #d7dce3;
        min-height: 48px;
        background: #ffffff;
    }

    /* ---------------------------------
       Metric
    --------------------------------- */

    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 12px;
    }

    /* ---------------------------------
       Mobile
    --------------------------------- */

    @media (max-width: 600px) {

        .block-container {
            padding-top: 5.2rem !important;
            padding-left: 0.75rem !important;
            padding-right: 0.75rem !important;
        }

        .pro-title {
            font-size: 21px;
            letter-spacing: -0.8px;
        }

        .pro-subtitle {
            font-size: 12px;
        }

        .today-badge {
            font-size: 13px;
            padding: 7px 13px;
        }

        .pro-card,
        .result-card {
            padding: 16px;
            border-radius: 17px;
        }

        .prediction-label {
            width: 58px;
            font-size: 13px;
        }

        .prediction-number {
            font-size: 21px;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# ヘッダー
# =========================================================

st.markdown(
    '<div class="pro-title">🚤 やっちゃんの競艇AI予想PRO</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="pro-subtitle">データ分析 × AIによる3連単予想</div>',
    unsafe_allow_html=True,
)

st.markdown(
    f'<div class="today-badge">📅 {today.strftime("%Y年%m月%d日")}　本日開催</div>',
    unsafe_allow_html=True,
)


# =========================================================
# 当日データ取得
# =========================================================

raw_today = data.get_data(target_date)


# =========================================================
# 会場・レース選択
# =========================================================

st.markdown(
    '<div class="pro-card">',
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2)

with col1:
    st.markdown(
        '<div class="section-label">開催場</div>',
        unsafe_allow_html=True,
    )

    stadium_no = st.selectbox(
        "開催場",
        options=list(data.STADIUMS.keys()),
        format_func=lambda x: data.stadium_name(x),
        label_visibility="collapsed",
    )

with col2:
    st.markdown(
        '<div class="section-label">レース</div>',
        unsafe_allow_html=True,
    )

    race_no = st.selectbox(
        "レース",
        options=list(range(1, 13)),
        format_func=lambda x: f"{x}R",
        label_visibility="collapsed",
    )

st.markdown(
    "</div>",
    unsafe_allow_html=True,
)


# =========================================================
# 選択レースの状態確認
# =========================================================

selected_race = None
race_rows = None

if raw_today:
    selected_race = data.get_race(
        raw_today,
        stadium_no,
        race_no,
    )

    if selected_race:
        race_rows = data.get_race_rows(
            selected_race,
            stadium_no,
            race_no,
        )


# =========================================================
# AI予想ボタン
# =========================================================

predict_clicked = st.button(
    "🚤 AI予想する",
    use_container_width=True,
)


# =========================================================
# AI予想
# =========================================================

if predict_clicked:

    # -----------------------------------------
    # 今日のデータがない
    # -----------------------------------------

    if raw_today is None:
        st.error(
            f"⚠️ {today.strftime('%Y年%m月%d日')}の開催データを取得できませんでした。"
        )

        st.info(
            "開催前、またはデータ更新前の可能性があります。"
        )

        st.stop()

    # -----------------------------------------
    # レースがない
    # -----------------------------------------

    if selected_race is None:
        st.error(
            f"⚠️ 本日の{data.stadium_name(stadium_no)} "
            f"{race_no}Rのデータがありません。"
        )

        st.info(
            "そのレースが開催されていない、またはまだ番組データが公開されていない可能性があります。"
        )

        st.stop()

    # -----------------------------------------
    # 6艇揃っているか
    # -----------------------------------------

    if not data.validate_race(
        selected_race,
        target_date,
        stadium_no,
        race_no,
    ):
        st.error(
            "⚠️ このレースの出走データがまだ揃っていません。"
        )

        st.info(
            "番組データが更新されるまで少し待ってから再度お試しください。"
        )

        st.stop()

    if race_rows is None or race_rows.empty:
        st.error(
            "⚠️ AI予想に必要な選手データを取得できませんでした。"
        )
        st.stop()

    # -----------------------------------------
    # 過去データ
    # -----------------------------------------

    with st.spinner("AIが過去データを分析しています…"):

        history = data.history14(
            target_date
        )

        prediction = tri_ai(
            race_rows,
            history,
        )

    if not isinstance(prediction, dict):
        st.error(
            "⚠️ AI予想データの生成に失敗しました。"
        )
        st.stop()

    # =====================================================
    # レース情報
    # =====================================================

    st.markdown(
        '<div class="result-card">',
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="race-header">
            {data.stadium_name(stadium_no)} {race_no}R
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -----------------------------------------
    # 出走選手
    # -----------------------------------------

    for _, row in race_rows.iterrows():

        lane = int(row["艇番"])
        name = str(row["選手名"])

        st.markdown(
            f"""
            <div class="boat-row">
                <div class="boat-number">{lane}</div>
                <div class="boat-name">{name}選手</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )

    # =====================================================
    # 予想
    # =====================================================

    main = prediction.get(
        "main",
        [],
    )

    counter = prediction.get(
        "counter",
        [],
    )

    hole = prediction.get(
        "hole",
        [],
    )

    def combo_text(combo):
        if not combo:
            return "—"

        return "-".join(
            str(int(x))
            for x in combo
        )

    st.markdown(
        '<div class="result-card">',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="result-title">🎯 AI予想</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="prediction-row">
            <div class="prediction-label prediction-main">
                🎯 本命
            </div>
            <div class="prediction-number">
                {combo_text(main)}
            </div>
        </div>

        <div class="prediction-row">
            <div class="prediction-label prediction-counter">
                🔥 対抗
            </div>
            <div class="prediction-number">
                {combo_text(counter)}
            </div>
        </div>

        <div class="prediction-row">
            <div class="prediction-label prediction-hole">
                💥 穴
            </div>
            <div class="prediction-number">
                {combo_text(hole)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )

    # =====================================================
    # AI自信度
    # =====================================================

    boat_probs = prediction.get(
        "boat_probs",
        {},
    )

    if isinstance(boat_probs, dict):

        values = sorted(
            [
                float(v)
                for v in boat_probs.values()
            ],
            reverse=True,
        )

        if values:
            confidence = values[0]

            # 1着確率から5段階評価
            if confidence >= 0.42:
                stars = "★★★★★"
            elif confidence >= 0.34:
                stars = "★★★★☆"
            elif confidence >= 0.27:
                stars = "★★★☆☆"
            elif confidence >= 0.20:
                stars = "★★☆☆☆"
            else:
                stars = "★☆☆☆☆"
        else:
            stars = "★★★☆☆"

    else:
        stars = "★★★☆☆"

    st.markdown(
        f"""
        <div class="confidence-card">
            <div class="confidence-title">
                AI自信度
            </div>
            <div class="confidence-stars">
                {stars}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# AI実力テスト
# =========================================================

with st.expander(
    "📊 AIの実力を検証する",
    expanded=False,
):

    backtest.render_backtest()
