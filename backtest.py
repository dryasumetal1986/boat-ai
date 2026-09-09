from datetime import timedelta
import re

import pandas as pd
import streamlit as st

import data
from ai import tri_ai


START_DATE = data.API_START_DATE
PAGE_SIZE = 10


# =========================================================
# 実際の着順
# =========================================================

def get_actual_order(race):
    return data.get_result_order(race)


# =========================================================
# 3連単配当取得
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

    target = (
        int(order[0]),
        int(order[1]),
        int(order[2]),
    )

    for item in trifecta:

        if not isinstance(item, dict):
            continue

        combination = item.get("combination", "")
        nums = re.findall(
            r"\d+",
            str(combination),
        )

        if len(nums) < 3:
            continue

        combo = (
            int(nums[0]),
            int(nums[1]),
            int(nums[2]),
        )

        if combo == target:

            try:
                return int(
                    item.get("amount", 0)
                )
            except Exception:
                return 0

    return 0


# =========================================================
# AIランキングを艇番に統一
# =========================================================

def normalize_ranking(ranking):

    result = []

    if not isinstance(
        ranking,
        (list, tuple),
    ):
        return result

    for item in ranking:

        try:

            if isinstance(item, dict):

                value = item.get(
                    "boat",
                    item.get(
                        "艇番",
                        item.get(
                            "number",
                            0,
                        ),
                    ),
                )

            else:
                value = item

            boat = int(value)

            if (
                1 <= boat <= 6
                and boat not in result
            ):
                result.append(boat)

        except Exception:
            continue

    return result


# =========================================================
# AIの6点買い
# =========================================================

def make_bets(
    main,
    counter,
    hole,
):

    bets = [
        (
            main,
            counter,
            hole,
        ),
        (
            main,
            hole,
            counter,
        ),
        (
            counter,
            main,
            hole,
        ),
        (
            counter,
            hole,
            main,
        ),
        (
            hole,
            main,
            counter,
        ),
        (
            hole,
            counter,
            main,
        ),
    ]

    return [
        bet
        for bet in bets
        if len(set(bet)) == 3
    ]


# =========================================================
# 1レース分析
# =========================================================

def analyze_race(
    race,
    stadium_no,
    race_no,
):

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

    main = int(
        prediction.get(
            "main",
            1,
        )
    )

    counter = int(
        prediction.get(
            "counter",
            2,
        )
    )

    hole = int(
        prediction.get(
            "hole",
            3,
        )
    )

    bets = make_bets(
        main,
        counter,
        hole,
    )

    actual_trifecta = (
        actual[0],
        actual[1],
        actual[2],
    )

    ai_hit = (
        actual_trifecta in bets
    )

    actual_payout = get_trifecta_payout(
        race,
        actual,
    )

    ai_payout = (
        actual_payout
        if ai_hit
        else 0
    )

    ranking = normalize_ranking(
        prediction.get(
            "ranking",
            [],
        )
    )

    top3_hit = (
        len(
            set(ranking[:3])
            & set(actual[:3])
        ) == 3
        if len(ranking) >= 3
        else False
    )

    return {
        "日付": str(
            race.get(
                "date",
                "",
            )
        ),
        "開催場": data.stadium_name(
            stadium_no
        ),
        "レース": f"{race_no}R",

        "本命": main,
        "対抗": counter,
        "穴": hole,

        "結果": "-".join(
            str(x)
            for x in actual[:3]
        ),

        "実配当": actual_payout,
        "3連単配当": ai_payout,

        "本命1着":
            actual[0] == main,

        "本命3連対":
            main in actual[:3],

        "AI上位3艇3連対":
            top3_hit,

        "AI買い的中":
            ai_hit,

        "3連単完全的中":
            ai_hit,
    }


# =========================================================
# 1日分の全国24場を取得
# =========================================================

def get_completed_races_for_date(
    target_date,
):

    raw = data.get_data(
        target_date
    )

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

        if not data.race_has_result(
            race
        ):
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
# バックテスト実行
# =========================================================

