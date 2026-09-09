from datetime import date, timedelta

import pandas as pd
import streamlit as st

import data
from ai import tri_ai


# =========================================================
# 実際の3連単結果
# =========================================================

def _extract_actual_order(race):

    results = race.get(
        "results",
        {},
    )

    if not results:
        return None

    rows = []

    if isinstance(results, list):

        rows = results

    elif isinstance(results, dict):

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

        if not rows:

            numeric_items = []

            for key, value in results.items():

                try:
                    numeric_items.append(
                        (int(key), value)
                    )
                except Exception:
                    continue

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

        rank = (
            row.get("着順")
            or row.get("rank")
            or row.get("finish")
            or row.get("finish_position")
            or row.get("finishPosition")
            or row.get("順位")
            or index + 1
        )

        lane = (
            row.get("艇番")
            or row.get("boat")
            or row.get("boat_number")
            or row.get("boatNumber")
            or row.get("枠")
            or row.get("lane")
        )

        try:
            rank = int(float(rank))
            lane = int(float(lane))
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

    if (
        len(result) != 3
        or len(set(result)) != 3
    ):
        return None

    return tuple(result)


# =========================================================
# 的中
# =========================================================

def _is_hit(prediction, actual):

    if prediction is None or actual is None:
        return False

    return tuple(prediction) == tuple(actual)


# =========================================================
# 自信度
# =========================================================

def confidence_from_probs(boat_probs):

    if not boat_probs:
        return "★☆☆☆☆"

    try:

        if isinstance(boat_probs, dict):
            values = list(
                boat_probs.values()
            )
        else:
            values = list(boat_probs)

        values = sorted(
            [
                float(value)
                for value in values
            ],
            reverse=True,
        )

        if not values:
            return "★☆☆☆☆"

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
# 1レース
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
            raw = data.get_data(target_date)

        race = data.get_race(
            raw,
            stadium_no,
            race_no,
        )

        if not data.validate_race(
            race,
            target_date,
            stadium_no,
            race_no,
        ):
            return None

        rows = data.get_race_rows(
            race,
            stadium_no,
            race_no,
        )

        if rows is None or len(rows) != 6:
            return None

        actual = _extract_actual_order(
            race
        )

        if actual is None:
            return None

        if history is None:
            history = data.history14(
                target_date
            )

        prediction = tri_ai(
            rows,
            history,
        )

        if not prediction:
            return None

        main = prediction.get("main")
        counter = prediction.get("counter")
        hole = prediction.get("hole")

        return {
            "date": target_date,
            "stadium_no": stadium_no,
            "stadium": data.stadium_name(
                stadium_no
            ),
            "race": race_no,

            "main": (
                "-".join(map(str, main))
                if main
                else ""
            ),

            "counter": (
                "-".join(map(str, counter))
                if counter
                else ""
            ),

            "hole": (
                "-".join(map(str, hole))
                if hole
                else ""
            ),

            "actual": "-".join(
                map(str, actual)
            ),

            "main_hit": _is_hit(
                main,
                actual,
            ),

            "counter_hit": _is_hit(
                counter,
                actual,
            ),

            "hole_hit": _is_hit(
                hole,
                actual,
            ),

            "main_or_counter_hit": (
                _is_hit(main, actual)
                or _is_hit(counter, actual)
            ),

            "confidence": confidence_from_probs(
                prediction.get(
                    "boat_probs",
                    {},
                )
            ),
        }

    except Exception:
        return None


# =========================================================
# 直近Nレース
# =========================================================

def run_backtest(
    race_count=300,
    progress_callback=None,
):

    records = []

    # 今日ではなく昨日から開始
    current = date.today() - timedelta(days=1)

    # 十分余裕を持って探索
    max_days = 120

    for day_index in range(max_days):

        if len(records) >= race_count:
            break

        target_date = current.isoformat()

        try:

            raw = data.get_data(
                target_date
            )

        except Exception:

            current -= timedelta(days=1)
            continue

        # その日が存在しているかだけ先に確認
        if not isinstance(raw, dict):
            current -= timedelta(days=1)
            continue

        try:

            history = data.history14(
                target_date
            )

        except Exception:

            history = pd.DataFrame()

        for stadium_no in range(1, 25):

            if len(records) >= race_count:
                break

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

                if result is not None:
                    records.append(result)

        if progress_callback:

            progress_callback(
                min(
                    len(records) / race_count,
                    1.0,
                ),
                len(records),
                target_date,
            )

        current -= timedelta(days=1)

    return pd.DataFrame(records)


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

    return {
        "races": len(df),

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
            df["main_or_counter_hit"].mean()
            * 100
        ),
    }


