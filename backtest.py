from datetime import timedelta
import re
import time

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
        nums = re.findall(r"\d+", str(combination))

        if len(nums) < 3:
            continue

        combo = (
            int(nums[0]),
            int(nums[1]),
            int(nums[2]),
        )

        if combo == target:
            try:
                return int(item.get("amount", 0))
            except Exception:
                return 0

    return 0


# =========================================================
# AIランキングを艇番に統一
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
# AIの6点買い
# =========================================================

def make_bets(main, counter, hole):

    bets = [
        (main, counter, hole),
        (main, hole, counter),
        (counter, main, hole),
        (counter, hole, main),
        (hole, main, counter),
        (hole, counter, main),
    ]

    return [
        bet for bet in bets
        if len(set(bet)) == 3
    ]


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

    bets = make_bets(main, counter, hole)

    actual_trifecta = (
        actual[0],
        actual[1],
        actual[2],
    )

    ai_hit = actual_trifecta in bets

    actual_payout = get_trifecta_payout(
        race,
        actual,
    )

    ai_payout = actual_payout if ai_hit else 0

    ranking = normalize_ranking(
        prediction.get("ranking", [])
    )

    top3_hit = (
        len(set(ranking[:3]) & set(actual[:3])) == 3
        if len(ranking) >= 3
        else False
    )

    return {
        "日付": str(race.get("date", "")),
        "開催場": data.stadium_name(stadium_no),
        "レース": f"{race_no}R",
        "本命": main,
        "対抗": counter,
        "穴": hole,
        "結果": "-".join(str(x) for x in actual[:3]),
        "実配当": actual_payout,
        "3連単配当": ai_payout,
        "本命1着": actual[0] == main,
        "本命3連対": main in actual[:3],
        "AI上位3艇3連対": top3_hit,
        "AI買い的中": ai_hit,
        "3連単完全的中": ai_hit,
    }


# =========================================================
# 1日分の全国24場を取得
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
        key=lambda x: (x[0], x[1])
    )

    return completed


# =========================================================
# バックテスト実行
# =========================================================

def run_backtest(limit, progress_callback=None):

    yesterday = data.jst_today() - timedelta(days=1)
    current_date = yesterday

    records = []
    checked_days = 0
    available_races = 0
    completed_races = 0
    first_error = None

    while current_date >= START_DATE and len(records) < limit:

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
            races = get_completed_races_for_date(current_date)
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
    payout = int(df["3連単配当"].sum())

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
        "本命1着率": df["本命1着"].mean() * 100,
        "本命3連対率": df["本命3連対"].mean() * 100,
        "AI上位3艇3連対": df["AI上位3艇3連対"].mean() * 100,
        "AI買い的中率": df["AI買い的中"].mean() * 100,
        "3連単完全的中率": df["3連単完全的中"].mean() * 100,
    }


# =========================================================
# 6艇周回レース演出
# =========================================================

def show_boat_race(placeholder, frame, total_frames=36, laps=3):

    # 横長の競艇場をUnicodeで描画。
    # HTML/CSSアニメーションは使わず、スマホでも安定する方式。
    phase = frame % total_frames
    lap_progress = phase / total_frames
    total_progress = lap_progress * laps

    # コース上の代表位置
    # 0=スタート付近、1=第1ターン、2=第2ターン、3=ゴール付近
    track_length = 40

    boats = []

    # 6艇ごとに少し速度差をつける
    speeds = [1.00, 1.05, 0.96, 1.08, 0.92, 1.02]

    for i, speed in enumerate(speeds):

        p = (
            total_progress * speed
            + i * 0.035
        ) % 1.0

        # 長方形コースの周囲を4区間で移動
        if p < 0.25:
            # 上辺：左→右
            t = p / 0.25
            x = int(t * track_length)
            y = 0
            icon = "🚤"

        elif p < 0.50:
            # 右辺：上→下
            t = (p - 0.25) / 0.25
            x = track_length
            y = int(t * 2)
            icon = "🚤"

        elif p < 0.75:
            # 下辺：右→左
            t = (p - 0.50) / 0.25
            x = int((1 - t) * track_length)
            y = 2
            icon = "🚤"

        else:
            # 左辺：下→上
            t = (p - 0.75) / 0.25
            x = 0
            y = int((1 - t) * 2)
            icon = "🚤"

        boats.append(
            (
                i + 1,
                x,
                y,
                icon,
            )
        )

    # 15×45程度のコースを作る
    width = 44
    height = 9

    grid = [
        ["　"] * width
        for _ in range(height)
    ]

    # コース
    for x in range(width):
        grid[1][x] = "━"
        grid[7][x] = "━"

    for y in range(1, 8):
        grid[y][1] = "┃"
        grid[y][width - 2] = "┃"

    grid[1][1] = "┏"
    grid[1][width - 2] = "┓"
    grid[7][1] = "┗"
    grid[7][width - 2] = "┛"

    # 内側の水面
    for y in range(2, 7):
        for x in range(3, width - 3):
            if grid[y][x] == "　":
                grid[y][x] = "🌊"

    # 6艇を配置
    for number, x, y, icon in boats:

        gx = min(
            width - 3,
            max(2, x + 1),
        )

        gy = min(
            height - 2,
            max(1, y + 2),
        )

        grid[gy][gx] = icon

    lines = [
        "".join(row)
        for row in grid
    ]

    with placeholder.container():

        st.markdown(
            "### 🚤 6艇 周回レース中"
        )

        st.caption(
            f"🏁 {laps}周シミュレーション　"
            f"リアルタイム追い抜き演出"
        )

        st.code(
            "\n".join(lines),
            language=None,
        )

        # 舟番号
        st.markdown(
            "　1️⃣　2️⃣　3️⃣　4️⃣　5️⃣　6️⃣"
        )


