import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo

import data
from ai import tri_ai
import backtest


st.set_page_config(
    page_title="やっちゃんの競艇AI予想PRO",
    page_icon="🚤",
    layout="centered",
)


# =========================
# CSS
# =========================

st.markdown("""
<style>

.stApp {
    background: #f4f7fb;
}

.block-container {
    max-width: 760px;
    padding-top: 5rem !important;
    padding-bottom: 3rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}

/* タイトル */

.title {
    font-size: 28px;
    font-weight: 900;
    color: #0f172a !important;
    margin-bottom: 3px;
}

.subtitle {
    font-size: 13px;
    font-weight: 700;
    color: #64748b !important;
    margin-bottom: 12px;
}

.date-badge {
    display: inline-block;
    background: #eaf2ff;
    border: 1px solid #c8dcff;
    border-radius: 20px;
    padding: 7px 13px;
    color: #1458c5 !important;
    font-size: 12px;
    font-weight: 900;
    margin-bottom: 20px;
}

/* ラベル */

.label {
    color: #0f172a !important;
    font-size: 14px;
    font-weight: 900;
    margin: 8px 0 6px;
}

/* レース */

.race-title {
    background: #0f172a;
    color: #ffffff !important;
    border-radius: 13px;
    padding: 13px 16px;
    font-size: 20px;
    font-weight: 900;
    margin-top: 18px;
    margin-bottom: 10px;
}

/* 選手 */

.player-box {
    background: #ffffff;
    border: 1px solid #dbe3ee;
    border-radius: 13px;
    overflow: hidden;
    margin-bottom: 15px;
}

.player-row {
    display: flex;
    align-items: center;
    min-height: 44px;
    border-bottom: 1px solid #edf1f5;
    padding: 0 14px;
    color: #0f172a !important;
    font-size: 14px;
    font-weight: 750;
}

.player-row:last-child {
    border-bottom: none;
}

.boat-no {
    width: 55px;
    color: #2563eb !important;
    font-weight: 900;
}

/* 予想 */

.predict-card {
    background: #ffffff;
    border: 1px solid #dbe3ee;
    border-radius: 13px;
    padding: 14px;
    margin-bottom: 10px;
}

.predict-label {
    color: #64748b !important;
    font-size: 13px;
    font-weight: 900;
    margin-bottom: 5px;
}

.predict-number {
    color: #0f172a !important;
    font-size: 27px;
    font-weight: 950;
    letter-spacing: 2px;
}

.main-card {
    border-left: 5px solid #2563eb;
}

.counter-card {
    border-left: 5px solid #64748b;
}

.hole-card {
    border-left: 5px solid #0f172a;
}

/* 自信度 */

.confidence {
    background: #0f172a;
    border-radius: 13px;
    padding: 15px;
    text-align: center;
    margin-top: 14px;
}

.conf-title {
    color: #cbd5e1 !important;
    font-size: 12px;
    font-weight: 800;
}

.conf-stars {
    color: #ffffff !important;
    font-size: 24px;
    letter-spacing: 3px;
}

/* スマホ */

@media(max-width:640px) {
    .title {
        font-size: 24px;
    }

    .predict-number {
        font-size: 23px;
    }

    .race-title {
        font-size: 18px;
    }
}

</style>
""", unsafe_allow_html=True)


# =========================
# 日付
# =========================

JST = ZoneInfo("Asia/Tokyo")
today = datetime.now(JST).date()
target_date = today.isoformat()


# =========================
# タイトル
# =========================

st.markdown(
    '<div class="title">🚤 やっちゃんの競艇AI予想PRO</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">データ分析 × AIによる3連単予想</div>',
    unsafe_allow_html=True,
)

st.markdown(
    f'<div class="date-badge">📅 {today.strftime("%Y年%m月%d日")}　本日開催</div>',
    unsafe_allow_html=True,
)


# =========================
# データ
# =========================

try:
    raw_today = data.get_data(target_date)
except Exception:
    raw_today = None

if raw_today is None:
    st.warning("本日のレースデータを取得できませんでした。")


# =========================
# 開催場
# =========================

st.markdown(
    '<div class="label">開催場</div>',
    unsafe_allow_html=True,
)

stadium_numbers = list(data.STADIUMS.keys())

stadium_names = [
    data.stadium_name(x)
    for x in stadium_numbers
]