# =========================================================
# 自信度別
# =========================================================

def confidence_summary(df):

    if df is None or df.empty:
        return pd.DataFrame()

    result = (
        df.groupby("confidence")
        .agg(
            レース数=(
                "main_hit",
                "count",
            ),
            本命的中率=(
                "main_hit",
                "mean",
            ),
            本命対抗的中率=(
                "main_or_counter_hit",
                "mean",
            ),
        )
        .reset_index()
    )

    result["本命的中率"] = (
        result["本命的中率"] * 100
    ).round(1)

    result["本命対抗的中率"] = (
        result["本命対抗的中率"] * 100
    ).round(1)

    order = [
        "★★★★★",
        "★★★★☆",
        "★★★☆☆",
        "★★☆☆☆",
        "★☆☆☆☆",
    ]

    result["sort"] = result[
        "confidence"
    ].map(
        {
            value: index
            for index, value in enumerate(order)
        }
    )

    result = (
        result
        .sort_values("sort")
        .drop(columns=["sort"])
    )

    return result


# =========================================================
# 画面
# =========================================================

def render_backtest():

    st.markdown(
        '<div class="backtest-title">📊 AI実力テスト</div>',
        unsafe_allow_html=True,
    )

    st.caption(
        "日付指定なし。直近の完了レースから自動で必要数を集めて検証します。"
    )

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
        f"📌 直近 {race_count:,}R を自動探索します。"
    )

    if not st.button(
        "🚀 検証開始",
        use_container_width=True,
        key="start_backtest",
    ):
        return

    progress = st.progress(0)
    status = st.empty()

    def update_progress(
        ratio,
        found,
        target_date,
    ):

        progress.progress(
            min(max(ratio, 0.0), 1.0)
        )

        status.write(
            f"🔎 {target_date} を確認中 — "
            f"{found:,} / {race_count:,}R"
        )

    with st.spinner(
        "AIが過去レースを検証しています..."
    ):

        df = run_backtest(
            race_count=race_count,
            progress_callback=update_progress,
        )

    progress.progress(1.0)
    status.empty()

    if df is None or df.empty:

        st.error(
            "検証できる完了レースが見つかりませんでした。"
        )

        return

    summary = summarize_backtest(df)

    st.success(
        f"✅ {summary['races']:,}レースの検証が完了しました。"
    )

    # =====================================================
    # 結果カード
    # =====================================================

    st.markdown(
        "#### 🎯 検証結果"
    )

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "検証レース",
            f"{summary['races']:,}R",
        )

    with col2:

        st.metric(
            "本命的中率",
            f"{summary['main_hit_rate']:.1f}%",
        )

    col3, col4 = st.columns(2)

    with col3:

        st.metric(
            "対抗的中率",
            f"{summary['counter_hit_rate']:.1f}%",
        )

    with col4:

        st.metric(
            "本命＋対抗",
            f"{summary['main_or_counter_rate']:.1f}%",
        )

    st.metric(
        "穴的中率",
        f"{summary['hole_hit_rate']:.1f}%",
    )


    # =====================================================
    # 自信度
    # =====================================================

    st.markdown(
        "#### ⭐ 自信度別成績"
    )

    confidence_df = confidence_summary(
        df
    )

    if not confidence_df.empty:

        st.dataframe(
            confidence_df,
            use_container_width=True,
            hide_index=True,
        )


    # =====================================================
    # レース別
    # =====================================================

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

    display_df["結果"] = display_df.apply(
        result_label,
        axis=1,
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


    # =====================================================
    # CSV
    # =====================================================

    csv = df.to_csv(
        index=False
    ).encode("utf-8-sig")

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
