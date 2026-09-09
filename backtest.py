import streamlit as st
import pandas as pd
from datetime import date, timedelta

import data
from ai import tri_ai


# =========================================================
# 設定
# =========================================================

RACE_OPTIONS = [100, 300, 500, 1000]


# =========================================================
# バックテスト専用CSS
# =========================================================

def _inject_css():
    st.markdown(
        """
        <style>

        /* ==============================================
           バックテスト全体
        ============================================== */

        .bt-wrap {
            margin-top: 4px;
        }

        .bt-title {
            color: #111827 !important;
            font-size: 24px !important;
            font-weight: 900 !important;
            line-height: 1.3 !important;
            margin: 0 0 5px 0 !important;
        }

        .bt-description {
            color: #64748b !important;
            font-size: 13px !important;
            line-height: 1.7 !important;
            margin-bottom: 18px !important;
        }

        /* ==============================================
           選択エリア
        ============================================== */

        .bt-select-title {
            color: #111827 !important;
            font-size: 14px !important;
            font-weight: 900 !important;
            margin-bottom: 8px !important;
        }

        .bt-select-card {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 14px 15px 6px 15px;
            margin-bottom: 14px;
        }

        /* ==============================================
           Radio
        ============================================== */

        div[data-testid="stRadio"] {
            margin-top: 0 !important;
        }

        div[data-testid="stRadio"] > label {
            color: #111827 !important;
            font-weight: 900 !important;
            font-size: 14px !important;
        }

        div[data-testid="stRadio"] label {
            color: #111827 !important;
        }

        div[data-testid="stRadio"] label p {
            color: #111827 !important;
            font-size: 14px !important;
            font-weight: 800 !important;
        }

        div[data-testid="stRadio"] [role="radiogroup"] {
            gap: 7px !important;
        }

        div[data-testid="stRadio"] [role="radio"] {
            color: #111827 !important;
            background: #ffffff !important;
            border: 1px solid #d7dee8 !important;
            border-radius: 12px !important;
            padding: 10px 12px !important;
        }

        /* ==============================================
           実行ボタン
        ============================================== */

        .bt-run-area {
            margin: 12px 0 20px 0;
        }

        /* ==============================================
           情報カード
        ============================================== */

        .bt-info {
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            border-radius: 14px;
            padding: 12px 14px;
            color: #1e40af !important;
            font-size: 13px;
            font-weight: 700;
            margin-bottom: 16px;
        }

        /* ==============================================
           結果タイトル
        ============================================== */

        .bt-result-title {
            color: #111827 !important;
            font-size: 20px !important;
            font-weight: 900 !important;
            margin: 22px 0 12px 0 !important;
        }

        /* ==============================================
           成功表示
        ============================================== */

        .bt-success {
            background: #ecfdf5;
            border: 1px solid #a7f3d0;
            color: #065f46 !important;
            border-radius: 14px;
            padding: 12px 14px;
            font-size: 14px;
            font-weight: 800;
            margin: 14px 0;
        }

        /* ==============================================
           モバイル
        ============================================== */

        @media (max-width: 600px) {

            .bt-title {
                font-size: 21px !important;
            }

            .bt-description {
                font-size: 12px !important;
            }

            div[data-testid="stRadio"] [role="radio"] {
                padding: 9px 10px !important;
            }
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# ユーティリティ
# =========================================================

def _combo_tuple(combo):
    if not combo:
        return tuple()

    try:
        return tuple(int(x) for x in combo)
    except (TypeError, ValueError):
        return tuple()


def _combo_text(combo):
    values = _combo_tuple(combo)

    if not values:
        return "—"

    return "-".join(str(x) for x in values)


def _confidence_from_probs(boat_probs):
    if not isinstance(boat_probs, dict):
        return 0.0

    values = []

    for value in boat_probs.values():
        try:
            values.append(float(value))
        except (TypeError, ValueError):
            pass

    if not values:
        return 0.0

    values.sort(reverse=True)

    if len(values) >= 2:
        return values[0] * 0.7 + values[1] * 0.3

    return values[0]


def _confidence_stars(value):
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


# =========================================================
# 1レース検証
# =========================================================

def evaluate_race(
    raw,
    target_date,
    stadium_no,
    race_no,
    history=None,
):
    race = data.get_race(
        raw,
        stadium_no,
        race_no,
    )

    if race is None:
        return None

    if not data.validate_race(
        race,
        target_date,
        stadium_no,
        race_no,
    ):
        return None

    actual = data.get_result_order(
        raw,
        stadium_no,
        race_no,
    )

    if actual is None:
        return None

    actual_tuple = tuple(
        int(x) for x in actual[:3]
    )

    if len(actual_tuple) != 3:
        return None

    race_rows = data.get_race_rows(
        race,
        stadium_no,
        race_no,
    )

    if race_rows is None or race_rows.empty:
        return None

    if history is None:
        history = data.history14(
            target_date
        )

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

    return {
        "日付": str(target_date),
        "場": data.stadium_name(stadium_no),
        "場番号": int(stadium_no),
        "R": f"{race_no}R",
        "R番号": int(race_no),

        "実際の結果": _combo_text(
            actual_tuple
        ),

        "本命": _combo_text(main),
        "対抗": _combo_text(counter),
        "穴": _combo_text(hole),

        "本命的中": int(
            main == actual_tuple
        ),

        "対抗的中": int(
            counter == actual_tuple
        ),

        "穴的中": int(
            hole == actual_tuple
        ),

        "3点カバー": int(
            actual_tuple in {
                main,
                counter,
                hole,
            }
        ),

        "AI自信度": round(
            _confidence_from_probs(
                prediction.get(
                    "boat_probs",
                    {},
                )
            ) * 100,
            1,
        ),
    }


# =========================================================
# バックテスト実行
# =========================================================

def run_backtest(
    race_count=100,
    progress_callback=None,
    status_callback=None,
):
    race_count = int(race_count)

    records = []

    # 今日の未完了レースを除外
    current = date.today() - timedelta(days=1)

    max_days = 180
    days_checked = 0

    while (
        len(records) < race_count
        and days_checked < max_days
    ):

        target_date = current

        if status_callback:
            status_callback(
                f"🔎 {target_date} を確認中　"
                f"{len(records)} / {race_count}R"
            )

        raw = data.get_data(
            target_date
        )

        if raw:

            completed_races = []

            # ---------------------------------------------
            # 完了済みレースだけ抽出
            # ---------------------------------------------

            for stadium_no in range(1, 25):

                for race_no in range(1, 13):

                    actual = data.get_result_order(
                        raw,
                        stadium_no,
                        race_no,
                    )

                    if actual is not None:
                        completed_races.append(
                            (
                                stadium_no,
                                race_no,
                            )
                        )

            # ---------------------------------------------
            # 完了レースが存在
            # ---------------------------------------------

            if completed_races:

                if status_callback:
                    status_callback(
                        f"📊 {target_date}　"
                        f"完了 {len(completed_races)}R　"
                        f"取得 {len(records)} / "
                        f"{race_count}R"
                    )

                # その日のAI用履歴を1回だけ取得
                history = data.history14(
                    target_date
                )

                for stadium_no, race_no in completed_races:

                    if len(records) >= race_count:
                        break

                    result = evaluate_race(
                        raw,
                        target_date,
                        stadium_no,
                        race_no,
                        history=history,
                    )

                    if result is None:
                        continue

                    records.append(result)

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
                            f"{race_no}R　"
                            f"{len(records)} / "
                            f"{race_count}R"
                        )

            else:

                if status_callback:
                    status_callback(
                        f"⏭ {target_date}　"
                        f"完了レースなし"
                    )

        else:

            if status_callback:
                status_callback(
                    f"⏭ {target_date}　"
                    f"データなし"
                )

        days_checked += 1

        if len(records) >= race_count:
            break

        current -= timedelta(days=1)

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)

    # 新しいレースを上に
    df = df.sort_values(
        [
            "日付",
            "場番号",
            "R番号",
        ],
        ascending=[
            False,
            True,
            True,
        ],
    )

    df = df.head(
        race_count
    ).reset_index(
        drop=True
    )

    if progress_callback:
        progress_callback(1.0)

    return df


# =========================================================
# 集計
# =========================================================

def summarize_backtest(df):
    if df is None or df.empty:
        return {
            "races": 0,
            "main": 0.0,
            "counter": 0.0,
            "hole": 0.0,
            "coverage": 0.0,
        }

    total = len(df)

    return {
        "races": total,

        "main": round(
            df["本命的中"].mean() * 100,
            1,
        ),

        "counter": round(
            df["対抗的中"].mean() * 100,
            1,
        ),

        "hole": round(
            df["穴的中"].mean() * 100,
            1,
        ),

        "coverage": round(
            df["3点カバー"].mean() * 100,
            1,
        ),
    }


# =========================================================
# 自信度別
# =========================================================

def confidence_summary(df):
    if df is None or df.empty:
        return pd.DataFrame()

    work = df.copy()

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

    levels = [
        "★★★★★",
        "★★★★☆",
        "★★★☆☆",
        "★★☆☆☆",
        "★☆☆☆☆",
    ]

    rows = []

    for level in levels:

        subset = work[
            work["自信度"] == level
        ]

        if subset.empty:
            continue

        rows.append(
            {
                "AI自信度": level,
                "レース数": len(subset),
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

    _inject_css()

    # =====================================================
    # ヘッダー
    # =====================================================

    st.markdown(
        """
        <div class="bt-wrap">

            <div class="bt-title">
                📊 AI実力テスト
            </div>

            <div class="bt-description">
                最新の完了レースから自動取得して、
                AI予想の的中率を検証します。
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    # =====================================================
    # 選択
    # =====================================================

    st.markdown(
        '<div class="bt-select-card">',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="bt-select-title">検証するレース数</div>',
        unsafe_allow_html=True,
    )

    race_count = st.radio(
        "検証するレース数",
        options=RACE_OPTIONS,
        format_func=lambda x: f"直近{x:,}レース",
        label_visibility="collapsed",
        key="bt_race_count",
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )

    # =====================================================
    # 説明
    # =====================================================

    st.markdown(
        f"""
        <div class="bt-info">
            🔎 昨日のレースから逆順に探して、
            完了済みのレースを {race_count:,}R 集めます。
            <br>
            目標数に到達した時点で自動終了します。
        </div>
        """,
        unsafe_allow_html=True,
    )

    # =====================================================
    # 実行
    # =====================================================

    if st.button(
        "🚀 この条件で検証開始",
        use_container_width=True,
        key="bt_start",
    ):

        progress = st.progress(0)

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

        st.session_state[
            "bt_result"
        ] = df

        st.session_state[
            "bt_result_count"
        ] = race_count

        if df.empty:

            st.error(
                "⚠️ 検証できる完了レースが見つかりませんでした。"
            )

            return

        st.markdown(
            f"""
            <div class="bt-success">
                ✅ {len(df):,}レースの検証が完了しました。
            </div>
            """,
            unsafe_allow_html=True,
        )

    # =====================================================
    # 結果取得
    # =====================================================

    df = st.session_state.get(
        "bt_result"
    )

    result_count = st.session_state.get(
        "bt_result_count"
    )

    if df is None or df.empty:
        return

    # 現在選択している件数と結果が違う場合
    if result_count != race_count:
        return

    # =====================================================
    # 集計
    # =====================================================

    summary = summarize_backtest(
        df
    )

    st.markdown(
        '<div class="bt-result-title">📈 検証結果</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "検証レース",
            f"{summary['races']:,}R",
        )

    with col2:
        st.metric(
            "3点カバー率",
            f"{summary['coverage']:.1f}%",
        )

    col3, col4 = st.columns(2)

    with col3:
        st.metric(
            "🎯 本命的中率",
            f"{summary['main']:.1f}%",
        )

    with col4:
        st.metric(
            "🔥 対抗的中率",
            f"{summary['counter']:.1f}%",
        )

    st.metric(
        "💥 穴的中率",
        f"{summary['hole']:.1f}%",
    )

    # =====================================================
    # 自信度
    # =====================================================

    st.markdown(
        '<div class="bt-result-title">🤖 AI自信度別</div>',
        unsafe_allow_html=True,
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
    # 詳細
    # =====================================================

    st.markdown(
        '<div class="bt-result-title">🏁 レース別検証</div>',
        unsafe_allow_html=True,
    )

    columns = [
        "日付",
        "場",
        "R",
        "実際の結果",
        "本命",
        "対抗",
        "穴",
        "AI自信度",
        "3点カバー",
    ]

    columns = [
        x
        for x in columns
        if x in df.columns
    ]

    st.dataframe(
        df[columns],
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
        "📥 検証結果をCSV保存",
        data=csv,
        file_name=(
            f"yacchan_backtest_"
            f"{race_count}R.csv"
        ),
        mime="text/csv",
        use_container_width=True,
    
