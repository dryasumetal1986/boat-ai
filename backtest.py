import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone

import data
from ai import tri_ai

JST = timezone(timedelta(hours=9))


# =========================
# 過去データ
# =========================
@st.cache_data(ttl=300)
def _history(stadium_no, race_date):
    try:
        return data.history14(stadium_no, race_date)
    except Exception:
        return []


# =========================
# 3連単配当
# =========================
def trifecta_payout(race):
    result = data.get_result(race)

    if not isinstance(result, dict):
        return 0

    payouts = result.get("payouts", {})
    if not isinstance(payouts, dict):
        return 0

    trifecta = payouts.get("trifecta", [])
    if not isinstance(trifecta, list):
        return 0

    for item in trifecta:
        if not isinstance(item, dict):
            continue

        try:
            amount = int(
                str(item.get("amount", 0)).replace(",", "")
            )
        except Exception:
            amount = 0

        if amount > 0:
            return amount

    return 0


# =========================
# 着順
# =========================
def result_order(race):
    try:
        return tuple(data.get_result_order(race)[:3])
    except Exception:
        return ()


# =========================
# 6点買い
# =========================
def make_bets(ai):
    try:
        main = int(ai.get("main", 0))
        counter = int(ai.get("counter", 0))
        hole = int(ai.get("hole", 0))
    except Exception:
        return []

    if not all(1 <= x <= 6 for x in [main, counter, hole]):
        return []

    if len({main, counter, hole}) != 3:
        return []

    return [
        (main, counter, hole),
        (main, hole, counter),
        (counter, main, hole),
        (counter, hole, main),
        (hole, main, counter),
        (hole, counter, main),
    ]


# =========================
# バックテスト実行
# =========================
def run_backtest(stadium_no, target_count):

    today = datetime.now(JST).date()
    check_date = today - timedelta(days=1)
    start_date = datetime(2026, 1, 1)

    records = []

    progress = st.progress(0)
    status = st.empty()

    while check_date >= start_date and len(records) < target_count:

        stadium = data.stadium_name(stadium_no)

        status.info(
            f"🔄 {check_date} {stadium}を検証中"
        )

        try:
            races = data.all_races_for_date(
                check_date,
                stadium_no
            )
        except Exception:
            races = []

        for race in races:

            if len(records) >= target_count:
                break

            try:
                result = data.get_result(race)

                if not result:
                    continue

                actual = result_order(race)

                if len(actual) < 3:
                    continue

                rows = data.get_race_rows(race)

                if rows is None or len(rows) == 0:
                    continue

                history = _history(
                    stadium_no,
                    check_date
                )

                ai = tri_ai(
                    rows,
                    history,
                    stadium_no
                )

                bets = make_bets(ai)

                # 6点を作れないレースは検証対象外
                if len(bets) != 6:
                    continue

                main = int(ai["main"])
                counter = int(ai["counter"])
                hole = int(ai["hole"])

                main_win = actual[0] == main
                main_top3 = main in actual

                ai_top3 = all(
                    x in actual
                    for x in [main, counter, hole]
                )

                exact = actual == (
                    main,
                    counter,
                    hole
                )

                bet_hit = actual in bets

                payout = (
                    trifecta_payout(race)
                    if bet_hit
                    else 0
                )

                records.append({
                    "日付": check_date,
                    "場番号": stadium_no,
                    "場": stadium,
                    "R": race.get("race_number", ""),
                    "本命": main,
                    "対抗": counter,
                    "穴": hole,
                    "実着1": actual[0],
                    "実着2": actual[1],
                    "実着3": actual[2],
                    "本命1着": main_win,
                    "本命3連対": main_top3,
                    "AI上位3艇3連対": ai_top3,
                    "3連単完全的中": exact,
                    "買い目的中": bet_hit,
                    "買い目数": 6,
                    "3連単配当": payout,
                    "3連単的中": bet_hit and payout > 0,
                })

            except Exception:
                continue

            progress.progress(
                min(len(records) / target_count, 1.0)
            )

        check_date -= timedelta(days=1)

    progress.progress(1.0)

    status.success(
        f"✅ {len(records)}レースの検証が完了しました。"
    )

    return pd.DataFrame(records)


# =========================
# 指標
# =========================
def calculate_metrics(df):

    if df.empty:
        return {}

    investment = (
        df["買い目数"].sum() * 100
    )

    payout = (
        df["3連単配当"].sum()
    )

    roi = (
        payout / investment * 100
        if investment > 0
        else 0
    )

    return {
        "main_win": df["本命1着"].mean() * 100,
        "main_top3": df["本命3連対"].mean() * 100,
        "ai_top3": df["AI上位3艇3連対"].mean() * 100,
        "exact": df["3連単完全的中"].mean() * 100,
        "bet_hit": df["買い目的中"].mean() * 100,
        "investment": investment,
        "payout": payout,
        "roi": roi,
    }


# =========================
# 結果表示
# ※ app.pyから引数なしで呼べる
# =========================
def render_backtest():

    df = st.session_state.get("backtest_df")

    if df is None or df.empty:
        st.info("まだバックテスト結果がありません。")
        return

    m = calculate_metrics(df)

    st.subheader("📈 バックテスト結果")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "本命1着率",
        f"{m['main_win']:.1f}%"
    )

    c2.metric(
        "本命3連対率",
        f"{m['main_top3']:.1f}%"
    )

    c3.metric(
        "AI上位3艇3連対",
        f"{m['ai_top3']:.1f}%"
    )

    c4, c5, c6 = st.columns(3)

    c4.metric(
        "3連単完全的中",
        f"{m['exact']:.1f}%"
    )

    c5.metric(
        "AI買い目的中率",
        f"{m['bet_hit']:.1f}%"
    )

    c6.metric(
        "買い目回収率",
        f"{m['roi']:.1f}%"
    )

    c7, c8 = st.columns(2)

    c7.metric(
        "投資額",
        f"{m['investment']:,.0f}円"
    )

    c8.metric(
        "払戻額",
        f"{m['payout']:,.0f}円"
    )

    roi = m["roi"]

    if roi >= 100:
        stars = "★★★★★"
    elif roi >= 90:
        stars = "★★★★"
    elif roi >= 80:
        stars = "★★★"
    elif roi >= 70:
        stars = "★★"
    else:
        stars = "★"

    st.write(f"🤖 AI評価 {stars}")

    with st.expander("🔎 バックテスト詳細を見る"):
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


# =========================
# バックテスト画面
# =========================
def show_backtest(stadium_no):

    st.subheader("📊 AIバックテスト")

    st.caption(
        "2026-01-01以降の確定レースを自動で遡って検証します。"
    )

    count = st.selectbox(
        "検証レース数",
        [100, 300, 500, 1000],
        index=0
    )

    if st.button(
        "🚀 バックテスト開始",
        use_container_width=True
    ):

        df = run_backtest(
            stadium_no,
            count
        )

        st.session_state["backtest_df"] = df

        st.rerun()

    render_backtest()
