import streamlit as st
import pandas as pd

from data import (
    STADIUM_NAMES,
    get_data,
    get_race,
    get_race_rows,
    history14,
    available_stadiums,
    available_races,
    jst_today,
)

from ai import tri_ai
from backtest import render_backtest


# =========================================================
# ページ設定
# =========================================================

st.set_page_config(
    page_title="やっちゃんの競艇AI予想PRO",
    page_icon="🚤",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
    <style>

    .stApp {
        background:
            radial-gradient(
                circle at top,
                #172033 0%,
                #0b1020 42%,
                #070b14 100%
            );
        color: #f5f7fb;
    }

    .block-container {
        max-width: 1100px;
        padding-top: 1.2rem;
        padding-bottom: 4rem;
    }

    /* -----------------------------------------
       タイトル
    ----------------------------------------- */

    .app-title {
        font-size: 2.15rem;
        font-weight: 900;
        letter-spacing: 0.02em;
        color: #ffffff;
        margin-bottom: 0.1rem;
    }

    .app-subtitle {
        color: #aeb8c9;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }

    /* -----------------------------------------
       セクションタイトル
    ----------------------------------------- */

    .section-title {
        font-size: 1.25rem;
        font-weight: 800;
        color: #ffffff;
        margin-top: 1.2rem;
        margin-bottom: 0.6rem;
    }

    /* -----------------------------------------
       レースヘッダー
    ----------------------------------------- */

    .race-header {
        background:
            linear-gradient(
                135deg,
                rgba(31, 41, 65, 0.98),
                rgba(13, 20, 35, 0.98)
            );
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 18px;
        padding: 18px 20px;
        margin: 14px 0 20px 0;
        box-shadow:
            0 10px 30px rgba(0,0,0,0.25);
    }

    .race-date {
        color: #b8c2d4;
        font-size: 0.95rem;
        margin-bottom: 4px;
    }

    .race-title {
        color: #ffffff;
        font-size: 1.65rem;
        font-weight: 900;
    }

    /* -----------------------------------------
       予想カード
    ----------------------------------------- */

    .prediction-card {
        background:
            linear-gradient(
                145deg,
                rgba(25, 34, 54, 0.98),
                rgba(13, 19, 32, 0.98)
            );
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 18px;
        padding: 20px;
        min-height: 150px;
        box-shadow:
            0 10px 28px rgba(0,0,0,0.22);
        margin-bottom: 12px;
    }

    .pred-label {
        font-size: 0.95rem;
        color: #b8c2d4;
        font-weight: 700;
        margin-bottom: 6px;
    }

    .pred-boat {
        font-size: 2rem;
        font-weight: 900;
        color: #ffffff;
    }

    .pred-small {
        color: #8f9bb0;
        font-size: 0.82rem;
        margin-top: 4px;
    }

    /* -----------------------------------------
       自信度
    ----------------------------------------- */

    .confidence-card {
        background:
            linear-gradient(
                135deg,
                rgba(24, 34, 54, 0.98),
                rgba(12, 18, 31, 0.98)
            );
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.09);
        padding: 14px 18px;
        margin: 12px 0 18px 0;
        text-align: center;
    }

    .confidence-label {
        color: #aeb8c9;
        font-size: 0.9rem;
        margin-bottom: 4px;
    }

    .confidence-stars {
        font-size: 1.5rem;
        letter-spacing: 0.12em;
        color: #ffffff;
        font-weight: 900;
    }

    /* -----------------------------------------
       出走艇
    ----------------------------------------- */

    .boat-card {
        background:
            linear-gradient(
                145deg,
                #1b263b,
                #111827
            );
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 16px;
        padding: 15px 14px;
        min-height: 145px;
        margin-bottom: 12px;
        box-shadow:
            0 8px 22px rgba(0,0,0,0.22);
    }

    .boat-number {
        font-size: 0.85rem;
        color: #9eabc0;
        font-weight: 700;
    }

    .boat-name {
        font-size: 1.05rem;
        font-weight: 900;
        color: #ffffff;
        margin-top: 6px;
        margin-bottom: 10px;
        min-height: 30px;
    }

    .boat-mark {
        font-size: 0.85rem;
        font-weight: 800;
        color: #ffffff;
        min-height: 22px;
    }

    /* -----------------------------------------
       ランキング
    ----------------------------------------- */

    .ranking-card {
        background:
            linear-gradient(
                145deg,
                #182238,
                #101725
            );
        border: 1px solid rgba(255,255,255,0.09);
        border-radius: 14px;
        padding: 13px 16px;
        margin-bottom: 8px;
    }

    .ranking-number {
        font-weight: 900;
        color: #ffffff;
        font-size: 1.05rem;
    }

    .ranking-boat {
        font-weight: 800;
        color: #ffffff;
        margin-left: 8px;
    }

    .ranking-prob {
        float: right;
        color: #d7deea;
        font-weight: 800;
    }

    /* -----------------------------------------
       説明
    ----------------------------------------- */

    .info-box {
        background: rgba(20, 29, 47, 0.82);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 14px 16px;
        color: #b9c4d5;
        line-height: 1.7;
        margin-bottom: 14px;
    }

    /* -----------------------------------------
       ボタン
    ----------------------------------------- */

    div.stButton > button {
        width: 100%;
        min-height: 52px;
        border-radius: 14px;
        font-weight: 900;
        font-size: 1.05rem;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# HTML表示ヘルパー
# =========================================================

def show_html(html: str):
    """
    Streamlit 1.49.1 の st.html を使用。
    HTMLがそのまま画面に表示される問題を防止。
    """
    st.html(html)


# =========================================================
# セッション状態
# =========================================================

if "prediction_cache" not in st.session_state:
    st.session_state.prediction_cache = {}

if "selected_race_key" not in st.session_state:
    st.session_state.selected_race_key = None


# =========================================================
# タイトル
# =========================================================

show_html(
    """
    <div class="app-title">
        🚤 やっちゃんの競艇AI予想PRO
    </div>
    <div class="app-subtitle">
        AI × 展示 × 選手成績 × モーター解析
    </div>
    """
)


# =========================================================
# 基準日
# =========================================================

try:
    target_date = jst_today()
except Exception:
    from datetime import date
    target_date = date.today()


# =========================================================
# 当日データ取得
# =========================================================

raw = get_data(target_date)


if raw is None:
    st.error(
        "⚠️ 本日のレースデータを取得できませんでした。"
    )

    st.info(
        "APIから本日のデータを取得できていません。"
        "少し時間を置いて再読み込みしてください。"
    )

    st.stop()


# =========================================================
# 開催場一覧
# =========================================================

stadium_numbers = available_stadiums(raw)


if not stadium_numbers:
    st.warning(
        "⚠️ 現在、開催場データを取得できません。"
    )
    st.stop()


# =========================================================
# 開催場選択
# =========================================================

st.markdown(
    '<div class="section-title">📍 開催場</div>',
    unsafe_allow_html=True,
)

stadium_options = []

for number in stadium_numbers:
    name = STADIUM_NAMES.get(
        int(number),
        f"{number}場",
    )

    stadium_options.append(
        (int(number), name)
    )


stadium_labels = [
    name
    for _, name in stadium_options
]


selected_stadium_name = st.selectbox(
    "開催場を選択",
    stadium_labels,
    label_visibility="visible",
)


selected_stadium = next(
    number
    for number, name in stadium_options
    if name == selected_stadium_name
)


# =========================================================
# レース一覧
# =========================================================

race_numbers = available_races(
    raw,
    selected_stadium,
)


if not race_numbers:
    st.warning(
        f"⚠️ {selected_stadium_name}のレースデータがありません。"
    )
    st.stop()


race_options = [
    f"{int(race)}R"
    for race in race_numbers
]


st.markdown(
    '<div class="section-title">🏁 レース</div>',
    unsafe_allow_html=True,
)


selected_race_label = st.selectbox(
    "レースを選択",
    race_options,
    label_visibility="visible",
)


selected_race = int(
    selected_race_label.replace("R", "")
)


# =========================================================
# 現在のレースキー
# =========================================================

race_key = (
    f"{target_date.isoformat()}_"
    f"{selected_stadium}_"
    f"{selected_race}"
)


# =========================================================
# レース選択が変わったら以前の予想を表示しない
# =========================================================

if (
    st.session_state.selected_race_key
    != race_key
):
    st.session_state.selected_race_key = race_key


# =========================================================
# 現在のレース
# =========================================================

race = get_race(
    raw,
    selected_stadium,
    selected_race,
)


if race is None:
    st.warning(
        "⚠️ 選択したレースのデータを取得できませんでした。"
    )
    st.stop()


# =========================================================
# 予想開始前
# =========================================================

prediction = st.session_state.prediction_cache.get(
    race_key
)


# =========================================================
# AI予想セクション
# =========================================================

st.markdown(
    '<div class="section-title">🤖 AI予想</div>',
    unsafe_allow_html=True,
)


# =========================================================
# 予想開始前は説明＋ボタンだけ
# =========================================================

if prediction is None:

    st.info(
        "👆 「AI予想開始」を押すと、"
        "展示・選手成績・モーターなどを解析します。"
    )

    predict_clicked = st.button(
        "🚀 AI予想開始",
        type="primary",
        use_container_width=True,
        key="predict_button",
    )

    if predict_clicked:

        with st.spinner(
            "🤖 AIが展示・選手成績・モーターを解析中..."
        ):

            # -----------------------------------------
            # 出走データ
            # -----------------------------------------

            race_df = get_race_rows(
                race
            )

            if race_df is None or race_df.empty:
                st.error(
                    "⚠️ 出走艇データを取得できませんでした。"
                )
                st.stop()

            # -----------------------------------------
            # 過去14日データ
            # -----------------------------------------

            try:
                hist = history14(
                    selected_stadium,
                    selected_race,
                    target_date,
                )
            except TypeError:
                # 旧形式との互換
                try:
                    hist = history14(
                        selected_stadium,
                        selected_race,
                    )
                except Exception:
                    hist = pd.DataFrame()

            except Exception:
                hist = pd.DataFrame()

            # -----------------------------------------
            # AI予想
            # -----------------------------------------

            prediction = tri_ai(
                race_df,
                hist,
                selected_stadium,
            )

            # -----------------------------------------
            # 保存
            # -----------------------------------------

            st.session_state.prediction_cache[
                race_key
            ] = prediction

        # 再描画
        st.rerun()


# =========================================================
# ここから予想結果
# =========================================================

if prediction is not None:

    # =====================================================
    # レース情報
    # =====================================================

    show_html(
        f"""
        <div class="race-header">
            <div class="race-date">
                🗓 {target_date.strftime("%Y-%m-%d")}
            </div>
            <div class="race-title">
                📍 {selected_stadium_name}　{selected_race}R
            </div>
        </div>
        """
    )


    # =====================================================
    # 本命・対抗・穴
    # =====================================================

    main = int(
        prediction.get("main", 1)
    )

    counter = int(
        prediction.get("counter", 2)
    )

    hole = int(
        prediction.get("hole", 3)
    )


    pred_cols = st.columns(3)


    with pred_cols[0]:

        show_html(
            f"""
            <div class="prediction-card">
                <div class="pred-label">
                    🎯 本命
                </div>
                <div class="pred-boat">
                    {main}号艇
                </div>
                <div class="pred-small">
                    AI最上位評価
                </div>
            </div>
            """
        )


    with pred_cols[1]:

        show_html(
            f"""
            <div class="prediction-card">
                <div class="pred-label">
                    🔥 対抗
                </div>
                <div class="pred-boat">
                    {counter}号艇
                </div>
                <div class="pred-small">
                    AI第2位評価
                </div>
            </div>
            """
        )


    with pred_cols[2]:

        show_html(
            f"""
            <div class="prediction-card">
                <div class="pred-label">
                    💥 穴
                </div>
                <div class="pred-boat">
                    {hole}号艇
                </div>
                <div class="pred-small">
                    穴候補として選択
                </div>
            </div>
            """
        )


    # =====================================================
    # 自信度
    # =====================================================

    confidence = float(
        prediction.get(
            "confidence",
            0.5,
        )
    )

    stars = int(
        prediction.get(
            "stars",
            3,
        )
    )

    stars = max(
        1,
        min(5, stars),
    )

    star_text = (
        "★" * stars
        + "☆" * (5 - stars)
    )

    confidence_percent = round(
        confidence * 100,
        1,
    )


    show_html(
        f"""
        <div class="confidence-card">
            <div class="confidence-label">
                🤖 AI自信度　{confidence_percent}%
            </div>
            <div class="confidence-stars">
                {star_text}
            </div>
        </div>
        """
    )


    # =====================================================
    # 出走艇
    # =====================================================

    st.markdown(
        '<div class="section-title">🚤 出走艇</div>',
        unsafe_allow_html=True,
    )


    race_df = prediction.get(
        "data"
    )

    if race_df is None:
        race_df = get_race_rows(
            race
        )


    if race_df is None:
        race_df = pd.DataFrame()


    # 6艇表示
    for start in range(0, 6, 3):

        cols = st.columns(3)

        for offset, col in enumerate(cols):

            boat_no = start + offset + 1

            with col:

                row = None

                if (
                    isinstance(
                        race_df,
                        pd.DataFrame,
                    )
                    and not race_df.empty
                    and len(race_df) >= boat_no
                ):
                    try:
                        row = race_df.iloc[
                            boat_no - 1
                        ]
                    except Exception:
                        row = None


                if row is not None:

                    name = str(
                        row.get(
                            "選手名",
                            f"{boat_no}号艇",
                        )
                    )

                else:

                    name = (
                        f"{boat_no}号艇"
                    )


                marks = []

                if boat_no == main:
                    marks.append(
                        "🎯 本命"
                    )

                if boat_no == counter:
                    marks.append(
                        "🔥 対抗"
                    )

                if boat_no == hole:
                    marks.append(
                        "💥 穴"
                    )

                mark_text = " ".join(
                    marks
                )


                show_html(
                    f"""
                    <div class="boat-card">
                        <div class="boat-number">
                            {boat_no}号艇
                        </div>

                        <div class="boat-name">
                            {name}
                        </div>

                        <div class="boat-mark">
                            {mark_text}
                        </div>
                    </div>
                    """
                )


    # =====================================================
    # AI予測確率
    # =====================================================

    st.markdown(
        '<div class="section-title">📊 AI予測確率</div>',
        unsafe_allow_html=True,
    )


    boat_probs = prediction.get(
        "boat_probs",
        {},
    )


    probability_rows = []

    for boat in range(1, 7):

        prob = float(
            boat_probs.get(
                boat,
                0.0,
            )
        )

        probability_rows.append(
            {
                "艇": f"{boat}号艇",
                "AI確率": prob,
            }
        )


    prob_df = pd.DataFrame(
        probability_rows
    )


    st.bar_chart(
        prob_df.set_index("艇"),
        y="AI確率",
        height=330,
    )


    # =====================================================
    # AI総合ランキング
    # =====================================================

    st.markdown(
        '<div class="section-title">🏆 AI総合ランキング</div>',
        unsafe_allow_html=True,
    )


    ranking = prediction.get(
        "ranking",
        [],
    )


    if not ranking:

        ranking = [
            1,
            2,
            3,
            4,
            5,
            6,
        ]


    for rank, boat in enumerate(
        ranking,
        start=1,
    ):

        boat = int(boat)

        prob = float(
            boat_probs.get(
                boat,
                0.0,
            )
        )


        show_html(
            f"""
            <div class="ranking-card">
                <span class="ranking-number">
                    {rank}位
                </span>

                <span class="ranking-boat">
                    {boat}号艇
                </span>

                <span class="ranking-prob">
      
