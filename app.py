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

    /* 全体 */
    .stApp {
        background: #f3f5f8;
    }

    .block-container {
        max-width: 720px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    /* フォント */
    html, body, [class*="css"] {
        font-family:
            "Noto Sans JP",
            "Hiragino Kaku Gothic ProN",
            "Yu Gothic",
            "Meiryo",
            sans-serif;
    }

    /* タイトル */
    .pro-title {
        text-align: center;
        font-size: 30px;
        font-weight: 900;
        letter-spacing: 0.03em;
        color: #111827;
        margin-bottom: 6px;
    }

    .pro-subtitle {
        text-align: center;
        font-size: 13px;
        color: #6b7280;
        margin-bottom: 24px;
    }

    /* 選択エリア */
    .select-label {
        font-size: 13px;
        font-weight: 700;
        color: #374151;
        margin-bottom: 4px;
    }

    /* AI予想ボタン */
    div.stButton > button {
        width: 100%;
        height: 54px;
        border-radius: 14px;
        border: none;
        background: #2563eb;
        color: white;
        font-size: 17px;
        font-weight: 800;
        box-shadow: 0 5px 14px rgba(37, 99, 235, 0.20);
        transition: 0.2s;
    }

    div.stButton > button:hover {
        background: #1d4ed8;
        color: white;
        transform: translateY(-1px);
    }

    /* 区切り */
    .divider {
        height: 1px;
        background: #d9dee7;
        margin: 26px 0;
    }

    /* レースカード */
    .race-card {
        background: white;
        border-radius: 18px;
        padding: 20px 22px;
        box-shadow: 0 4px 15px rgba(15, 23, 42, 0.06);
        margin-bottom: 20px;
    }

    .race-title {
        font-size: 22px;
        font-weight: 900;
        color: #111827;
        margin-bottom: 16px;
    }

    .racer-row {
        display: flex;
        align-items: center;
        padding: 10px 0;
        border-bottom: 1px solid #eef0f4;
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
        background: #f1f5f9;
        color: #111827;
        font-weight: 900;
        margin-right: 12px;
    }

    .racer-name {
        font-weight: 700;
    }

    /* 予想カード */
    .prediction-card {
        background: white;
        border-radius: 18px;
        padding: 18px 22px;
        margin-bottom: 12px;
        box-shadow: 0 4px 15px rgba(15, 23, 42, 0.05);
    }

    .prediction-label {
        font-size: 14px;
        font-weight: 800;
        margin-bottom: 6px;
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

    /* 自信度 */
    .confidence-card {
        background: #111827;
        border-radius: 18px;
        padding: 20px;
        text-align: center;
        color: white;
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
    }

    /* バックテスト */
    .backtest-title {
        font-size: 18px;
        font-weight: 900;
        color: #111827;
        margin-bottom: 8px;
    }

    /* モバイル */
    @media (max-width: 600px) {

        .block-container {
            padding-left: 14px;
            padding-right: 14px;
            padding-top: 1.2rem;
        }

        .pro-title {
            font-size: 25px;
        }

        .race-card,
        .prediction-card {
            padding: 16px;
        }

        .prediction-value {
            font-size: 24px;
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


# 選択された場名 → 場番号
stadium_no = next(
    (
        number
        for number, name in data.STADIUMS.items()
        if name == stadium_name_selected
    ),
    None,
)


# =========================================================
# AI予想ボタン
# =========================================================

predict_button = st.button(
    "🚤 AI予想する",
    use_container_width=True,
)


# =========================================================
# AI予想
# =========================================================

if predict_button:

    target_date = date.today().isoformat()

    with st.spinner("AIがレースを分析しています..."):

        try:
            # ---------------------------------------------
            # データ取得
            # ---------------------------------------------

            raw = data.get_data(target_date)

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

            # ---------------------------------------------
            # レースデータ確認
            # ---------------------------------------------

            if not data.validate_race(
                race,
                stadium_no,
                race_no,
            ):
                st.error("レースデータの確認に失敗しました。")
                st.stop()

            # ---------------------------------------------
            # 6艇データ
            # ---------------------------------------------

            race_rows = data.get_race_rows(race)

            if not race_rows or len(race_rows) != 6:
                st.error("6艇分の選手データを取得できませんでした。")
                st.stop()

            # ---------------------------------------------
            # 過去データ
            # ---------------------------------------------

            history = data.history14(
                target_date
            )

            # ---------------------------------------------
            # AI予想
            # ---------------------------------------------

            prediction = tri_ai(
                race_rows,
                history,
            )

            if not prediction:
                st.error("AI予想を作成できませんでした。")
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
        f'<div class="race-title">'
        f'{stadium_name_selected} {race_no}R'
        f'</div>',
        unsafe_allow_html=True,
    )

    # 6艇表示
    for i, racer in enumerate(race_rows, start=1):

        racer_name = (
            racer.get("選手名")
            or racer.get("name")
            or "選手情報なし"
        )

        st.markdown(
            f'''
            <div class="racer-row">
                <span class="boat-number">{i}</span>
                <span class="racer-name">{racer_name}</span>
            </div>
            ''',
            unsafe_allow_html=True,
        )

    st.markdown(
        '</div>',
        unsafe_allow_html=True,
    )


    # =====================================================
    # AI予想結果
    # =====================================================

    main = prediction.get("main")
    counter = prediction.get("counter")
    hole = prediction.get("hole")

    # -----------------------------------------------------
    # 本命
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # 対抗
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # 穴
    # -----------------------------------------------------

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

with st.expander("📊 AIの実力を検証する"):

    st.markdown(
        '<div class="backtest-title">過去レースでAIを検証</div>',
        unsafe_allow_html=True,
    )

    st.caption(
        "過去のレースを使って、本命・対抗・穴の的中率を確認できます。"
    )

    backtest.render_backtest()