def run_backtest(
    limit,
    progress_callback=None,
):

    yesterday = (
        data.jst_today()
        - timedelta(days=1)
    )

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

            races = (
                get_completed_races_for_date(
                    current_date
                )
            )

            available_races += len(
                races
            )

        except Exception as e:

            if first_error is None:
                first_error = str(e)

            current_date -= timedelta(
                days=1
            )

            continue

        for (
            stadium_no,
            race_no,
            race,
        ) in races:

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

        current_date -= timedelta(
            days=1
        )

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

        "検証レース数":
            total,

        "投資金額":
            investment,

        "払戻金額":
            payout,

        "回収率":
            roi,

        "本命1着率":
            df["本命1着"].mean()
            * 100,

        "本命3連対率":
            df["本命3連対"].mean()
            * 100,

        "AI上位3艇3連対":
            df["AI上位3艇3連対"].mean()
            * 100,

        "AI買い的中率":
            df["AI買い的中"].mean()
            * 100,

        "3連単完全的中率":
            df["3連単完全的中"].mean()
            * 100,
    }


# =========================================================
# スマホ向け結果表示
# 前へ / 次へ方式
# =========================================================

def show_result_cards(df):

    st.markdown(
        "### 📋 検証結果"
    )

    pages = (
        len(df)
        + PAGE_SIZE
        - 1
    ) // PAGE_SIZE

    if pages <= 0:
        return

    page = int(
        st.session_state.get(
            "backtest_result_page",
            1,
        )
    )

    page = max(
        1,
        min(page, pages),
    )

    start = (
        page - 1
    ) * PAGE_SIZE

    end = min(
        start + PAGE_SIZE,
        len(df),
    )

    page_df = df.iloc[
        start:end
    ]

    st.caption(
        f"{start + 1}〜{end}レース"
        f"　｜　{page} / {pages}ページ"
    )

    # -----------------------------------------------------
    # レース結果
    # -----------------------------------------------------

    for _, row in page_df.iterrows():

        hit = bool(
            row["AI買い的中"]
        )

        actual_payout = int(
            row["実配当"]
        )

        ai_payout = int(
            row["3連単配当"]
        )

        with st.container(
            border=True
        ):

            st.markdown(
                f"**📅 {row['日付']}　"
                f"🏟️ {row['開催場']}　"
                f"🏁 {row['レース']}**"
            )

            st.markdown(
                f"🎯 本命 "
                f"**{row['本命']}号艇**　"
                f"🔥 対抗 "
                f"**{row['対抗']}号艇**　"
                f"💥 穴 "
                f"**{row['穴']}号艇**"
            )

            st.markdown(
                f"🏆 実着順 "
                f"**{row['結果']}**"
            )

            st.markdown(
                f"💴 実際の3連単 "
                f"**{actual_payout:,}円**"
            )

            if hit:

                st.success(
                    f"🎯 AI買い的中　"
                    f"AI回収 "
                    f"**{ai_payout:,}円**"
                )

            else:

                st.error(
                    "❌ AI買い外れ　"
                    "AI回収 **0円**"
                )

    # =====================================================
    # ページ移動
    # =====================================================

    if pages > 1:

        st.markdown("---")

        col1, col2 = st.columns(
            2
        )

        # 前へ
        with col1:

            if page > 1:

                if st.button(
                    "◀ 前へ",
                    use_container_width=True,
                    key=f"backtest_prev_{page}",
                ):

                    st.session_state[
                        "backtest_result_page"
                    ] = page - 1

                    st.rerun()

            else:

                st.button(
                    "◀ 前へ",
                    use_container_width=True,
                    disabled=True,
                    use_container_width=True,
                    key="backtest_prev_disabled",
                )

        # 次へ
        with col2:

            if page < pages:

                if st.button(
                    "次へ ▶",
                    use_container_width=True,
                    key=f"backtest_next_{page}",
                ):

                    st.session_state[
                        "backtest_result_page"
                    ] = page + 1

                    st.rerun()

            else:

                st.button(
                    "次へ ▶",
                    use_container_width=True,
                    disabled=True,
                    use_container_width=True,
                    key="backtest_next_disabled",
                )


# =========================================================
# バックテスト画面
# =========================================================

