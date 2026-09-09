from datetime import timedelta
import re

import pandas as pd
import streamlit as st

import data
from ai import tri_ai


# =========================================================
# 基本設定
# =========================================================

START_DATE = data.API_START_DATE


# =========================================================
# 着順
# =========================================================

def get_actual_order(race):
    return data.get_result_order(race)


# =========================================================
# 3連単配当
# =========================================================

def get_trifecta_payout(race, order):
    if len(order) < 3:
        return 0

    result = data.get_result(race)

    payouts = result.get("payouts", {})
    if not isinstance(payouts, dict):
        return 0

    trifecta = payouts.get("trifecta", [])
    if not isinstance(trifecta, list):
        return 0

    target = tuple(int(x) for x in order[:3])

    for item in trifecta:
        if not isinstance(item, dict):
            continue

        combo = item.get("combination", "")
        nums = re.findall(r"\d+", str(combo))

        if len(nums) >= 3:
            combo_tuple = tuple(int(x) for x in nums[:3])

            if combo_tuple == target:
                try:
                    return int(item.get("amount", 0))
                except Exception:
                    return 0

    return 0


# =========================================================
# AIランキングを艇番に変換
# =========================================================

def normalize_ranking(ranking):
    result = []

    if not isinstance(ranking, (list, tuple)):
        return result

    for item in ranking:
        try:
            if isinstance(item, dict):
                value = item.get(
                    "boat",
                    item.get(
                        "艇番",
                        item.get("number", 0),
                    ),
                )
            else:
                value = item

            boat = int(value)

            if 1 <= boat <= 6 and boat not in result:
                result.append(boat)

        except Exception:
            continue

    return result


# =========================================================
# 6点買い
# =========================================================

def make_bets(main, counter, hole):
    candidates = [
        (main, counter, hole),
        (main, hole, counter),
        (counter, main, hole),
        (counter, hole, main),
        (hole, main, counter),
        (hole, counter, main),
    ]

    result = []

    for bet in candidates:
        if len(set(bet)) == 3:
            result.append(bet)

    return result


# =========================================================
# 1レース分析
# =========================================================

def analyze_race(race, stadium_no, race_no):
    rows = data.get_race_rows(race)

    if rows is None or rows.empty:
        return None

    history = data.history14(
        stadium_no,
        race_no,
        race.get("date"),
    )

    prediction = tri_ai(
        rows,
        history,
        stadium_no,
    )

    actual = get_actual_order(race)

    if len(actual) < 3:
        return None

    main = int(prediction.get("main", 1))
    counter = int(prediction.get("counter", 2))
    hole = int(prediction.get("hole", 3))

    bets = make_bets(
        main,
        counter,
        hole,
    )

    actual_trifecta = tuple(actual[:3])

    hit = actual_trifecta in bets

    payout = (
        get_trifecta_payout(
            race,
            actual,
        )
        if hit
        else 0
    )

    ranking = normalize_ranking(
        prediction.get("ranking", [])
    )

    top3_hit = (
        len(
            set(ranking[:3])
            & set(actual[:3])
        )
        == 3
        if len(ranking) >= 3
        else False
    )

    main_win = actual[0] == main
    main_top3 = main in actual[:3]

    return {
        "日付": str(race.get("date", "")),
        "開催場": data.stadium_name(stadium_no),
        "場番号": stadium_no,
        "レース": f"{race_no}R",
        "本命": main,
        "対抗": counter,
        "穴": hole,
        "結果": "-".join(
            str(x) for x in actual[:3]
        ),
        "3連単配当": payout,
        "本命1着": main_win,
        "本命3連対": main_top3,
        "AI上位3艇3連対": top3_hit,
        "AI買い的中": hit,
        "3連単完全的中": hit,
    }


# =========================================================
# その日の全国24場・完走済みレース取得
# =========================================================

def get_completed_races_for_date(target_date):
    raw = data.get_data(target_date)

    if not raw:
        return []

    races = data.all_races_for_date(raw)

    completed = []

    for stadium_no, race_no, race in races:

        if not data.race_has_result(race):
            continue

        completed.append(
            (
                int(stadium_no),
                int(race_no),
                race,
            )
        )

    completed.sort(
        key=lambda x: (
            x[0],
            x[1],
        )
    )

    return completed


