from datetime import timedelta
import pandas as pd
import streamlit as st

import data
from ai import tri_ai


START_DATE = data.API_START_DATE
PAGE_SIZE = 10


# =========================================================
# 実際の着順を取得
# =========================================================
def get_actual_order(race):
    return data.get_result_order(race)


# =========================================================
# 3連単払戻金取得
# =========================================================
def get_trifecta_payout(race, actual_order):
    result = data.get_result(race)

    payouts = result.get("payouts", {})
    if not isinstance(payouts, dict):
        return 0

    trifecta = payouts.get("trifecta", [])
    if not isinstance(trifecta, list):
        return 0

    if len(actual_order) < 3:
        return 0

    target = (
        f"{actual_order[0]}-"
        f"{actual_order[1]}-"
        f"{actual_order[2]}"
    )

    for item in trifecta:
        if not isinstance(item, dict):
            continue

        combination = str(
            item.get("combination", "")
        ).strip()

        if combination == target:
            try:
                return int(
                    item.get("amount", 0)
                )
            except (TypeError, ValueError):
                return 0

    return 0


# =========================================================
# AIランキングを正規化
# =========================================================
def normalize_ranking(result):
    ranking = result.get("ranking", [])

    if isinstance(ranking, pd.DataFrame):
        ranking = ranking.to_dict("records")

    if not isinstance(ranking, list):
        return []

    output = []

    for item in ranking:
        if isinstance(item, dict):
            boat = (
                item.get("艇")
                or item.get("艇番")
                or item.get("boat")
                or item.get("boat_number")
            )

            if boat is None:
                continue

            try:
                boat = int(boat)
            except (TypeError, ValueError):
                continue

            if 1 <= boat <= 6:
                output.append(boat)

        else:
            try:
                boat = int(item)

                if 1 <= boat <= 6:
                    output.append(boat)

            except (TypeError, ValueError):
                pass

    return list(dict.fromkeys(output))


# =========================================================
# AI買い目
# 本命・対抗・穴の6通り
# =========================================================
def make_ai_bets(main, counter, hole):
    candidates = [
        (main, counter, hole),
        (main, hole, counter),
        (counter, main, hole),
        (counter, hole, main),
        (hole, main, counter),
        (hole, counter, main),
    ]

    return list(dict.fromkeys(candidates))


# =========================================================
# 1レース分析
# =========================================================
def analyze_race(stadium_no, race_no, race):
    rows = data.get_race_rows(race)

    # DataFrame / list 両対応
    if rows is None:
        return None

    if isinstance(rows, pd.DataFrame):
        if rows.empty:
            return None
    else:
        if not rows:
            return None

    history = pd.DataFrame()

    try:
        race_date = race.get("date")

        history = data.history14(
            stadium_no,
            race_no,
            race_date,
        )

    except Exception:
        history = pd.DataFrame()

    try:
        ai_result = tri_ai(
            rows,
            history,
            stadium_no,
        )

    except Exception:
        return None

    main = ai_result.get("main")
    counter = ai_result.get("counter")
    hole = ai_result.get("hole")

    try:
        main = int(main)
        counter = int(counter)
        hole = int(hole)

    except (TypeError, ValueError):
        return None

    actual_order = get_actual_order(race)

    if len(actual_order) < 3:
        return None

    payout = get_trifecta_payout(
        race,
        actual_order,
    )

    ranking = normalize_ranking(
        ai_result
    )

    top3 = ranking[:3]

    ai_bets = make_ai_bets(
        main,
        counter,
        hole,
    )

    actual_trifecta = tuple(
        actual_order[:3]
    )

    ai_hit = (
        actual_trifecta in ai_bets
    )

    main_win = (
        actual_order[0] == main
    )

    main_top3 = (
        main in actual_order[:3]
    )

    ai_top3_hit = any(
        boat in actual_order[:3]
        for boat in top3
    )

    return {
        "日付": race.get("date", ""),
        "場": data.stadium_name(
            stadium_no
        ),
        "R": f"{race_no}R",
        "本命": main,
        "対抗": counter,
        "穴": hole,
        "実着順": "-".join(
            map(
                str,
                actual_order[:3],
            )
        ),
        "3連単配当": payout,
        "本命1着": main_win,
        "本命3連対": main_top3,
        "AI上位3艇3連対": ai_top3_hit,
        "AI買い的中": ai_hit,
    }


