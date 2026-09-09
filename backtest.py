# backtest.py

from datetime import date, timedelta
import itertools

import pandas as pd
import streamlit as st

import data
from ai import tri_ai


# =========================================================
# 実際の着順を取り出す
# APIの多少の形式違いにも対応
# =========================================================

def _extract_actual_order(race):
    results = race.get("results", {})

    if not results:
        return None

    rows = []

    if isinstance(results, list):
        rows = results

    elif isinstance(results, dict):
        # よくある形式
        for key in ["racer", "racers", "results", "result"]:
            value = results.get(key)
            if isinstance(value, list):
                rows = value
                break

        # {"1": {...}, "2": {...}} のような形式
        if not rows:
            numeric_items = []
            for k, v in results.items():
                try:
                    rank = int(k)
                    numeric_items.append((rank, v))
                except Exception:
                    pass

            if numeric_items:
                numeric_items.sort(key=lambda x: x[0])
                rows = [v for _, v in numeric_items]

    if not rows:
        return None

    order = []

    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue

        rank = (
            row.get("着順")
            or row.get("rank")
            or row.get("finish")
            or row.get("finish_position")
            or row.get("順位")
            or (i + 1)
        )

        try:
            rank = int(rank)
        except Exception:
            continue

        lane = (
            row.get("艇番")
            or row.get("boat")
            or row.get("boat_number")
            or row.get("枠")
            or row.get("lane")
        )

        if lane is None:
            continue

        try:
            lane = int(lane)
        except Exception:
            continue

        order.append((rank, lane))

    if len(order) < 3:
        return None

    order.sort(key=lambda x: x[0])

    result = [lane for _, lane in order[:3]]

    if len(result) != 3:
        return None

    if len(set(result)) != 3:
        return None

    return tuple(result)


# =========================================================
# 3連単的中判定
# =========================================================

def _is_hit(prediction, actual):
    if prediction is None or actual is None:
        return False

    return tuple(prediction) == tuple(actual)


# =========================================================
# 自信度
# =========================================================

def _confidence_from_probs(boat_probs):
    if not boat_probs:
        return "★☆☆☆☆"

    try:
        values = sorted(
            [float(v) for v in boat_probs],
            reverse=True
        )

        top = values[0]

        if top >= 0.45:
            return "★★★★★"
        elif top >= 0.38:
            return "★★★★☆"
        elif top >= 0.32:
            return "★★★☆☆"
        elif top >= 0.26:
            return "★★☆☆☆"
        else:
            return "★☆☆☆☆"

    except Exception:
        return "★★★☆☆"


# =========================================================
# 1レース検証
# =========================================================

def evaluate_race(target_date, stadium_no, race_no):
    try:
        raw = data.get_data(target_date)

        race = data.get_race(
            raw,
            stadium_no,
            race_no
        )

        if not race:
            return None

        rows = data.get_race_rows(race)

        if not rows or len(rows) != 6:
            return None

        # 過去14日間のデータ
        history = data.history14(target_date)

        result = tri_ai(
            rows,
            history
        )

        if not result:
            return None

        actual = _extract_actual_order(race)

        if actual is None:
            return None

        main = result.get("main")
        counter = result.get("counter")
        hole = result.get("hole")

        boat_probs = result.get("boat_probs", [])

        return {
            "date": target_date,
            "stadium_no": stadium_no,
            "stadium": data.stadium_name(stadium_no),
            "race": race_no,
            "main": tuple(main) if main else None,
            "counter": tuple(counter) if counter else None,
            "hole": tuple(hole) if hole else None,
            "actual": actual,
            "main_hit": _is_hit(main, actual),
            "counter_hit": _is_hit(counter, actual),
            "hole_hit": _is_hit(hole, actual),
            "main_or_counter_hit": (
                _is_hit(main, actual)
                or _is_hit(counter, actual)
            ),
            "confidence": _confidence_from_probs(boat_probs),
        }

    except Exception:
        return None


# =========================================================
# 指定期間をバックテスト
# =========================================================

def run_backtest(start_date, end_date, max_races=None):
    records = []

    current = start_date

    while current <= end_date:

        target_date = current.isoformat()

        try:
            raw = data.get_data(target_date)
        except Exception:
            current += timedelta(days=1)
            continue

        for stadium_no in range(1, 25):

            for race_no in range(1, 13):

                if max_races is not None and len(records) >= max_races:
                    return pd.DataFrame(records)

                try:
                    race = data.get_race(
                        raw,
                        stadium_no,
                        race_no
                    )

                    if not race:
                        continue

                    rows = data.get_race_rows(race)

                    if not rows or len(rows) != 6:
                        continue

                    actual = _extract_actual_order(race)

                    if actual is None:
                        continue

                    history = data.history14(target_date)

                    result = tri_ai(
                        rows,
                        history
                    )

                    if not result:
                        continue

                    main = result.get("main")
                    counter = result.get("counter")
                    hole = result.get("hole")

                    boat_probs = result.get("boat_probs", [])

                    records.append({
                        "date": target_date,
                        "stadium_no": stadium_no,
                        "stadium": data.stadium_name(stadium_no),
                        "race": race_no,
                        "main": "-".join(map(str, main))
                        if main else "",
                        "counter": "-".join(map(str, counter))
                        if counter else "",
                        "hole": "-".join(map(str, hole))
                        if hole else "",
                        "actual": "-".join(map(str, actual)),
                        "main_hit": _is_hit(main, actual),
                        "counter_hit": _is_hit(counter, actual),
                        "hole_hit": _is_hit(hole, actual),
                        "main_or_counter_hit": (
                            _is_hit(main, actual)
                            or _is_hit(counter, actual)
                        ),
                        "confidence": _confidence_from_probs(
                            boat_probs
                        ),
                    })

                    if len(records) % 10 == 0:
                        print(
                            f"バックテスト: {len(records)}レース"
                        )

                except Exception:
                    continue

        current += timedelta(days=1)

    return pd.DataFrame(records)


