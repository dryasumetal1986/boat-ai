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
)


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
    <style>

    /* ================================================
       全体
    ================================================ */

    .stApp {
        background: #f4f6f9;
        color: #111827;
    }

    .block-container {
        max-width: 720px;
        padding-top: 1.5rem;
        padding-bottom: 4rem;
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

    /* 通常テキストを黒系に */
    .stMarkdown,
    .stCaption,
    .stText,
    p,
    label {
        color: #111827;
    }


    /* ================================================
       タイトル
    ================================================ */

    .pro-title {
        text-align: center;
        font-size: 30px;
        font-weight: 900;
        letter-spacing: 0.02em;
        color: #111827;
        margin-top: 10px;
        margin-bottom: 6px;
        line-height: 1.3;
    }

    .pro-subtitle {
        text-align: center;
        font-size: 13px;
        font-weight: 600;
        color: #6b7280;
        margin-bottom: 28px;
    }


    /* ================================================
       ラベル
    ================================================ */

    .select-label {
        font-size: 13px;
        font-weight: 800;
        color: #374151;
        margin-bottom: 5px;
    }


    /* ================================================
       Selectbox
    ================================================ */

    div[data-baseweb="select"] > div {
        background: #ffffff !important;
        border: 1px solid #d7dce4 !important;
        border-radius: 12px !important;
        color: #111827 !important;
        min-height: 50px;
    }

    div[data-baseweb="select"] span {
        color: #111827 !important;
    }

    div[data-baseweb="select"] svg {
        fill: #111827 !important;
    }


    /* ================================================
       AI予想ボタン
    ================================================ */

    div.stButton > button {
        width: 100%;
        min-height: 54px;
        border-radius: 14px;
        border: none;
        background: #2563eb;
        color: #ffffff !important;
        font-size: 17px;
        font-weight: 800;
        box-shadow:
            0 7px 18px rgba(37, 99, 235, 0.22);
        transition: 0.15s;
    }

    div.stButton > button p {
        color: #ffffff !important;
    }

    div.stButton > button:hover {
        background: #1d4ed8;
        color: #ffffff !important;
        transform: translateY(-1px);
    }


    /* ================================================
       区切り
    ================================================ */

    .divider {
        height: 1px;
        background: #d9dee7;
        margin: 28px 0;
    }


    /* ================================================
       レースカード
    ================================================ */

    .race-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 20px 22px;
        box-shadow:
            0 5px 18px rgba(15, 23, 42, 0.06);
        margin-bottom: 20px;
    }

    .race-title {
        font-size: 22px;
        font-weight: 900;
        color: #111827;
        margin-bottom: 15px;
    }

    .racer-row {
        display: flex;
        align-items: center;
        padding: 10px 0;
        border-bottom: 1px solid #edf0f4;
        font-size: 15px;
        color: #374151;
    }

    .racer-row:last-child {
        border-bottom: none;
    }

    .boat-number {
        width: 32px;
        height: 32px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
        background: #eef2f7;
        color: #111827;
        font-weight: 900;
        margin-right: 12px;
        flex-shrink: 0;
    }

    .racer-name {
        font-weight: 700;
        color: #111827;
    }


    /* ================================================
       予想カード
    ================================================ */

    .prediction-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 18px 22px;
        margin-bottom: 12px;
        box-shadow:
            0 4px 15px rgba(15, 23, 42, 0.05);
    }

    .prediction-label {
        font-size: 14px;
        font-weight: 900;
        margin-bottom: 5px;
    }

    .prediction-value {
        font-size: 27px;
        font-weight: 900;
        letter-spacing: 0.06em;
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


    /* ================================================
       自信度
    ================================================ */

    .confidence-card {
        background: #111827;
        border-radius: 18px;
        padding: 20px;
        text-align: center;
        color: #ffffff;
        margin-top: 18px;
    }

    .confidence-title {
        font-size: 13px;
        color: #cbd5e1;
        margin-bottom: 6px;
    }

    .confidence-stars {
        font-size: 25px;
        letter-spacing: 0.08em;
        color: #ffffff;
    }


    /* ================================================
       バックテスト Expander
    ================================================ */

    [data-testid="stExpander"] {
        background: #ffffff !important;
        border: 1px solid #dfe4eb !important;
        border-radius: 16px !important;
        overflow: hidden;
        box-shadow:
            0 4px 15px rgba(15, 23, 42, 0.05);
    }

    [data-testid="stExpander"] details {
        background: #ffffff !important;
    }

    [data-testid="stExpander"] summary {
        background: #111827 !important;
        color: #ffffff !important;
        padding: 17px 18px !important;
        font-weight: 800 !important;
        font-size: 16px !important;
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


    /* ================================================
       バックテスト見出し
    ================================================ */

    .backtest-title {
        font-size: 20px;
        font-weight: 900;
        color: #111827 !important;
        margin-bottom: 6px;
    }


    /* ================================================
       Radio
    ================================================ */

    div[role="radiogroup"] {
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 12px 14px;
    }

    div[role="radiogroup"] label {
        color: #111827 !important;
    }

    div[role="radiogroup"] label p {
        color: #111827 !important;
        font-weight: 700;
    }


    /* ================================================
       Info
    ================================================ */

    div[data-testid="stAlert"] {
        border-radius: 12px;
    }


    /* ================================================
       Metric
    ================================================ */

    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 14px;
    }

    [data-testid="stMetricLabel"] {
        color: #6b7280 !important;
    }

    [data-testid="stMetricValue"] {
        color: #111827 !important;
        font-weight: 900;
    }


    /* ================================================
       DataFrame
    ================================================ */

    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
    }


    /* ================================================
       Download
    ================================================ */

    .stDownloadButton button {
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        color: #111827 !important;
    }

    .stDownloadButton button p {
        color: #111827 !important;
    }


    /* ================================================
       Mobile
    ================================================ */

    @media (max-width: 600px) {

        .block-container {
            padding-left: 14px;
            padding-right: 14px;
            padding-top: 1rem;
        }

        .pro-title {
            font-size: 24px;
        }

        .pro-subtitle {
            font-size: 12px;
            margin-bottom: 22px;
        }

        .race-card,
        .prediction-card {
            padding: 16px;
        }

        .prediction-value {
            font-size: 24px;
        }

        [data-testid="stExpanderDetails"] {
            padding: 16px !important;
        }

        div[role="radiogroup"] {
            padding: 10px;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# タイトル
# =========================================================

st.markdown(
    '<div class="pro-title">🚤 やっちゃんの競艇AI予想PRO</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="pro-subtitle">データ分析型・競艇AI予想システム</div>',
    unsafe_allow_html=True,
)


# =========================================================
# 場・レース選択
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


# 場名 → 場番号
stadium_no = next(
    (
        number
        for number, name in data.STADIUMS.items()
        if name == stadium_name_selected
    ),
    None,
)


# =========================================================
# AI予想
# =========================================================

predict_button = st.button(
    "🚤 AI予想する",
    use_container_width=True,
)


if predict_button:

    target_date = date.today().isoformat()

    with st.spinner(
        "AIがレースを分析しています..."
    ):

        try:

            raw = data.get_data(
                target_date
            )

            race = data.get_race(
                raw,
                stadium_no,
                race_no,
            )

            if not race:

                st.error(
                    f"{stadium_name_selected} {race_no}R のデータが見つかりません。"
                )
                st.stop()

            if not data.validate_race(
                race,
                stadium_no,
                race_no,
            ):

                st.error(
                    "レースデータの確認に失敗しました。"
                )
                st.stop()

            race_rows = data.get_race_rows(
                race
            )

            if not race_rows or len(race_rows) != 6:

                st.error(
                    "6艇分の選手データを取得できませんでした。"
                )
                st.stop()

            history = data.history14(
                target_date
            )

            prediction = tri_ai(
                race_rows,
                history,
            )

            if not prediction:

                st.error(
                    "AI予想を作成できませんでした。"
                )
                st.stop()

        except Exception as e:

            st.error(
                "データ取得またはAI予想中にエラーが発生しました。"
            )

            st.exception(e)
            st.stop()


    # =====================================================
    # レース情報
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
        f'''
        <div class="race-title">
            {stadium_name_selected} {race_no}R
        </div>
        ''',
        unsafe_allow_html=True,
    )

    for i, racer in enumerate(
        race_rows,
        start=1
    ):

        racer_name = (
            racer.get("選手名")
            or racer.get("name")
            or "選手情報なし"
        )

        st.markdown(
            f'''
            <div class="racer-row">
                <span class="boat-number">
                    {i}
                </span>
                <span class="racer-name">
                    {racer_name}
                </span>
            </div>
            ''',
            unsafe_allow_html=True,
        )

    st.markdown(
        '</div>',
        unsafe_allow_html=True,
    )


    # =====================================================
    # 予想
    # =====================================================

    main = prediction.get("main")
    counter = prediction.get("counter")
    hole = prediction.get("hole")


    if main:

        main_text = "-".join(
            map(str, main)
        )

        st.markdown(
            f'''
            <div class="prediction-card">
                <div class="prediction-label main-label">
                    🎯 本命
                </div>

                <div class="prediction-value">
                    {main_text}
                </div>
            </div>
            ''',
            unsafe_allow_html=True,
        )


    if counter:

        counter_text = "-".join(
            map(str, counter)
        )

        st.markdown(
            f'''
            <div class="prediction-card">
                <div class="prediction-label counter-label">
                    🔥 対抗
                </div>

                <div class="prediction-value">
                    {counter_text}
                </div>
            </div>
            ''',
            unsafe_allow_html=True,
        )


    if hole:

        hole_text = "-".join(
            map(str, hole)
        )

        st.markdown(
            f'''
            <div class="prediction-card">
                <div class="prediction-label hole-label">
                    💥 穴
                </div>

                <div class="prediction-value">
                    {hole_text}
                </div>
            </div>
            ''',
            unsafe_allow_html=True,
        )


    # =====================================================
    # 自信度
    # =====================================================

    boat_probs = prediction.get(
        "boat_probs",
        []
    )

    confidence = "★★★☆☆"

    try:

        if boat_probs:

            top_prob = max(
                float(x)
                for x in boat_probs
            )

            if top_prob >= 0.45:
                confidence = "★★★★★"

            elif top_prob >= 0.38:
                confidence = "★★★★☆"

            elif top_prob >= 0.32:
                confidence = "★★★☆☆"

            elif top_prob >= 0.26:
                confidence = "★★☆☆☆"

            else:
                confidence = "★☆☆☆☆"

    except Exception:

        confidence = "★★★☆☆"


    st.markdown(
        f'''
        <div class="confidence-card">

            <div class="confidence-title">
                AI自信度
            </div>

            <div class="confidence-stars">
                {confidence}
            </div>

        </div>
        ''',
        unsafe_allow_html=True,
    )


# =========================================================
# AIバックテスト
# =========================================================

st.markdown(
    '<div class="divider"></div>',
    unsafe_allow_html=True,
)


with st.expander(
    "📊 AIの実力を検証する"
):

    st.markdown(
        '''
        <div class="backtest-title">
            📊 AI実力テスト
        </div>
        ''',
        unsafe_allow_html=True,
    )

    st.caption(
        "日付を指定せず、直近のレース数だけ選んでAIを検証できます。"
    )

    backtest.render_backtest()
