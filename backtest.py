import io
from datetime import date, timedelta

import pandas as pd
import streamlit as st

import data
from ai import tri_ai


RACE_OPTIONS = [100, 300, 500, 1000]


def _combo_text(combo):
    return "-".join(str(x) for x in combo)


def _confidence_from_probs(probs):
    if not probs:
        return 0.0

    values = list(probs.values())

    if not values:
        return 0.0

    return max(values)


def _confidence_stars(confidence):
    if confidence >= 0.35:
        return "★★★★★"
    if confidence >= 0.28:
        return "★★★★☆"
    if confidence >= 0.22:
        return "★★★☆☆"
    if confidence >= 0.16:
        return "★★☆☆☆"
    return "★☆☆☆☆"


def _normalize_prediction(prediction):
    """
    tri_ai の戻り値を安全に統一する。
    """

    if isinstance(prediction, dict):
        return {
            "main": prediction.get("main", []),
            "counter": prediction.get("counter", []),
            "hole": prediction.get("hole", []),
            "boat_probs": prediction.get("boat_probs", {}),
        }

    # 古い tri_ai が tuple を返す場合にも対応
    if isinstance(prediction, tuple) and len(prediction) >= 2:
        combinations = prediction[0]
        boat_probs = prediction[1]

        combinations = combinations or []

        main = combinations[0] if len(combinations) > 0 else []
        counter = combinations[1] if len(combinations) > 1 else []
        hole = combinations[2] if len(combinations) > 2 else []

        return {
            "main": main,
            "counter": counter,
            "hole": hole,
            "boat_probs": boat_probs or {},
        }

    return {
        "main": [],
        "counter": [],
        "hole": [],
        "boat_probs": {},
    }


def evaluate_race(race, stadium_no, race_no, history):
    """
    完了レース1件をAIで予想し、実際の結果と比較する。
    """

    actual = data.get_result_order(
        race_raw={
            "programs": {
                "stadiums": {
                    str(stadium_no): {
                        "races": {
                            str(race_no): race
                        }
                    }
                }
            }
        },
        stadium_no=stadium_no,
        race_no=race_no,
    )

    if not actual:
        return None

    try:
        race_rows = data.get_race_rows(
            race,
            stadium_no,
            race_no,
        )
    except TypeError:
        race_rows = data.get_race_rows(race)

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

    prediction = _normalize_prediction(prediction)

    main = prediction["main"]
    counter = prediction["counter"]
    hole = prediction["hole"]
    probs = prediction["boat_probs"]

    if len(actual) < 3:
        return None

    actual_tuple = tuple(actual[:3])

    main_hit = tuple(main[:3]) == actual_tuple if len(main) >= 3 else False
    counter_hit = (
        tuple(counter[:3]) == actual_tuple
        if len(counter) >= 3
        else False
    )
    hole_hit = tuple(hole[:3]) == actual_tuple if len(hole) >= 3 else False

    confidence = _confidence_from_probs(probs)

    return {
        "場": data.stadium_name(stadium_no),
        "場番号": stadium_no,
        "R": race_no,
        "本命": _combo_text(main),
        "対抗": _combo_text(counter),
        "穴": _combo_text(hole),
        "実結果": _combo_text(actual_tuple),
        "本命的中": main_hit,
        "対抗的中": counter_hit,
        "穴的中": hole_hit,
        "AI自信度": confidence,
        "評価": _confidence_stars(confidence),
    }


def _get_completed_races(raw):
    """
    v1 API形式から完了済みレースを取得。
    """

    results = []

    programs = raw.get("programs", {})
    stadiums = programs.get("stadiums", {})

    for stadium_key, stadium in stadiums.items():
        try:
            stadium_no = int(stadium_key)
        except (TypeError, ValueError):
            continue

        races = stadium.get("races", {})

        for race_key, race in races.items():
            try:
                race_no = int(race_key)
            except (TypeError, ValueError):
                continue

            order = data.get_result_order(
                raw,
                stadium_no,
                race_no,
            )

            if order:
                results.append(
                    (
                        stadium_no,
                        race_no,
                        race,
                    )
                )

    results.sort(
        key=lambda x: (
            x[0],
            x[1],
        )
    )

    return results


