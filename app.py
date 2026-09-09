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
)


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
    <style>

    .stApp {
        background: #f4f7fb;
    }

    .block-container {
        max-width: 760px;
        padding-top: 5.7rem !important;
        padding-bottom: 3rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    header[data-testid="stHeader"] {
        background: rgba(244,247,251,0.96);
    }

    /* ---------- title ---------- */

    .pro-title {
        color: #0f172a;
        font-size: 30px;
        font-weight: 950;
        line-height: 1.25;
        margin-bottom: 4px;
    }

    .pro-subtitle {
        color: #64748b;
        font-size: 13px;
        font-weight: 700;
        margin-bottom: 14px;
    }

    .today-badge {
        display: inline-block;
        background: #eaf2ff;
        color: #1458c5;
        border: 1px solid #c8dcff;
        border-radius: 999px;
        padding: 7px 13px;
        font-size: 12px;
        font-weight: 850;
        margin-bottom: 20px;
    }

    /* ---------- labels ---------- */

    .section-title {
        color: #0f172a;
        font-size: 14px;
        font-weight: 900;
        margin-top: 8px;
        margin-bottom: 6px;
    }

    /* ---------- selectbox ---------- */

    div[data-testid="stSelectbox"] label {
        color: #0f172a !important;
        font-weight: 850 !important;
    }

    div[data-testid="stSelectbox"] div[role="combobox"] {
        background: #ffffff !important;
        color: #111827 !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 12px !important;
        min-height: 46px !important;
        box-shadow: 0 2px 8px rgba(15,23,42,0.04);
    }

    div[data-testid="stSelectbox"] div[role="combobox"] * {
        color: #111827 !important;
    }

    /* ---------- buttons ---------- */

    div[data-testid="stButton"] button {
        width: 100%;
        min-height: 52px;
        border-radius: 13px;
        font-size: 16px;
        font-weight: 950;
    }

    /* ---------- race header ---------- */

    .race-header {
        background: #0f172a;
        color: #ffffff;
        border-radius: 14px;
        padding: 14px 16px;
        margin-top: 20px;
        margin-bottom: 12px;
        font-size: 20px;
        font-weight: 950;
    }

    /* ---------- boats ---------- */

    .boat-list {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        overflow: hidden;
        margin-bottom: 16px;
    }

    .boat-row {
        display: flex;
        align-items: center;
        min-height: 44px;
        padding: 0 14px;
        border-bottom: 1px solid #edf1f5;
        color: #1e293b;
        font-size: 14px;
        font-weight: 750;
    }

    .boat-row:last-child {
        border-bottom: none;
    }

    .boat-number {
        width: 42px;
        color: #2563eb;
        font-weight: 950;
    }

    /* ---------- predictions ---------- */

    .prediction-box {
        background: #ffffff;
        border: 1px solid #dce4ef;
        border-radius: 14px;
        padding: 15px;
        margin-bottom: 10px;
    }

    .main-box {
        border-left: 5px solid #2563eb;
    }

    .counter-box {
        border-left: 5px solid #64748b;
    }

    .hole-box {
        border-left: 5px solid #0f172a;
    }

    .prediction-label {
        color: #64748b;
        font-size: 13px;
        font-weight: 900;
        margin-bottom: 4px;
    }

    .prediction-value {
        color: #0f172a;
        font-size: 25px;
        font-weight: 950;
        letter-spacing: 1px;
    }

    /* ---------- confidence ---------- */

    .confidence-box {
        background: #0f172a;
        color: #ffffff;
        border-radius: 14px;
        padding: 16px;
        text-align: center;
        margin-top: 15px;
    }

    .confidence-title {
        color: #cbd5e1;
        font-size: 12px;
        font-weight: 750;
    }

    .confidence-stars {
        font-size: 24px;
        letter-spacing: 3px;
    }

    /* ---------- expander ---------- */

    div[data-testid="stExpander"] {
        background: #ffffff !important;
        border: 1px solid #dbe3ee !important;
        border-radius: 14px !important;
        margin-top: 24px;
        overflow: hidden;
    }

    div[data-testid="stExpander"] summary {
        color: #0f172a !important;
        font-weight: 900 !important;
    }

    div[data-testid="stExpander"] summary span {
        color: #0f172a !important;
    }

    @media (max-width: 640px) {

        .block-container {
            padding-top: 5.1rem !important;
        }

        .pro-title {
            font-size: 25px;
        }

        .race-header {
            font-size: 18px;
        }

        .prediction-value {
            font-size: 22px;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# JST
# =========================================================

JST = ZoneInfo("Asia/Tokyo")

now = datetime.now(JST)
today = now.date()
target_date = today.isoformat()


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
# 今日のデータ
# =========================================================

try:
    raw_today = data.get_data(target_date)
except Exception:
    raw_today = None


if raw_today is None:
    st.warning(
        "本日のレースデータを取得できませんでした。"
    )


# =========================================================
# 開催場
# =========================================================

stadium_numbers = list(data.STADIUMS.keys())

stadium_labels = [
    data.stadium_name(no)
    for no in stadium_numbers
]

st.markdown(
    '<div class="section-title">開催場</div>',
    unsafe_allow_html=True,
)

selected_stadium_name = st.selectbox(
    "開催場",
    stadium_labels,
    label_visibility="collapsed",
    key="stadium_select",
)

selected_stadium_no = stadium_numbers[
    stadium_labels.index(selected_stadium_name)
]


# =========================================================
# レース
# =========================================================

st.markdown(
    '<div class="section-title">レース</div>',
    unsafe_allow_html=True,
)

selected_race = st.selectbox(
    "レース",
    list(range(1, 13)),
    format_func=lambda x: f"{x}R",
    label_visibility="collapsed",
    key="race_select",
)


# =========================================================
# 選択されたレースを取得
# =========================================================

race = None

if raw_today:

    try:
        race = data.get_race(
            raw_today,
            selected_stadium_no,
            selected_race,
        )
    except Exception:
        race = None


# =========================================================
# レース情報を選択時点で表示
# =========================================================

if race:

    try:
        race_rows_preview = data.get_race_rows(
            race,
            selected_stadium_no,
            selected_race,
        )
    except TypeError:
        try:
            race_rows_preview = data.get_race_rows(race)
        except Exception:
            race_rows_preview = None
    except Exception:
        race_rows_preview = None

    if (
        race_rows_preview is not None
        and len(race_rows_preview) == 6
    ):

        st.markdown(
            f"""
            <div class="race-header">
                {selected_stadium_name} {selected_race}R
            </div>
            """,
            unsafe_allow_html=True,
        )

        boat_html = '<div class="boat-list">'

        for _, row in race_rows_preview.iterrows():

            lane = row.get("枠", "")

            name = (
                row.get("選手名")
                or row.get("選手")
                or row.get("名前")
                or "選手"
            )

            boat_html += (
                '<div class="boat-row">'
                f'<div class="boat-number">{lane}号艇</div>'
                f'<div>{name}</div>'
                '</div>'
            )

        boat_html += "</div>"

        st.markdown(
            boat_html,
            unsafe_allow_html=True,
        )


# =========================================================
# AI予想
# =========================================================

predict_clicked = st.button(
    "🚤 AI予想する",
    type="primary",
    use_container_width=True,
)


if predict_clicked:

    if not raw_today:
        st.error(
            "本日のレースデータが取得できません。"
        )
        st.stop()

    if not race:
        st.warning(
            f"{selected_stadium_name} {selected_race}R "
            "のデータがまだ公開されていません。"
        )
        st.stop()

    try:
        valid = data.validate_race(
            race,
            selected_stadium_no,
            selected_race,
            target_date,
        )
    except TypeError:

        try:
            valid = data.validate_race(
                race,
                selected_stadium_no,
                selected_race,
            )
        except Exception:
            valid = True

    except Exception:
        valid = False

    if not valid:
        st.warning(
            "6艇分の出走データが揃っていません。"
        )
        st.stop()

    try:
        race_rows = data.get_race_rows(
            race,
            selected_stadium_no,
            selected_race,
        )
    except TypeError:
        race_rows = data.get_race_rows(race)

    if race_rows is None or len(race_rows) != 6:
        st.warning(
            "6艇分のデータを取得できませんでした。"
        )
        st.stop()

    try:
        history = data.history14(target_date)
    except Exception:
        history = None

    try:
        prediction = tri_ai(
            race_rows,
            history,
        )
    except Exception as e:
        st.error(
            "AI予想の計算中にエラーが発生しました。"
        )
        st.exception(e)
        st.stop()

    # 新形式
    if isinstance(prediction, dict):

        main = prediction.get("main", [])
        counter = prediction.get("counter", [])
        hole = prediction.get("hole", [])
        boat_probs = prediction.get("boat_probs", {})

    # 旧形式
    elif isinstance(prediction, tuple):

        combinations = (
            prediction[0]
            if len(prediction) > 0
            else []
        )

        boat_probs = (
            prediction[1]
            if len(prediction) > 1
            else {}
        )

        main = (
            combinations[0]
            if len(combinations) > 0
            else []
        )

        counter = (
            combinations[1]
            if len(combinations) > 1
            else []
        )

        hole = (
            combinations[2]
            if len(combinations) > 2
            else []
        )

    else:

        main = []
        counter = []
        hole = []
        boat_probs = {}

    def combo_text(combo):

        if not combo:
            return "—"

        return "-".join(
            str(x)
            for x in combo
        )

    st.markdown(
        f"""
        <div class="prediction-box main-box">
            <div class="prediction-label">🎯 本命</div>
            <div class="prediction-value">
                {combo_text(main)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="prediction-box counter-box">
            <div class="prediction-label">🔥 対抗</div>
            <div class="prediction-value">
                {combo_text(counter)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="prediction-box hole-box">
            <div class="prediction-label">💥 穴</div>
            <div class="prediction-value">
                {combo_text(hole)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 自信度
    confidence = 0.0

    if isinstance(boat_probs, dict) and boat_probs:

        try:
            confidence = max(
                float(v)
                for v in boat_probs.values()
            )
        except Exception:
            confidence = 0.0

    if confidence >= 0.35:
        stars = "★★★★★"
    elif confidence >= 0.28:
        stars = "★★★★☆"
    elif confidence >= 0.22:
        stars = "★★★☆☆"
    elif confidence >= 0.16:
        stars = "★★☆☆☆"
    else:
        stars = "★☆☆☆☆"

    st.markdown(
        f"""
        <div class="confidence-box">
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
# バックテスト
# =========================================================

with st.expander(
    "📊 AIの実力を検証する",
    expanded=False,
):

    backtest.render_backtest()
