from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

import data
from ai import tri_ai


RACE_OPTIONS = [100, 300, 500, 1000]
JST = ZoneInfo("Asia/Tokyo")


def combo_text(x):
    return "—" if not x else "-".join(map(str, x))


def stars(x):
    return (
        "★★★★★" if x >= .35 else
        "★★★★☆" if x >= .28 else
        "★★★☆☆" if x >= .22 else
        "★★☆☆☆" if x >= .16 else
        "★☆☆☆☆"
    )


def normalize(p):
    if isinstance(p, dict):
        return p
    if isinstance(p, tuple):
        c = p[0] if len(p) else []
        return {
            "main": c[0] if len(c) > 0 else [],
            "counter": c[1] if len(c) > 1 else [],
            "hole": c[2] if len(c) > 2 else [],
            "boat_probs": p[1] if len(p) > 1 else {},
        }
    return {
        "main": [],
        "counter": [],
        "hole": [],
        "boat_probs": {},
    }


def completed(raw):
    out = []
    stadiums = raw.get("programs", {}).get("stadiums", {})

    for sk, stadium in stadiums.items():
        try:
            sn = int(sk)
        except Exception:
            continue

        for rk, race in stadium.get("races", {}).items():
            try:
                rn = int(rk)
                order = data.get_result_order(raw, sn, rn)
                rows = data.get_race_rows(race, sn, rn)

                if order and len(order) >= 3 and len(rows) == 6:
                    out.append((sn, rn, race, order))

            except Exception:
                continue

    return sorted(out, key=lambda x: (x[1], x[0]))


def evaluate(raw, sn, rn, race, history):
    try:
        actual = data.get_result_order(raw, sn, rn)
        rows = data.get_race_rows(race, sn, rn)

        if not actual or len(rows) != 6:
            return None

        p = normalize(tri_ai(rows, history))

    except Exception:
        return None

    main = p["main"]
    counter = p["counter"]
    hole = p["hole"]
    probs = p["boat_probs"]

    actual = tuple(actual[:3])

    try:
        confidence = max(map(float, probs.values()))
    except Exception:
        confidence = 0.0

    return {
        "場": data.stadium_name(sn),
        "場番号": sn,
        "R": rn,
        "本命": combo_text(main),
        "対抗": combo_text(counter),
        "穴": combo_text(hole),
        "実結果": combo_text(actual),
        "本命的中": tuple(main[:3]) == actual,
        "対抗的中": tuple(counter[:3]) == actual,
        "穴的中": tuple(hole[:3]) == actual,
        "AI自信度": confidence,
        "評価": stars(confidence),
    }


def run_backtest(
    race_count=100,
    progress_callback=None,
    status_callback=None,
):
    results = []
    start = datetime.now(JST).date() - timedelta(days=1)

    for i in range(180):
        if len(results) >= race_count:
            break

        day = start - timedelta(days=i)
        text = day.isoformat()

        if status_callback:
            status_callback(
                len(results),
                race_count,
                f"{text} を確認中",
            )

        raw = data.get_data(text)
        if not raw:
            continue

        races = completed(raw)
        if not races:
            continue

        try:
            history = data.history14(text)
        except Exception:
            history = None

        for sn, rn, race, _ in races:
            if len(results) >= race_count:
                break

            result = evaluate(
                raw,
                sn,
                rn,
                race,
                history,
            )

            if result is None:
                continue

            result["日付"] = text
            results.append(result)

            if progress_callback:
                progress_callback(
                    len(results),
                    race_count,
                    f"{text} {data.stadium_name(sn)} {rn}Rを検証中",
                )

    if status_callback:
        status_callback(
            len(results),
            race_count,
            "検証完了",
        )

    return pd.DataFrame(results)


def summary(df):
    if df is None or df.empty:
        return 0, 0, 0, 0

    return (
        len(df),
        int(df["本命的中"].sum()),
        int(df["対抗的中"].sum()),
        int(df["穴的中"].sum()),
    )


