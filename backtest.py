from datetime import date, timedelta

import pandas as pd
import streamlit as st

import data
from ai import tri_ai


# =========================================================
# 設定
# =========================================================

RACE_OPTIONS = [100, 300, 500, 1000]


# =========================================================
# 共通処理
# =========================================================

def combo_text(combo):
    if not combo:
        return "—"

    return "-".join(
        str(x) for x in combo
    )


def normalize_prediction(prediction):

    # 新形式
    if isinstance(prediction, dict):

        return {
            "main": prediction.get("main", []),
            "counter": prediction.get("counter", []),
            "hole": prediction.get("hole", []),
            "boat_probs": prediction.get("boat_probs", {}),
        }

    # 旧形式
    if isinstance(prediction, tuple):

        combinations = (
            prediction[0]
            if len(prediction) > 0
            else []
        )

        boat_probs = (
            prediction[1]
            if len(prediction) > 1
            else {}
        )

        return {
            "main": (
                combinations[0]
                if len(combinations) > 0
                else []
            ),
            "counter": (
                combinations[1]
                if len(combinations) > 1
                else []
            ),
            "hole": (
                combinations[2]
                if len(combinations) > 2
                else []
            ),
            "boat_probs": boat_probs or {},
        }

    return {
        "main": [],
        "counter": [],
        "hole": [],
        "boat_probs": {},
    }


def confidence_stars(confidence):

    if confidence >= 0.35:
        return "★★★★★"

    if confidence >= 0.28:
        return "★★★★☆"

    if confidence >= 0.22:
        return "★★★☆☆"

    if confidence >= 0.16:
        return "★★☆☆☆"

    return "★☆☆☆☆"


# =========================================================
# 完了レース取得
# =========================================================

def get_completed_races(raw):

    completed = []

    if not raw:
        return completed

    programs = raw.get(
        "programs",
        {},
    )

    stadiums = programs.get(
        "stadiums",
        {},
    )

    for stadium_key, stadium in stadiums.items():

        try:
            stadium_no = int(stadium_key)
        except Exception:
            continue

        races = stadium.get(
            "races",
            {},
        )

        for race_key, race in races.items():

            try:
                race_no = int(race_key)
            except Exception:
                continue

            try:
                result = race.get(
                    "result",
                    {},
                )

                racers = result.get(
                    "racers",
                    {},
                )

                if not racers:
                    continue

                order = data.get_result_order(
                    raw,
                    stadium_no,
                    race_no,
                )

                if not order:
                    continue

                if len(order) < 3:
                    continue

                completed.append(
                    (
                        stadium_no,
                        race_no,
                        race,
                        order,
                    )
                )

            except Exception:
                continue

    completed.sort(
        key=lambda x: (
            x[0],
            x[1],
        )
    )

    return completed


# =========================================================
# 1レース検証
# =========================================================

