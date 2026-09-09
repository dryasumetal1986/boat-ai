import time
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

import data
from ai import tri_ai


START_DATE = date(2026, 1, 1)
BET_YEN = 100


# =========================
# 基本
# =========================

def get_yesterday_jst():
    return datetime.now(data.JST).date() - timedelta(days=1)


def get_stadium_no(race):
    try:
        n = race.get("stadium_number")
        if n is not None:
            return int(n)
    except Exception:
        pass
    return 0


def get_race_no(race, key=None):
    try:
        n = race.get("race_number")
        if n is not None:
            return int(n)
    except Exception:
        pass

    try:
        if key is not None:
            return int(key)
    except Exception:
        pass

    return 0


# =========================
# 完走結果
# =========================

def get_actual_order(race):
    try:
        result = data.get_result(race)

        if not isinstance(result, dict):
            return []

        racers = result.get("racers", [])

        if not isinstance(racers, list):
            return []

        rows = []

        for r in racers:
            if not isinstance(r, dict):
                continue

            try:
                place = int(r.get("place_number", 0))
            except Exception:
                place = 0

            try:
                boat = int(
                    r.get(
                        "boat_number",
                        r.get("number", 0)
                    )
                )
            except Exception:
                boat = 0

            if place > 0 and boat > 0:
                rows.append((place, boat))

        rows.sort(key=lambda x: x[0])

        return [boat for _, boat in rows]

    except Exception:
        return []


def has_completed_result(race):
    return len(get_actual_order(race)) >= 3


# =========================
# 3連単配当
# =========================

def trifecta_payout(race):
    try:
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
                amount = int(item.get("amount", 0))
            except Exception:
                amount = 0

            if amount > 0:
                return amount

    except Exception:
        pass

    return 0


# =========================
# AI買い目
# =========================

def make_bets(ai):
    try:
        main = int(ai.get("main", 0))
        counter = int(ai.get("counter", 0))
        hole = int(ai.get("hole", 0))
    except Exception:
        return []

    nums = [main, counter, hole]

    if not all(1 <= x <= 6 for x in nums):
        return []

    if len(set(nums)) != 3:
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
# 1レース検証
# =========================

def analyze_race(race):
    stadium_no = get_stadium_no(race)

    if stadium_no < 1 or stadium_no > 24:
        return None

    race_no = get_race_no(race)

    if race_no < 1:
        return None

    actual = get_actual_order(race)

    if len(actual) < 3:
        return None

    rows = data.get_race_rows(race)

    if rows is None:
        return None

    if len(rows) < 6:
        return None

    race_date = race.get("date")

    if not race_date:
        return None

    history = data.history14(
        stadium_no,
        race_date
    )

    ai = tri_ai(
        rows,
        history,
        stadium_no
    )

    if not isinstance(ai, dict):
        return None

    main = int(ai.get("main", 0))
    counter = int(ai.get("counter", 0))
    hole = int(ai.get("hole", 0))

    bets = make_bets(ai)

    if len(bets) != 6:
        return None

    actual_trifecta = tuple(actual[:3])

    hit_main = (
        main == actual[0]
    )

    hit_main_top3 = (
        main in actual[:3]
    )

    ai_top3 = ai.get("ranking", [])[:3]

    ai_top3 = [
        int(x)
        for x in ai_top3
        if str(x).isdigit()
    ]

    hit_ai_top3 = (
        len(ai_top3) == 3
        and all(x in actual[:3] for x in ai_top3)
    )

    hit_trifecta = (
        actual_trifecta in bets
    )

    payout = trifecta_payout(race)

    bet_payout = (
        payout
        if hit_trifecta
        else 0
    )

    stadium_name = data.stadium_name(
        stadium_no
    )

    return {
        "日付": str(race_date),
        "場": stadium_name,
        "場番号": stadium_no,
        "R": race_no,

        "本命": main,
        "対抗": counter,
        "穴": hole,

        "実着順": "-".join(
            map(str, actual)
        ),

        "本命1着": int(hit_main),
        "本命3連対": int(hit_main_top3),
        "AI上位3艇3連対": int(hit_ai_top3),
        "3連単完全的中": int(hit_trifecta),

        "買い目数": len(bets),
        "買い目的中": int(hit_trifecta),

        "3連単配当": payout,
        "払戻額": bet_payout,

        "投資額": len(bets) * BET_YEN,

        "買い目": " ".join(
            f"{a}-{b}-{c}"
            for a, b, c in bets
        ),

        "信頼度": ai.get(
            "confidence_percent",
            0
        ),
    }


