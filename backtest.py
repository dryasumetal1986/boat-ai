import streamlit as st
import pandas as pd
from datetime import date, timedelta

import data
from ai import tri_ai


# =========================================================
# 基本設定
# =========================================================

RACE_OPTIONS = {
    100: "直近100レース",
    300: "直近300レース",
    500: "直近500レース",
    1000: "直近1,000レース",
}


# =========================================================
# ユーティリティ
# =========================================================

def _combo_tuple(combo):
    """
    AIの組み合わせを安全にtuple化
    """
    if not combo:
        return tuple()

    try:
        return tuple(
            int(x)
            for x in combo
        )
    except (TypeError, ValueError):
        return tuple()


def _combo_text(combo):
    """
    [1, 2, 3] → 1-2-3
    """
    values = _combo_tuple(combo)

    if not values:
        return "—"

    return "-".join(
        str(x)
        for x in values
    )


def _confidence_from_probs(boat_probs):
    """
    1着確率からAI自信度を算出
    """
    if not isinstance(boat_probs, dict):
        return 0.0

    values = []

    for value in boat_probs.values():
        try:
            values.append(float(value))
        except (TypeError, ValueError):
            continue

    if not values:
        return 0.0

    values.sort(reverse=True)

    if len(values) >= 2:
        return (
            values[0] * 0.7
            + values[1] * 0.3
        )

    return values[0]


def _confidence_stars(confidence):
    """
    自信度を5段階表示
    """
    confidence = float(confidence)

    if confidence >= 0.42:
        return "★★★★★"

    if confidence >= 0.34:
        return "★★★★☆"

    if confidence >= 0.27:
        return "★★★☆☆"

    if confidence >= 0.20:
        return "★★☆☆☆"

    return "★☆☆☆☆"


# =========================================================
# 1レースを検証
# =========================================================

def evaluate_race(
    raw,
    target_date,
    stadium_no,
    race_no,
    history=None,
):
    """
    1レースについて

    実際の着順
    AI本命
    AI対抗
    AI穴

    を比較する。
    """

    # -----------------------------------------------------
    # レース取得
    # -----------------------------------------------------

    race = data.get_race(
        raw,
        stadium_no,
        race_no,
    )

    if race is None:
        return None

    # -----------------------------------------------------
    # 6艇の出走データ確認
    # -----------------------------------------------------

    if not data.validate_race(
        race,
        target_date,
        stadium_no,
        race_no,
    ):
        return None

    # -----------------------------------------------------
    # ★ 完了レース判定
    # -----------------------------------------------------

    actual = data.get_result_order(
        raw,
        stadium_no,
        race_no,
    )

    if actual is None:
        return None

    actual_tuple = tuple(
        int(x)
        for x in actual[:3]
    )

    if len(actual_tuple) != 3:
        return None

    # -----------------------------------------------------
    # AI用データ
    # -----------------------------------------------------

    race_rows = data.get_race_rows(
        race,
        stadium_no,
        race_no,
    )

    if race_rows is None:
        return None

    if race_rows.empty:
        return None

    # -----------------------------------------------------
    # 過去データ
    # -----------------------------------------------------

    if history is None:
        history = data.history14(
            target_date
        )

    # -----------------------------------------------------
    # AI予想
    # -----------------------------------------------------

    prediction = tri_ai(
        race_rows,
        history,
    )

    if not isinstance(prediction, dict):
        return None

    main = _combo_tuple(
        prediction.get("main")
    )

    counter = _combo_tuple(
        prediction.get("counter")
    )

    hole = _combo_tuple(
        prediction.get("hole")
    )

    # -----------------------------------------------------
    # 的中判定
    # -----------------------------------------------------

    main_hit = (
        1
        if main == actual_tuple
        else 0
    )

    counter_hit = (
        1
        if counter == actual_tuple
        else 0
    )

    hole_hit = (
        1
        if hole == actual_tuple
        else 0
    )

    coverage_hit = (
        1
        if actual_tuple in {
            main,
            counter,
            hole,
        }
        else 0
    )

    # -----------------------------------------------------
    # 自信度
    # -----------------------------------------------------

    boat_probs = prediction.get(
        "boat_probs",
        {},
    )

    confidence = _confidence_from_probs(
        boat_probs
    )

    return {
        "日付": str(target_date),

        "場": data.stadium_name(
            stadium_no
        ),

        "場番号": int(stadium_no),

        "R": f"{race_no}R",

        "R番号": int(race_no),

        "実際の結果": _combo_text(
            actual_tuple
        ),

        "本命": _combo_text(
            main
        ),

        "対抗": _combo_text(
            counter
        ),

        "穴": _combo_text(
            hole
        ),

        "本命的中": main_hit,

        "対抗的中": counter_hit,

        "穴的中": hole_hit,

        "3点カバー": coverage_hit,

        "AI自信度": round(
            confidence * 100,
            1,
        ),

        "AI自信度ランク": _confidence_stars(
            confidence
        ),
    }


# =========================================================
# バックテスト本体
# =========================================================