def animate_boat_race(placeholder):

    # 短時間で3周しているように見せる
    frames = 42

    for frame in range(frames):

        show_boat_race(
            placeholder,
            frame,
            total_frames=frames,
            laps=3,
        )

        time.sleep(0.06)


# =========================================================
# スマホ向け結果表示
# ページは一番下に置き、session_stateで保持
# =========================================================

def show_result_cards(df):

    st.markdown("### 📋 検証結果")

    pages = (
        len(df) + PAGE_SIZE - 1
    ) // PAGE_SIZE

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

    start = (page - 1) * PAGE_SIZE
    end = min(
        start + PAGE_SIZE,
        len(df),
    )

    page_df = df.iloc[start:end]

    st.caption(
        f"{start + 1}〜{end}レースを表示"
    )

    for _, row in page_df.iterrows():

        hit = bool(row["AI買い的中"])
        actual_payout = int(row["実配当"])
        ai_payout = int(row["3連単配当"])

        with st.container(border=True):

            st.markdown(
                f"**📅 {row['日付']}　"
                f"🏟️ {row['開催場']}　"
                f"🏁 {row['レース']}**"
            )

            st.markdown(
                f"🎯 本命 **{row['本命']}号艇**　"
                f"🔥 対抗 **{row['対抗']}号艇**　"
                f"💥 穴 **{row['穴']}号艇**"
            )

            st.markdown(
                f"🏆 実着順 **{row['結果']}**"
            )

            st.markdown(
                f"💴 実際の3連単 **{actual_payout:,}円**"
            )

            if hit:
                st.success(
                    f"🎯 AI買い的中　"
                    f"AI回収 **{ai_payout:,}円**"
                )
            else:
                st.error(
                    "❌ AI買い外れ　AI回収 **0円**"
                )

    # ページ番号は一番下だけ
    if pages > 1:

        st.markdown(
            f"**ページ {page} / {pages}**"
        )

        cols = st.columns(
            min(pages, 5)
        )

        for i in range(pages):

            with cols[i % len(cols)]:

                if st.button(
                    str(i + 1),
                    key=f"backtest_page_{i + 1}",
                    use_container_width=True,
                ):

                    st.session_state[
                        "backtest_result_page"
                    ] = i + 1

                    st.rerun()


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

    start = st.button(
        "🚀 バックテスト開始",
        use_container_width=True,
        key="start_backtest",
    )

    # -----------------------------------------------------
    # 新規バックテスト
    # -----------------------------------------------------

    if start:

        st.session_state.pop(
            "backtest_df",
            None,
        )

        st.session_state[
            "backtest_result_page"
        ] = 1

        progress = st.progress(0)
        status = st.empty()
        count_box = st.empty()
        animation = st.empty()

        # 先にレース演出
        show_boat_race(
            animation,
            0,
            total_frames=36,
            laps=3,
        )

        # 6艇が3周
        # バックテスト開始時の演出として実行
        animate_boat_race(
            animation
        )

        # -------------------------------------------------
        # 進捗コールバック
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

                name = data.stadium_name(
                    stadium
                )

                status.info(
                    f"🔄 {target_date} "
                    f"{name} "
                    f"{race_no}Rを検証中"
                )

            elif mode == "done":

                name = data.stadium_name(
                    stadium
                )

                status.success(
                    f"✅ {target_date} "
                    f"{name} "
                    f"{race_no}R "
                    f"検証完了"
                )

            progress.progress(
                min(done / total, 1.0)
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

            animation.empty()
            progress.empty()
            status.empty()
            count_box.empty()

            st.error(
                "バックテスト中にエラーが発生しました。"
            )

            st.exception(e)
            return

        animation.empty()

        # -------------------------------------------------
        # データなし
        # -------------------------------------------------

        if not records:

            progress.empty()

            status.error(
                "検証できる完了済みレースが見つかりませんでした。"
            )

            st.info(
                f"検索日数: {checked_days}日"
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
                    st.code(first_error)

            return

        # -------------------------------------------------
        # 保存
        # -------------------------------------------------

        df = pd.DataFrame(records)

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
            text=f"{len(df)} / {limit} レース",
        )

        status.success(
            f"🎉 {len(df)}レースの検証が完了しました！"
        )

        count_box.markdown(
            f"### {len(df)} / {limit} レース"
        )

        # 結果を保存したのでここでは表示せず、
        # 下のsaved_df処理に任せる

    # -----------------------------------------------------
    # 保存済み結果
    # -----------------------------------------------------

    saved_df = st.session_state.get(
        "backtest_df"
    )

    if (
        isinstance(saved_df, pd.DataFrame)
        and not saved_df.empty
    ):

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

        show_result_cards(
            saved_df
        )
