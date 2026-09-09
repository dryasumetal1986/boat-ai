from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

import data
from ai import tri_ai


JST = ZoneInfo("Asia/Tokyo")

RACE_OPTIONS = [
    100,
    300,
    500,
    1000,
]


# =========================
# 3連単表示
# =========================

def combo(x):

    if not x:
        return "—"

    return "-".join(
        map(str, x)
    )


# =========================
# 星
# =========================

def stars(x):

    if x >= 0.35:
        return "★★★★★"

    if x >= 0.28:
        return "★★★★☆"

    if x >= 0.22:
        return "★★★☆☆"

    if x >= 0.16:
        return "★★☆☆☆"

    return "★☆☆☆☆"


# =========================
# AI結果統一
# =========================

def normalize(p):

    if isinstance(p, dict):
        return p

    if isinstance(p, tuple):

        combos = (
            p[0]
            if len(p)
            else []
        )

        return {
            "main":
                combos[0]
                if len(combos) > 0
                else [],

            "counter":
                combos[1]
                if len(combos) > 1
                else [],

            "hole":
                combos[2]
                if len(combos) > 2
                else [],

            "boat_probs":
                p[1]
                if len(p) > 1
                else {},
        }

    return {
        "main": [],
        "counter": [],
        "hole": [],
        "boat_probs": {},
    }


# =========================
# 完了レース取得
# =========================

def get_completed(raw):

    result = []

    if not isinstance(raw, dict):
        return result

    programs = raw.get(
        "programs",
        {},
    )

    stadiums = programs.get(
        "stadiums",
        {},
    )

    for sk, stadium in stadiums.items():

        try:
            sn = int(sk)
        except Exception:
            continue

        races = stadium.get(
            "races",
            {},
        )

        for rk, race in races.items():

            try:

                rn = int(rk)

                actual = data.get_result_order(
                    raw,
                    sn,
                    rn,
                )

                rows = data.get_race_rows(
                    race,
                    sn,
                    rn,
                )

                if (
                    actual
                    and len(actual) >= 3
                    and len(rows) == 6
                ):

                    result.append(
                        (
                            sn,
                            rn,
                            race,
                        )
                    )

            except Exception:
                continue

    return sorted(
        result,
        key=lambda x: (
            x[1],
            x[0],
        ),
    )


# =========================
# 1レース評価
# =========================

def evaluate(
    raw,
    sn,
    rn,
    race,
    history,
):

    try:

        actual = data.get_result_order(
            raw,
            sn,
            rn,
        )

        rows = data.get_race_rows(
            race,
            sn,
            rn,
        )

        if not actual:
            return None

        if len(rows) != 6:
            return None

        prediction = normalize(
            tri_ai(
                rows,
                history,
            )
        )

    except Exception:
        return None


    main = prediction.get(
        "main",
        [],
    )

    counter = prediction.get(
        "counter",
        [],
    )

    hole = prediction.get(
        "hole",
        [],
    )

    probs = prediction.get(
        "boat_probs",
        {},
    )


    try:

        confidence = max(
            float(v)
            for v in probs.values()
        )

    except Exception:

        confidence = 0.0


    actual = tuple(
        actual[:3]
    )


    return {
        "日付": "",
        "場": data.stadium_name(sn),
        "R": rn,
        "本命": combo(main),
        "対抗": combo(counter),
        "穴": combo(hole),
        "実結果": combo(actual),

        "本命的中":
            tuple(main[:3]) == actual,

        "対抗的中":
            tuple(counter[:3]) == actual,

        "穴的中":
            tuple(hole[:3]) == actual,

        "AI自信度":
            confidence,

        "評価":
            stars(confidence),
    }


# =========================
# 進捗表示
# =========================

def progress_view(
    current,
    total,
    status,
):

    if total <= 0:
        percent = 0
    else:
        percent = min(
            current / total * 100,
            100,
        )


    st.progress(
        percent / 100,
        text=(
            f"{current:,} / "
            f"{total:,} レース"
        ),
    )


    # =========================
    # ステータス
    # =========================

    st.html(
        f"""
        <div style="
            background:#082f49;
            color:#ffffff;
            border-radius:12px;
            padding:12px;
            text-align:center;
            margin:10px 0;
        ">

            <div style="
                color:#ffffff;
                font-size:14px;
                font-weight:900;
            ">
                🔄 {status}
            </div>

            <div style="
                color:#ffffff;
                font-size:20px;
                font-weight:950;
                margin-top:3px;
            ">
                {current:,} / {total:,} レース
            </div>

        </div>
        """
    )


    # =========================
    # ボート表示
    # =========================

    st.html(
        """
        <div style="
            background:#075985;
            border-radius:14px;
            height:105px;
            overflow:hidden;
            position:relative;
            margin-bottom:15px;
        ">

            <div style="
                position:absolute;
                left:5%;
                top:8px;
                font-size:25px;
            ">
                🚤
            </div>

            <div style="
                position:absolute;
                left:28%;
                top:27px;
                font-size:25px;
            ">
                🚤
            </div>

            <div style="
                position:absolute;
                left:51%;
                top:46px;
                font-size:25px;
            ">
                🚤
            </div>

            <div style="
                position:absolute;
                left:74%;
                top:65px;
                font-size:25px;
            ">
                🚤
            </div>

            <div style="
                position:absolute;
                left:95%;
                top:84px;
                font-size:25px;
            ">
                🚤
            </div>

        </div>
        """
    )


