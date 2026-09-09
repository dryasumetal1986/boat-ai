import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone

import data
from ai import tri_ai


JST = timezone(timedelta(hours=9))
START_DATE = datetime(2026, 1, 1).date()


# =========================
# 開催場番号を取得
# =========================
def get_stadium_no():
    for key in [
        "stadium_no",
        "selected_stadium_no",
        "backtest_stadium_no",
    ]:
        value = st.session_state.get(key)

        if value is not None:
            try:
                return int(value)
            except Exception:
                pass

    name = st.session_state.get("stadium")

    if isinstance(name, str):
        for no, n in data.STADIUM_NAMES.items():
            if name == n:
                return int(no)

    return 1


# =========================
# 指定日の指定場レース取得
# all_races_for_date()は使わない
# =========================
def get_day_races(check_date, target_stadium):

    try:
        raw = data.get_data(check_date)
    except Exception:
        return []

    if not isinstance(raw, dict):
        return []

    programs = raw.get("programs", {})

    if not isinstance(programs, dict):
        return []

    stadiums = programs.get("stadiums", {})

    if not isinstance(stadiums, dict):
        return []

    result = []

    # 全開催場を確認
    for _, stadium_data in stadiums.items():

        if not isinstance(stadium_data, dict):
            continue

        races = stadium_data.get("races", {})

        if not isinstance(races, dict):
            continue

        for key, race in races.items():

            if not isinstance(race, dict):
                continue

            # レース自身が持っている場番号を優先
            race_stadium = race.get(
                "stadium_number"
            )

            try:
                race_stadium = int(
                    race_stadium
                )
            except Exception:
                continue

            if race_stadium != target_stadium:
                continue

            r = dict(race)

            try:
                race_number = int(
                    r.get(
                        "race_number",
                        str(key).replace("R", "")
                    )
                )
            except Exception:
                continue

            r["race_number"] = race_number
            r["stadium_number"] = target_stadium
            r["date"] = str(check_date)

            result.append(r)

    result.sort(
        key=lambda x: x["race_number"]
    )

    return result


# =========================
# 過去14日データ
# =========================
@st.cache_data(ttl=300)
def get_history(target_stadium, check_date):

    try:
        return data.history14(
            target_stadium,
            check_date
        )
    except Exception:
        return []


# =========================
# 実着順
# =========================
def get_actual_order(race):

    try:
        order = data.get_result_order(
            race
        )

        if order and len(order) >= 3:
            return tuple(order[:3])

    except Exception:
        pass

    return ()


# =========================
# 3連単配当
# =========================
def get_trifecta_payout(race):

    try:
        result = data.get_result(
            race
        )
    except Exception:
        return 0

    if not isinstance(result, dict):
        return 0

    payouts = result.get(
        "payouts",
        {}
    )

    if not isinstance(payouts, dict):
        return 0

    trifecta = payouts.get(
        "trifecta",
        []
    )

    if not isinstance(trifecta, list):
        return 0

    for item in trifecta:

        if not isinstance(item, dict):
            continue

        try:
            amount = int(
                str(
                    item.get(
                        "amount",
                        0
                    )
                ).replace(",", "")
            )
        except Exception:
            amount = 0

        if amount > 0:
            return amount

    return 0