selected_stadium = st.selectbox(
    "開催場",
    stadium_names,
    label_visibility="collapsed",
)

stadium_no = stadium_numbers[
    stadium_names.index(selected_stadium)
]


# =========================
# レース
# =========================

st.markdown(
    '<div class="label">レース</div>',
    unsafe_allow_html=True,
)

race_no = st.selectbox(
    "レース",
    range(1, 13),
    format_func=lambda x: f"{x}R",
    label_visibility="collapsed",
)


# =========================
# レース取得
# =========================

race = None

if raw_today:

    try:
        race = data.get_race(
            raw_today,
            stadium_no,
            race_no,
        )
    except Exception:
        race = None


# =========================
# AI予想
# =========================

if st.button(
    "🚤 AI予想する",
    type="primary",
    use_container_width=True,
):

    if not raw_today:
        st.error("本日のレースデータが取得できません。")
        st.stop()

    if not race:
        st.warning(
            f"{selected_stadium} {race_no}R "
            "のデータがまだ公開されていません。"
        )
        st.stop()

    try:
        valid = data.validate_race(
            race,
            target_date=target_date,
            stadium_no=stadium_no,
            race_no=race_no,
        )
    except Exception as e:
        st.error("レースデータの確認に失敗しました。")
        st.exception(e)
        st.stop()

    if not valid:
        st.warning("6艇分の出走データが揃っていません。")
        st.stop()

    try:
        rows = data.get_race_rows(
            race,
            stadium_no,
            race_no,
        )
    except TypeError:
        rows = data.get_race_rows(race)
    except Exception as e:
        st.error("出走データの取得に失敗しました。")
        st.exception(e)
        st.stop()

    if rows is None or len(rows) != 6:
        st.warning("6艇分のデータを取得できませんでした。")
        st.stop()

    try:
        history = data.history14(target_date)
    except Exception:
        history = None

    try:
        result = tri_ai(rows, history)
    except Exception as e:
        st.error("AI予想の計算に失敗しました。")
        st.exception(e)
        st.stop()

    # -------------------------
    # 結果を統一
    # -------------------------

    if isinstance(result, dict):

        main = result.get("main", [])
        counter = result.get("counter", [])
        hole = result.get("hole", [])
        probs = result.get("boat_probs", {})

    elif isinstance(result, tuple):

        combos = result[0] if len(result) else []
        probs = result[1] if len(result) > 1 else {}

        main = combos[0] if len(combos) > 0 else []
        counter = combos[1] if len(combos) > 1 else []
        hole = combos[2] if len(combos) > 2 else []

    else:

        main = []
        counter = []
        hole = []
        probs = {}

    def combo(x):
        if not x:
            return "—"
        return "-".join(str(v) for v in x)

    try:
        confidence = max(
            float(v) for v in probs.values()
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


    # =========================
    # 予想結果
    # =========================

    st.markdown(
        f'<div class="race-title">{selected_stadium} {race_no}R</div>',
        unsafe_allow_html=True,
    )


    # 6艇表示
    player_html = ""

    for _, row in rows.iterrows():

        try:
            no = int(row["艇番"])
        except Exception:
            no = "?"

        name = str(
            row.get("選手名", "選手")
        )

        player_html += f"""
        <div class="player-row">
            <div class="boat-no">{no}号艇</div>
            <div>{name}</div>
        </div>
        """

    st.markdown(
        f'<div class="player-box">{player_html}</div>',
        unsafe_allow_html=True,
    )


    # 本命
    st.markdown(
        f"""
        <div class="predict-card main-card">
            <div class="predict-label">🎯 本命</div>
            <div class="predict-number">{combo(main)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


    # 対抗
    st.markdown(
        f"""
        <div class="predict-card counter-card">
            <div class="predict-label">🔥 対抗</div>
            <div class="predict-number">{combo(counter)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


    # 穴
    st.markdown(
        f"""
        <div class="predict-card hole-card">
            <div class="predict-label">💥 穴</div>
            <div class="predict-number">{combo(hole)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


    # 自信度
    st.markdown(
        f"""
        <div class="confidence">
            <div class="conf-title">AI自信度</div>
            <div class="conf-stars">{stars}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================
# バックテスト
# =========================

with st.expander(
    "📊 AIの実力を検証する",
    expanded=False,
):

    backtest.render_backtest()