def run_backtest(
    race_count=100,
    progress_callback=None,
    status_callback=None,
):
    """
    最新の完了レースから遡って
    指定されたレース数を検証する。

    race_count:
        100
        300
        500
        1000
    """

    race_count = int(race_count)

    records = []

    # -----------------------------------------------------
    # 今日ではなく「昨日」からスタート
    # -----------------------------------------------------

    current = date.today() - timedelta(
        days=1
    )

    # 最大探索日数
    max_days = 180

    days_checked = 0

    # -----------------------------------------------------
    # 日付を遡る
    # -----------------------------------------------------

    while (
        len(records) < race_count
        and days_checked < max_days
    ):

        target_date = current

        # -------------------------------------------------
        # 進捗表示
        # -------------------------------------------------

        if status_callback:
            status_callback(
                f"🔎 {target_date} を確認中 — "
                f"{len(records)} / {race_count}R"
            )

        # -------------------------------------------------
        # 当日のデータ取得
        # -------------------------------------------------

        raw = data.get_data(
            target_date
        )

        if raw:

            # ---------------------------------------------
            # ★ 先に「完了レース」だけを探す
            # ---------------------------------------------

            completed_races = []

            for stadium_no in range(1, 25):

                for race_no in range(1, 13):

                    actual = data.get_result_order(
                        raw,
                        stadium_no,
                        race_no,
                    )

                    if actual is None:
                        continue

                    completed_races.append(
                        (
                            stadium_no,
                            race_no,
                        )
                    )

            # ---------------------------------------------
            # 完了レースがあった場合
            # ---------------------------------------------

            if completed_races:

                if status_callback:
                    status_callback(
                        f"📊 {target_date} — "
                        f"完了 {len(completed_races)}R / "
                        f"取得 {len(records)} / "
                        f"{race_count}R"
                    )

                # -----------------------------------------
                # この日の過去14日データは1回だけ取得
                # -----------------------------------------

                history = data.history14(
                    target_date
                )

                # -----------------------------------------
                # AI検証
                # -----------------------------------------

                for stadium_no, race_no in completed_races:

                    if len(records) >= race_count:
                        break

                    result = evaluate_race(
                        raw=raw,
                        target_date=target_date,
                        stadium_no=stadium_no,
                        race_no=race_no,
                        history=history,
                    )

                    if result is None:
                        continue

                    records.append(result)

                    # -------------------------------------
                    # 進捗
                    # -------------------------------------

                    if progress_callback:
                        progress_callback(
                            min(
                                len(records)
                                / race_count,
                                1.0,
                            )
                        )

                    if status_callback:
                        status_callback(
                            f"📈 {target_date} "
                            f"{data.stadium_name(stadium_no)} "
                            f"{race_no}R — "
                            f"{len(records)} / "
                            f"{race_count}R"
                        )

            else:

                if status_callback:
                    status_callback(
                        f"⏭ {target_date} — "
                        f"完了レースなし"
                    )

        else:

            if status_callback:
                status_callback(
                    f"⏭ {target_date} — "
                    f"データなし"
                )

        # -------------------------------------------------
        # 次の日へ
        # -------------------------------------------------

        days_checked += 1

        if len(records) >= race_count:
            break

        current -= timedelta(
            days=1
        )

    # =====================================================
    # 終了
    # =====================================================

    if progress_callback:
        progress_callback(
            1.0
            if records
            else 0.0
        )

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)

    # 新しい順
    if "日付" in df.columns:
        df = df.sort_values(
            ["日付", "場番号", "R番号"],
            ascending=[
                False,
                True,
                True,
            ],
        )

    # 指定数に揃える
    df = df.head(
        race_count
    ).reset_index(
        drop=True
    )

    return df


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
            "coverage_rate": 0.0,
        }

    total = len(df)

    main_rate = (
        df["本命的中"].sum()
        / total
        * 100
    )

    counter_rate = (
        df["対抗的中"].sum()
        / total
        * 100
    )

    hole_rate = (
        df["穴的中"].sum()
        / total
        * 100
    )

    coverage_rate = (
        df["3点カバー"].sum()
        / total
        * 100
    )

    return {
        "races": total,
        "main_hit_rate": round(
            main_rate,
            1,
        ),
        "counter_hit_rate": round(
            counter_rate,
            1,
        ),
        "hole_hit_rate": round(
            hole_rate,
            1,
        ),
        "coverage_rate": round(
            coverage_rate,
            1,
        ),
    }


# =========================================================
# 自信度別集計
# =========================================================

