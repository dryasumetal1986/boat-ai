from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

import data
from ai import tri_ai

JST = timezone(timedelta(hours=9))


def _money(v):
    try:
        return int(
            float(
                str(v)
                .replace(",", "")
                .replace("円", "")
                .replace("¥", "")
            )
        )
    except Exception:
        return 0


def trifecta_payout(race):
    result = data.get_result(race)
    if not isinstance(result, dict):
        return 0

    keys = [
        "trifecta_payout",
        "3連単払戻",
        "3連単",
        "payout",
        "payouts",
    ]

    for key in keys:
        value = result.get(key)

        if isinstance(value, dict):
            for k in [
                "payout",
                "amount",
                "money",
                "払戻金",
                "払戻",
            ]:
                if k in value:
                    money = _money(value[k])
                    if money > 0:
                        return money
        else:
            money = _money(value)
            if money > 0:
                return money

    return 0


def _history(stadium, race_no, target):
    rows = []

    for n in range(1, 15):
        d = target - timedelta(days=n)

        if d < data.API_START_DATE:
            break

        raw = data.get_data(d)
        race = data.get_race(
            raw,
            stadium,
            race_no,
        )

        if not race:
            continue

        order = data.get_result_order(race)

        if len(order) < 3:
            continue

        df = data.get_race_rows(race)

        if df.empty:
            continue

        df = df.copy()
        places = {
            boat: i + 1
            for i, boat in enumerate(order)
        }

        df["着順"] = df["枠"].map(places)
        df["日付"] = d.isoformat()
        df = df.dropna(subset=["着順"])

        if not df.empty:
            rows.append(df)

    if not rows:
        return pd.DataFrame()

    return pd.concat(
        rows,
        ignore_index=True,
    )


def run_backtest(
    target_count=100,
    progress_callback=None,
):
    try:
        target_count = int(target_count)
    except Exception:
        target_count = 100

    target_count = max(
        1,
        target_count,
    )

    # data.jst_today() は使わない
    current = (
        datetime.now(JST).date()
        - timedelta(days=1)
    )

    result_rows = []

    while (
        current >= data.API_START_DATE
        and len(result_rows) < target_count
    ):
        raw = data.get_data(current)

        if raw:
            races = data.all_races_for_date(raw)

            for stadium, race_no, race in races:
                if len(result_rows) >= target_count:
                    break

                if not data.race_has_result(race):
                    continue

                order = data.get_result_order(race)

                if len(order) < 3:
                    continue

                df = data.get_race_rows(race)

                if df.empty:
                    continue

                df = df.copy()
                df["場"] = stadium

                try:
                    history = _history(
                        stadium,
                        race_no,
                        current,
                    )

                    ai = tri_ai(
                        df,
                        history=history,
                        stadium_number=stadium,
                    )
                except Exception:
                    continue

                ranking = ai.get(
                    "ranking",
                    [],
                )

                if len(ranking) < 3:
                    continue

                main = int(
                    ai.get("main", ranking[0])
                )

                counter = int(
                    ai.get("counter", ranking[1])
                )

                hole = int(
                    ai.get("hole", ranking[2])
                )

                actual = [
                    int(x)
                    for x in order[:3]
                ]

                result_rows.append(
                    {
                        "日付": current.isoformat(),
                        "場番号": stadium,
                        "場": data.stadium_name(stadium),
                        "R": race_no,
                        "本命": main,
                        "対抗": counter,
                        "穴": hole,
                        "実着1": actual[0],
                        "実着2": actual[1],
                        "実着3": actual[2],
                        "本命1着": main == actual[0],
                        "本命3連対": main in actual,
                        "AI上位3艇3連対":
                            all(
                                x in actual
                                for x in ranking[:3]
                            ),
                        "3連単的中":
                            (
                                main,
                                counter,
                                hole,
                            )
                            == tuple(actual),
                        "3連単配当":
                            trifecta_payout(race),
                    }
                )

                if progress_callback:
                    progress_callback(
                        len(result_rows),
                        target_count,
                        current,
                        stadium,
                        race_no,
                    )

        current -= timedelta(days=1)

    return pd.DataFrame(result_rows)