def render_backtest(
    stadium_no=None,
):

    st.markdown("---")

    st.markdown(
        "## 📊 AI予想バックテスト"
    )

    st.caption(
        "🌎 全国24場を対象に、"
        "昨日から2026-01-01まで遡って検証"
    )

    # -----------------------------------------------------
    # レース数選択
    # -----------------------------------------------------

    limit = st.selectbox(
        "検証レース数",
        [100, 300, 500, 1000],
        key="backtest_limit",
    )

    # -----------------------------------------------------
    # 開始ボタン
    # -----------------------------------------------------

    start = st.button(
        "🚀 バックテスト開始",
        use_container_width=True,
        key="start_backtest",
    )

    # -----------------------------------------------------
    # 新規バックテスト
    # -----------------------------------------------------

    if start:

        # 古い結果を削除
        st.session_state.pop(
            "backtest_df",
            None,
        )

        st.session_state[
            "backtest_result_page"
        ] = 1

        progress = st.progress(
            0
        )

        status = st.empty()

        count_box = st.empty()

        # -------------------------------------------------
        # 進捗表示
        # -------------------------------------------------

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
                    f"🔎 {target_date} "
                    f"全国24場を検索中..."
                )

            elif mode == "analyze":

                name = (
                    data.stadium_name(
                        stadium
                    )
                )

                status.info(
                    f"🔄 {target_date} "
                    f"{name} "
                    f"{race_no}Rを検証中"
                )

            elif mode == "done":

                name = (
                    data.stadium_name(
                        stadium
                    )
                )

                status.success(
                    f"✅ {target_date} "
                    f"{name} "
                    f"{race_no}R "
                    f"検証完了"
                )

            progress.progress(
                min(
                    done / total,
                    1.0,
                )
            )

            count_box.markdown(
                f"### {done} / {total} レース"
            )

        # -------------------------------------------------
        # バックテスト実行
        # -------------------------------------------------

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

            progress.empty()
            status.empty()
            count_box.empty()

            st.error(
                "バックテスト中に"
                "エラーが発生しました。"
            )

            st.exception(e)

            return

        # -------------------------------------------------
        # データなし
        # -------------------------------------------------

        if not records:

            progress.empty()

            status.error(
                "検証できる完了済み"
                "レースが見つかりませんでした。"
            )

            st.info(
                f"検索日数: "
                f"{checked_days}日"
            )

            st.info(
                f"取得できたレース: "
                f"{available_races}件"
            )

            st.info(
                f"検証できたレース: "
                f"{completed_races}件"
            )

            if first_error:

                with st.expander(
                    "🔧 最初に発生したエラー"
                ):

                    st.code(
                        first_error
                    )

            return

        # -------------------------------------------------
        # 結果を保存
        # -------------------------------------------------

        df = pd.DataFrame(
            records
        )

        st.session_state[
            "backtest_df"
        ] = df

        st.session_state[
            "backtest_result_limit"
        ] = int(limit)

        st.session_state[
            "backtest_result_page"
        ] = 1

        progress.progress(
            1.0,
            text=(
                f"{len(df)} / "
                f"{limit} レース"
            ),
        )

        status.success(
            f"🎉 {len(df)}レースの"
            f"検証が完了しました！"
        )

        count_box.markdown(
            f"### {len(df)} / "
            f"{limit} レース"
        )

    # =====================================================
    # 保存済み結果
    # =====================================================

    saved_df = st.session_state.get(
        "backtest_df"
    )

    if not isinstance(
        saved_df,
        pd.DataFrame,
    ):
        return

    if saved_df.empty:
        return

    # -----------------------------------------------------
    # 成績
    # -----------------------------------------------------

    metrics = calculate_metrics(
        saved_df
    )

    st.markdown(
        "### 📈 バックテスト成績"
    )

    c1, c2 = st.columns(2)

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

    c1, c2 = st.columns(2)

    with c1:

        st.metric(
            "🎯 本命3連対率",
            f"{metrics['本命3連対率']:.1f}%",
        )

    with c2:

        st.metric(
            "🔥 AI買い的中率",
            f"{metrics['AI買い的中率']:.1f}%",
        )

    c1, c2 = st.columns(2)

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

    c1, c2 = st.columns(2)

    with c1:

        st.metric(
            "AI上位3艇3連対",
            f"{metrics['AI上位3艇3連対']:.1f}%",
        )

    with c2:

        st.metric(
            "3連単完全的中率",
            f"{metrics['3連単完全的中率']:.1f}%",
        )

    # -----------------------------------------------------
    # 結果一覧
    # -----------------------------------------------------

    show_result_cards(
        sav
