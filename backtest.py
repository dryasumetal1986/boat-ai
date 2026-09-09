# backtest.py
# 🚤 やっちゃんの競艇AI予想PRO
# バックテスト完全版

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from data import (
    STADIUM_NAMES,
    get_data,
    get_race,
    get_race_rows,
    get_result_order,
    get_trifecta_payout,
    is_completed,
)

from ai import tri_ai


# =========================================================
# API開始日
# =========================================================

API_START_DATE = date(
    2026,
    1,
    1,
)


# =========================================================
# 1レース検証
# =========================================================

def evaluate_race(
    race: Dict[str, Any],
    stadium_number: int,
    race_number: int,
    race_date: date,
) -> Dict[str, Any] | None:

    if not is_completed(
        race
    ):
        return None

    rows = get_race_rows(
        race,
        stadium_number,
    )

    if len(rows) < 6:
        return None

    result = get_result_order(
        race
    )

    if len(result) < 3:
        return None

    try:

        df = pd.DataFrame(
            rows
        )

        prediction = tri_ai(
            df,
            history=None,
            stadium_number=stadium_number,
        )

    except Exception:

        return None

    main = int(
        prediction["main"]
    )

    counter = int(
        prediction["counter"]
    )

    hole = int(
        prediction["hole"]
    )

    ranking = prediction.get(
        "ranking",
        [],
    )

    # -----------------------------------------------------
    # 的中判定
    # -----------------------------------------------------

    main_win = (
        main == result[0]
    )

    main_top3 = (
        main in result[:3]
    )

    top3_hit = (
        len(
            set(ranking[:3])
            & set(result[:3])
        )
        == 3
    )

    exact_trifecta = (
        result[:3]
        == [
            main,
            counter,
            hole,
        ]
    )

    combination = (
        f"{main}-"
        f"{counter}-"
        f"{hole}"
    )

    payout = get_trifecta_payout(
        race,
        combination,
    )

    return {
        "date": race_date,
        "stadium_number": stadium_number,
        "stadium_name": STADIUM_NAMES.get(
            stadium_number,
            f"{stadium_number}場",
        ),
        "race_number": race_number,

        "main": main,
        "counter": counter,
        "hole": hole,

        "result1": result[0],
        "result2": result[1],
        "result3": result[2],

        "main_win": main_win,
        "main_top3": main_top3,
        "top3_hit": top3_hit,
        "exact_trifecta": exact_trifecta,

        "combination": combination,
        "payout": payout,
    }


# =========================================================
# バックテスト本体
# =========================================================

def run_backtest(
    count: int,
    progress_callback=None,
) -> List[Dict[str, Any]]:

    results: List[
        Dict[str, Any]
    ] = []

    today = date.today()

    current_date = (
        today
        - timedelta(days=1)
    )

    # -----------------------------------------------------
    # 2026年1月1日まで遡る
    # -----------------------------------------------------

    total_days = (
        current_date
        - API_START_DATE
    ).days + 1

    scanned_days = 0

    while (
        current_date
        >= API_START_DATE
        and len(results) < count
    ):

        scanned_days += 1

        raw = get_data(
            current_date
        )

        if raw is not None:

            stadiums = raw.get(
                "programs",
                {},
            ).get(
                "stadiums",
                {},
            )

            if isinstance(
                stadiums,
                dict,
            ):

                for (
                    stadium_key,
                    stadium_data,
                ) in stadiums.items():

                    try:

                        stadium_number = int(
                            stadium_key
                        )

                    except Exception:

                        continue

                    if not isinstance(
                        stadium_data,
                        dict,
                    ):
                        continue

                    races = stadium_data.get(
                        "races",
                        {},
                    )

                    if not isinstance(
                        races,
                        dict,
                    ):
                        continue

                    for race_key in sorted(
                        races.keys(),
                        key=lambda x: int(x)
                        if str(x).isdigit()
                        else 99,
                    ):

                        if len(results) >= count:
                            break

                        try:

                            race_number = int(
                                race_key
                            )

                        except Exception:

                            continue

                        race = get_race(
                            raw,
                            stadium_number,
                            race_number,
                        )

                        if race is None:
                            continue

                        if not is_completed(
                            race
                        ):
                            continue

                        item = evaluate_race(
                            race,
                            stadium_number,
                            race_number,
                            current_date,
                        )

                        if item is None:
                            continue

                        results.append(
                            item
                        )

                        if progress_callback:

                            progress_callback(
                                len(results),
                                count,
                                current_date,
                                stadium_number,
                                race_number,
                                scanned_days,
                                total_days,
                            )

                    if len(results) >= count:
                        break

        current_date -= timedelta(
            days=1
        )

    return results


# =========================================================
# 結果表示
# =========================================================