# =========================================================
# 集計
# =========================================================

def summarize_backtest(df):

    if df is None or df.empty:
        return {
            "races": 0,
            "main_hit_rate": 0,
            "counter_hit_rate": 0,
            "hole_hit_rate": 0,
            "main_or_counter_rate": 0,
        }

    total = len(df)

    return {
        "races": total,
        "main_hit_rate": (
            df["main_hit"].mean() * 100
        ),
        "counter_hit_rate": (
            df["counter_hit"].mean() * 100
        ),
        "hole_hit_rate": (
            df["hole_hit"].mean() * 100
        ),
        "main_or_counter_rate": (
            df["main_or_counter_hit"].mean() * 100
        ),
    }


# =========================================================
# 自信度別集計
# =========================================================

def confidence_summary(df):

    if df is None or df.empty:
        return pd.DataFrame()

    result = (
        df.groupby("confidence")
        .agg(
            レース数=("main_hit", "count"),
            本命的中率=("main_hit", "mean"),
            本命対抗的中率=("main_or_counter_hit", "mean"),
        )
        .reset_index()
    )

    result["本命的中率"] = (
        result["本命的中率"] * 100
    ).round(1)

    result["本命対抗的中率"] = (
        result["本命対抗的中率"] * 100
    ).round(1)

    return result


# =========================================================
# Streamlit画面
# =========================================================

def render_backtest():

    st.markdown("## 📊 AIバックテスト")

    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input(
            "開始日",
            value=date.today() - timedelta(days=14)
        )

    with col2:
        end_date = st.date_input(
            "終了日",
            value=date.today() - timedelta(days=1)
        )

    max_races = st.number_input(
        "検証レース数",
        min_value=1,
        max_value=5000,
        value=300,
        step=100,
        help="最初は300レース程度がおすすめです。"
    )

    if start_date >= end_date:
        st.warning("開始日は終了日より前にしてください。")
        return

    if st.button(
        "🚀 バックテスト開始",
        use_container_width=True
    ):

        progress = st.progress(0)

        with st.spinner(
            "過去レースを検証しています..."
        ):
            df = run_backtest(
                start_date,
                end_date,
                max_races=max_races
            )

        progress.progress(100)

        if df.empty:
            st.error(
                "検証できるレースがありませんでした。"
            )
            return

        summary = summarize_backtest(df)

        st.success(
            f"{summary['races']}レースの検証が完了しました。"
        )

        st.markdown("### 🎯 検証結果")

        c1, c2 = st.columns(2)

        with c1:
            st.metric(
                "検証レース",
                f"{summary['races']}R"
            )

        with c2:
            st.metric(
                "本命3連単的中率",
                f"{summary['main_hit_rate']:.1f}%"
            )

        c3, c4 = st.columns(2)

        with c3:
            st.metric(
                "対抗3連単的中率",
                f"{summary['counter_hit_rate']:.1f}%"
            )

        with c4:
            st.metric(
                "本命＋対抗",
                f"{summary['main_or_counter_rate']:.1f}%"
            )

        st.markdown("### ⭐ 自信度別")

        confidence_df = confidence_summary(df)

        if not confidence_df.empty:
            st.dataframe(
                confidence_df,
                use_container_width=True,
                hide_index=True
            )

        st.markdown("### 📋 レース別結果")

        display_df = df.copy()

        display_df["結果"] = display_df.apply(
            lambda x:
                "🎯 本命"
                if x["main_hit"]
                else (
                    "🔥 対抗"
                    if x["counter_hit"]
                    else (
                        "💥 穴"
                        if x["hole_hit"]
                        else "－"
                    )
                ),
            axis=1
        )

        display_df = display_df[
            [
                "date",
                "stadium",
                "race",
                "main",
                "counter",
                "hole",
                "actual",
                "confidence",
                "結果",
            ]
        ]

        display_df.columns = [
            "日付",
            "場",
            "R",
            "本命",
            "対抗",
            "穴",
            "実際の結果",
            "自信度",
            "結果",
        ]

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

        csv = df.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            "📥 検証結果CSVを保存",
            data=csv,
            file_name="boat_ai_backtest.csv",
            mime="text/csv",
            use_container_width=True
          )
