from datetime import timedelta

import pandas as pd
import streamlit as st

from ai import tri_ai
from data import (
    API_START_DATE,
    STADIUM_NAMES,
    all_races_for_date,
    get_data,
    get_result_order,
    get_race_rows,
    history14,
    jst_today,
    race_has_result,
    stadium_name,
)


def _money(value):
    if value is None:
        return None

    try:
        text = str(value)
        digits = "".join(
            ch for ch in text
            if ch.isdigit()
        )

        if not digits:
            return None

        return int(digits)

    except Exception:
        return None


def _normalize_combo(value):
    if value is None:
        return ""

    text = str(value)

    text = (
        text.replace("－", "-")
        .replace("–", "-")
        .replace("—", "-")
        .replace("→", "-")
        .replace(" ", "")
        .replace("　", "")
        .replace("/", "-")
        .replace(">", "-")
    )

    digits = [
        ch for ch in text
        if ch in "123456"
    ]

    if len(digits) >= 3:
        return "-".join(
            digits[:3]
        )

    return text


def _search_payout(value, prediction):
    """
    payoutsの形が多少違っても
    3連単配当を探す。
    """

    target = _normalize_combo(
        prediction
    )

    if isinstance(value, dict):
        combination_keys = [
            "combination",
            "combo",
            "組合せ",
            "組み合わせ",
            "組合",
            "result",
        ]

        payout_keys = [
            "payout",
            "amount",
            "払戻",
            "払戻金",
            "金額",
        ]

        combination = None

        for key in combination_keys:
            if key in value:
                combination = value[key]
                break

        if combination is not None:
            if (
                _normalize_combo(
                    combination
                )
                == target
            ):
                for key in payout_keys:
                    if key in value:
                        money = _money(
                            value[key]
                        )
                        if money is not None:
                            return money

        for child in value.values():
            found = _search_payout(
                child,
                prediction,
            )

            if found is not None:
                return found

        return None

    if isinstance(value, list):
        for item in value:
            found = _search_payout(
                item,
                prediction,
            )

            if found is not None:
                return found

    return None


def trifecta_payout(
    race,
    prediction,
):
    """
    レース結果から3連単配当を取得。
    """

    if not isinstance(race, dict):
        return None

    result = race.get(
        "result",
        {},
    )

    if not isinstance(result, dict):
        return None

    payout_sources = []

    for key in (
        "payouts",
        "payout",
        "払い戻し",
        "払戻",
        "payouts_list",
    ):
        if key in result:
            payout_sources.append(
                result[key]
            )

    for source in payout_sources:
        found = _search_payout(
            source,
            prediction,
        )

        if found is not None:
            return found

    return None


def _history_from_cache(
    raw_cache,
    stadium_number,
    race_number,
    target_date,
):
    """
    バックテスト中は同じ日付データを
    メモリキャッシュして高速化する。
    """

    records = []

    for days_back in range(1, 15):
        d = (
            target_date
            - timedelta(days=days_back)
        )

        if d < API_START_DATE:
            break

        if d not in raw_cache:
            raw_cache[d] = get_data(d)

        raw = raw_cache.get(d)

        if not raw:
            continue

        from data import get_race

        race = get_race(
            raw,
            stadium_number,
            race_number,
        )

        if not race:
            continue

        actual = get_result_order(
            race
        )

        if len(actual) < 3:
            continue

        rows = get_race_rows(
            race
        )

        if rows.empty:
            continue

        place_map = {
            boat: place + 1
            for place, boat
            in enumerate(actual)
        }

        rows = rows.copy()

        rows["着順"] = rows["枠"].map(
            place_map
        )

        rows["日付"] = d.isoformat()

        rows = rows.dropna(
            subset=["着順"]
        )

        if not rows.empty:
            records.append(rows)

    if not records:
        return pd.DataFrame()

    return pd.concat(
        records,
        ignore_index=True,
    )