# =========================
# 全国からレース抽出
# =========================

def get_completed_races_for_date(check_date):
    """
    1日分の全国24場データから
    完了済みレースだけを返す。
    """

    raw = data.get_data(check_date)

    if not isinstance(raw, dict):
        return []

    programs = raw.get(
        "programs",
        {}
    )

    if not isinstance(programs, dict):
        return []

    stadiums = programs.get(
        "stadiums",
        {}
    )

    if not isinstance(stadiums, dict):
        return []

    result = []

    for stadium_key, stadium_data in stadiums.items():

        if not isinstance(stadium_data, dict):
            continue

        races = stadium_data.get(
            "races",
            {}
        )

        if not isinstance(races, dict):
            continue

        for race_key, race in races.items():

            if not isinstance(race, dict):
                continue

            stadium_no = get_stadium_no(race)

            # 念のためキーからも補完
            if not (
                1 <= stadium_no <= 24
            ):
                try:
                    stadium_no = int(
                        stadium_key
                    )
                except Exception:
                    stadium_no = 0

            if not (
                1 <= stadium_no <= 24
            ):
                continue

            race_no = get_race_no(
                race,
                race_key
            )

            if not (
                1 <= race_no <= 12
            ):
                continue

            if not has_completed_result(
                race
            ):
                continue

            result.append(race)

    result.sort(
        key=lambda x: (
            get_stadium_no(x),
            get_race_no(x)
        )
    )

    return result


# =========================
# 全国バックテスト
# =========================

def run_backtest(
    target_count=100,
    progress_callback=None
):
    records = []

    current_date = get_yesterday_jst()

    error_count = 0
    first_error = None

    total_days = (
        current_date - START_DATE
    ).days + 1

    checked_days = 0

    while (
        current_date >= START_DATE
        and len(records) < target_count
    ):

        checked_days += 1

        try:
            races = get_completed_races_for_date(
                current_date
            )
        except Exception as e:
            races = []
            error_count += 1

            if first_error is None:
                first_error = (
                    f"{current_date}: {e}"
                )

        for race in races:

            if len(records) >= target_count:
                break

            stadium_no = get_stadium_no(
                race
            )

            race_no = get_race_no(
                race
            )

            stadium_name = data.stadium_name(
                stadium_no
            )

            if progress_callback:
                progress_callback(
                    current_date,
                    stadium_name,
                    race_no,
                    len(records),
                    target_count
                )

            try:
                item = analyze_race(
                    race
                )

                if item is not None:
                    records.append(item)

            except Exception as e:
                error_count += 1

                if first_error is None:
                    first_error = (
                        f"{current_date} "
                        f"{stadium_name} "
                        f"{race_no}R: {e}"
                    )

            time.sleep(0.01)

        current_date -= timedelta(days=1)

    df = pd.DataFrame(records)

    return (
        df,
        checked_days,
        error_count,
        first_error
    )


# =========================
# 成績計算
# =========================

