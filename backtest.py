import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone

import data
from ai import tri_ai


JST = timezone(timedelta(hours=9))
START_DATE = datetime(2026, 1, 1).date()


def stadium_no():
    v = st.session_state.get("stadium_no")
    if v is not None:
        try:
            return int(v)
        except:
            pass

    name = st.session_state.get("stadium")

    if isinstance(name, str):
        for no, n in data.STADIUM_NAMES.items():
            if name == n:
                return int(no)

    return 1


def get_day_races(d, no):
    try:
        raw = data.get_data(d)
    except Exception:
        return []

    if not isinstance(raw, dict):
        return []

    programs = raw.get("programs", {})
    stadiums = programs.get("stadiums", {})

    if not isinstance(stadiums, dict):
        return []

    name = data.stadium_name(no)
    stadium = None

    for key, value in stadiums.items():
        s = str(key)

        if (
            s == str(no)
            or s == str(no).zfill(2)
            or s == name
        ):
            stadium = value
            break

    if stadium is None:
        return []

    races = stadium.get("races", {})

    if not isinstance(races, dict):
        return []

    result = []

    for key, race in races.items():
        if not isinstance(race, dict):
            continue

        r = dict(race)

        try:
            rn = int(
                r.get(
                    "race_number",
                    str(key).replace("R", "")
                )
            )
        except:
            continue

        r["race_number"] = rn
        r["stadium_number"] = no
        r["date"] = str(d)

        result.append(r)

    result.sort(
        key=lambda x: x["race_number"]
    )

    return result


def get_history(no, d):
    try:
        return data.history14(no, d)
    except:
        return []


def actual_order(race):
    try:
        order = data.get_result_order(race)

        if order and len(order) >= 3:
            return tuple(order[:3])
    except:
        pass

    return ()


def payout(race):
    try:
        result = data.get_result(race)
    except:
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
        except:
            amount = 0

        if amount > 0:
            return amount

    return 0


def make_bets(ai):
    try:
        a = int(ai["main"])
        b = int(ai["counter"])
        c = int(ai["hole"])
    except:
        return []

    if not all(
        1 <= x <= 6
        for x in [a, b, c]
    ):
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


def run_backtest(no, target):

    today = datetime.now(JST).date()
    d = today - timedelta(days=1)

    rows = []

    progress = st.progress(0)
    status = st.empty()

    days = 0
    found = 0
    completed = 0
    ai_ok = 0
    errors = 0
    first_error = ""

    while d >= START_DATE and len(rows) < target:

        days += 1
        name = data.stadium_name(no)

        status.info(
            f"🔄 {d} {name}を検索中"
        )

        try:
            races = get_day_races(d, no)
        except Exception as e:
            races = []

            if not first_error:
                first_error = (
                    f"{type(e).__name__}: {e}"
                )

        found += len(races)

        for race in races:

            if len(rows) >= target:
                break

            rn = race.get(
                "race_number",
                "?"
            )

            status.info(
                f"🔄 {d} {name} {rn}Rを検証中"
            )

            try:
                result = data.get_result(race)

                if not result:
                    continue

                completed += 1

                actual = actual_order(race)

                if len(actual) < 3:
                    continue

                race_rows = data.get_race_rows(
                    race
                )

                if race_rows is None:
                    continue

                if len(race_rows) == 0:
                    continue

                history = get_history(no, d)

                ai = tri_ai(
                    race_rows,
                    history,
                    no
                )

                ai_ok += 1

                bets = make_bets(ai)

                if len(bets) != 6:
                    continue

                main = int(ai["main"])
                counter = int(ai["counter"])
                hole = int(ai["hole"])

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

                hit = actual in bets

                money = (
                    payout(race)
                    if hit else 0
                )

                rows.append({
                    "日付": d,
                    "場番号": no,
                    "場": name,
                    "R": rn,
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
                    "買い目的中": hit,
                    "買い目数": 6,
                    "3連単配当": money,
                    "3連単的中": (
                        hit and money > 0
                    ),
                })

                progress.progress(
                    min(
                        len(rows) / target,
                        1.0
                    )
                )

            except Exception as e:
                errors += 1

                if not first_error:
                    first_error = (
                        f"{d} {rn}R "
                        f"{type(e).__name__}: {e}"
                    )

                continue

        d -= timedelta(days=1)

    progress.progress(1.0)

    status.success(
        f"✅ {len(rows)}レースの検証が完了しました。"
    )

    st.caption(
        f"🔎 検索日数 {days}日 / "
        f"対象レース {found} / "
        f"確定結果 {completed} / "
        f"AI処理 {ai_ok}"
    )

    if errors:
        st.caption(
            f"⚠️ 処理エラー {errors}件"
        )

    if first_error and not rows:
        st.error(
            f"最初のエラー: {first_error}"
        )

    return pd.DataFrame(rows)


def calc(df):

    investment = int(
        df["買い目数"].sum()
    ) * 100

    payout_total = int(
        df["3連単配当"].sum()
    )

    roi = (
        payout_total /
        investment * 100
        if investment
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
        "hit":
            df["買い目的中"].mean() * 100,
        "investment":
            investment,
        "payout":
            payout_total,
        "roi":
            roi,
    }


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


def render_backtest(stadium_no=None):

    st.subheader("📊 AIバックテスト")

    st.caption(
        "2026-01-01以降の確定レースを自動で遡って検証します。"
    )

    if stadium_no is None:
        stadium_no = stadium_no()

    try:
        no = int(stadium_no)
    except:
        no = 1

    count = st.selectbox(
        "検証レース数",
        [100, 300, 500, 1000],
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
            no,
            count
        )

        if not df.empty:
            st.session_state[
                "backtest_df"
            ] = df

            st.session_state[
                "backtest_target"
            ] = count

        else:
            st.error(
                "検証できる確定レースがありませんでした。"
            )

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

    m = calc(df)

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
        f"{m['hit']:.1f}%"
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