def evaluate_race(
    raw,
    stadium_no,
    race_no,
    race,
    history,
):

    try:
        actual = data.get_result_order(
            raw,
            stadium_no,
            race_no,
        )
    except Exception:
        return None

    if not actual or len(actual) < 3:
        return None

    try:
        race_rows = data.get_race_rows(
            race,
            stadium_no,
            race_no,
        )
    except TypeError:
        try:
            race_rows = data.get_race_rows(
                race
            )
        except Exception:
            return None
    except Exception:
        return None

    if race_rows is None:
        return None

    if len(race_rows) != 6:
        return None

    try:
        prediction = tri_ai(
            race_rows,
            history,
        )
    except Exception:
        return None

    prediction = normalize_prediction(
        prediction
    )

    main = prediction["main"]
    counter = prediction["counter"]
    hole = prediction["hole"]
    boat_probs = prediction["boat_probs"]

    actual_tuple = tuple(
        actual[:3]
    )

    main_hit = (
        len(main) >= 3
        and tuple(main[:3]) == actual_tuple
    )

    counter_hit = (
        len(counter) >= 3
        and tuple(counter[:3]) == actual_tuple
    )

    hole_hit = (
        len(hole) >= 3
        and tuple(hole[:3]) == actual_tuple
    )

    confidence = 0.0

    if isinstance(boat_probs, dict) and boat_probs:

        try:
            confidence = max(
                float(v)
                for v in boat_probs.values()
            )
        except Exception:
            confidence = 0.0

    return {
        "場": data.stadium_name(
            stadium_no
        ),
        "場番号": stadium_no,
        "R": race_no,
        "本命": combo_text(main),
        "対抗": combo_text(counter),
        "穴": combo_text(hole),
        "実結果": combo_text(actual_tuple),
        "本命的中": main_hit,
        "対抗的中": counter_hit,
        "穴的中": hole_hit,
        "AI自信度": confidence,
        "評価": confidence_stars(
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

    rows = []

    # 昨日からスタート
    current_date = (
        date.today()
        - timedelta(days=1)
    )

    # 最大180日
    max_days = 180

    for day_index in range(max_days):

        if len(rows) >= race_count:
            break

        target_date = (
            current_date
            - timedelta(days=day_index)
        )

        date_text = (
            target_date.isoformat()
        )

        if status_callback:

            status_callback(
                f"📡 {date_text} を確認中　"
                f"{len(rows):,} / "
                f"{race_count:,} レース"
            )

        try:
            raw = data.get_data(
                date_text
            )
        except Exception:
            continue

        if not raw:
            continue

        completed = get_completed_races(
            raw
        )

        if not completed:
            continue

        # その日の過去14日データ
        try:
            history = data.history14(
                date_text
            )
        except Exception:
            history = None

        for (
            stadium_no,
            race_no,
            race,
            actual_order,
        ) in completed:

            if len(rows) >= race_count:
                break

            result = evaluate_race(
                raw,
                stadium_no,
                race_no,
                race,
                history,
            )

            if result is None:
                continue

            result["日付"] = date_text

            rows.append(result)

            if progress_callback:

                progress_callback(
                    min(
                        len(rows)
                        / race_count,
                        1.0,
                    )
                )

    return pd.DataFrame(rows)


# =========================================================
# 集計
# =========================================================

def summarize_backtest(df):

    if df is None or df.empty:

        return {
            "total": 0,
            "main": 0,
            "counter": 0,
            "hole": 0,
        }

    return {
        "total": len(df),
        "main": int(
            df["本命的中"].sum()
        ),
        "counter": int(
            df["対抗的中"].sum()
        ),
        "hole": int(
            df["穴的中"].sum()
        ),
    }


# =========================================================
# UI
# =========================================================

def render_backtest():

    st.markdown(
        """
        <div class="backtest-title">
            📊 AIバックテスト
        </div>
        <div class="backtest-subtitle">
            過去の完了レースを使ってAI予想の精度を検証します
        </div>

        <div class="backtest-info">
            📌 日付ではなく<strong>完了レース数</strong>で指定します。<br>
            指定した件数に達するまで、過去へ自動的に遡ります。
        </div>
        """,
        unsafe_allow_html=True,
    )

    # =====================================================
    # レース数
    # =====================================================

    race_count = st.selectbox(
        "検証するレース数",
        RACE_OPTIONS,
        format_func=lambda x:
            f"直近{x:,}レース",
        key="backtest_race_count",
    )

    st.write("")

    start = st.button(
        "🚀 バックテスト開始",
        type="primary",
        use_container_width=True,
        key="start_backtest",
    )

    if not start:
        return

    progress = st.progress(0)

    status = st.empty()

    try:

        df = run_backtest(
            race_count=race_count,
            progress_callback=progress.progress,
            status_callback=status.info,
        )

    except Exception as e:

        progress.empty()
        status.empty()

        st.error(
            "バックテスト中にエラーが発生しました。"
        )

        st.exception(e)

        return

    progress.empty()
    status.empty()

    # =====================================================
    # データなし
    # =====================================================

    if df is None or df.empty:

        st.error(
            "ここまで探しましたが、"
            "検証できる完了レースが見つかりませんでした。"
        )

        return

    # =====================================================
    # 集計
    # =====================================================

    summary = summarize_backtest(
        df
    )

    total = summary["total"]

    main_rate = (
        summary["main"]
        / total
        * 100
        if total
        else 0
    )

    counter_rate = (
        summary["counter"]
        / total
        * 100
        if total
        else 0
    )

    hole_rate = (
        summary["hole"]
        / total
        * 100
        if total
        else 0
    )

    # =====================================================
    # 結果
    # =====================================================

    st.markdown(
        """
        <div class="backtest-title">
            📈 検証結果
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "検証レース",
            f"{total:,}",
        )

    with c2:
        st.metric(
            "本命的中率",
            f"{main_rate:.1f}%",
        )

    with c3:
        st.metric(
            "対抗的中率",
            f"{counter_rate:.1f}%",
        )

    with c4:
        st.metric(
            "穴的中率",
            f"{hole_rate:.1f}%",
        )

    # =====================================================
    # 自信度
    # =====================================================

    if "AI自信度" in df.columns:

        avg_confidence = float(
            df["AI自信度"].mean()
        )

        stars = confidence_stars(
            avg_confidence
        )

        st.markdown(
            f"""
            <div class="confidence-box">
                <div class="confidence-title">
                    平均AI自信度
                </div>
                <div class="confidence-stars">
                    {stars}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # =====================================================
    # 明細
    # =====================================================

    st.markdown(
        """
        <div class="section-title">
            検証レース一覧
        </div>
        """,
        unsafe_allow_html=True,
    )

    display_columns = [
        "日付",
        "場",
        "R",
        "本命",
        "対抗",
        "穴",
        "実結果",
        "評価",
    ]

    available = [
        col
        for col in display_columns
        if col in df.columns
    ]

    st.dataframe(
        df[available],
        use_container_width=True,
        hide_index=True,
    )

    # =====================================================
    # CSV
    # =====================================================

    csv_data = df.to_csv(
        index=False,
        encoding="utf-8-sig",
    )

    st.download_button(
        "⬇️ 検証結果をCSV保存",
        data=csv_data,
        file_name=(
            f"boat_ai_backtest_"
            f"{race_count}.csv"
        ),
        mime="text/csv",
        use_container_width=True,
    )