def calculate_metrics(df):
    if df is None or df.empty:
        return {
            "count": 0,
            "main_win_rate": 0,
            "main_top3_rate": 0,
            "top3_rate": 0,
            "trifecta_rate": 0,
            "roi": 0,
            "stars": 1,
        }

    count = len(df)

    win = df["本命1着"].mean() * 100
    top3 = df["本命3連対"].mean() * 100
    ai3 = (
        df["AI上位3艇3連対"].mean()
        * 100
    )
    tri = (
        df["3連単的中"].mean()
        * 100
    )

    investment = count * 100

    payout = (
        df["3連単配当"]
        .fillna(0)
        .apply(_money)
        .sum()
    )

    roi = (
        payout / investment * 100
        if investment
        else 0
    )

    score = 0

    if win >= 50:
        score += 2
    elif win >= 40:
        score += 1

    if top3 >= 80:
        score += 2
    elif top3 >= 70:
        score += 1

    if ai3 >= 20:
        score += 1

    if tri >= 10:
        score += 1

    if roi >= 100:
        score += 2
    elif roi >= 80:
        score += 1

    stars = (
        5 if score >= 7 else
        4 if score >= 5 else
        3 if score >= 3 else
        2 if score >= 2 else
        1
    )

    return {
        "count": count,
        "main_win_rate": win,
        "main_top3_rate": top3,
        "top3_rate": ai3,
        "trifecta_rate": tri,
        "roi": roi,
        "stars": stars,
    }


def render_backtest():
    st.markdown("---")
    st.subheader("📊 AIバックテスト")
    st.caption(
        "2026-01-01以降の確定レースを自動で遡って検証します。"
    )

    count = st.selectbox(
        "検証レース数",
        [100, 300, 500, 1000],
        key="backtest_count",
    )

    if not st.button(
        "🔍 バックテスト開始",
        type="primary",
        use_container_width=True,
        key="backtest_start",
    ):
        return

    bar = st.progress(0)
    status = st.empty()
    counter = st.empty()
    boats = st.empty()

    def progress(
        current,
        total,
        target_date,
        stadium,
        race_no,
    ):
        bar.progress(
            min(
                current / total,
                1.0,
            )
        )

        name = data.stadium_name(stadium)

        status.info(
            f"🔄 {target_date} "
            f"{name} {race_no}Rを検証中"
        )

        counter.write(
            f"**{current} / {total} レース**"
        )

        boat = (
            (current - 1) % 6
        ) + 1

        boats.write(
            " ".join(
                "🚤" if i == boat else "▫️"
                for i in range(1, 7)
            )
        )

    with st.spinner(
        "バックテストを実行しています..."
    ):
        df = run_backtest(
            count,
            progress,
        )

    bar.progress(1.0)
    boats.write("🚤 **バックテスト完了！**")

    if df.empty:
        status.error(
            "⚠️ 検証できる確定レースがありませんでした。"
        )
        return

    m = calculate_metrics(df)

    status.success(
        f"✅ {m['count']}レースの検証が完了しました。"
    )

    counter.write(
        f"**{m['count']} / {count} レース**"
    )

    st.markdown("### 📈 バックテスト結果")

    c1, c2 = st.columns(2)

    with c1:
        st.metric(
            "本命1着率",
            f"{m['main_win_rate']:.1f}%",
        )

    with c2:
        st.metric(
            "本命3連対率",
            f"{m['main_top3_rate']:.1f}%",
        )

    c3, c4 = st.columns(2)

    with c3:
        st.metric(
            "AI上位3艇3連対",
            f"{m['top3_rate']:.1f}%",
        )

    with c4:
        st.metric(
            "3連単完全的中",
            f"{m['trifecta_rate']:.1f}%",
        )

    st.metric(
        "簡易回収率",
        f"{m['roi']:.1f}%",
    )

    st.markdown(
        f"### 🤖 AI評価 {'★' * m['stars']}"
    )

    with st.expander(
        "🔎 バックテスト詳細を見る"
    ):
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )
