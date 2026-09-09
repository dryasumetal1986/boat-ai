# backtest.py

from datetime import date, timedelta

import pandas as pd
import streamlit as st

import data
from ai import tri_ai


# =========================================================
# 実際の3連単結果を取得
# =========================================================

def _extract_actual_order(race):
    results = race.get("results", {})

    if not results:
        return None

    rows = []

    # results がリストの場合
    if isinstance(results, list):
        rows = results

    # results が辞書の場合
    elif isinstance(results, dict):

        # よくあるキー
        for key in [
            "racer",
            "racers",
            "results",
            "result",
        ]:
            value = results.get(key)

            if isinstance(value, list):
                rows = value
                break

        # {"1": {...}, "2": {...}} 形式
        if not rows:

            numeric_items = []

            for key, value in results.items():

                try:
                    rank = int(key)
                    numeric_items.append(
                        (rank, value)
                    )
                except Exception:
                    continue

            if numeric_items:

                numeric_items.sort(
                    key=lambda x: x[0]
                )

                rows = [
                    value
                    for _, value in numeric_items
                ]

    if not rows:
        return None

    order = []

    for index, row in enumerate(rows):

        if not isinstance(row, dict):
            continue

        # 着順
        rank = (
            row.get("着順")
            or row.get("rank")
            or row.get("finish")
            or row.get("finish_position")
            or row.get("順位")
            or index + 1
        )

        try:
            rank = int(rank)
        except Exception:
            continue

        # 艇番
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

        if 1 <= lane <= 6:
            order.append(
                (rank, lane)
            )

    if len(order) < 3:
        return None

    order.sort(
        key=lambda x: x[0]
    )

    result = [
        lane
        for _, lane in order[:3]
    ]

    if len(result) != 3:
        return None

    if len(set(result)) != 3:
        return None

    return tuple(result)


# =========================================================
# 的中判定
# =========================================================

def _is_hit(prediction, actual):

    if prediction is None:
        return False

    if actual is None:
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
            [
                float(value)
                for value in boat_probs
            ],
            reverse=True
        )

        top = values[0]

        if top >= 0.45:
            return "★★★★★"

        if top >= 0.38:
            return "★★★★☆"

        if top >= 0.32:
            return "★★★☆☆"

        if top >= 0.26:
            return "★★☆☆☆"

        return "★☆☆☆☆"

    except Exception:
        return "★★★☆☆"


# =========================================================
# 1レースを検証
# =========================================================

def evaluate_race(
    target_date,
    stadium_no,
    race_no,
    history=None,
    raw=None,
):

    try:

        if raw is None:
            raw = data.get_data(
                target_date
            )

        race = data.get_race(
            raw,
            stadium_no,
            race_no
        )

        if not race:
            return None

        if not data.validate_race(
            race,
            stadium_no,
            race_no
        ):
            return None

        # 6艇
        rows = data.get_race_rows(
            race
        )

        if not rows:
            return None

        if len(rows) != 6:
            return None

        # 実際の着順
        actual = _extract_actual_order(
            race
        )

        if actual is None:
            return None

        # 学習用過去データ
        if history is None:
            history = data.history14(
                target_date
            )

        # AI予想
        prediction = tri_ai(
            rows,
            history
        )

        if not prediction:
            return None

        main = prediction.get(
            "main"
        )

        counter = prediction.get(
            "counter"
        )

        hole = prediction.get(
            "hole"
        )

        boat_probs = prediction.get(
            "boat_probs",
            []
        )

        return {
            "date": target_date,
            "stadium_no": stadium_no,
            "stadium": data.stadium_name(
                stadium_no
            ),
            "race": race_no,

            "main": (
                "-".join(
                    map(str, main)
                )
                if main
                else ""
            ),

            "counter": (
                "-".join(
                    map(str, counter)
                )
                if counter
                else ""
            ),

            "hole": (
                "-".join(
                    map(str, hole)
                )
                if hole
                else ""
            ),

            "actual": "-".join(
                map(str, actual)
            ),

            "main_hit": _is_hit(
                main,
                actual
            ),

            "counter_hit": _is_hit(
                counter,
                actual
            ),

            "hole_hit": _is_hit(
                hole,
                actual
            ),

            "main_or_counter_hit": (
                _is_hit(main, actual)
                or
                _is_hit(counter, actual)
            ),

            "confidence": (
                _confidence_from_probs(
                    boat_probs
                )
            ),
        }

    except Exception:
        return None


# =========================================================
# 直近○レースを取得してバックテスト
# =========================================================

def run_backtest(
    race_count=300
):

    records = []

    # 今日から過去へ
    current = date.today()

    # 最大60日まで遡る
    max_days = 60

    days_checked = 0

    while (
        len(records) < race_count
        and days_checked < max_days
    ):

        target_date = current.isoformat()

        try:

            # その日のデータ
            raw = data.get_data(
                target_date
            )

            # その日の過去14日データ
            # 同じ日付では1回だけ取得
            history = data.history14(
                target_date
            )

        except Exception:

            current -= timedelta(
                days=1
            )

            days_checked += 1
            continue

        # 24場
        for stadium_no in range(1, 25):

            if len(records) >= race_count:
                break

            # 1R～12R
            for race_no in range(1, 13):

                if len(records) >= race_count:
                    break

                result = evaluate_race(
                    target_date=target_date,
                    stadium_no=stadium_no,
                    race_no=race_no,
                    history=history,
                    raw=raw,
                )

                if result is None:
                    continue

                records.append(result)

        # 前日へ
        current -= timedelta(
            days=1
        )

        days_checked += 1

    return pd.DataFrame(
        records
    )


# =========================================================
# 集計
# =========================================================

def summarize_backtest(df):

    if df is None or df.empty:

        return {
            "races": 0,
            "main_hit_rate": 0.0,
            "counter_hit_rate": 0.0,
            "hole_hit_rate": 0.0,
            "main_or_counter_rate": 0.0,
        }

    total = len(df)

    return {
        "races": total,

        "main_hit_rate": (
            df["main_hit"].mean()
            * 100
        ),

        "counter_hit_rate": (
            df["counter_hit"].mean()
            * 100
        ),

        "hole_hit_rate": (
            df["hole_hit"].mean()
            * 100
        ),

        "main_or_counter_rate": (
            df[
                "main_or_counter_hit"
            ].mean()
            * 100
        ),
    }


# =========================================================
# 自信度別集計
# =========================================================

def confidence_summary(df):

    if df is None or df.empty:
        return pd.DataFrame()

    result = (
        df.groupby(
            "confidence"
        )
        .agg(
            レース数=(
                "main_hit",
                "count"
            ),

            本命的中率=(
                "main_hit",
                "mean"
            ),

            本命対抗的中率=(
                "main_or_counter_hit",
                "mean"
            ),
        )
        .reset_index()
    )

    result[
        "本命的中率"
    ] = (
        result["本命的中率"]
        * 100
    ).round(1)

    result[
        "本命対抗的中率"
    ] = (
        result["本命対抗的中率"]
        * 100
    ).round(1)

    return result


# =========================================================
# Streamlit画面
# =========================================================

def render_backtest():

    st.markdown(
        "### 📊 AI実力テスト"
    )

    st.caption(
        "日付を指定せず、直近のレース数だけ選んでAIを検証できます。"
    )

    # ---------------------------------------------
    # レース数選択
    # ---------------------------------------------

    race_count = st.radio(
        "検証するレース数",
        options=[
            100,
            300,
            500,
            1000,
        ],
        format_func=lambda x:
            f"直近{x:,}レース",
        horizontal=True,
    )

    st.info(
        f"📌 直近 {race_count:,} レースを自動で探して検証します。"
    )

    # ---------------------------------------------
    # 開始
    # ---------------------------------------------

    if st.button(
        "🚀 検証開始",
        use_container_width=True,
        key="start_backtest",
    ):

        progress = st.progress(
            0
        )

        status = st.empty()

        status.write(
            f"🔎 直近{race_count:,}レースを探しています..."
        )

        with st.spinner(
            "AIが過去レースを検証しています..."
        ):

            df = run_backtest(
                race_count=race_count
            )

        progress.progress(
            100
        )

        status.empty()

        # -----------------------------------------
        # データなし
        # -----------------------------------------

        if df is None or df.empty:

            st.error(
                "検証できるレースがありませんでした。"
            )

            return

        # -----------------------------------------
        # 集計
        # -----------------------------------------

        summary = summarize_backtest(
            df
        )

        st.success(
            f"✅ {summary['races']:,}レースの検証が完了しました。"
        )

        # -----------------------------------------
        # 結果
        # -----------------------------------------

        st.markdown(
            "#### 🎯 検証結果"
        )

        col1, col2 = st.columns(2)

        with col1:

            st.metric(
                "検証レース",
                f"{summary['races']:,}R"
            )

        with col2:

            st.metric(
                "本命的中率",
                f"{summary['main_hit_rate']:.1f}%"
            )

        col3, col4 = st.columns(2)

        with col3:

            st.metric(
                "対抗的中率",
                f"{summary['counter_hit_rate']:.1f}%"
            )

        with col4:

            st.metric(
                "本命＋対抗",
                f"{summary['main_or_counter_rate']:.1f}%"
            )

        # -----------------------------------------
        # 穴
        # -----------------------------------------

        st.metric(
            "穴的中率",
            f"{summary['hole_hit_rate']:.1f}%"
        )

        # -----------------------------------------
        # 自信度
        # -----------------------------------------

        st.markdown(
            "#### ⭐ 自信度別成績"
        )

        confidence_df = (
            confidence_summary(df)
        )

        if not confidence_df.empty:

            st.dataframe(
                confidence_df,
                use_container_width=True,
                hide_index=True,
            )

        # -----------------------------------------
        # レース別
        # -----------------------------------------

        st.markdown(
            "#### 📋 レース別結果"
        )

        display_df = df.copy()

        def result_label(row):

            if row["main_hit"]:
                return "🎯 本命"

            if row["counter_hit"]:
                return "🔥 対抗"

            if row["hole_hit"]:
                return "💥 穴"

            return "－"

        display_df[
            "結果"
        ] = display_df.apply(
            result_label,
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
            hide_index=True,
        )

        # -----------------------------------------
        # CSV
        # -----------------------------------------

        csv = df.to_csv(
            index=False
        ).encode(
            "utf-8-sig"
        )

        st.download_button(
            "📥 検証結果CSVを保存",
            data=csv,
            file_name=(
                f"boat_ai_backtest_"
                f"{race_count}.csv"
            ),
            mime="text/csv",
            use_container_width=True,
        )