# =========================================================
# 指定日の全開催レース取得
# =========================================================
def get_completed_races_for_date(
    target_date
):
    raw = data.get_data(target_date)

    if not raw:
        return []

    races = data.all_races_for_date(
        raw
    )

    completed = []

    for (
        stadium_no,
        race_no,
        race,
    ) in races:

        try:
            actual_order = (
                get_actual_order(race)
            )

            if len(actual_order) >= 3:
                completed.append(
                    (
                        stadium_no,
                        race_no,
                        race,
                    )
                )

        except Exception:
            continue

    return completed


# =========================================================
# バックテスト本体
# 全国24場
# =========================================================
def run_backtest(
    target_count,
    start_date=None,
):
    if start_date is None:
        start_date = (
            data.jst_today()
            - timedelta(days=1)
        )

    current_date = start_date

    results = []

    while (
        current_date >= START_DATE
        and len(results) < target_count
    ):

        races = (
            get_completed_races_for_date(
                current_date
            )
        )

        for (
            stadium_no,
            race_no,
            race,
        ) in races:

            if len(results) >= target_count:
                break

            analyzed = analyze_race(
                stadium_no,
                race_no,
                race,
            )

            if analyzed is not None:
                results.append(
                    analyzed
                )

        current_date -= timedelta(
            days=1
        )

    if not results:
        return pd.DataFrame()

    return pd.DataFrame(results)


# =========================================================
# 指標計算
# =========================================================
def calculate_metrics(df):
    if df.empty:
        return {
            "investment": 0,
            "payout": 0,
            "roi": 0,
            "main_win_rate": 0,
            "main_top3_rate": 0,
            "ai_top3_rate": 0,
            "ai_hit_rate": 0,
            "perfect_rate": 0,
        }

    race_count = len(df)

    # 1レース6点買い × 100円
    investment = (
        race_count * 6 * 100
    )

    payout = int(
        df.loc[
            df["AI買い的中"] == True,
            "3連単配当",
        ].sum()
    )

    roi = (
        payout / investment * 100
        if investment
        else 0
    )

    main_win_rate = (
        df["本命1着"].mean() * 100
    )

    main_top3_rate = (
        df["本命3連対"].mean() * 100
    )

    ai_top3_rate = (
        df["AI上位3艇3連対"].mean()
        * 100
    )

    ai_hit_rate = (
        df["AI買い的中"].mean() * 100
    )

    perfect_rate = ai_hit_rate

    return {
        "investment": investment,
        "payout": payout,
        "roi": roi,
        "main_win_rate": main_win_rate,
        "main_top3_rate": main_top3_rate,
        "ai_top3_rate": ai_top3_rate,
        "ai_hit_rate": ai_hit_rate,
        "perfect_rate": perfect_rate,
    }


# =========================================================
# 検証結果カード表示
# 10レースずつ
# =========================================================
def show_result_cards(df):
    if df is None or df.empty:
        return

    total_pages = max(
        1,
        (
            len(df) + PAGE_SIZE - 1
        ) // PAGE_SIZE,
    )

    if (
        "backtest_result_page"
        not in st.session_state
    ):
        st.session_state[
            "backtest_result_page"
        ] = 0

    page = st.session_state[
        "backtest_result_page"
    ]

    page = max(
        0,
        min(
            page,
            total_pages - 1,
        ),
    )

    start = page * PAGE_SIZE

    end = min(
        start + PAGE_SIZE,
        len(df),
    )

    page_df = df.iloc[
        start:end
    ]

    # =====================================================
    # 検証結果の先頭アンカー
    # =====================================================
    st.markdown(
        '<div id="backtest-results-top"></div>',
        unsafe_allow_html=True,
    )

    st.subheader(
        "📋 検証結果"
    )

    st.caption(
        f"{start + 1}〜{end} / "
        f"{len(df)}レース"
    )

    # =====================================================
    # レースカード
    # =====================================================
    for _, row in page_df.iterrows():

        date_text = str(
            row.get("日付", "")
        )

        stadium = str(
            row.get("場", "")
        )

        race_no = str(
            row.get("R", "")
        )

        main = row.get(
            "本命",
            "",
        )

        counter = row.get(
            "対抗",
            "",
        )

        hole = row.get(
            "穴",
            "",
        )

        actual = str(
            row.get(
                "実着順",
                "",
            )
        )

        payout = int(
            row.get(
                "3連単配当",
                0,
            )
            or 0
        )

        ai_hit = bool(
            row.get(
                "AI買い的中",
                False,
            )
        )

        with st.container(
            border=True
        ):

            st.markdown(
                f"**{date_text}｜"
                f"{stadium}｜"
                f"{race_no}**"
            )

            st.write(
                f"🎯 本命 **{main}**　"
                f"🔥 対抗 **{counter}**　"
                f"💥 穴 **{hole}**"
            )

            st.write(
                f"🏁 実着順 **{actual}**"
            )

            if payout > 0:
                st.write(
                    f"💰 3連単配当 "
                    f"**{payout:,}円**"
                )
            else:
                st.write(
                    "💰 3連単配当 **0円**"
                )

            if ai_hit:
                st.success(
                    "🎉 AI買い的中！"
                )
            else:
                st.caption(
                    "AI買い：ハズレ"
                )

    # =====================================================
    # ページ切り替え
    # =====================================================
    if total_pages > 1:

        st.divider()

        col1, col2 = st.columns(2)

        with col1:

            if st.button(
                "◀ 前へ",
                disabled=(page <= 0),
                use_container_width=True,
                key="backtest_prev",
            ):

                st.session_state[
                    "backtest_result_page"
                ] = page - 1

                st.session_state[
                    "backtest_scroll_results"
                ] = True

                st.rerun()

        with col2:

            if st.button(
                "次へ ▶",
                disabled=(
                    page >=
                    total_pages - 1
                ),
                use_container_width=True,
                key="backtest_next",
            ):

                st.session_state[
                    "backtest_result_page"
                ] = page + 1

                st.session_state[
                    "backtest_scroll_results"
                ] = True

                st.rerun()

        st.caption(
            f"ページ {page + 1} / "
            f"{total_pages}"
        )

    # =====================================================
    # ページ切り替え後に自動スクロール
    # =====================================================
    if st.session_state.get(
        "backtest_scroll_results",
        False,
    ):

        st.session_state[
            "backtest_scroll_results"
        ] = False

        st.components.v1.html(
            """
            <script>
            setTimeout(function() {
                const target =
                    window.parent.document
                    .getElementById(
                        "backtest-results-top"
                    );

                if (target) {
                    target.scrollIntoView({
                        behavior: "smooth",
                        block: "start"
                    });
                }
            }, 150);
            </script>
            """,
            height=0,
        )