def run_backtest(
    race_count=100,
    progress_callback=None,
    status_callback=None,
):
    """
    直近の完了レースを指定件数まで自動探索して検証。
    """

    rows = []

    # 今日ではなく「昨日」から開始
    current_date = date.today() - timedelta(days=1)

    # 最大180日まで遡る
    max_days = 180

    for day_index in range(max_days):
        if len(rows) >= race_count:
            break

        target_date = current_date - timedelta(days=day_index)
        date_text = target_date.isoformat()

        if status_callback:
            status_callback(
                f"📡 {date_text} の完了レースを確認中… "
                f"({len(rows)}/{race_count})"
            )

        try:
            raw = data.get_data(date_text)
        except Exception:
            continue

        if not raw:
            continue

        completed = _get_completed_races(raw)

        if not completed:
            continue

        # 日ごとに履歴を一度だけ取得
        try:
            history = data.history14(date_text)
        except Exception:
            history = None

        for stadium_no, race_no, race in completed:
            if len(rows) >= race_count:
                break

            result = evaluate_race(
                race,
                stadium_no,
                race_no,
                history,
            )

            if result is None:
                continue

            result["日付"] = date_text
            rows.append(result)

            if progress_callback:
                progress_callback(
                    min(len(rows) / race_count, 1.0)
                )

    return pd.DataFrame(rows)


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
        "main": int(df["本命的中"].sum()),
        "counter": int(df["対抗的中"].sum()),
        "hole": int(df["穴的中"].sum()),
    }


def confidence_summary(df):
    if df is None or df.empty:
        return "—"

    value = float(df["AI自信度"].mean())

    return _confidence_stars(value)


def render_backtest():
    st.markdown(
        """
        <style>
        .bt-title {
            font-size: 22px;
            font-weight: 900;
            color: #111827;
            margin-top: 8px;
            margin-bottom: 4px;
        }

        .bt-subtitle {
            font-size: 13px;
            color: #64748b;
            margin-bottom: 18px;
        }

        .bt-label {
            font-size: 14px;
            font-weight: 800;
            color: #111827;
            margin-top: 8px;
            margin-bottom: 6px;
        }

        .bt-info {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 12px 14px;
            color: #334155;
            font-size: 13px;
            line-height: 1.6;
            margin-bottom: 16px;
        }

        .bt-result-title {
            font-size: 18px;
            font-weight: 900;
            color: #111827;
            margin-top: 20px;
            margin-bottom: 10px;
        }

        div[data-testid="stSelectbox"] label {
            color: #111827 !important;
            font-weight: 800 !important;
        }

        div[data-testid="stSelectbox"] div[role="combobox"] {
            background: #ffffff !important;
            color: #111827 !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 10px !important;
        }

        div[data-testid="stSelectbox"] div[role="combobox"] * {
            color: #111827 !important;
        }

        div[data-testid="stButton"] button {
            width: 100%;
            min-height: 48px;
            border-radius: 12px;
            font-weight: 900;
            font-size: 15px;
        }

        @media (max-width: 640px) {
            .bt-title {
                font-size: 20px;
            }

            .bt-subtitle {
                font-size: 12px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="bt-title">📊 AIバックテスト</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="bt-subtitle">'
        '過去の完了レースを使ってAI予想の精度を検証します'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="bt-info">'
        '📌 日付ではなく<strong>完了レース数</strong>で指定します。'
        '<br>'
        '指定した件数に達するまで、過去へ自動的に遡ります。'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="bt-label">検証するレース数</div>',
        unsafe_allow_html=True,
    )

    race_count = st.selectbox(
        "検証するレース数",
        RACE_OPTIONS,
        format_func=lambda x: f"直近{x:,}レース",
        label_visibility="collapsed",
        key="bt_race_count",
    )

    st.write("")

    run = st.button(
        "🚀 バックテスト開始",
        type="primary",
        key="run_backtest",
    )

    if not run:
        return

    progress = st.progress(0.0)
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

    if df is None or df.empty:
        st.error(
            "ここまで探しましたが、検証できる完了レースが見つかりませんでした。"
        )
        return

    summary = summarize_backtest(df)

    st.markdown(
        '<div class="bt-result-title">📈 検証結果</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "検証レース",
            f"{summary['total']:,}",
        )

    with c2:
        main_rate = (
            summary["main"] / summary["total"] * 100
            if summary["total"]
            else 0
        )
        st.metric(
            "本命的中率",
            f"{main_rate:.1f}%",
        )

    with c3:
        counter_rate = (
            summary["counter"] / summary["total"] * 100
            if summary["total"]
            else 0
        )
        st.metric(
            "対抗的中率",
            f"{counter_rate:.1f}%",
        )

    with c4:
        hole_rate = (
            summary["hole"] / summary["total"] * 100
            if summary["total"]
            else 0
        )
        st.metric(
            "穴的中率",
            f"{hole_rate:.1f}%",
        )

    st.markdown(
        '<div class="bt-result-title">🎯 AI自信度</div>',
        unsafe_allow_html=True,
    )

    st.write(
        f"平均自信度：{confidence_summary(df)}"
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
        col for col in display_columns
        if col in df.columns
    ]

    st.dataframe(
        df[available_columns],
        use_container_width=True,
        hide_index=True,
    )

    csv = df.to_csv(
        index=False,
        encoding="utf-8-sig",
    )

    st.download_button(
        "⬇️ 検証結果をCSV保存",
        data=csv,
        file_name=f"boat_ai_backtest_{race_count}.csv",
        mime="text/csv",
        use_container_width=True,
    )