def run_backtest(
    target_count,
    progress_callback=None,
):
    """
    2026-01-01まで遡って、
    完了済みレースをtarget_count件集める。
    """

    target_count = int(
        target_count
    )

    current_date = (
        jst_today()
        - timedelta(days=1)
    )

    raw_cache = {}

    records = []
    scanned_days = 0

    while (
        current_date >= API_START_DATE
        and len(records) < target_count
    ):
        if current_date not in raw_cache:
            raw_cache[current_date] = (
                get_data(current_date)
            )

        raw = raw_cache.get(
            current_date
        )

        scanned_days += 1

        if raw:
            races = all_races_for_date(
                raw
            )

            for (
                stadium_number,
                race_number,
                race,
            ) in races:

                if len(records) >= target_count:
                    break

                # 結果がない開催中レースは除外
                if not race_has_result(
                    race
                ):
                    continue

                rows = get_race_rows(
                    race
                )

                if rows.empty:
                    continue

                actual = get_result_order(
                    race
                )

                if len(actual) < 3:
                    continue

                # 現在レースより前の履歴だけを使う
                history = (
                    _history_from_cache(
                        raw_cache,
                        stadium_number,
                        race_number,
                        current_date,
                    )
                )

                try:
                    prediction = tri_ai(
                        rows,
                        history,
                        stadium_number,
                    )
                except Exception:
                    continue

                main = int(
                    prediction["main"]
                )

                counter = int(
                    prediction["counter"]
                )

                hole = int(
                    prediction["hole"]
                )

                ranking = [
                    int(x)
                    for x in prediction[
                        "ranking"
                    ][:3]
                ]

                actual_top3 = [
                    int(x)
                    for x in actual[:3]
                ]

                main_win = (
                    main == actual[0]
                )

                main_top3 = (
                    main in actual_top3
                )

                ai_top3_coverage = (
                    set(ranking)
                    == set(actual_top3)
                )

                predicted_trifecta = (
                    f"{main}-{counter}-{hole}"
                )

                actual_trifecta = (
                    f"{actual[0]}-{actual[1]}-{actual[2]}"
                )

                trifecta_hit = (
                    predicted_trifecta
                    == actual_trifecta
                )

                payout = None

                if trifecta_hit:
                    payout = (
                        trifecta_payout(
                            race,
                            predicted_trifecta,
                        )
                    )

                records.append(
                    {
                        "日付": current_date.isoformat(),
                        "場": stadium_name(
                            stadium_number
                        ),
                        "場番号": stadium_number,
                        "R": race_number,
                        "本命": main,
                        "対抗": counter,
                        "穴": hole,
                        "AI上位3艇": "-".join(
                            map(
                                str,
                                ranking,
                            )
                        ),
                        "実着順": "-".join(
                            map(
                                str,
                                actual,
                            )
                        ),
                        "本命1着": main_win,
                        "本命3連対": main_top3,
                        "上位3艇完全一致": (
                            ai_top3_coverage
                        ),
                        "3連単的中": (
                            trifecta_hit
                        ),
                        "予想3連単": (
                            predicted_trifecta
                        ),
                        "実際3連単": (
                            actual_trifecta
                        ),
                        "3連単配当": payout,
                    }
                )

                if progress_callback:
                    progress_callback(
                        len(records),
                        target_count,
                        current_date,
                        stadium_number,
                        race_number,
                    )

        current_date -= timedelta(days=1)

    result_df = pd.DataFrame(
        records
    )

    return {
        "data": result_df,
        "count": len(records),
        "scanned_days": scanned_days,
        "completed": (
            len(records) >= target_count
        ),
    }


def _rate(series):
    if len(series) == 0:
        return 0.0

    return (
        float(series.mean())
        * 100
    )