def show_backtest_result(
    results: List[Dict[str, Any]]
):

    if not results:

        st.error(
            "⚠️ 検証可能なレースがありませんでした。"
        )

        return

    df = pd.DataFrame(
        results
    )

    total = len(df)

    main_win_rate = (
        df["main_win"].mean()
        * 100
    )

    main_top3_rate = (
        df["main_top3"].mean()
        * 100
    )

    top3_rate = (
        df["top3_hit"].mean()
        * 100
    )

    trifecta_rate = (
        df["exact_trifecta"].mean()
        * 100
    )

    # -----------------------------------------------------
    # 回収率
    # -----------------------------------------------------

    bet_count = total

    total_bet = (
        bet_count
        * 100
    )

    total_return = int(
        df["payout"].sum()
    )

    recovery = (
        total_return
        / total_bet
        * 100
        if total_bet > 0
        else 0
    )

    # -----------------------------------------------------
    # 評価
    # -----------------------------------------------------

    if (
        main_top3_rate >= 75
        and recovery >= 100
    ):
        rating = "★★★★★"

    elif (
        main_top3_rate >= 65
        and recovery >= 90
    ):
        rating = "★★★★☆"

    elif (
        main_top3_rate >= 55
    ):
        rating = "★★★☆☆"

    elif (
        main_top3_rate >= 45
    ):
        rating = "★★☆☆☆"

    else:
        rating = "★☆☆☆☆"

    # -----------------------------------------------------
    # 結果
    # -----------------------------------------------------

    st.markdown(
        "## 🏆 AIバックテスト結果"
    )

    st.caption(
        "過去の完了レースを使ってAI予想の精度を検証しました。"
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "検証レース数",
            f"{total:,}",
        )

    with col2:

        st.metric(
            "🎯 本命1着率",
            f"{main_win_rate:.1f}%",
        )

    with col3:

        st.metric(
            "🎯 本命3連対率",
            f"{main_top3_rate:.1f}%",
        )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "🏆 AI上位3艇3連対",
            f"{top3_rate:.1f}%",
        )

    with col2:

        st.metric(
            "🎯 3連単完全的中",
            f"{trifecta_rate:.1f}%",
        )

    with col3:

        st.metric(
            "💰 簡易回収率",
            f"{recovery:.1f}%",
        )

    st.markdown(
        f"### 🤖 AI評価　{rating}"
    )

    # -----------------------------------------------------
    # 最近の検証
    # -----------------------------------------------------

    st.subheader(
        "📋 検証結果"
    )

    display_df = df[
        [
            "date",
            "stadium_name",
            "race_number",
            "main",
            "counter",
            "hole",
            "result1",
            "result2",
            "result3",
            "main_win",
            "main_top3",
            "exact_trifecta",
            "payout",
        ]
    ].copy()

    display_df.columns = [
        "日付",
        "会場",
        "R",
        "本命",
        "対抗",
        "穴",
        "1着",
        "2着",
        "3着",
        "本命1着",
        "本命3連対",
        "3連単的中",
        "払戻",
    ]

    display_df["R"] = (
        display_df["R"].astype(str)
        + "R"
    )

    st.dataframe(
        display_df.head(100),
        use_container_width=True,
        hide_index=True,
    )


# =========================================================
# UI
# =========================================================

def render_backtest():

    st.divider()

    st.markdown(
        "## 📊 AIの実力を検証する"
    )

    st.write(
        "過去の完了レースを使って、AI予想の精度を検証します。"
    )

    st.info(
        "📌 日付ではなく完了レース数で指定します。"
        "指定した件数に達するまで、"
        "2026年1月1日まで自動的に遡ります。"
    )

    count = st.selectbox(
        "検証するレース数",
        [
            100,
            300,
            500,
            1000,
        ],
        format_func=lambda x: (
            f"直近{x:,}レース"
        ),
        key="backtest_count",
    )

    if st.button(
        "🚀 バックテスト開始",
        type="primary",
        use_container_width=True,
        key="start_backtest",
    ):

        progress = st.progress(
            0
        )

        status = st.empty()

        def update(
            current,
            target,
            current_date,
            stadium_number,
            race_number,
            scanned_days,
            total_days,
        ):

            ratio = min(
                current / target,
                1.0,
            )

            progress.progress(
                ratio
            )

            venue = STADIUM_NAMES.get(
                stadium_number,
                f"{stadium_number}場",
            )

            status.markdown(
                f"""
**🔄 {current_date} {venue} {race_number}Rを検証中**

**{current:,} / {target:,} レース**

過去へ {scanned_days} 日遡っています。
"""
            )

        with st.spinner(
            "🔍 過去レースを検索・検証しています..."
        ):

            results = run_backtest(
                count,
                update,
            )

        progress.progress(
            1.0
        )

        status.empty()

        if len(results) < count:

            st.warning(
                f"⚠️ APIから取得できた検証可能レースは "
                f"{len(results):,}件でした。"
                f"（2026年1月1日まで検索）"
            )

        if results:

            show_backtest_result(
                results
            )

        else:

            st.error(
                "⚠️ 検証可能な完了レースを取得できませんでした。"
    )
