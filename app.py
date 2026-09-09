import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo

import data
from ai import tri_ai
import backtest


# =========================
# ページ設定
# =========================

st.set_page_config(
    page_title="やっちゃんの競艇AI予想PRO",
    page_icon="🚤",
    layout="centered",
)


# =========================
# CSS
# =========================

st.markdown(
    """
    <style>

    .stApp {
        background:#f4f7fb;
    }

    .block-container {
        max-width:760px;
        padding-top:5rem !important;
        padding-bottom:3rem !important;
        padding-left:1rem !important;
        padding-right:1rem !important;
    }

    .label {
        color:#0f172a !important;
        font-size:14px;
        font-weight:900;
        margin:8px 0 6px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# 日付
# =========================

JST = ZoneInfo(
    "Asia/Tokyo"
)

today = datetime.now(
    JST
).date()

target_date = today.isoformat()


# =========================
# タイトル
# =========================

st.html(
    f"""
    <div style="
        font-size:28px;
        font-weight:900;
        color:#0f172a;
        margin-bottom:3px;
    ">
        🚤 やっちゃんの競艇AI予想PRO
    </div>

    <div style="
        font-size:13px;
        font-weight:700;
        color:#64748b;
        margin-bottom:12px;
    ">
        データ分析 × AIによる3連単予想
    </div>

    <div style="
        display:inline-block;
        background:#eaf2ff;
        border:1px solid #c8dcff;
        border-radius:20px;
        padding:7px 13px;
        color:#1458c5;
        font-size:12px;
        font-weight:900;
        margin-bottom:20px;
    ">
        📅 {today.strftime("%Y年%m月%d日")}　本日開催
    </div>
    """
)


# =========================
# データ取得
# =========================

try:

    raw_today = data.get_data(
        target_date
    )

except Exception as e:

    raw_today = None

    st.html(
        f"""
        <div style="
            background:#fff1f2;
            border:1px solid #fecdd3;
            border-radius:12px;
            padding:14px;
            margin:10px 0 18px;
            color:#9f1239;
        ">

            <div style="
                font-size:15px;
                font-weight:900;
                margin-bottom:5px;
            ">
                ⚠️ レースデータを取得できませんでした
            </div>

            <div style="
                font-size:12px;
                font-weight:700;
            ">
                APIとの通信中にエラーが発生しました。
            </div>

        </div>
        """
    )


if raw_today is None:

    st.html(
        f"""
        <div style="
            background:#fff7ed;
            border:1px solid #fed7aa;
            border-radius:12px;
            padding:14px;
            margin:10px 0 18px;
            color:#9a3412;
        ">

            <div style="
                font-size:15px;
                font-weight:900;
                margin-bottom:5px;
            ">
                ⚠️ 本日のレースデータを取得できませんでした
            </div>

            <div style="
                font-size:12px;
                font-weight:700;
                line-height:1.7;
            ">
                APIから本日のデータを取得できていません。<br>
                少し時間を置いて再読み込みしてください。
            </div>

        </div>
        """
    )


# =========================
# 開催場
# =========================

st.markdown(
    '<div class="label">開催場</div>',
    unsafe_allow_html=True,
)


stadium_numbers = list(
    data.STADIUMS.keys()
)


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
    stadium_names.index(
        selected_stadium
    )
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
    format_func=lambda x:
        f"{x}R",
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

        st.html(
            """
            <div style="
                background:#fff1f2;
                border:1px solid #fecdd3;
                border-radius:12px;
                padding:14px;
                color:#9f1239;
                font-weight:800;
            ">
                ⚠️ 本日のレースデータが取得できていません。
            </div>
            """
        )

        st.stop()


    if not race:

        st.html(
            f"""
            <div style="
                background:#fff7ed;
                border:1px solid #fed7aa;
                border-radius:12px;
                padding:14px;
                color:#9a3412;
                font-weight:800;
            ">
                ⚠️ {selected_stadium} {race_no}R
                のデータがまだ公開されていません。
            </div>
            """
        )

        st.stop()


    # =========================
    # レース確認
    # =========================

    try:

        valid = data.validate_race(
            race,
            target_date=target_date,
            stadium_no=stadium_no,
            race_no=race_no,
        )

    except Exception as e:

        st.error(
            "レースデータの確認に失敗しました。"
        )

        st.exception(e)

        st.stop()


    if not valid:

        st.html(
            """
            <div style="
                background:#fff7ed;
                border:1px solid #fed7aa;
                border-radius:12px;
                padding:14px;
                color:#9a3412;
                font-weight:800;
            ">
                ⚠️ 6艇分の出走データが揃っていません。
            </div>
            """
        )

        st.stop()


    # =========================
    # 6艇
    # =========================

    try:

        rows = data.get_race_rows(
            race,
            stadium_no,
            race_no,
        )

    except Exception as e:

        st.error(
            "出走データの取得に失敗しました。"
        )

        st.exception(e)

        st.stop()


    if rows is None or len(rows) != 6:

        st.html(
            """
            <div style="
                background:#fff7ed;
                border:1px solid #fed7aa;
                border-radius:12px;
                padding:14px;
                color:#9a3412;
                font-weight:800;
            ">
                ⚠️ 6艇分のデータを取得できませんでした。
            </div>
            """
        )

        st.stop()


    # =========================
    # 履歴
    # =========================

    try:

        history = data.history14(
            target_date
        )

    except Exception:

        history = None


    # =========================
    # AI
    # =========================

    try:

        result = tri_ai(
            rows,
            history,
        )

    except Exception as e:

        st.error(
            "AI予想の計算に失敗しました。"
        )

        st.exception(e)

        st.stop()


    # =========================
    # 結果
    # =========================

    if isinstance(
        result,
        dict,
    ):

        main = result.get(
            "main",
            [],
        )

        counter = result.get(
            "counter",
            [],
        )

        hole = result.get(
            "hole",
            [],
        )

        probs = result.get(
            "boat_probs",
            {},
        )

    else:

        main = []
        counter = []
        hole = []
        probs = {}


    # =========================
    # 3連単
    # =========================

    def combo(value):

        if not value:
            return "—"

        return "-".join(
            str(v)
            for v in value
        )


    # =========================
    # 自信度
    # =========================

    try:

        confidence = max(
            float(v)
            for v in probs.values()
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
    # レースタイトル
    # =========================

    st.html(
        f"""
        <div style="
            background:#0f172a;
            color:#ffffff;
            border-radius:13px;
            padding:13px 16px;
            font-size:20px;
            font-weight:900;
            margin-top:18px;
            margin-bottom:10px;
        ">
            {selected_stadium} {race_no}R
        </div>
        """
    )


    # =========================
    # 選手一覧
    # =========================

    player_html = ""


    for _, row in rows.iterrows():

        try:
            no = int(
                row["艇番"]
            )
        except Exception:
            no = "?"


        name = str(
            row.get(
                "選手名",
                "選手",
            )
        )


        player_html += f"""
        <div style="
            display:flex;
            align-items:center;
            min-height:44px;
            border-bottom:1px solid #edf1f5;
            padding:0 14px;
            color:#0f172a;
            font-size:14px;
            font-weight:750;
        ">

            <div style="
                width:55px;
                color:#2563eb;
                font-weight:900;
            ">
                {no}号艇
            </div>

            <div>
                {name}
            </div>

        </div>
        """


    st.html(
        f"""
        <div style="
            background:#ffffff;
            border:1px solid #dbe3ee;
            border-radius:13px;
            overflow:hidden;
            margin-bottom:15px;
        ">
            {player_html}
        </div>
        """
    )


    # =========================
    # 本命
    # =========================

    st.html(
        f"""
        <div style="
            background:#ffffff;
            border:1px solid #dbe3ee;
            border-left:5px solid #2563eb;
            border-radius:13px;
            padding:14px;
            margin-bottom:10px;
        ">

            <div style="
                color:#64748b;
                font-size:13px;
                font-weight:900;
                margin-bottom:5px;
            ">
                🎯 本命
            </div>

            <div style="
                color:#0f172a;
                font-size:27px;
                font-weight:950;
                letter-spacing:2px;
            ">
                {combo(main)}
            </div>

        </div>
        """
    )


    # =========================
    # 対抗
    # =========================

    st.html(
        f"""
        <div style="
            background:#ffffff;
            border:1px solid #dbe3ee;
            border-left:5px solid #64748b;
            border-radius:13px;
            padding:14px;
            margin-bottom:10px;
        ">

            <div style="
                color:#64748b;
                font-size:13px;
                font-weight:900;
                margin-bottom:5px;
            ">
                🔥 対抗
            </div>

            <div style="
                color:#0f172a;
                font-size:27px;
                font-weight:950;
                letter-spacing:2px;
            ">
                {combo(counter)}
            </div>

        </div>
        """
    )


    # =========================
    # 穴
    # =========================

    st.html(
        f"""
        <div style="
            background:#ffffff;
            border:1px solid #dbe3ee;
            border-left:5px solid #0f172a;
            border-radius:13px;
            padding:14px;
            margin-bottom:10px;
        ">

            <div style="
                color:#64748b;
                font-size:13px;
                font-weight:900;
                margin-bottom:5px;
            ">
                💥 穴
            </div>

            <div style="
                color:#0f172a;
                font-size:27px;
                font-weight:950;
                letter-spacing:2px;
            ">
                {combo(hole)}
            </div>

        </div>
        """
    )


    # =========================
    # 自信度
    # =========================

    st.html(
        f"""
        <div style="
            background:#0f172a;
            border-radius:13px;
            padding:15px;
            text-align:center;
            margin-top:14px;
        ">

            <div style="
                color:#cbd5e1;
                font-size:12px;
                font-weight:800;
            ">
                AI自信度
            </div>

            <div style="
                color:#ffffff;
                font-size:24px;
                letter-spacing:3px;
            ">
                {stars}
            </div>

        </div>
        """
    )


# =========================
# バックテスト
# =========================

with st.expander(
    "📊 AIの実力を検証する",
    expanded=False,
):

    backtest.render_backtest()