def calculate_metrics(result_df):
    if result_df.empty:
        return {
            "main_win_rate": 0.0,
            "main_top3_rate": 0.0,
            "top3_rate": 0.0,
            "trifecta_rate": 0.0,
            "roi": None,
            "grade": "☆☆☆☆☆",
        }

    main_win_rate = _rate(
        result_df["本命1着"]
    )

    main_top3_rate = _rate(
        result_df["本命3連対"]
    )

    top3_rate = _rate(
        result_df["上位3艇完全一致"]
    )

    trifecta_rate = _rate(
        result_df["3連単的中"]
    )

    valid_payouts = result_df[
        result_df["3連単配当"].notna()
    ]

    if len(valid_payouts) > 0:
        total_return = (
            valid_payouts[
                "3連単配当"
            ]
            .astype(float)
            .sum()
        )

        # 1レース100円投資として計算
        total_bet = (
            len(result_df) * 100
        )

        roi = (
            total_return
            / total_bet
            * 100
        )
    else:
        roi = None

    score = 0

    if main_win_rate >= 50:
        score += 1

    if main_top3_rate >= 75:
        score += 1

    if top3_rate >= 15:
        score += 1

    if trifecta_rate >= 8:
        score += 1

    if roi is not None and roi >= 100:
        score += 1

    grade = (
        "★" * score
        + "☆" * (5 - score)
    )

    return {
        "main_win_rate": main_win_rate,
        "main_top3_rate": main_top3_rate,
        "top3_rate": top3_rate,
        "trifecta_rate": trifecta_rate,
        "roi": roi,
        "grade": grade,
    }


def render_backtest():
    st.markdown("---")

    st.markdown(
        "## 📊 AIバックテスト"
    )

    st.caption(
        "2026-01-01まで自動で遡り、完了済みレースを検証します。"
    )

    target_count = st.selectbox(
        "検証するレース数",
        [100, 300, 500, 1000],
        format_func=lambda x: (
            f"{x}レース"
        ),
        key="backtest_count",
    )

    start = st.button(
        "🔍 バックテスト開始",
        key="backtest_start",
        use_container_width=True,
    )

    if not start:
        return

    progress = st.progress(0.0)

    status = st.empty()
    count_text = st.empty()
    boat_text = st.empty()

    def callback(
        done,
        total,
        d,
        stadium_number,
        race_number,
    ):
        ratio = min(
            done / max(total, 1),
            1.0,
        )

        progress.progress(
            ratio
        )

        status.markdown(
            f"🔄 {d.isoformat()} "
            f"{stadium_name(stadium_number)} "
            f"{race_number}Rを検証中"
        )

        count_text.markdown(
            f"**{done} / {total} レース**"
        )

        blocks = int(
            ratio * 20
        )

        boat_text.markdown(
            "🚤"
            + "━" * blocks
            + "●"
            + "━" * (20 - blocks)
        )

    result = run_backtest(
        target_count,
        progress_callback=callback,
    )

    progress.progress(1.0)

    result_df = result["data"]

    if result_df.empty:
        status.error(
            "検証可能な完了済みレースを取得できませんでした。"
        )

        st.info(
            f"2026-01-01まで遡って"
            f"{result['scanned_days']}日間を確認しました。"
        )

        return

    metrics = calculate_metrics(
        result_df
    )

    status.success(
        f"✅ {result['count']}レースの検証が完了しました。"
    )

    if result["count"] < target_count:
        st.warning(
            f"2026-01-01まで検索しましたが、"
            f"{target_count}レース中"
            f"{result['count']}レースしか取得できませんでした。"
        )

    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)

    with col1:
        st.metric(
            "本命1着率",
            f"{metrics['main_win_rate']:.1f}%",
        )

    with col2:
        st.metric(
            "本命3連対率",
            f"{metrics['main_top3_rate']:.1f}%",
        )

    with col3:
        st.metric(
            "AI上位3艇 完全一致",
            f"{metrics['top3_rate']:.1f}%",
        )

    with col4:
        st.metric(
            "3連単完全的中",
            f"{metrics['trifecta_rate']:.1f}%",
        )

    if metrics["roi"] is not None:
        st.metric(
            "簡易回収率",
            f"{metrics['roi']:.1f}%",
        )
    else:
        st.metric(
            "簡易回収率",
            "—",
        )

    st.markdown(
        f"### 🤖 AI評価 {metrics['grade']}"
    )

    display_columns = [
        "日付",
        "場",
        "R",
        "本命",
        "対抗",
        "穴",
        "AI上位3艇",
        "実着順",
        "本命1着",
        "本命3連対",
        "3連単的中",
    ]

    display_columns = [
        col
        for col in display_columns
        if col in result_df.columns
    ]

    st.dataframe(
        result_df[
            display_columns
        ],
        use_container_width=True,
        height=450,
        )