# =========================
# バックテスト本体
# =========================

def run_backtest(
    count,
    update,
):

    results = []


    start = (
        datetime.now(JST).date()
        - timedelta(days=1)
    )


    # 最大180日前まで
    for day_index in range(180):

        if len(results) >= count:
            break


        day = (
            start
            - timedelta(days=day_index)
        )

        date_text = day.isoformat()


        update(
            len(results),
            count,
            f"{date_text} を確認中",
        )


        try:

            raw = data.get_data(
                date_text
            )

        except Exception:

            continue


        if not raw:
            continue


        races = get_completed(
            raw
        )


        if not races:
            continue


        try:

            history = data.history14(
                date_text
            )

        except Exception:

            history = None


        for sn, rn, race in races:

            if len(results) >= count:
                break


            update(
                len(results),
                count,
                (
                    f"{date_text} "
                    f"{data.stadium_name(sn)} "
                    f"{rn}Rを検証中"
                ),
            )


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

            results.append(
                result
            )


            update(
                len(results),
                count,
                (
                    f"{date_text} "
                    f"{data.stadium_name(sn)} "
                    f"{rn}Rを検証完了"
                ),
            )


    update(
        len(results),
        count,
        "検証完了",
    )


    return pd.DataFrame(
        results
    )


# =========================
# 集計
# =========================

def summary(df):

    if df.empty:
        return 0, 0, 0, 0


    return (
        len(df),

        int(
            df["本命的中"].sum()
        ),

        int(
            df["対抗的中"].sum()
        ),

        int(
            df["穴的中"].sum()
        ),
    )


# =========================
# 画面
# =========================

def render_backtest():

    # =========================
    # 説明
    # =========================

    st.html(
        """
        <div style="
            background:#ffffff;
            border:1px solid #dbe3ee;
            border-radius:14px;
            padding:16px;
            margin-bottom:15px;
        ">

            <div style="
                color:#0f172a;
                font-size:19px;
                font-weight:950;
            ">
                📊 AIの実力を検証する
            </div>

            <div style="
                color:#334155;
                font-size:13px;
                font-weight:700;
                margin-top:5px;
            ">
                過去の完了レースを使って
                AI予想の精度を検証します
            </div>

            <div style="
                color:#475569;
                font-size:12px;
                margin-top:9px;
                line-height:1.7;
            ">
                📌 日付ではなく完了レース数で指定します。<br>
                指定した件数に達するまで、
                過去へ自動的に遡ります。
            </div>

        </div>
        """
    )


    # =========================
    # 件数
    # =========================

    count = st.selectbox(
        "検証するレース数",
        RACE_OPTIONS,
        format_func=lambda x:
            f"直近{x:,}レース",
        key="backtest_count",
    )


    # =========================
    # 開始
    # =========================

    if not st.button(
        "🚀 バックテスト開始",
        type="primary",
        use_container_width=True,
        key="backtest_start",
    ):

        return


    area = st.empty()


    # =========================
    # 更新
    # =========================

    def update(
        current,
        total,
        status,
    ):

        with area.container():

            progress_view(
                current,
                total,
                status,
            )


    # =========================
    # 実行
    # =========================

    try:

        df = run_backtest(
            count,
            update,
        )

    except Exception as e:

        area.empty()

        st.error(
            "バックテスト中にエラーが発生しました。"
        )

        st.exception(e)

        return


    area.empty()


    # =========================
    # データなし
    # =========================

    if df.empty:

        st.error(
            "過去180日まで探しましたが、"
            "検証可能なレースを取得できませんでした。"
        )

        return


    # =========================
    # 集計
    # =========================

    total, main, counter, hole = summary(
        df
    )


    st.success(
        f"バックテスト完了："
        f"{total:,}レースを検証しました。"
    )


    # =========================
    # 3つの数字
    # =========================

    c1, c2, c3 = st.columns(3)


    c1.metric(
        "🎯 本命的中",
        f"{main:,}",
    )


    c2.metric(
        "🔥 対抗的中",
        f"{counter:,}",
    )


    c3.metric(
        "💥 穴的中",
        f"{hole:,}",
    )


    # =========================
    # 的中率
    # =========================

    st.html(
        f"""
        <div style="
            background:#ffffff;
            border:1px solid #dbe3ee;
            border-radius:12px;
            padding:12px;
            margin:12px 0;
            color:#0f172a;
            font-weight:800;
        ">

            的中率：

            本命
            {main / total * 100:.1f}%

            ／ 対抗
            {counter / total * 100:.1f}%

            ／ 穴
            {hole / total * 100:.1f}%

        </div>
        """
    )


    # =========================
    # 結果一覧
    # =========================

    columns = [
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
        df[columns],
        use_container_width=True,
        hide_index=True,
        )