# =========================
# AI 3連単6点
# =========================
def make_bets(ai):

    try:
        main = int(
            ai["main"]
        )

        counter = int(
            ai["counter"]
        )

        hole = int(
            ai["hole"]
        )

    except Exception:
        return []

    if not all(
        1 <= x <= 6
        for x in [
            main,
            counter,
            hole
        ]
    ):
        return []

    if len({
        main,
        counter,
        hole
    }) != 3:
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
def run_backtest(
    target_stadium,
    target_count
):

    today = datetime.now(
        JST
    ).date()

    check_date = (
        today -
        timedelta(days=1)
    )

    records = []

    progress = st.progress(0)
    status = st.empty()

    search_days = 0
    found_races = 0
    completed_races = 0
    ai_success = 0
    errors = 0

    first_error = ""

    stadium_name = data.stadium_name(
        target_stadium
    )

    while (
        check_date >= START_DATE
        and len(records) < target_count
    ):

        search_days += 1

        status.info(
            f"🔄 {check_date} "
            f"{stadium_name}を検索中"
        )

        # -------------------------
        # 指定日の指定場を取得
        # -------------------------
        try:

            races = get_day_races(
                check_date,
                target_stadium
            )

        except Exception as e:

            races = []

            errors += 1

            if not first_error:
                first_error = (
                    f"{check_date} "
                    f"レース取得エラー: "
                    f"{type(e).__name__}: {e}"
                )

        found_races += len(races)

        # -------------------------
        # 各レース
        # -------------------------
        for race in races:

            if len(records) >= target_count:
                break

            race_no = race.get(
                "race_number",
                "?"
            )

            status.info(
                f"🔄 {check_date} "
                f"{stadium_name} "
                f"{race_no}Rを検証中"
            )

            try:

                # -----------------
                # 確定結果
                # -----------------
                result = data.get_result(
                    race
                )

                if not result:
                    continue

                completed_races += 1

                # -----------------
                # 実着順
                # -----------------
                actual = get_actual_order(
                    race
                )

                if len(actual) < 3:
                    continue

                # -----------------
                # 出走表
                # -----------------
                race_rows = data.get_race_rows(
                    race
                )

                if race_rows is None:
                    continue

                if len(race_rows) == 0:
                    continue

                # -----------------
                # 過去成績
                # -----------------
                history = get_history(
                    target_stadium,
                    check_date
                )

                # -----------------
                # AI予想
                # -----------------
                ai = tri_ai(
                    race_rows,
                    history,
                    target_stadium
                )

                ai_success += 1

                # -----------------
                # 6点買い
                # -----------------
                bets = make_bets(
                    ai
                )

                if len(bets) != 6:
                    continue

                main = int(
                    ai["main"]
                )

                counter = int(
                    ai["counter"]
                )

                hole = int(
                    ai["hole"]
                )

                # -----------------
                # 本命1着
                # -----------------
                main_win = (
                    actual[0] == main
                )

                # -----------------
                # 本命3連対
                # -----------------
                main_top3 = (
                    main in actual
                )

                # -----------------
                # AI上位3艇が
                # 全て3着以内
                # -----------------
                ai_top3 = all(
                    x in actual
                    for x in [
                        main,
                        counter,
                        hole
                    ]
                )

                # -----------------
                # 本命→対抗→穴
                # 完全的中
                # -----------------
                exact = (
                    actual ==
                    (
                        main,
                        counter,
                        hole
                    )
                )

                # -----------------
                # 6点のどれか的中
                # -----------------
                bet_hit = (
                    actual in bets
                )

                # -----------------
                # 配当
                # 的中時だけ取得
                # -----------------
                payout = 0

                if bet_hit:
                    payout = (
                        get_trifecta_payout(
                            race
                        )
                    )

                # -----------------
                # 保存
                # -----------------
                records.append({

                    "日付":
                        check_date,

                    "場番号":
                        target_stadium,

                    "場":
                        stadium_name,

                    "R":
                        race_no,

                    "本命":
                        main,

                    "対抗":
                        counter,

                    "穴":
                        hole,

                    "実着1":
                        actual[0],

                    "実着2":
                        actual[1],

                    "実着3":
                        actual[2],

                    "本命1着":
                        main_win,

                    "本命3連対":
                        main_top3,

                    "AI上位3艇3連対":
                        ai_top3,

                    "3連単完全的中":
                        exact,

                    "買い目的中":
                        bet_hit,

                    "買い目数":
                        6,

                    "3連単配当":
                        payout,

                    "3連単的中":
                        (
                            bet_hit
                            and payout > 0
                        ),
                })

                progress.progress(
                    min(
                        len(records) /
                        target_count,
                        1.0
                    )
                )

            except Exception as e:

                errors += 1

                if not first_error:
                    first_error = (
                        f"{check_date} "
                        f"{race_no}R "
                        f"{type(e).__name__}: "
                        f"{e}"
                    )

                continue

        check_date -= timedelta(
            days=1
        )

    progress.progress(1.0)

    status.success(
        f"✅ {len(records)}レースの"
        f"検証が完了しました。"
    )

    # -------------------------
    # 診断情報
    # -------------------------
    st.caption(
        f"🔎 検索日数 {search_days}日 / "
        f"対象レース {found_races} / "
        f"確定結果 {completed_races} / "
        f"AI処理 {ai_success}"
    )

    if errors > 0:
        st.caption(
            f"⚠️ 処理エラー {errors}件"
        )

    if first_error and not records:
        st.error(
            f"最初のエラー: "
            f"{first_error}"
        )

    return pd.DataFrame(
        records
    )


# =========================
# 指標計算
# =========================
def calculate_metrics(df):

    if df.empty:
        return {}

    investment = (
        int(
            df["買い目数"].sum()
        ) * 100
    )

    payout_total = int(
        df["3連単配当"].sum()
    )

    if investment > 0:
        roi = (
            payout_total /
            investment *
            100
        )
    else:
        roi = 0

    return {

        "main_win":
            df["本命1着"].mean()
            * 100,

        "main_top3":
            df["本命3連対"].mean()
            * 100,

        "ai_top3":
            df["AI上位3艇3連対"].mean()
            * 100,

        "exact":
            df["3連単完全的中"].mean()
            * 100,

        "bet_hit":
            df["買い目的中"].mean()
            * 100,

        "investment":
            investment,

        "payout":
            payout_total,

        "roi":
            roi,
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
# =========================
def render_backtest(
    stadium_no=None
):

    st.subheader(
        "📊 AIバックテスト"
    )

    st.caption(
        "2026-01-01以降の確定レースを"
        "自動で遡って検証します。"
    )

    # -------------------------
    # 開催場
    # -------------------------
    if stadium_no is None:
        stadium_no = get_stadium_no()

    try:
        selected_no = int(
            stadium_no
        )
    except Exception:
        selected_no = 1

    # -------------------------
    # 検証レース数
    # -------------------------
    count = st.selectbox(
        "検証レース数",
        [
            100,
            300,
            500,
            1000
        ],
        index=0,
        key="backtest_count"
    )

    # -------------------------
    # 開始
    # -------------------------
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
            selected_no,
            count
        )

        if df.empty:

            st.error(
                "検証できる確定レースが"
                "ありませんでした。"
            )

        else:

            st.session_state[
                "backtest_df"
            ] = df

            st.session_state[
                "backtest_target"
            ] = count

    # -------------------------
    # 保存済み結果
    # -------------------------
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
        f"✅ {len(df)}レースの"
        f"検証が完了しました。"
    )

    st.write(
        f"{len(df)} / {target} レース"
    )

    st.info(
        "🚤 バックテスト完了！"
    )

    # -------------------------
    # 指標
    # -------------------------
    m = calculate_metrics(
        df
    )

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
        f"{m['investment']:,}円"
    )

    c8.metric(
        "払戻額",
        f"{m['payout']:,}円"
    )

    st.write(
        f"🤖 AI評価 "
        f"{ai_rating(m['roi'])}"
    )

    # -------------------------
    # 詳細
    # -------------------------
    with st.expander(
        "🔎 バックテスト詳細を見る"
    ):

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
    )
