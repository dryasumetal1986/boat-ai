import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone

import data
from ai import tri_ai


JST = timezone(timedelta(hours=9))
START_DATE = datetime(2026, 1, 1).date()


# =========================
# 開催場番号
# =========================
def get_stadium_no():
    for key in [
        "stadium_no",
        "selected_stadium_no",
        "backtest_stadium_no",
    ]:
        v = st.session_state.get(key)
        if v is not None:
            try:
                return int(v)
            except Exception:
                pass

    name = st.session_state.get("stadium")

    if isinstance(name, str):
        for no, n in data.STADIUM_NAMES.items():
            if name == n:
                return int(no)

    return 1


# =========================
# 過去成績
# =========================
@st.cache_data(ttl=300)
def get_history(stadium_no, d):
    try:
        return data.history14(stadium_no, d)
    except Exception:
        return []


# =========================
# 3連単配当
# =========================
def get_payout(race):

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

    for x in trifecta:
        if not isinstance(x, dict):
            continue

        try:
            amount = int(
                str(x.get("amount", 0))
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
def get_actual(race):

    try:
        x = data.get_result_order(race)

        if x and len(x) >= 3:
            return tuple(x[:3])

    except Exception:
        pass

    return ()


# =========================
# 3連単6点
# =========================
def make_bets(ai):

    try:
        a = int(ai["main"])
        b = int(ai["counter"])
        c = int(ai["hole"])
    except Exception:
        return []

    if not all(1 <= x <= 6 for x in [a, b, c]):
        return []

    if len({a, b, c}) != 3:
        return []

    return [
        (a, b, c),
        (a, c, b),
        (b, a, c),
        (b, c, a),
        (c, a, b),
        (c, b, a),
    ]


# =========================
# バックテスト
# =========================
def run_backtest(stadium_no, target):

    # JSTで昨日
    today = datetime.now(JST).date()
    d = today - timedelta(days=1)

    records = []

    progress = st.progress(0)
    status = st.empty()

    # 診断情報
    days = 0
    race_count = 0
    result_count = 0
    ai_count = 0
    error_count = 0
    first_error = ""

    while d >= START_DATE and len(records) < target:

        days += 1

        stadium = data.stadium_name(stadium_no)

        status.info(
            f"🔄 {d} {stadium}を検索中"
        )

        # -------------------------
        # レース取得
        # -------------------------
        try:
            races = data.all_races_for_date(
                d,
                stadium_no
            )

            if races is None:
                races = []

        except Exception as e:
            races = []
            if not first_error:
                first_error = (
                    f"レース取得エラー: {type(e).__name__}: {e}"
                )

        race_count += len(races)

        # -------------------------
        # レース処理
        # -------------------------
        for race in races:

            if len(records) >= target:
                break

            race_no = race.get(
                "race_number",
                "?"
            )

            status.info(
                f"🔄 {d} {stadium} "
                f"{race_no}Rを検証中"
            )

            try:

                # 結果
                result = data.get_result(race)

                if not result:
                    continue

                result_count += 1

                # 実着順
                actual = get_actual(race)

                if len(actual) < 3:
                    continue

                # 出走表
                rows = data.get_race_rows(race)

                if rows is None:
                    continue

                if len(rows) == 0:
                    continue

                # 過去成績
                history = get_history(
                    stadium_no,
                    d
                )

                # AI
                ai = tri_ai(
                    rows,
                    history,
                    stadium_no
                )

                ai_count += 1

                # 買い目
                bets = make_bets(ai)

                if len(bets) != 6:
                    continue

                main = int(ai["main"])
                counter = int(ai["counter"])
                hole = int(ai["hole"])

                # 判定
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

                exact = (
                    actual ==
                    (main, counter, hole)
                )

                bet_hit = (
                    actual in bets
                )

                payout = 0

                if bet_hit:
                    payout = get_payout(race)

                records.append({

                    "日付": d,
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
                        exact,

                    "買い目的中":
                        bet_hit,

                    "買い目数": 6,

                    "3連単配当":
                        payout,

                    "3連単的中":
                        bet_hit and payout > 0,
                })

            except Exception as e:

                error_count += 1

                if not first_error:
                    first_error = (
                        f"{d} {race_no}R: "
                        f"{type(e).__name__}: {e}"
                    )

                continue

            progress.progress(
                min(
                    len(records) / target,
                    1.0
                )
            )

        d -= timedelta(days=1)

    progress.progress(1.0)

    # =========================
    # 診断表示
    # =========================
    st.caption(
        f"🔎 検索日数 {days}日 / "
        f"取得レース {race_count} / "
        f"確定結果 {result_count} / "
        f"AI処理 {ai_count}"
    )

    if error_count > 0:
        st.caption(
            f"⚠️ 処理エラー {error_count}件"
        )

    if first_error and len(records) == 0:
        st.error(
            f"最初のエラー: {first_error}"
        )

    status.success(
        f"✅ {len(records)}レースの検証が完了しました。"
    )

    return pd.DataFrame(records)


# =========================
# 指標
# =========================
def metrics(df):

    if df.empty:
        return {}

    investment = (
        int(df["買い目数"].sum())
        * 100
    )

    payout = int(
        df["3連単配当"].sum()
    )

    roi = (
        payout / investment * 100
        if investment > 0
        else 0
    )

    return {
        "main_win":
            df["本命1着"].mean() * 100,

        "main_top3":
            df["本命3連対"].mean() * 100,

        "ai_top3":
            df["AI上位3艇3連対"].mean() * 100,

        "exact":
            df["3連単完全的中"].mean() * 100,

        "bet_hit":
            df["買い目的中"].mean() * 100,

        "investment":
            investment,

        "payout":
            payout,

        "roi":
            roi,
    }


# =========================
# AI評価
# =========================
def rating(roi):

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
# メイン画面
# =========================
def render_backtest(stadium_no=None):

    st.subheader(
        "📊 AIバックテスト"
    )

    st.caption(
        "2026-01-01以降の確定レースを自動で遡って検証します。"
    )

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
        key="backtest_count"
    )

    if st.button(
        "🚀 バックテスト開始",
        use_container_width=True,
        key="backtest_start"
    ):

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
                "検証できる確定レースがありませんでした。"
            )

        else:

            st.session_state[
                "backtest_df"
            ] = df

            st.session_state[
                "backtest_target"
            ] = count

    # =========================
    # 結果
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

    m = metrics(df)

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
        f"🤖 AI評価 {rating(m['roi'])}"
    )

    with st.expander(
        "🔎 バックテスト詳細を見る"
    ):

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )
