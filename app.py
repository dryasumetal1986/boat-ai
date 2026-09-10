import html
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

import ai
import backtest
import data


# ============================================================
# 基本設定
# ============================================================

st.set_page_config(
    page_title="やっちゃんの競艇AI予想PRO",
    page_icon="🚤",
    layout="wide",
)


st.markdown(
    """
<style>

.block-container {
    padding-top: 3.5rem !important;
    padding-bottom: 3rem !important;
}

h1 {
    margin-top: 0 !important;
    padding-top: 0 !important;
}

.backtest-anchor {
    scroll-margin-top: 90px;
}

.result-card {
    border: 1px solid #ddd;
    border-radius: 10px;
    padding: 10px 12px;
    margin-bottom: 8px;
}

.page-buttons {
    display: flex;
    gap: 8px;
    align-items: center;
    margin-top: 12px;
}

.page-button {
    display: inline-block;
    padding: 7px 15px;
    border: 1px solid #aaa;
    border-radius: 7px;
    text-decoration: none !important;
    color: inherit !important;
    background: #fff;
}

.page-button:hover {
    background: #eee;
}

.page-number {
    padding: 7px 10px;
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# 日付
# ============================================================

today = datetime.now(
    ZoneInfo("Asia/Tokyo")
).strftime("%Y%m%d")


# ============================================================
# Session
# ============================================================

if "prediction" not in st.session_state:
    st.session_state.prediction = None

if "backtest" not in st.session_state:
    st.session_state.backtest = None


# ============================================================
# タイトル
# ============================================================

st.title(
    "🚤 やっちゃんの競艇AI予想PRO"
)

st.caption(
    "AI予想・公式3連単オッズ・EV分析・バックテスト｜"
    + datetime.now(
        ZoneInfo("Asia/Tokyo")
    ).strftime("%Y/%m/%d")
)


# ============================================================
# レース選択
# ============================================================

col1, col2 = st.columns(2)


with col1:

    stadium_number = st.selectbox(
        "競艇場",
        list(data.STADIUMS.keys()),
        format_func=lambda x:
            f"{x}: {data.get_stadium_name(x)}",
        index=20,
    )


with col2:

    race_number = st.selectbox(
        "レース",
        list(range(1, 13)),
        format_func=lambda x:
            f"{x}R",
    )


# ============================================================
# AI予想実行
# ============================================================

if st.button(
    "🤖 AI予想を実行",
    type="primary",
    use_container_width=True,
):

    with st.spinner(
        "公式データを取得中..."
    ):

        raw = data.get_data(
            today
        )

        race = data.get_race(
            raw,
            stadium_number,
            race_number,
        )

        if race is None:

            st.error(
                "レースデータを取得できませんでした。"
            )

            st.stop()

        racers = data.get_race_racers(
            race
        )

        odds = data.get_trifecta_odds(
            stadium_number,
            race_number,
            today,
        )

        prediction = ai.tri_ai(
            racers,
            odds,
        )

        st.session_state.prediction = {
            "stadium":
                stadium_number,

            "race":
                race_number,

            "prediction":
                prediction,
        }


# ============================================================
# AI予想表示
# ============================================================

pred = st.session_state.prediction


if pred:

    prediction = pred["prediction"]

    stadium = pred["stadium"]

    race_no = pred["race"]

    st.divider()

    st.subheader("🤖 AI予想")

    st.write(
        f"📍 "
        f"{data.get_stadium_name(stadium)} "
        f"{race_no}R"
    )

    c1, c2, c3 = st.columns(3)


    with c1:

        st.metric(
            "🔥 本命",
            f"{prediction['main']}号艇",
        )


    with c2:

        st.metric(
            "⚡ 対抗",
            f"{prediction['counter']}号艇",
        )


    with c3:

        st.metric(
            "💥 穴",
            f"{prediction['hole']}号艇",
        )


    st.write(
        f"AI信頼度 ⭐⭐⭐ "
        f"（"
        f"{prediction['confidence'] * 100:.1f}"
        f"%）"
    )


    # ========================================================
    # 1着確率
    # ========================================================

    st.subheader(
        "📊 6艇1着確率"
    )

    for boat in prediction["ranking"]:

        probability = prediction[
            "probabilities"
        ].get(
            boat,
            0.0,
        )

        st.write(
            f"{boat}号艇 "
            f"{probability * 100:.3f}%"
        )


    # ========================================================
    # EV
    # ========================================================

    st.subheader(
        "💰 3連単EV分析"
    )

    odds = prediction.get(
        "odds",
        {},
    )

    st.write(
        "公式3連単オッズ取得済み："
        f"{len(odds)}/120通り"
    )

    st.caption(
        "EV = AI確率 × 公式オッズ − 1"
        "｜市場確率 = 1 ÷ オッズ"
    )

    candidates = prediction.get(
        "trifecta_candidates",
        [],
    )

    shown = 0

    for item in candidates:

        if item["odds"] is None:
            continue

        combo = item[
            "combination"
        ]

        probability = item[
            "probability"
        ]

        odd = item["odds"]

        ev_rate = item[
            "ev_rate"
        ]

        market = item[
            "market_probability"
        ]

        edge = item["edge"]

        st.write(
            f"🎯 "
            f"{combo[0]}-"
            f"{combo[1]}-"
            f"{combo[2]} "
            f"オッズ：{odd:g}倍 "
            f"AI確率："
            f"{probability * 100:.3f}% "
            f"市場確率："
            f"{market * 100:.3f}% "
            f"EV："
            f"{ev_rate:+.1f}% "
            f"Edge："
            f"{edge * 100:+.3f}%"
        )

        shown += 1

        if shown >= 8:
            break


# ============================================================
# バックテスト
# ============================================================

st.divider()

st.subheader(
    "📋 検証結果"
)

st.write(
    "当日を除外し、前日までの完了レースを"
    "2026/01/01まで遡って検証します。"
)


count = st.number_input(
    "検証レース数",
    min_value=10,
    max_value=1000,
    value=100,
    step=10,
)


if st.button(
    "📋 バックテスト実行",
    use_container_width=True,
):

    progress = st.progress(0)

    def update_progress(value):

        progress.progress(
            min(
                max(
                    float(value),
                    0.0,
                ),
                1.0,
            )
        )

    with st.spinner(
        "バックテスト中..."
    ):

        result = backtest.run_backtest(
            today,
            int(count),
            update_progress,
        )

    progress.empty()

    st.session_state.backtest = result

    # ページを1ページ目に戻す
    st.query_params["bt_page"] = "1"

    st.rerun()


bt = st.session_state.backtest


# ============================================================
# バックテスト結果
# ============================================================

if bt:

    st.markdown(
        '<div id="backtest-results" '
        'class="backtest-anchor"></div>',
        unsafe_allow_html=True,
    )


    if bt["total"] == 0:

        st.warning(
            "検証できるレースがありません。"
        )

        st.stop()


    # ========================================================
    # 指標
    # ========================================================

    m1, m2, m3 = st.columns(3)


    with m1:

        st.metric(
            "本命1着率",
            f"{bt['main_win_rate']:.1f}%",
        )


    with m2:

        st.metric(
            "本命3連対率",
            f"{bt['main_top3_rate']:.1f}%",
        )


    with m3:

        st.metric(
            "AI上位3艇 全艇3連対率",
            f"{bt['top3_all_top3_rate']:.1f}%",
        )


    m4, m5 = st.columns(2)


    with m4:

        st.metric(
            "AI3連単完全的中率",
            f"{bt['trifecta_hit_rate']:.1f}%",
        )


    with m5:

        st.metric(
            "回収率",
            f"{bt['recovery']:.1f}%",
        )


    st.write(
        f"検証レース数 "
        f"{bt['total']}R"
    )

    st.write(
        f"💰 投資額："
        f"{bt['investment']:,}円 "
        f"払戻："
        f"{bt['payout']:,}円"
    )

    st.caption(
        "1レース600円｜"
        "AI本命・対抗・穴の3連単1点｜"
        "当日除外"
    )


    # ========================================================
    # ページング
    # ========================================================

    results = bt["results"]

    per_page = 10

    total_pages = max(
        1,
        (
            len(results)
            + per_page
            - 1
        )
        // per_page,
    )


    try:

        page = int(
            st.query_params.get(
                "bt_page",
                "1",
            )
        )

    except Exception:

        page = 1


    page = max(
        1,
        min(
            page,
            total_pages,
        ),
    )


    start = (
        page - 1
    ) * per_page

    end = min(
        start + per_page,
        len(results),
    )


    st.write(
        f"{start + 1}～{end}件 / "
        f"{len(results)}件"
    )


    # ========================================================
    # 結果表示
    # ========================================================

    for item in results[start:end]:

        actual = item.get(
            "actual",
            [],
        )

        actual_text = "-".join(
            str(x)
            for x in actual
        )

        predicted = (
            item["main"],
            item["counter"],
            item["hole"],
        )

        actual3 = tuple(
            actual[:3]
        )

        hit = (
            len(actual3) == 3
            and predicted
            == actual3
        )

        top3_count = len(
            set(
                [
                    item["main"],
                    item["counter"],
                    item["hole"],
                ]
            )
            & set(actual[:3])
        )

        mark = (
            "🎯"
            if hit
            else "❌"
        )

        hit_text = (
            "3連単的中"
            if hit
            else "3連単不的中"
        )

        stadium_name = html.escape(
            str(item["stadium"])
        )


        st.markdown(
            f"""
<div class="result-card">
<b>
{item['date']}
{stadium_name}
{item['race']}R
</b><br>
🤖 AI：🔥{item['main']}号艇
⚡{item['counter']}号艇
💥{item['hole']}号艇<br>
🏁 結果：{actual_text}<br>
{mark} {hit_text}
📊 AI上位3艇：
{top3_count}/3艇
</div>
""",
            unsafe_allow_html=True,
        )


    # ========================================================
    # ページ移動
    # ========================================================

    prev_page = max(
        1,
        page - 1,
    )

    next_page = min(
        total_pages,
        page + 1,
    )


    prev_url = (
        f"?bt_page={prev_page}"
        f"#backtest-results"
    )

    next_url = (
        f"?bt_page={next_page}"
        f"#backtest-results"
    )


    if page <= 1:

        prev_html = (
            '<span class="page-button" '
            'style="opacity:.4;">'
            '← 前へ'
            '</span>'
        )

    else:

        prev_html = (
            f'<a class="page-button" '
            f'href="{prev_url}">'
            f'← 前へ'
            f'</a>'
        )


    if page >= total_pages:

        next_html = (
            '<span class="page-button" '
            'style="opacity:.4;">'
            '次へ →'
            '</span>'
        )

    else:

        next_html = (
            f'<a class="page-button" '
            f'href="{next_url}">'
            f'次へ →'
            f'</a>'
        )


    st.markdown(
        f"""
<div class="page-buttons">
    {prev_html}
    <span class="page-number">
        {page} / {total_pages}
    </span>
    {next_html}
</div>
""",
        unsafe_allow_html=True,
    )