# =========================================================
# バックテスト本体
# =========================================================

def run_backtest(limit, progress_callback=None):
    yesterday = data.jst_today() - timedelta(days=1)

    current_date = yesterday

    records = []

    checked_days = 0
    available_races = 0
    completed_races = 0
    first_error = None

    while (
        current_date >= START_DATE
        and len(records) < limit
    ):

        checked_days += 1

        if progress_callback:
            progress_callback(
                len(records),
                limit,
                None,
                None,
                current_date,
                "search",
            )

        try:
            races = get_completed_races_for_date(
                current_date
            )

            available_races += len(races)

        except Exception as e:
            if first_error is None:
                first_error = str(e)

            current_date -= timedelta(days=1)
            continue

        for stadium_no, race_no, race in races:

            if len(records) >= limit:
                break

            if progress_callback:
                progress_callback(
                    len(records),
                    limit,
                    stadium_no,
                    race_no,
                    current_date,
                    "analyze",
                )

            try:
                result = analyze_race(
                    race,
                    stadium_no,
                    race_no,
                )

                if result is None:
                    continue

                records.append(result)
                completed_races += 1

                if progress_callback:
                    progress_callback(
                        len(records),
                        limit,
                        stadium_no,
                        race_no,
                        current_date,
                        "done",
                    )

            except Exception as e:

                if first_error is None:
                    first_error = (
                        f"{current_date} "
                        f"{data.stadium_name(stadium_no)} "
                        f"{race_no}R: {e}"
                    )

        current_date -= timedelta(days=1)

    return (
        records,
        checked_days,
        available_races,
        completed_races,
        first_error,
    )


# =========================================================
# 成績計算
# =========================================================

def calculate_metrics(df):
    if df.empty:
        return {}

    total = len(df)

    investment = total * 600

    payout = int(
        df["3連単配当"].sum()
    )

    roi = (
        payout / investment * 100
        if investment
        else 0
    )

    return {
        "検証レース数": total,
        "投資金額": investment,
        "払戻金額": payout,
        "回収率": roi,
        "本命1着率": (
            df["本命1着"].mean() * 100
        ),
        "本命3連対率": (
            df["本命3連対"].mean() * 100
        ),
        "AI上位3艇3連対": (
            df["AI上位3艇3連対"].mean() * 100
        ),
        "AI買い目的中率": (
            df["AI買い的中"].mean() * 100
        ),
        "3連単完全的中率": (
            df["3連単完全的中"].mean() * 100
        ),
    }


# =========================================================
# 船アニメーション
# =========================================================

BOAT_HTML = """
<style>
.yacht-wrap {
    width: 100%;
    padding: 8px 0 14px 0;
}

.yacht-title {
    text-align: center;
    font-size: 15px;
    font-weight: 700;
    margin-bottom: 6px;
}

.yacht-track {
    position: relative;
    height: 58px;
    overflow: hidden;
    border-radius: 14px;
    border: 1px solid rgba(120,120,120,.25);
    background:
        linear-gradient(
            to bottom,
            rgba(120,180,220,.12),
            rgba(80,150,210,.22)
        );
}

.yacht-wave {
    position: absolute;
    bottom: 7px;
    left: 0;
    width: 100%;
    font-size: 18px;
    letter-spacing: 8px;
    opacity: .55;
}

.yacht {
    position: absolute;
    top: 10px;
    left: -70px;
    font-size: 34px;
    animation: yacht-run 2.3s linear infinite;
}

@keyframes yacht-run {
    0% {
        left: -70px;
        transform: translateY(0);
    }

    50% {
        transform: translateY(-5px);
    }

    100% {
        left: calc(100% + 20px);
        transform: translateY(0);
    }
}
</style>

<div class="yacht-wrap">
    <div class="yacht-title">
        🚤 AIバックテスト実行中
    </div>

    <div class="yacht-track">
        <div class="yacht">🚤</div>
        <div class="yacht-wave">
            〰️ 〰️ 〰️ 〰️ 〰️ 〰️ 〰️
        </div>
    </div>
</div>
"""


# =========================================================
# バックテスト画面
# =========================================================