# =========================================================
# バックテスト画面
# =========================================================
def render_backtest(
    stadium_no=None
):
    st.divider()

    st.subheader(
        "📊 AI予想バックテスト"
    )

    st.caption(
        "🌎 全国24場を対象に、"
        "昨日から2026-01-01まで遡って検証"
    )

    count = st.selectbox(
        "検証レース数",
        [100, 300, 500, 1000],
        index=0,
        key="backtest_count",
    )

    # =====================================================
    # バックテスト開始
    # =====================================================
    if st.button(
        "🚀 バックテスト開始",
        use_container_width=True,
        key="backtest_start",
    ):

        st.session_state[
            "backtest_result_page"
        ] = 0

        st.session_state[
            "backtest_scroll_results"
        ] = False

        st.session_state[
            "backtest_df"
        ] = None

        progress = st.progress(
            0
        )

        status = st.empty()

        status.info(
            "全国24場の過去レースを検索中..."
        )

        df = run_backtest(
            int(count)
        )

        progress.progress(
            1.0
        )

        if df.empty:

            status.error(
                "検証できるレースが"
                "見つかりませんでした。"
            )

            return

        st.session_state[
            "backtest_df"
        ] = df

        st.session_state[
            "backtest_result_page"
        ] = 0

        status.success(
            f"🎉 {len(df)}レースの"
            "検証が完了しました！"
        )

    # =====================================================
    # 保存済み結果
    # ページ変更では再バックテストしない
    # =====================================================
    df = st.session_state.get(
        "backtest_df"
    )

    if df is None or df.empty:
        return

    st.write(
        f"**{len(df)} / "
        f"{len(df)} レース**"
    )

    # =====================================================
    # 指標
    # =====================================================
    metrics = calculate_metrics(
        df
    )

    st.metric(
        "💰 回収率",
        f"{metrics['roi']:.1f}%",
    )

    st.metric(
        "🎯 本命1着率",
        f"{metrics['main_win_rate']:.1f}%",
    )

    st.metric(
        "🎯 本命3連対率",
        f"{metrics['main_top3_rate']:.1f}%",
    )

    st.metric(
        "🔥 AI買い的中率",
        f"{metrics['ai_hit_rate']:.1f}%",
    )

    st.write(
        f"投資金額 "
        f"**{metrics['investment']:,}円**"
    )

    st.write(
        f"払戻金額 "
        f"**{metrics['payout']:,}円**"
    )

    st.write(
        f"AI上位3艇3連対 "
        f"**{metrics['ai_top3_rate']:.1f}%**"
    )

    st.write(
        f"3連単完全的中率 "
        f"**{metrics['perfect_rate']:.1f}%**"
    )

    # =====================================================
    # 検証結果
    # =====================================================
    show_result_cards(
        df
    )
