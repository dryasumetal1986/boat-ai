import streamlit as st
from datetime import date

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
# CSS
# =========================================================

st.markdown(
    """
    <style>

    /* =====================================================
       BASE
    ===================================================== */

    .stApp {
        background: #f4f6f9;
        color: #111827;
    }

    .block-container {
        max-width: 720px;
        padding-top: 5.8rem !important;
        padding-bottom: 4rem !important;
    }

    html,
    body,
    [class*="css"] {
        font-family:
            "Noto Sans JP",
            "Hiragino Kaku Gothic ProN",
            "Yu Gothic",
            "Meiryo",
            sans-serif;
    }

    p,
    label,
    .stMarkdown,
    .stCaption {
        color: #111827;
    }


    /* =====================================================
       TITLE
       ===================================================== */

    .pro-title {
        text-align: center;
        font-size: 28px;
        font-weight: 900;
        letter-spacing: 0.01em;
        color: #111827 !important;
        line-height: 1.35;
        margin: 0 0 7px 0;
        white-space: nowrap;
    }

    .pro-subtitle {
        text-align: center;
        font-size: 12px;
        font-weight: 700;
        color: #64748b !important;
        margin-bottom: 28px;
        letter-spacing: 0.05em;
    }


    /* =====================================================
       SELECT
       ===================================================== */

    .select-label {
        font-size: 13px;
        font-weight: 900;
        color: #374151 !important;
        margin: 0 0 5px 2px;
    }

    div[data-baseweb="select"] > div {
        background: #ffffff !important;
        border: 1px solid #d7dce4 !important;
        border-radius: 13px !important;
        min-height: 50px;
        box-shadow: none !important;
    }

    div[data-baseweb="select"] span {
        color: #111827 !important;
    }

    div[data-baseweb="select"] svg {
        fill: #111827 !important;
    }


    /* =====================================================
       BUTTON
       ===================================================== */

    div.stButton > button {
        width: 100%;
        min-height: 54px;
        border: none !important;
        border-radius: 14px !important;
        background: #2563eb !important;
        color: #ffffff !important;
        font-size: 17px !important;
        font-weight: 900 !important;
        box-shadow: 0 7px 18px rgba(37, 99, 235, 0.22);
        transition: 0.15s ease;
    }

    div.stButton > button p {
        color: #ffffff !important;
        font-weight: 900 !important;
    }

    div.stButton > button:hover {
        background: #1d4ed8 !important;
        transform: translateY(-1px);
    }


    /* =====================================================
       DIVIDER
       ===================================================== */

    .divider {
        height: 1px;
        background: #d9dee7;
        margin: 28px 0;
    }


    /* =====================================================
       RACE CARD
       ===================================================== */

    .race-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 20px 22px;
        box-shadow: 0 5px 18px rgba(15, 23, 42, 0.06);
        margin-bottom: 18px;
    }

    .race-title {
        font-size: 22px;
        font-weight: 900;
        color: #111827 !important;
        margin-bottom: 13px;
    }

    .racer-row {
        display: flex;
        align-items: center;
        min-height: 49px;
        border-bottom: 1px solid #edf0f4;
        font-size: 15px;
    }

    .racer-row:last-child {
        border-bottom: none;
    }

    .boat-number {
        width: 31px;
        height: 31px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
        background: #eef2f7;
        color: #111827 !important;
        font-weight: 900;
        margin-right: 12px;
        flex-shrink: 0;
    }

    .racer-name {
        color: #111827 !important;
        font-weight: 700;
    }


    /* =====================================================
       PREDICTION
       ===================================================== */

    .prediction-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 17px;
        padding: 17px 21px;
        margin-bottom: 11px;
        box-shadow: 0 4px 15px rgba(15, 23, 42, 0.05);
    }

    .prediction-label {
        font-size: 13px;
        font-weight: 900;
        margin-bottom: 4px;
    }

    .prediction-value {
        font-size: 27px;
        font-weight: 900;
        letter-spacing: 0.08em;
        color: #111827 !important;
    }

    .main-label {
        color: #2563eb !important;
    }

    .counter-label {
        color: #f97316 !important;
    }

    .hole-label {
        color: #dc2626 !important;
    }


    /* =====================================================
       CONFIDENCE
       ===================================================== */

    .confidence-card {
        background: #111827;
        border-radius: 18px;
        padding: 20px;
        text-align: center;
        margin-top: 17px;
    }

    .confidence-title {
        font-size: 12px;
        font-weight: 700;
        color: #cbd5e1 !important;
        margin-bottom: 5px;
    }

    .confidence-stars {
        font-size: 24px;
        letter-spacing: 0.08em;
        color: #ffffff !important;
    }


    /* =====================================================
       BACKTEST
       ===================================================== */

    [data-testid="stExpander"] {
        background: #ffffff !important;
        border: 1px solid #dfe4eb !important;
        border-radius: 16px !important;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(15, 23, 42, 0.05);
    }

    [data-testid="stExpander"] details {
        background: #ffffff !important;
    }

    [data-testid="stExpander"] summary {
        background: #111827 !important;
        color: #ffffff !important;
        padding: 17px 18px !important;
        font-weight: 900 !important;
        font-size: 15px !important;
    }

    [data-testid="stExpander"] summary p {
        color: #ffffff !important;
    }

    [data-testid="stExpander"] summary svg {
        fill: #ffffff !important;
    }

    [data-testid="stExpanderDetails"] {
        background: #ffffff !important;
        color: #111827 !important;
        padding: 20px !important;
    }

    [data-testid="stExpanderDetails"] p {
        color: #374151 !important;
    }

    .backtest-title {
        font-size: 20px;
        font-weight: 900;
        color: #111827 !important;
        margin-bottom: 5px;
    }


    /* =====================================================
       RADIO
       ===================================================== */

    div[role="radiogroup"] {
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 10px 12px;
    }

    div[role="radiogroup"] label,
    div[role="radiogroup"] label p {
        color: #111827 !important;
    }

    div[role="radiogroup"] label p {
        font-weight: 800 !important;
    }


    /* =====================================================
       INFO / ALERT
       ===================================================== */

    div[data-testid="stAlert"] {
        border-radius: 12px !important;
    }


    /* =====================================================
       METRIC
       ===================================================== */

    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 14px;
    }

    [data-testid="stMetricLabel"] {
        color: #64748b !important;
    }

    [data-testid="stMetricValue"] {
        color: #111827 !important;
        font-weight: 900 !important;
    }


    /* =====================================================
       TABLE
       ===================================================== */

    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
    }


    /* =====================================================
       DOWNLOAD
       ===================================================== */

    .stDownloadButton button {
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        color: #111827 !important;
    }

    .stDownloadButton button p {
        color: #111827 !important;
    }


    /* =====================================================
       MOBILE
       ===================================================== */

    @media (max-width: 600px) {

        .block-container {
            padding-left: 14px !important;
            padding-right: 14px !important;
            padding-top: 5.3rem !important;
        }

        .pro-title {
            font-size: 21px;
            letter-spacing: 0;
        }

        .pro-subtitle {
            font-size: 11px;
            margin-bottom: 22px;
        }

        .race-card,
        .prediction-card {
            padding: 16px;
        }

        .race-title {
            font-size: 20px;
        }

        .prediction-value {
            font-size: 24px;
        }

        [data-testid="stExpanderDetails"] {
            padding: 16px !important;
        }

        div[role="radiogroup"] {
            padding: 9px;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# TITLE
# =========================================================

st.markdown(
    '<div class="pro-title">🚤 やっちゃんの競艇AI予想PRO</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="pro-subtitle">DATA ANALYSIS × RACE PREDICTION</div>',
    unsafe_allow_html=True,
)


# =========================================================
# SELECT
# =========================================================

col1, col2 = st.columns([2.2, 1])

with col1:

    st.markdown(
        '<div class="select-label">場</div>',
        unsafe_allow_html=True,
    )

    stadium_name_selected = st.selectbox(
        "場",
        list(data.STADIUMS.values()),
        label_visibility="collapsed",
    )

with col2:

    st.markdown(
        '<div class="select-label">R</div>',
        unsafe_allow_html=True,
    )

    race_no = st.selectbox(
        "R",
        range(1, 13),
        format_func=lambda x: f"{x}R",
        label_visibility="collapsed",
    )


stadium_no = next(
    (
        number
        for number, name in data.STADIUMS.items()
        if name == stadium_name_selected
    ),
    None,
)


# =========================================================
# PREDICT
# =========================================================

if st.button(
    "🚤 AI予想する",
    use_container_width=True,
):

    target_date = date.today().isoformat()

    with st.spinner("AIがレースを分析しています..."):

        try:

            raw = data.get_data(target_date)

            race = data.get_race(
                raw,
                stadium_no,
                race_no,
            )

            if not data.validate_race(
                race,
                target_date,
                stadium_no,
                race_no,
            ):
                st.error("レースデータの確認に失敗しました。")
                st.stop()

            race_rows = data.get_race_rows(
                race,
                stadium_no,
                race_no,
            )

            if race_rows is None or len(race_rows) != 6:
                st.error("6艇分の選手データを取得できませんでした。")
                st.stop()

            history = data.history14(target_date)

            prediction = tri_ai(
                race_rows,
                history,
            )

        except Exception as e:

            st.error(
                "データ取得またはAI予想中にエラーが発生しました。"
            )

            st.exception(e)
            st.stop()


    # =====================================================
    # RACE
    # =====================================================

    st.markdown(
        '<div class="divider"></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="race-card">',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="race-title">{stadium_name_selected} {race_no}R</div>',
        unsafe_allow_html=True,
    )

    for i, racer in enumerate(
        race_rows.to_dict("records"),
        start=1,
    ):

        racer_name = (
            racer.get("選手名")
            or "選手情報なし"
        )

        st.markdown(
            f"""
            <div class="racer-row">
                <span class="boat-number">{i}</span>
                <span class="racer-name">{racer_name}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        '</div>',
        unsafe_allow_html=True,
    )


    # =====================================================
    # PREDICTIONS
    # =====================================================

    prediction_items = [
        ("🎯 本命", prediction.get("main"), "main-label"),
        ("🔥 対抗", prediction.get("counter"), "counter-label"),
        ("💥 穴", prediction.get("hole"), "hole-label"),
    ]

    for label, combo, css_class in prediction_items:

        if not combo:
            continue

        text = "-".join(map(str, combo))

        st.markdown(
            f"""
            <div class="prediction-card">
                <div class="prediction-label {css_class}">
                    {label}
                </div>
                <div class="prediction-value">
                    {text}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


    # =====================================================
    # CONFIDENCE
    # =====================================================

    boat_probs = prediction.get(
        "boat_probs",
        {},
    )

    confidence = backtest.confidence_from_probs(
        boat_probs
    )

    st.markdown(
        f"""
        <div class="confidence-card">
            <div class="confidence-title">
                AI自信度
            </div>
            <div class="confidence-stars">
                {confidence}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# BACKTEST
# =========================================================

st.markdown(
    '<div class="divider"></div>',
    unsafe_allow_html=True,
)

with st.expander(
    "📊 AIの実力を検証する",
):

    backtest.render_backtest()
