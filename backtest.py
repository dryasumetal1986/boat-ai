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
# 文字列
# =========================================================

def combo_text(combo):
    if not combo:
        return "—"

    return "-".join(str(x) for x in combo)


def confidence_stars(confidence):
    if confidence >= 0.35:
        return "★★★★★"
    elif confidence >= 0.28:
        return "★★★★☆"
    elif confidence >= 0.22:
        return "★★★☆☆"
    elif confidence >= 0.16:
        return "★★☆☆☆"
    else:
        return "★☆☆☆☆"


# =========================================================
# AI予想形式を統一
# =========================================================

def normalize_prediction(prediction):

    # 新しい ai.py
    if isinstance(prediction, dict):

        return {
            "main": prediction.get("main", []),
            "counter": prediction.get("counter", []),
            "hole": prediction.get("hole", []),
            "boat_probs": prediction.get(
                "boat_probs",
                {},
            ),
        }

    # 古い ai.py
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
        except (TypeError, ValueError):
            continue

        races = stadium.get(
            "races",
            {},
        )

        for race_key, race in races.items():

            try:
                race_no = int(race_key)
            except (TypeError, ValueError):
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

    # -----------------------------------------
    # 6艇データ
    # -----------------------------------------

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

    # -----------------------------------------
    # AI
    # -----------------------------------------

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

    # -----------------------------------------
    # 的中判定
    # -----------------------------------------

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

    # -----------------------------------------
    # AI自信度
    # -----------------------------------------

    confidence = 0.0

    if (
        isinstance(boat_probs, dict)
        and boat_probs
    ):

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
        "実結果": combo_text(
            actual_tuple
        ),
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

    # 昨日から過去へ
    current_date = (
        date.today()
        - timedelta(days=1)
    )

    # 最大180日
    max_days = 180

    for day_index in range(max_days):

        # -----------------------------------------
        # 必要件数に到達
        # -----------------------------------------

        if len(rows) >= race_count:
            break

        target_date = (
            current_date
            - timedelta(days=day_index)
        )

        date_text = (
            target_date.isoformat()
        )

        # -----------------------------------------
        # ステータス
        # -----------------------------------------

        status_text = (
            f"{date_text} を確認中"
        )

        if status_callback:
            status_callback(
                len(rows),
                race_count,
                status_text,
            )

        # -----------------------------------------
        # API
        # -----------------------------------------

        try:
            raw = data.get_data(
                date_text
            )
        except Exception:
            continue

        if not raw:
            continue

        # -----------------------------------------
        # 完了レース
        # -----------------------------------------

        completed = get_completed_races(
            raw
        )

        if not completed:
            continue

        # -----------------------------------------
        # 過去14日データ
        # -----------------------------------------

        try:
            history = data.history14(
                date_text
            )
        except Exception:
            history = None

        # -----------------------------------------
        # 各レース
        # -----------------------------------------

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

            # -------------------------------------
            # 進捗更新
            # -------------------------------------

            if progress_callback:
                progress_callback(
                    len(rows),
                    race_count,
                    (
                        f"{date_text} "
                        f"{data.stadium_name(stadium_no)} "
                        f"{race_no}R を検証中"
                    ),
                )

    # 最終状態
    if status_callback:
        status_callback(
            len(rows),
            race_count,
            "検証完了",
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
# レース進捗画面
# =========================================================

def render_race_progress(
    current,
    total,
    status_text,
):

    if total <= 0:
        percent = 0
    else:
        percent = min(
            current / total * 100,
            100,
        )

    st.markdown(
        f"""
        <style>

        /* ======================================
           水面
           ====================================== */

        .race-progress {
            position: relative;
            width: 100%;
            height: 205px;
            overflow: hidden;
            border-radius: 18px;

            background:
                linear-gradient(
                    180deg,
                    #075985 0%,
                    #0284c7 45%,
                    #0369a1 100%
                );

            border: 2px solid #0ea5e9;

            box-shadow:
                0 10px 28px
                rgba(2,132,199,0.30);

            margin-top: 14px;
            margin-bottom: 18px;
        }


        /* ======================================
           水面の波
           ====================================== */

        .race-progress::before {
            content: "";
            position: absolute;
            inset: 0;

            background:
                repeating-linear-gradient(
                    -7deg,
                    rgba(255,255,255,0.20) 0px,
                    rgba(255,255,255,0.20) 2px,
                    transparent 2px,
                    transparent 19px
                );

            animation:
                waterMove 1.4s linear infinite;
        }


        @keyframes waterMove {

            0% {
                transform: translateX(0);
            }

            100% {
                transform: translateX(42px);
            }
        }


        /* ======================================
           ボート
           ====================================== */

        .race-boat {
            position: absolute;

            left: -80px;

            font-size: 30px;

            z-index: 4;

            white-space: nowrap;

            animation:
                boatMove 3.2s linear infinite;
        }


        .boat-1 {
            top: 22px;
            animation-delay: 0s;
        }

        .boat-2 {
            top: 52px;
            animation-delay: 0.35s;
        }

        .boat-3 {
            top: 82px;
            animation-delay: 0.7s;
        }

        .boat-4 {
            top: 112px;
            animation-delay: 1.05s;
        }

        .boat-5 {
            top: 142px;
            animation-delay: 1.4s;
        }

        .boat-6 {
            top: 172px;
            animation-delay: 1.75s;
        }


        @keyframes boatMove {

            0% {
                left: -80px;
                transform: translateY(0)
                           rotate(-2deg);
            }

            25% {
                transform: translateY(-2px)
                           rotate(1deg);
            }

            50% {
                transform: translateY(1px)
                           rotate(-1deg);
            }

            75% {
                transform: translateY(-2px)
                           rotate(1deg);
            }

            100% {
                left: 110%;
                transform: translateY(0)
                           rotate(-2deg);
            }
        }


        /* ======================================
           進捗情報
           ====================================== */

        .race-progress-info {
            position: absolute;

            right: 14px;
            top: 14px;

            z-index: 10;

            min-width: 235px;

            padding: 11px 14px;

            background:
                rgba(2,24,55,0.91);

            border:
                1px solid
                rgba(255,255,255,0.45);

            border-radius: 13px;

            color: #ffffff;

            box-shadow:
                0 6px 18px
                rgba(0,0,0,0.22);
        }


        .race-progress-status {
            color: #dbeafe;

            font-size: 12px;

            font-weight: 850;

            line-height: 1.4;

            white-space: nowrap;

            overflow: hidden;

            text-overflow: ellipsis;
        }


        .race-progress-count {
            color: #ffffff;

            font-size: 20px;

            font-weight: 950;

            line-height: 1.25;

            margin-top: 3px;
        }


        /* ======================================
           進捗バー
           ====================================== */

        .race-progress-bar {
            width: 100%;

            height: 6px;

            margin-top: 8px;

            background:
                rgba(255,255,255,0.25);

            border-radius: 999px;

            overflow: hidden;
        }


        .race-progress-bar-inner {
            width: {percent:.2f}%;

            height: 100%;

            background: #ffffff;

            border-radius: 999px;

            transition:
                width 0.3s ease;
        }


        /* ======================================
           スマホ
           ====================================== */

        @media (max-width: 640px) {

            .race-progress {
                height: 190px;
            }

            .race-progress-info {
                left: 12px;
                right: 12px;
                top: 12px;

                min-width: 0;
            }

            .race-progress-status {
                font-size: 11px;
            }

            .race-progress-count {
                font-size: 18px;
            }

            .race-boat {
                font-size: 25px;
            }

        }

        </style>


        <div class="race-progress">

            <div class="race-boat boat-1">
                🚤
            </div>

            <div class="race-boat boat-2">
                🚤
            </div>

            <div class="race-boat boat-3">
                🚤
            </div>

            <div class="race-boat boat-4">
                🚤
            </div>

            <div class="race-boat boat-5">
                🚤
            </div>

            <div class="race-boat boat-6">
                🚤
            </div>


            <div class="race-progress-info">

                <div class="race-progress-status">
                    🔄 {status_text}
                </div>

                <div class="race-progress-count">
                    {current:,} / {total:,} レース
                </div>

                <div class="race-progress-bar">
                    <div
                        class="race-progress-bar-inner"
                    ></div>
                </div>

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# バックテスト画面
# =========================================================

def render_backtest():

    # -----------------------------------------------------
    # 見出し
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # レース数
    # -----------------------------------------------------

    race_count = st.selectbox(
        "検証するレース数",
        RACE_OPTIONS,
        format_func=lambda x:
            f"直近{x:,}レース",
        key="backtest_race_count",
    )

    st.write("")

    # -----------------------------------------------------
    # 開始
    # -----------------------------------------------------

    start = st.button(
        "🚀 バックテスト開始",
        type="primary",
        use_container_width=True,
        key="start_backtest",
    )

    if not start:
        return

    # -----------------------------------------------------
    # 進捗エリア
    # -----------------------------------------------------

    progress_area = st.empty()

    # 最初の表示
    with progress_area.container():

        render_race_progress(
            0,
            race_count,
            "テスト中 → 過去のレースを検索中",
        )

    # -----------------------------------------------------
    # コールバック
    # -----------------------------------------------------

    def update_progress(
        current,
        total,
        status_text,
    ):

        progress_area.empty()

        with progress_area.container():

            render_race_progress(
                current,
                total,
                status_text,
            )

    # -----------------------------------------------------
    # 実行
    # -----------------------------------------------------

    try:

        df = run_backtest(
            race_count=race_count,
            progress_callback=update_progress,
            status_callback=update_progress,
        )

    except Exception as e:

        progress_area.empty()

        st.error(
            "バックテスト中にエラーが発生しました。"
        )

        st.exception(e)

        return

    # -----------------------------------------------------
    # 完了
    # -----------------------------------------------------

    progress_area.empty()

    if df is None or df.empty:

        st.error(
            "ここまで探しましたが、"
            "検証できる完了レースが見つかりませんでした。"
        )

        return

    # -----------------------------------------------------
    # 集計
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # 結果タイトル
    # -----------------------------------------------------

    st.markdown(
        """
        <div class="backtest-title">
            📈 検証結果
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -----------------------------------------------------
    # Metrics
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # AI自信度
    # -----------------------------------------------------

    if "AI自信度" in df.columns:

        avg_confidence = float(
            df["AI自信度"].mean()
        )

        st.markdown(
            f"""
            <div class="confidence-box">

                <div class="confidence-title">
                    平均AI自信度
                </div>

                <div class="confidence-stars">
                    {confidence_stars(avg_confidence)}
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    # -----------------------------------------------------
    # 明細
    # -----------------------------------------------------

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

    available_columns = [
        col
        for col in display_columns
        if col in df.columns
    ]

    st.dataframe(
        df[available_columns],
        use_container_width=True,
        hide_index=True,
    )

    # -----------------------------------------------------
    # CSV
    # -----------------------------------------------------

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
