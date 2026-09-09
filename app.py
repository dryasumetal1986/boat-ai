import streamlit as st
from datetime import date

import data
from ai import tri_ai


# =========================
# ページ設定
# =========================
st.set_page_config(
    page_title="やっちゃんの競艇AI予想PRO",
    page_icon="🚤",
    layout="centered",
)


# =========================
# デザイン
# =========================
st.markdown(
    """
    <style>
    .stApp {
        background: #f5f7fa;
    }

    .main .block-container {
        max-width: 760px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    html, body, [class*="css"] {
        font-family:
            "Noto Sans JP",
            "Hiragino Kaku Gothic ProN",
            "Yu Gothic",
            "Meiryo",
            sans-serif;
    }

    .pro-title {
        text-align: center;
        font-size: 2rem;
        font-weight: 800;
        letter-spacing: 0.06em;
        color: #111827;
        margin-bottom: 0.3rem;
    }

    .pro-subtitle {
        text-align: center;
        color: #64748b;
        font-size: 0.85rem;
        letter-spacing: 0.12em;
        margin-bottom: 1.8rem;
    }

    .select-label {
        color: #475569;
        font-size: 0.85rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }

    .stButton > button {
        width: 100%;
        height: 3.2rem;
        border-radius: 12px;
        border: none;
        background: #2563eb;
        color: white;
        font-size: 1.05rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        box-shadow: 0 6px 18px rgba(37, 99, 235, 0.22);
        transition: 0.2s;
    }

    .stButton > button:hover {
        background: #1d4ed8;
        transform: translateY(-1px);
        box-shadow: 0 8px 22px rgba(37, 99, 235, 0.3);
    }

    .race-card {
        background: white;
        border-radius: 18px;
        padding: 1.3rem 1.4rem;
        margin-top: 1.4rem;
        box-shadow: 0 5px 20px rgba(15, 23, 42, 0.07);
        border: 1px solid #e5e7eb;
    }

    .race-title {
        text-align: center;
        font-size: 1.35rem;
        font-weight: 800;
        color: #111827;
        margin-bottom: 1rem;
        letter-spacing: 0.08em;
    }

    .racer {
        display: flex;
        align-items: center;
        padding: 0.65rem 0;
        border-bottom: 1px solid #eef2f7;
    }

    .racer:last-child {
        border-bottom: none;
    }

    .lane {
        width: 38px;
        height: 38px;
        border-radius: 9px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #f1f5f9;
        color: #0f172a;
        font-weight: 900;
        margin-right: 0.8rem;
        font-size: 1rem;
    }

    .racer-name {
        font-size: 0.98rem;
        font-weight: 700;
        color: #1e293b;
    }

    .prediction-card {
        background: #ffffff;
        border-radius: 18px;
        padding: 1.2rem 1.4rem;
        margin-top: 1.2rem;
        box-shadow: 0 5px 20px rgba(15, 23, 42, 0.07);
        border: 1px solid #e5e7eb;
    }

    .prediction-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.85rem 0;
        border-bottom: 1px solid #eef2f7;
    }

    .prediction-row:last-child {
        border-bottom: none;
    }

    .prediction-label {
        font-size: 0.9rem;
        font-weight: 800;
        color: #475569;
    }

    .prediction-number {
        font-size: 1.45rem;
        font-weight: 900;
        letter-spacing: 0.12em;
        color: #111827;
    }

    .main-label {
        color: #2563eb;
    }

    .counter-label {
        color: #f97316;
    }

    .hole-label {
        color: #dc2626;
    }

    .confidence-card {
        margin-top: 1.2rem;
        background: #111827;
        border-radius: 18px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 8px 25px rgba(15, 23, 42, 0.15);
    }

    .confidence-title {
        color: #94a3b8;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        margin-bottom: 0.35rem;
    }

    .confidence-stars {
        color: #60a5fa;
        font-size: 1.35rem;
        letter-spacing: 0.15em;
        font-weight: 900;
    }

    @media (max-width: 600px) {
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }

        .pro-title {
            font-size: 1.55rem;
        }

        .prediction-number {
            font-size: 1.25rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# タイトル
# =========================
st.markdown(
    '<div class="pro-title">🚤 やっちゃんの競艇AI予想PRO</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="pro-subtitle">BOAT RACE AI PREDICTION</div>',
    unsafe_allow_html=True,
)


# =========================
# 場
# =========================
stadium_name = st.selectbox(
    "場",
    list(data.STADIUMS.values()),
)

stadium_no = next(
    no for no, name in data.STADIUMS.items()
    if name == stadium_name
)


# =========================
# R
# =========================
race_no = st.selectbox(
    "R",
    list(range(1, 13)),
    format_func=lambda x: f"{x}R",
)


# =========================
# AI予想
# =========================
if st.button("🚤 AI予想する", use_container_width=True):

    # APIへ渡す日付は文字列に統一
    target_date = date.today().isoformat()

    with st.spinner("AIがレースを分析中…"):

        try:
            # データ取得
            raw = data.get_data(target_date)

            # 指定した場・Rを取得
            race = data.get_race(
                raw,
                stadium_no,
                race_no,
            )

            # データチェック
            data.validate_race(
                race,
                target_date,
                stadium_no,
                race_no,
            )

            # 6艇のデータ
            df = data.get_race_rows(
                race,
                stadium_no,
                race_no,
            )

            # 過去14日データ
            history = data.history14(target_date)

            # AI予想
            result, boat_probs = tri_ai(
                df,
                history,
            )

        except Exception as e:
            st.error(
                f"予想データの取得に失敗しました: {e}"
            )
            st.stop()


    # =========================
    # レース情報
    # =========================
    st.markdown(
        f"""
        <div class="race-card">
            <div class="race-title">
                {stadium_name}　{race_no}R
            </div>
        """,
        unsafe_allow_html=True,
    )

    for _, row in df.iterrows():

        lane = int(row["枠"])
        name = str(row["選手名"])

        st.markdown(
            f"""
            <div class="racer">
                <div class="lane">{lane}</div>
                <div class="racer-name">{name}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


    # =========================
    # AI予想
    # =========================
    st.markdown(
        '<div class="prediction-card">',
        unsafe_allow_html=True,
    )

    labels = [
        ("🎯 本命", "main-label", result[0]),
        ("🔥 対抗", "counter-label", result[1]),
        ("💥 穴", "hole-label", result[2]),
    ]

    for label, label_class, prediction in labels:

        st.markdown(
            f"""
            <div class="prediction-row">
                <div class="prediction-label {label_class}">
                    {label}
                </div>
                <div class="prediction-number">
                    {prediction}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


    # =========================
    # AI自信度
    # =========================
    confidence = "★★★☆☆"

    if boat_probs:
        top_prob = max(boat_probs.values())

        if top_prob < 0.35:
            confidence = "★★☆☆☆"
        elif top_prob < 0.45:
            confidence = "★★★☆☆"
        elif top_prob < 0.55:
            confidence = "★★★★☆"
        else:
            confidence = "★★★★★"

    st.markdown(
        f"""
        <div class="confidence-card">
            <div class="confidence-title">
                AI CONFIDENCE
            </div>
            <div class="confidence-stars">
                {confidence}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
            )