def render_progress(current, total, status):
    pct = 0 if total <= 0 else min(current / total * 100, 100)

    st.markdown(
        f"""
        <style>
        .bt-box {{
            background: linear-gradient(180deg,#075985,#0284c7,#0369a1);
            border-radius:16px;
            padding:12px;
            margin:12px 0 18px;
            overflow:hidden;
        }}
        .bt-info {{
            background:rgba(2,24,55,.92);
            color:#fff!important;
            border-radius:12px;
            padding:10px 12px;
            text-align:center;
            position:relative;
            z-index:2;
        }}
        .bt-status {{
            color:#dbeafe!important;
            font-size:12px;
            font-weight:800;
        }}
        .bt-count {{
            color:#fff!important;
            font-size:19px;
            font-weight:950;
            margin-top:2px;
        }}
        .bt-bar {{
            height:6px;
            background:rgba(255,255,255,.25);
            border-radius:99px;
            margin-top:7px;
            overflow:hidden;
        }}
        .bt-fill {{
            width:{pct:.2f}%;
            height:100%;
            background:#fff;
            transition:width .3s;
        }}
        .bt-boats {{
            height:95px;
            position:relative;
            overflow:hidden;
        }}
        .bt-boat {{
            position:absolute;
            left:-50px;
            font-size:24px;
            animation:btmove 2.8s linear infinite;
        }}
        .b1 {{top:3px}}
        .b2 {{top:18px;animation-delay:.25s}}
        .b3 {{top:33px;animation-delay:.5s}}
        .b4 {{top:48px;animation-delay:.75s}}
        .b5 {{top:63px;animation-delay:1s}}
        .b6 {{top:78px;animation-delay:1.25s}}
        @keyframes btmove {{
            from {{left:-50px}}
            to {{left:110%}}
        }}
        </style>

        <div class="bt-box">
            <div class="bt-boats">
                <div class="bt-boat b1">🚤</div>
                <div class="bt-boat b2">🚤</div>
                <div class="bt-boat b3">🚤</div>
                <div class="bt-boat b4">🚤</div>
                <div class="bt-boat b5">🚤</div>
                <div class="bt-boat b6">🚤</div>
            </div>

            <div class="bt-info">
                <div class="bt-status">🔄 {status}</div>
                <div class="bt-count">
                    {current:,} / {total:,} レース
                </div>
                <div class="bt-bar">
                    <div class="bt-fill"></div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_backtest():
    st.markdown(
        """
        <div style="
            color:#0f172a;
            font-size:19px;
            font-weight:950;
            margin-bottom:5px;">
            📊 AIの実力を検証する
        </div>

        <div style="
            color:#334155;
            font-size:13px;
            margin-bottom:12px;">
            過去の完了レースを使ってAI予想の精度を検証します
        </div>
        """,
        unsafe_allow_html=True,
    )

    count = st.selectbox(
        "検証するレース数",
        RACE_OPTIONS,
        format_func=lambda x: f"直近{x:,}レース",
        key="backtest_race_count",
    )

    if not st.button(
        "🚀 バックテスト開始",
        type="primary",
        use_container_width=True,
        key="start_backtest",
    ):
        return

    area = st.empty()

    def update(current, total, status):
        with area.container():
            render_progress(
                current,
                total,
                status,
            )

    try:
        df = run_backtest(
            count,
            update,
            update,
        )
    except Exception as e:
        area.empty()
        st.error("バックテスト中にエラーが発生しました。")
        st.exception(e)
        return

    area.empty()

    if df.empty:
        st.error(
            "過去180日まで探しましたが、"
            "検証可能なレースを取得できませんでした。"
        )
        return

    total, main, counter, hole = summary(df)

    st.success(
        f"バックテスト完了：{total:,}レースを検証しました。"
    )

    c1, c2, c3 = st.columns(3)

    c1.metric("🎯 本命的中", f"{main:,}")
    c2.metric("🔥 対抗的中", f"{counter:,}")
    c3.metric("💥 穴的中", f"{hole:,}")

    st.markdown(
        f"""
        <div style="
            background:#fff;
            border:1px solid #dbe3ee;
            border-radius:12px;
            padding:10px 12px;
            margin-top:10px;
            color:#0f172a;">
            的中率：
            本命 {main / total * 100:.1f}%
            ／ 対抗 {counter / total * 100:.1f}%
            ／ 穴 {hole / total * 100:.1f}%
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = [
        "日付",
        "場",
        "R",
        "本命",
        "対抗",
        "穴",
        "実結果",
        "本命的中",
        "対抗的中",
        "穴的中",
        "AI自信度",
        "評価",
    ]

    st.dataframe(
        df[cols],
        use_container_width=True,
        hide_index=True,
    )
