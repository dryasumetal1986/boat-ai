import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo

import ai
import backtest
import data


# =========================
# 設定
# =========================

st.set_page_config(
    page_title="🚤 やっちゃんの競艇AI予想PRO",
    page_icon="🚤",
    layout="wide",
)

st.markdown("""
<style>
.block-container{padding-top:1rem;max-width:1100px}
.card{border:1px solid #ddd;border-radius:12px;padding:12px;margin:6px 0}
.big{font-size:1.4rem;font-weight:bold}
@media(max-width:640px){
.block-container{padding:8px}
}
</style>
""", unsafe_allow_html=True)


# =========================
# Session
# =========================

for key, default in {
    "prediction": None,
    "prediction_meta": None,
    "backtest_result": None,
    "backtest_page": 0,
    "scroll_backtest": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# =========================
# 日付
# =========================

now = datetime.now(ZoneInfo("Asia/Tokyo"))
today = now.strftime("%Y%m%d")

st.title("🚤 やっちゃんの競艇AI予想PRO")
st.caption(
    f"AI予想・公式3連単オッズ・EV分析・バックテスト｜"
    f"{now:%Y/%m/%d}"
)


# =========================
# レース選択
# =========================

raw = data.get_data(today)
rows = data.get_race_rows(raw)

if not rows:
    st.warning("本日のレースデータを取得できませんでした。")
    st.stop()

stadiums = list(dict.fromkeys(
    (x["stadium_number"], x["stadium"]) for x in rows
))

c1, c2 = st.columns(2)

with c1:
    stadium_text = st.selectbox(
        "競艇場",
        [f"{n}: {name}" for n, name in stadiums],
    )

stadium_no = int(stadium_text.split(":")[0])
stadium_name = data.get_stadium_name(stadium_no)

race_numbers = sorted(
    x["race_number"]
    for x in rows
    if x["stadium_number"] == stadium_no
)

with c2:
    race_no = st.selectbox(
        "レース",
        race_numbers,
        format_func=lambda x: f"{x}R",
    )


# =========================
# AI予想
# =========================

if st.button(
    "🤖 AI予想を実行",
    type="primary",
    use_container_width=True,
):
    with st.spinner("AI分析中..."):

        race = data.get_race(
            raw,
            stadium_no,
            race_no,
        )

        racers = data.get_race_racers(race)

        odds = data.get_trifecta_odds(
            today,
            stadium_no,
            race_no,
        )

        st.session_state.prediction = ai.tri_ai(
            racers,
            odds=odds,
        )

        st.session_state.prediction_meta = (
            stadium_name,
            race_no,
        )


# =========================
# AI結果
# =========================

p = st.session_state.prediction

if p:

    st.divider()
    st.subheader("🤖 AI予想")

    main = p["main"]
    counter = p["counter"]
    hole = p["hole"]

    name, race_no = st.session_state.prediction_meta

    st.caption(f"📍 {name} {race_no}R")

    a, b, c = st.columns(3)

    for col, label, boat in [
        (a, "🔥 本命", main),
        (b, "⚡ 対抗", counter),
        (c, "💥 穴", hole),
    ]:
        with col:
            st.markdown(
                f'<div class="card">{label}'
                f'<div class="big">{boat}号艇</div></div>',
                unsafe_allow_html=True,
            )

    confidence = p["confidence"] * 100
    stars = "⭐" * max(1, min(5, round(confidence / 20)))

    st.write(
        f"AI信頼度 {stars}（{confidence:.1f}%）"
    )


    # =====================
    # 1着確率
    # =====================

    st.subheader("📊 6艇1着確率")

    for boat in p["ranking"]:
        prob = p["probabilities"][boat]

        st.progress(
            min(1.0, prob),
            text=f"{boat}号艇　{prob * 100:.3f}%",
        )


    # =====================
    # EV
    # =====================

    st.divider()
    st.subheader("💰 3連単EV分析")

    candidates = p["trifecta_candidates"]

    if not p["odds_available"]:
        st.warning("公式3連単オッズを取得できませんでした。")
    else:

        st.success(
            f"公式3連単オッズ取得済み："
            f"{len(p['odds'])}/120通り"
        )

        st.caption(
            "EV = AI確率 × 公式オッズ − 1"
            "｜市場確率 = 1 ÷ オッズ"
        )

        for x in candidates[:8]:

            combo = "-".join(
                map(str, x["combination"])
            )

            odd = x["odds"]
            prob = x["probability"] * 100
            market = x["market_probability"] * 100
            ev = x["ev_rate"]
            edge = x["edge"] * 100

            st.markdown(
                f"""
                <div class="card">
                <b>🎯 {combo}</b><br>
                オッズ：<b>{odd:g}倍</b>　
                AI確率：<b>{prob:.3f}%</b><br>
                市場確率：{market:.3f}%　
                EV：<b>{ev:+.1f}%</b>　
                Edge：{edge:+.3f}%
                </div>
                """,
                unsafe_allow_html=True,
            )


# =========================
# バックテスト
# =========================

st.divider()

st.markdown(
    '<div id="backtest-results"></div>',
    unsafe_allow_html=True,
)

st.subheader("📋 検証結果")

st.caption(
    "当日を除外し、前日までの完了レースを"
    "2026/01/01まで遡って検証します。"
)

count = st.selectbox(
    "検証レース数",
    [100, 300, 500, 1000],
)

if st.button(
    "🔎 バックテスト開始",
    use_container_width=True,
):

    progress = st.progress(
        0,
        text="検証中..."
    )

    def update(v):
        progress.progress(
            float(v),
            text=f"検証中... {v * 100:.0f}%",
        )

    st.session_state.backtest_result = (
        backtest.run_backtest(
            today,
            count,
            progress_callback=update,
        )
    )

    st.session_state.backtest_page = 0
    st.session_state.scroll_backtest = True

    st.rerun()


# =========================
# バックテスト結果
# =========================

r = st.session_state.backtest_result

if r and r["total"]:

    # ---------------------
    # 指標
    # ---------------------

    m1, m2 = st.columns(2)

    m1.metric(
        "本命1着率",
        f"{r['main_win_rate']:.1f}%",
    )

    m2.metric(
        "本命3連対率",
        f"{r['main_top3_rate']:.1f}%",
    )

    m3, m4 = st.columns(2)

    m3.metric(
        "AI上位3艇 全艇3連対率",
        f"{r['top3_all_top3_rate']:.1f}%",
    )

    m4.metric(
        "AI3連単完全的中率",
        f"{r['trifecta_hit_rate']:.1f}%",
    )

    m5, m6 = st.columns(2)

    m5.metric(
        "回収率",
        f"{r['recovery']:.1f}%",
    )

    m6.metric(
        "検証レース数",
        f"{r['total']}R",
    )

    st.write(
        f"💰 投資額：{r['investment']:,}円　"
        f"払戻：{r['payout']:,}円"
    )

    st.caption(
        f"1レース{backtest.BET_AMOUNT}円｜"
        "AI本命・対抗・穴の3連単1点｜当日除外"
    )


    # ---------------------
    # 一覧
    # ---------------------

    results = r["results"]

    page_size = 10
    pages = max(
        1,
        (len(results) + page_size - 1)
        // page_size,
    )

    page = min(
        st.session_state.backtest_page,
        pages - 1,
    )

    start = page * page_size
    end = min(
        start + page_size,
        len(results),
    )

    st.markdown(
        f"**{start + 1}～{end}件 / {len(results)}件**"
    )

    for x in results[start:end]:

        date = x["date"]

        if len(date) == 8:
            date = (
                f"{date[:4]}/{date[4:6]}/{date[6:]}"
            )

        actual = "-".join(
            map(str, x["actual"])
        )

        hit = (
            "🎯 3連単完全的中"
            if x["trifecta_hit"]
            else "❌ 3連単不的中"
        )

        st.markdown(
            f"""
            <div class="card">
            <b>{date} {x['stadium']} {x['race']}R</b><br>
            🤖 AI：
            🔥{x['main']}号艇　
            ⚡{x['counter']}号艇　
            💥{x['hole']}号艇<br>
            🏁 結果：<b>{actual}</b><br>
            {hit}　
            📊 AI上位3艇：<b>{x['ai_top3_hit_count']}/3艇</b>
            </div>
            """,
            unsafe_allow_html=True,
        )


    # ---------------------
    # ページ移動
    # ---------------------

    p1, p2, p3 = st.columns(3)

    with p1:
        if st.button(
            "◀ 前へ",
            disabled=page == 0,
            use_container_width=True,
        ):
            st.session_state.backtest_page -= 1
            st.session_state.scroll_backtest = True
            st.rerun()

    with p2:
        st.markdown(
            f"<div style='text-align:center;padding:8px'>"
            f"{page + 1} / {pages}</div>",
            unsafe_allow_html=True,
        )

    with p3:
        if st.button(
            "次へ ▶",
            disabled=page >= pages - 1,
            use_container_width=True,
        ):
            st.session_state.backtest_page += 1
            st.session_state.scroll_backtest = True
            st.rerun()


    # ---------------------
    # 自動スクロール
    # ---------------------

    if st.session_state.scroll_backtest:

        st.session_state.scroll_backtest = False

        st.components.v1.html(
            """
            <script>
            let n = 0;
            const timer = setInterval(() => {
                const el =
                    window.parent.document
                    .getElementById("backtest-results");

                if (el) {
                    el.scrollIntoView({
                        behavior:"smooth",
                        block:"start"
                    });
                    clearInterval(timer);
                }

                if (++n > 20) clearInterval(timer);
            }, 100);
            </script>
            """,
            height=1,
        )
