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
    if x >= .35:
        return "★★★★★"
    if x >= .28:
        return "★★★★☆"
    if x >= .22:
        return "★★★☆☆"
    if x >= .16:
        return "★★☆☆☆"
    return "★☆☆☆☆"


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

    if not isinstance(raw, dict):
        return out

    stadiums = raw.get("programs", {}).get("stadiums", {})

    for sk, stadium in stadiums.items():
        try:
            sn = int(sk)
        except Exception:
            continue

        for rk, race in stadium.get("races", {}).items():
            try:
                rn = int(rk)
                result = data.get_result_order(raw, sn, rn)
                rows = data.get_race_rows(race, sn, rn)

                if result and len(result) >= 3 and len(rows) == 6:
                    out.append((sn, rn, race))

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

        main = p.get("main", [])
        counter = p.get("counter", [])
        hole = p.get("hole", [])
        probs = p.get("boat_probs", {})

        try:
            confidence = max(float(v) for v in probs.values())
        except Exception:
            confidence = 0.0

        actual = tuple(actual[:3])

        return {
            "日付": "",
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

    except Exception:
        return None


def run_backtest(race_count, update=None):
    results = []

    start = datetime.now(JST).date() - timedelta(days=1)

    for i in range(180):
        if len(results) >= race_count:
            break

        day = start - timedelta(days=i)
        date_text = day.isoformat()

        if update:
            update(
                len(results),
                race_count,
                f"{date_text} を確認中",
            )

        try:
            raw = data.get_data(date_text)
        except Exception:
            continue

        if not raw:
            continue

        races = completed(raw)

        if not races:
            continue

        try:
            history = data.history14(date_text)
        except Exception:
            history = None

        for sn, rn, race in races:

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

            result["日付"] = date_text
            results.append(result)

            if update:
                update(
                    len(results),
                    race_count,
                    f"{date_text} {data.stadium_name(sn)} {rn}Rを検証中",
                )

    if update:
        update(
            len(results),
            race_count,
            "検証完了",
        )

    return pd.DataFrame(results)


def render_progress(current, total, status):
    pct = 0 if total == 0 else min(current / total * 100, 100)

    st.markdown(
        f"""
        <div style="
            background:#075985;
            border-radius:18px;
            padding:14px;
            margin:15px 0;
            border:2px solid #0ea5e9;
            color:white;
        ">

            <div style="
                background:#082f49;
                border-radius:12px;
                padding:12px;
                text-align:center;
                color:white !important;
            ">

                <div style="
                    color:#ffffff !important;
                    font-size:14px;
                    font-weight:900;
                    margin-bottom:4px;
                ">
                    🔄 {status}
                </div>

                <div style="
                    color:#ffffff !important;
                    font-size:20px;
                    font-weight:950;
                ">
                    {current:,} / {total:,} レース
                </div>

                <div style="
                    width:100%;
                    height:8px;
                    background:#164e63;
                    border-radius:99px;
                    margin-top:9px;
                    overflow:hidden;
                ">
                    <div style="
                        width:{pct:.1f}%;
                        height:100%;
                        background:#ffffff;
                        border-radius:99px;
                    "></div>
                </div>

            </div>

            <div style="
                position:relative;
                height:125px;
                overflow:hidden;
                margin-top:8px;
            ">

                <div style="
                    position:absolute;
                    left:-70px;
                    top:5px;
                    font-size:25px;
                    animation:boatmove 3s linear infinite;
                ">🚤</div>

                <div style="
                    position:absolute;
                    left:-70px;
                    top:27px;
                    font-size:25px;
                    animation:boatmove 3s linear infinite .35s;
                ">🚤</div>

                <div style="
                    position:absolute;
                    left:-70px;
                    top:49px;
                    font-size:25px;
                    animation:boatmove 3s linear infinite .7s;
                ">🚤</div>

                <div style="
                    position:absolute;
                    left:-70px;
                    top:71px;
                    font-size:25px;
                    animation:boatmove 3s linear infinite 1.05s;
                ">🚤</div>

                <div style="
                    position:absolute;
                    left:-70px;
                    top:93px;
                    font-size:25px;
                    animation:boatmove 3s linear infinite 1.4s;
                ">🚤</div>

            </div>

        </div>

        <style>
        @keyframes boatmove {{
            0% {{
                left:-70px;
            }}
            100% {{
                left:110%;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def summary(df):
    if df.empty:
        return 0, 0, 0, 0

    return (
        len(df),
        int(df["本命的中"].sum()),
        int(df["対抗的中"].sum()),
        int(df["穴的中"].sum()),
    )


def render_backtest():

    st.markdown(
        """
        <div style="
            background:#ffffff;
            border:1px solid #dbe3ee;
            border-radius:14px;
            padding:16px;
            margin-top:20px;
        ">

            <div style="
                color:#0f172a !important;
                font-size:19px;
                font-weight:950;
            ">
                📊 AIの実力を検証する
            </div>

            <div style="
                color:#334155 !important;
                font-size:13px;
                font-weight:700;
                margin-top:5px;
            ">
                過去の完了レースを使ってAI予想の精度を検証します
            </div>

            <div style="
                color:#475569 !important;
                font-size:12px;
                margin-top:8px;
            ">
                📌 日付ではなく完了レース数で指定します。<br>
                指定した件数に達するまで、過去へ自動的に遡ります。
            </div>

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
            background:#ffffff;
            color:#0f172a !important;
            border:1px solid #dbe3ee;
            border-radius:12px;
            padding:12px;
            margin:12px 0;
            font-weight:800;
        ">
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