def render_backtest(stadium_no=None):

    st.markdown("---")

    st.markdown(
        "## 📊 AI予想バックテスト"
    )

    st.caption(
        "🌎 全国24場を対象に、昨日から2026-01-01まで遡って検証"
    )

    limit = st.selectbox(
        "検証レース数",
        [100, 300, 500, 1000],
        key="backtest_limit",
    )

    if st.button(
        "🚀 バックテスト開始",
        use_container_width=True,
        key="start_backtest",
    ):

        progress = st.progress(0)
        status = st.empty()
        counter = st.empty()
        animation = st.empty()

        with animation.container():
            st.html(BOAT_HTML)

        def update_progress(
            done,
            total,
            stadium,
            race_no,
            target_date,
            mode,
        ):

            if mode == "search":

                status.info(
                    f"🔎 {target_date} 全国24場を検索中..."
                )

            elif mode == "analyze":

                name = data.stadium_name(
                    stadium
                )

                status.info(
                    f"🔄 {target_date} "
                    f"{name} {race_no}Rを検証中"
                )

            elif mode == "done":

                name = data.stadium_name(
                    stadium
                )

                status.success(
                    f"✅ {target_date} "
                    f"{name} {race_no}R 検証完了"
                )

            progress.progress(
                min(
                    done / total,
                    1.0,
                )
            )

            counter.markdown(
                f"### {done} / {total} レース"
            )

        try:

            (
                records,
                checked_days,
                available_races,
                completed_races,
                first_error,
            ) = run_backtest(
                int(limit),
                update_progress,
            )

        except Exception as e:

            animation.empty()
            status.empty()
            counter.empty()
            progress.empty()

            st.error(
                "バックテスト中にエラーが発生しました。"
            )

            st.exception(e)
            return

        animation.empty()

        if records:

            df = pd.DataFrame(records)

            metrics = calculate_metrics(df)

            progress.progress(1.0)

            status.success(
                f"🎉 {len(df)}レースの検証が完了しました！"
            )

            counter.markdown(
                f"### {len(df)} / {limit} レース"
            )

            # -------------------------------------------------
            # 指標
            # -------------------------------------------------

            c1, c2, c3, c4 = st.columns(4)

            with c1:
                st.metric(
                    "💰 回収率",
                    f"{metrics['回収率']:.1f}%",
                )

            with c2:
                st.metric(
                    "🎯 本命1着率",
                    f"{metrics['本命1着率']:.1f}%",
                )

            with c3:
                st.metric(
                    "🎯 本命3連対率",
                    f"{metrics['本命3連対率']:.1f}%",
                )

            with c4:
                st.metric(
                    "🔥 AI買い的中率",
                    f"{metrics['AI買い目的中率']:.1f}%",
                )

            c1, c2, c3, c4 = st.columns(4)

            with c1:
                st.metric(
                    "投資金額",
                    f"{metrics['投資金額']:,}円",
                )

            with c2:
                st.metric(
                    "払戻金額",
                    f"{metrics['払戻金額']:,}円",
                )

            with c3:
                st.metric(
                    "AI上位3艇3連対",
                    f"{metrics['AI上位3艇3連対']:.1f}%",
                )

            with c4:
                st.metric(
                    "3連単完全的中率",
                    f"{metrics['3連単完全的中率']:.1f}%",
                )

            # -------------------------------------------------
            # 結果一覧
            # -------------------------------------------------

            st.markdown(
                "### 📋 検証結果"
            )

            display_df = df[
                [
                    "日付",
                    "開催場",
                    "レース",
                    "本命",
                    "対抗",
                    "穴",
                    "結果",
                    "3連単配当",
                    "AI買い的中",
                ]
            ].copy()

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
            )

        else:

            progress.empty()
            status.error(
                "検証できる完了済みレースが見つかりませんでした。"
            )

            st.warning(
                f"検索日数: {checked_days}日"
            )

            st.info(
                f"取得できたレース: {available_races}件"
            )

            st.info(
                f"検証できたレース: {completed_races}件"
            )

            if first_error:
                with st.expander(
                    "🔧 最初に発生したエラー"
                ):
                    st.code(
                        first_error
        )
