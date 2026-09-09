import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone

import data
from ai import tri_ai


JST = timezone(timedelta(hours=9))


# =========================
# 現在選択されている開催場
# =========================
def get_stadium_no():
    keys = [
        "stadium_no",
        "selected_stadium_no",
        "backtest_stadium_no",
    ]

    for key in keys:
        value = st.session_state.get(key)

        if value is not None:
            try:
                return int(value)
            except Exception:
                pass

    # 場名で保存されている場合
    name = st.session_state.get("stadium")

    if isinstance(name, str):
        for no, stadium_name in data.STADIUM_NAMES.items():
            if name == stadium_name:
                return int(no)

    # 見つからない場合は桐生
    return 1


# =========================
# 過去14日データ
# =========================
@st.cache_data(ttl=300)
def get_history(stadium_no, race_date):
    try:
        return data.history14(
            stadium_no,
            race_date
        )
    except Exception:
        return []


# =========================
# 3連単配当
# =========================
def get_trifecta_payout(race):
    try:
        result = data.get_result(race)
    except Exception:
        return 0

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
                str(item.get("amount", 0))
                .replace(",", "")
            )
        except Exception:
            amount = 0

        if amount > 0:
            return amount

    return 0


# =========================
# 実着順
# =========================
def get_actual_order(race):
    try:
        order = data.get_result_order(race)

        if order and len(order) >= 3:
            return tuple(order[:3])

    except Exception:
        pass

    return ()


# =========================
# AI 6点買い
# =========================
def make_bets(ai):
    try:
        main = int(ai.get("main", 0))
        counter = int(ai.get("counter", 0))
        hole = int(ai.get("hole", 0))
    except Exception:
        return []

    if not all(
        1 <= x <= 6
        for x in [main, counter, hole]
    ):
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
# バックテスト本体
# =========================
def run_backtest(stadium_no, target_count):

    today = datetime.now(JST).date()

    check_date = today - timedelta(days=1)
    start_date = datetime(2026, 1, 1)

    records = []

    progress = st.progress(0)
    status = st.empty()

    while (
        check_date >= start_date
        and len(records) < target_count
    ):

        stadium = data.stadium_name(stadium_no)

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

            race_no = race.get(
                "race_number",
                ""
            )

            status.info(
                f"🔄 {check_date} "
                f"{stadium} {race_no}Rを検証中"
            )

            try:
                # 確定結果があるか確認
                result = data.get_result(race)

                if not result:
                    continue

                # 実着順
                actual = get_actual_order(race)

                if len(actual) < 3:
                    continue

                # 出走データ
                rows = data.get_race_rows(race)

                if rows is None or len(rows) == 0:
                    continue

                # 過去成績
                history = get_history(
                    stadium_no,
                    check_date
                )

                # AI予想
                ai = tri_ai(
                    rows,
                    history,
                    stadium_no
                )

                # 6点
                bets = make_bets(ai)

                # 本命・対抗・穴が成立しない場合は除外
                if len(bets) != 6:
                    continue

                main = int(ai["main"])
                counter = int(ai["counter"])
                hole = int(ai["hole"])

                # =====================
                # 判定
                # =====================

                main_win = (
                    actual[0] == main
                )

                main_top3 = (
                    main in actual
                )

                ai_top3 = all(
                    x in actual
                    for x in [
                        main,
                        counter,
                        hole
                    ]
                )

                exact_hit = (
                    actual ==
                    (main, counter, hole)
                )

                bet_hit = (
                    actual in bets
                )

                # 配当
                payout = 0

                if bet_hit:
                    payout = get_trifecta_payout(
                        race
                    )

                # =====================
                # 保存
                # =====================

                records.append({
                    "日付": check_date,
                    "場番号": stadium_no,
                    "場": stadium,
                    "R": race_no,

                    "本命": main,
                    "対抗": counter,
                    "穴": hole,

                    "実着1": actual[0],
                    "実着2": actual[1],
                    "実着3": actual[2],

                    "本命1着": main_win,
                    "本命3連対": main_top3,

                    "AI上位3艇3連対":
                        ai_top3,

                    "3連単完全的中":
                        exact_hit,

                    "買い目的中":
                        bet_hit,

                    # 成立したレースは必ず6点
                    "買い目数": 6,

                    "3連単配当":
                        payout,

                    "3連単的中":
                        bet_hit and payout > 0,
                })

            except Exception:
                continue

            # 進捗
            progress.progress(
                min(
                    len(records) /
                    target_count,
                    1.0
                )
            )

        check_date -= timedelta(days=1)

    progress.progress(1.0)

    status.success(
        f"✅ {len(records)}レースの検証が完了しました。"
    )

    return pd.DataFrame(records)


# =========================
# 指標計算
# =========================
def calculate_metrics(df):

    if df.empty:
        return {}

    main_win = (
        df["本命1着"].mean() * 100
    )

    main_top3 = (
        df["本命3連対"].mean() * 100
    )

    ai_top3 = (
        df["AI上位3艇3連対"].mean()
        * 100
    )

    exact = (
        df["3連単完全的中"].mean()
        * 100
    )

    bet_hit = (
        df["買い目的中"].mean()
        * 100
    )

    # 1点100円
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
        "main_win": main_win,
        "main_top3": main_top3,
        "ai_top3": ai_top3,
        "exact": exact,
        "bet_hit": bet_hit,
        "investment": investment,
        "payout": payout,
        "roi": roi,
    }


# =========================
# AI評価
# =========================
def ai_rating(roi):

    if roi >= 120:
        return "★★★★★"

    if roi >= 100:
        return "★★★★"

    if roi >= 90:
        return "★★★"

    if roi >= 70:
        return "★★"

    return "★"


# =========================
# バックテスト画面
# app.pyから render_backtest()
# で呼び出せる
# =========================
def render_backtest(stadium_no=None):

    st.subheader("📊 AIバックテスト")

    st.caption(
        "2026-01-01以降の確定レースを自動で遡って検証します。"
    )

    # 開催場
    if stadium_no is None:
        stadium_no = get_stadium_no()

    try:
        stadium_no = int(stadium_no)
    except Exception:
        stadium_no = 1

    count = st.selectbox(
        "検証レース数",
        [100, 300, 500, 1000],
        index=0,
        key="backtest_race_count"
    )

    # =========================
    # 開始
    # =========================
    if st.button(
        "🚀 バックテスト開始",
        use_container_width=True,
        key="backtest_start_button"
    ):

        # 古い結果を削除
        st.session_state.pop(
            "backtest_df",
            None
        )

        df = run_backtest(
            stadium_no,
            count
        )

        if df.empty:

            st.error(
                "検証できる確定レースが見つかりませんでした。"
            )

        else:

            st.session_state[
                "backtest_df"
            ] = df

            st.session_state[
                "backtest_target"
            ] = count

    # =========================
    # 結果表示
    # =========================

    df = st.session_state.get(
        "backtest_df"
    )

    if df is None or df.empty:
        return

    target = st.session_state.get(
        "backtest_target",
        len(df)
    )

    st.success(
        f"✅ {len(df)}レースの検証が完了しました。"
    )

    st.write(
        f"{len(df)} / {target} レース"
    )

    st.info(
        "🚤 バックテスト完了！"
    )

    # =========================
    # 指標
    # =========================

    m = calculate_metrics(df)

    st.subheader(
        "📈 バックテスト結果"
    )

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

    st.write(
        f"🤖 AI評価 {ai_rating(m['roi'])}"
    )

    # =========================
    # 詳細
    # =========================

    with st.expander(
        "🔎 バックテスト詳細を見る"
    ):

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
    )