def calculate_metrics(df):
    if df.empty:
        return {}

    races = len(df)

    main_win = (
        df["本命1着"].sum()
        / races
        * 100
    )

    main_top3 = (
        df["本命3連対"].sum()
        / races
        * 100
    )

    ai_top3 = (
        df["AI上位3艇3連対"].sum()
        / races
        * 100
    )

    trifecta_hit = (
        df["3連単完全的中"].sum()
        / races
        * 100
    )

    bet_hit = (
        df["買い目的中"].sum()
        / races
        * 100
    )

    investment = int(
        df["投資額"].sum()
    )

    payout = int(
        df["払戻額"].sum()
    )

    roi = (
        payout / investment * 100
        if investment > 0
        else 0
    )

    if roi >= 100:
        stars = 5
    elif roi >= 80:
        stars = 4
    elif roi >= 60:
        stars = 3
    elif roi >= 40:
        stars = 2
    else:
        stars = 1

    return {
        "races": races,
        "main_win": main_win,
        "main_top3": main_top3,
        "ai_top3": ai_top3,
        "trifecta_hit": trifecta_hit,
        "bet_hit": bet_hit,
        "investment": investment,
        "payout": payout,
        "roi": roi,
        "stars": stars,
    }


# =========================
# 画面
# =========================

def render_backtest(stadium_no=None):

    st.markdown(
        "## 📊 AI予想バックテスト"
    )

    st.caption(
        "🌎 全国24場を対象に、昨日から2026-01-01まで遡って検証"
    )

    target = st.selectbox(
        "検証レース数",
        [100, 300, 500, 1000],
        index=0,
        key="backtest_count"
    )

    if st.button(
        "🚀 バックテスト開始",
        use_container_width=True
    ):

        progress = st.progress(0)

        status = st.empty()

        info = st.empty()

        def update(
            check_date,
            stadium_name,
            race_no,
            count,
            total
        ):
            status.markdown(
                f"🔄 {check_date} "
                f"{stadium_name} "
                f"{race_no}Rを検証中"
            )

            info.write(
                f"{count} / {total} レース"
            )

            progress.progress(
                min(
                    count / total,
                    1.0
                )
            )

        with st.spinner(
            "全国24場の過去レースを検索中..."
        ):

            df, days, errors, first_error = (
                run_backtest(
                    target,
                    update
                )
            )

        progress.progress(1.0)

        status.success(
            f"✅ {len(df)}レースの検証完了"
        )

        if df.empty:
            st.error(
                "検証できる完了済みレースが見つかりませんでした。"
            )

            if first_error:
                st.caption(
                    f"最初のエラー: {first_error}"
                )

            return

        metrics = calculate_metrics(df)

        st.markdown(
            f"### 🌎 全国24場・{len(df)}レース"
        )

        cols = st.columns(4)

        cols[0].metric(
            "本命1着率",
            f"{metrics['main_win']:.1f}%"
        )

        cols[1].metric(
            "本命3連対率",
            f"{metrics['main_top3']:.1f}%"
        )

        cols[2].metric(
            "3連単完全的中",
            f"{metrics['trifecta_hit']:.1f}%"
        )

        cols[3].metric(
            "AI買い目的中率",
            f"{metrics['bet_hit']:.1f}%"
        )

        cols = st.columns(3)

        cols[0].metric(
            "投資額",
            f"{metrics['investment']:,}円"
        )

        cols[1].metric(
            "払戻額",
            f"{metrics['payout']:,}円"
        )

        cols[2].metric(
            "買い目回収率",
            f"{metrics['roi']:.1f}%"
        )

        st.write(
            "AI評価 "
            + "★" * metrics["stars"]
            + "☆" * (5 - metrics["stars"])
        )

        st.markdown(
            "### 📝 検証詳細"
        )

        display_cols = [
            "日付",
            "場",
            "R",
            "本命",
            "対抗",
            "穴",
            "実着順",
            "本命1着",
            "本命3連対",
            "AI上位3艇3連対",
            "3連単完全的中",
            "買い目数",
            "3連単配当",
            "払戻額",
            "投資額",
            "買い目",
        ]

        display_cols = [
            c for c in display_cols
            if c in df.columns
        ]

        st.dataframe(
            df[display_cols],
            use_container_width=True,
            hide_index=True
        )

        if errors:
            st.caption(
                f"⚠️ 一部レースでスキップ: "
                f"{errors}件"
            )

            if first_error:
                st.caption(
                    f"最初のエラー: {first_error}"
            )