def confidence_summary(df):
    if df is None or df.empty:
        return pd.DataFrame()

    work = df.copy()

    # 自信度を5段階に分類
    def rank(value):
        value = float(value)

        if value >= 42:
            return "★★★★★"

        if value >= 34:
            return "★★★★☆"

        if value >= 27:
            return "★★★☆☆"

        if value >= 20:
            return "★★☆☆☆"

        return "★☆☆☆☆"

    work["自信度"] = work[
        "AI自信度"
    ].apply(rank)

    order = [
        "★★★★★",
        "★★★★☆",
        "★★★☆☆",
        "★★☆☆☆",
        "★☆☆☆☆",
    ]

    rows = []

    for level in order:

        subset = work[
            work["自信度"] == level
        ]

        if subset.empty:
            continue

        total = len(subset)

        rows.append(
            {
                "AI自信度": level,
                "レース数": total,
                "本命的中率": round(
                    subset["本命的中"].mean()
                    * 100,
                    1,
                ),
                "3点カバー率": round(
                    subset["3点カバー"].mean()
                    * 100,
                    1,
                ),
            }
        )

    return pd.DataFrame(rows)


# =========================================================
# UI
# =========================================================

def render_backtest():

    st.markdown(
        """
        <div style="
            font-size:28px;
            font-weight:900;
            color:#111827;
            margin-bottom:6px;
        ">
            📊 AI実力テスト
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style="
            color:#6b7280;
            font-size:14px;
            line-height:1.7;
            margin-bottom:18px;
        ">
            日付を指定する必要はありません。<br>
            最新の完了レースから自動で必要数を集めて検証します。
        </div>
        """,
        unsafe_allow_html=True,
    )

    # =====================================================
    # レース数選択
    # =====================================================

    race_count = st.radio(
        "検証するレース数",
        options=list(
            RACE_OPTIONS.keys()
        ),
        format_func=lambda x: RACE_OPTIONS[x],
        horizontal=False,
        key="backtest_race_count",
    )

    st.info(
        f"📌 直近{race_count:,}Rを自動探索します。"
    )

    # =====================================================
    # 実行
    # =====================================================

    start = st.button(
        "🚀 検証開始",
        use_container_width=True,
        key="backtest_start",
    )

    # =====================================================
    # 実行
    # =====================================================

    if start:

        progress = st.progress(
            0.0
        )

        status = st.empty()

        with st.spinner(
            "AIが過去レースを検証しています…"
        ):

            def update_progress(value):
                progress.progress(
                    max(
                        0.0,
                        min(
                            float(value),
                            1.0,
                        ),
                    )
                )

            def update_status(message):
                status.write(message)

            df = run_backtest(
                race_count=race_count,
                progress_callback=update_progress,
                status_callback=update_status,
            )

        # -------------------------------------------------
        # 結果を保存
        # -------------------------------------------------

        st.session_state[
            "backtest_result"
        ] = df

        st.session_state[
            "backtest_result_count"
        ] = race_count

        progress.progress(
            1.0
        )

        if df.empty:

            st.error(
                "⚠️ ここまで探索しましたが、"
                "検証できる完了レースが見つかりませんでした。"
            )

            st.info(
                "APIのデータ更新状況を確認して、"
                "少し時間を置いてから再度実行してください。"
            )

            return

        st.success(
            f"✅ {len(df):,}Rの検証が完了しました。"
        )

    # =====================================================
    # 保存済み結果
    # =====================================================

    df = st.session_state.get(
        "backtest_result"
    )

    saved_count = st.session_state.get(
        "backtest_result_count"
    )

    # 別のレース数を選択した場合
    if (
        df is not None
        and saved_count != race_count
    ):
        df = None

    if df is None or df.empty:
        return

    # =====================================================
    # 集計
    # =====================================================

    summary = summarize_backtest(
        df
    )

    # =====================================================
    # メトリクス
    # =====================================================

    st.markdown(
        "### 📈 検証結果"
    )

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "検証レース数",
            f"{summary['races']:,}R",
        )

    with col2:
        st.metric(
            "3点カバー率",
            f"{summary['coverage_rate']:.1f}%",
        )

    col3, col4 = st.columns(2)

    with col3:
        st.metric(
            "🎯 本命的中率",
            f"{summary['main_hit_rate']:.1f}%",
        )

    with col4:
        st.metric(
            "🔥 対抗的中率",
            f"{summary['counter_hit_rate']:.1f}%",
        )

    st.metric(
        "💥 穴的中率",
        f"{summary['hole_hit_rate']:.1f}%",
    )

    # =====================================================
    # 自信度別
    # =====================================================

    st.markdown(
        "### 🤖 AI自信度別"
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
    # レース詳細
    # =====================================================

    st.markdown(
        "### 🏁 レース別検証"
    )

    display_columns = [
        "日付",
        "場",
        "R",
        "実際の結果",
        "本命",
        "対抗",
        "穴",
        "AI自信度ランク",
        "3点カバー",
    ]

    display_columns = [
        column
        for column in display_columns
        if column in df.columns
    ]

    st.dataframe(
        df[display_columns],
        use_container_width=True,
        hide_index=True,
    )

    # =====================================================
    # CSV
    # =====================================================

    csv = df.to_csv(
        index=False,
        encoding="utf-8-sig",
    )

    st.download_button(
        label="📥 検証結果をCSV保存",
        data=csv,
        file_name=(
            f"yacchan_backtest_"
            f"{race_count}R.csv"
        ),
        mime="text/csv",
        use_container_width=True,
    )
