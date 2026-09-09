import streamlit as st
import pandas as pd
from datetime import date

import data
from ai import score, tri_ai


# =========================
# 会場一覧
# =========================
STADIUMS = {
    1: "桐生",
    2: "戸田",
    3: "江戸川",
    4: "平和島",
    5: "多摩川",
    6: "浜名湖",
    7: "蒲郡",
    8: "常滑",
    9: "津",
    10: "三国",
    11: "びわこ",
    12: "住之江",
    13: "尼崎",
    14: "鳴門",
    15: "丸亀",
    16: "児島",
    17: "宮島",
    18: "徳山",
    19: "下関",
    20: "若松",
    21: "芦屋",
    22: "福岡",
    23: "唐津",
    24: "大村",
}


# =========================
# ページ設定
# =========================
st.set_page_config(
    page_title="競艇AI予想",
    page_icon="🚤",
    layout="wide",
)

st.title("🚤 競艇AI予想")


# =========================
# 入力
# =========================
col1, col2, col3 = st.columns(3)

with col1:
    td = st.date_input(
        "開催日",
        value=date.today(),
    )

with col2:
    stadium_no = st.selectbox(
        "競艇場",
        options=list(STADIUMS.keys()),
        format_func=lambda x: f"{x} - {STADIUMS[x]}",
    )

with col3:
    race_no = st.selectbox(
        "レース",
        options=list(range(1, 13)),
        format_func=lambda x: f"{x}R",
    )


# =========================
# AI予想
# =========================
if st.button("🤖 AI予想を実行", type="primary", use_container_width=True):

    with st.spinner("レースデータを取得しています..."):

        # ---------------------------------
        # データ取得
        # ---------------------------------
        try:
            all_data = data.get_data(td)
        except Exception as e:
            st.error(f"データ取得に失敗しました。\n\n{e}")
            st.stop()

        race = data.get_race(
            all_data,
            stadium_no,
            race_no,
        )

        if race is None:
            st.error("指定したレースのデータが見つかりません。")
            st.stop()

        # ---------------------------------
        # 選手データ
        # ---------------------------------
        racers = data.racers(
            race.get("racers")
            or race.get("entries")
            or race.get("entry")
            or []
        )

        if not racers:
            st.error("選手データが取得できませんでした。")
            st.stop()

        # ---------------------------------
        # 展示データ
        # ---------------------------------
        preview = (
            race.get("preview")
            or race.get("exhibition")
            or []
        )

        preview_list = data.racers(preview)

        preview_map = {}

        for p in preview_list:

            try:
                player_no = p.get(
                    "racerNumber",
                    p.get(
                        "playerNumber",
                        p.get(
                            "number",
                            p.get("選手番号")
                        )
                    ),
                )

                if player_no is None:
                    continue

                player_no = int(float(player_no))

                preview_map[player_no] = p

            except Exception:
                continue

        # ---------------------------------
        # AI用データ作成
        # ---------------------------------
        rows = []

        for i, r in enumerate(racers):

            lane = r.get(
                "entryNumber",
                r.get(
                    "boatNumber",
                    r.get(
                        "courseNumber",
                        r.get(
                            "枠",
                            r.get("lane", i + 1)
                        )
                    )
                ),
            )

            try:
                lane = int(float(lane))
            except Exception:
                lane = i + 1

            player_no = r.get(
                "racerNumber",
                r.get(
                    "playerNumber",
                    r.get(
                        "number",
                        r.get("選手番号")
                    )
                ),
            )

            try:
                player_no = int(float(player_no))
            except Exception:
                player_no = 0

            p = preview_map.get(player_no, {})

            # -----------------------------
            # 選手名
            # -----------------------------
            name = r.get(
                "racerName",
                r.get(
                    "name",
                    r.get(
                        "選手名",
                        "-"
                    )
                ),
            )

            # -----------------------------
            # 級別
            # -----------------------------
            grade = r.get(
                "grade",
                r.get(
                    "class",
                    r.get(
                        "級別",
                        "-"
                    )
                ),
            )

            # -----------------------------
            # 全国勝率
            # -----------------------------
            nationwide_win = r.get(
                "nationwideWinRate",
                r.get(
                    "nationalWinRate",
                    r.get(
                        "winRate",
                        r.get(
                            "全国勝率",
                            0
                        )
                    )
                ),
            )

            # -----------------------------
            # 全国2連率
            # -----------------------------
            nationwide_2 = r.get(
                "nationwide2Rate",
                r.get(
                    "national2Rate",
                    r.get(
                        "secondRate",
                        r.get(
                            "全国2連率",
                            0
                        )
                    )
                ),
            )

            # -----------------------------
            # 当地勝率
            # -----------------------------
            local_win = r.get(
                "localWinRate",
                r.get(
                    "localRate",
                    r.get(
                        "当地勝率",
                        0
                    )
                ),
            )

            # -----------------------------
            # モーター2連率
            # -----------------------------
            motor_2 = r.get(
                "motor2Rate",
                r.get(
                    "motorSecondRate",
                    r.get(
                        "モーター2連率",
                        0
                    )
                ),
            )

            # -----------------------------
            # 平均ST
            # -----------------------------
            avg_st = r.get(
                "averageST",
                r.get(
                    "avgST",
                    r.get(
                        "averageStartTiming",
                        r.get(
                            "平均ST",
                            0
                        )
                    )
                ),
            )

            # -----------------------------
            # 展示ST
            # -----------------------------
            exhibition_st = p.get(
                "startTiming",
                p.get(
                    "exhibitionST",
                    p.get(
                        "st",
                        p.get(
                            "展示ST",
                            0
                        )
                    )
                ),
            )

            # -----------------------------
            # 展示タイム
            # -----------------------------
            exhibition_time = p.get(
                "exhibitionTime",
                p.get(
                    "time",
                    p.get(
                        "展示タイム",
                        0
                    )
                ),
            )

            # -----------------------------
            # 展示進入
            # -----------------------------
            exhibition_course = p.get(
                "courseNumber",
                p.get(
                    "entryNumber",
                    p.get(
                        "course",
                        lane
                    )
                ),
            )

            # -----------------------------
            # 数値変換
            # -----------------------------
            def to_float(value):

                try:
                    if value is None:
                        return 0.0

                    return float(
                        str(value)
                        .replace(",", "")
                        .replace("%", "")
                        .strip()
                    )

                except Exception:
                    return 0.0

            rows.append(
                {
                    "枠": lane,
                    "展示進入": to_float(exhibition_course),
                    "選手名": name,
                    "選手番号": player_no,
                    "級別": grade,
                    "全国勝率": to_float(nationwide_win),
                    "全国2連率": to_float(nationwide_2),
                    "当地勝率": to_float(local_win),
                    "モーター2連率": to_float(motor_2),
                    "平均ST": to_float(avg_st),
                    "展示ST": to_float(exhibition_st),
                    "展示タイム": to_float(exhibition_time),
                    "場": stadium_no,
                }
            )

        df = pd.DataFrame(rows)

        if df.empty:
            st.error("AI計算用のデータが作成できませんでした。")
            st.stop()

        # ---------------------------------
        # 従来スコア
        # ---------------------------------
        df["学習AI"] = df.apply(score, axis=1)

        # ---------------------------------
        # 過去データ取得
        # ---------------------------------
        with st.spinner("過去レースデータを読み込んでAIを学習しています..."):

            try:
                history = pd.DataFrame(
                    data.history14(td)
                )
            except Exception as e:
                st.warning(
                    f"過去データの取得に失敗したため、現在のデータのみで予想します。\n\n{e}"
                )
                history = pd.DataFrame()

        # ---------------------------------
        # AI予想
        # ---------------------------------
        with st.spinner("AIが3連単を計算しています..."):

            try:
                result = tri_ai(
                    df,
                    history
                )

            except Exception as e:
                st.error(
                    f"AI予想の計算中にエラーが発生しました。\n\n{e}"
                )
                st.stop()

    # =========================================================
    # 選手評価
    # =========================================================
    st.subheader("👤 選手評価")

    racer_display = df[
        [
            "枠",
            "選手名",
            "選手番号",
            "級別",
            "全国勝率",
            "全国2連率",
            "当地勝率",
            "モーター2連率",
            "平均ST",
            "展示ST",
            "展示タイム",
            "学習AI",
        ]
    ].copy()

    racer_display = racer_display.sort_values(
        "学習AI",
        ascending=False
    )

    st.dataframe(
        racer_display,
        use_container_width=True,
        hide_index=True,
    )

    # =========================================================
    # AI予想ランキング
    # =========================================================
    st.subheader("🏆 AI 3連単予想")

    if result is None or result.empty:

        st.warning("AI予想結果がありません。")

    else:

        result_display = result.copy()

        # 表示用に小数点を整理
        for col in [
            "AI確率",
            "信頼度",
            "1着AI",
            "2着AI",
            "3着AI",
        ]:

            if col in result_display.columns:

                result_display[col] = pd.to_numeric(
                    result_display[col],
                    errors="coerce"
                ).round(2)

        st.dataframe(
            result_display.head(10),
            use_container_width=True,
            hide_index=True,
        )

        # =====================================================
        # 本命
        # =====================================================
        best = result.iloc[0]

        st.success(
            f"🥇 本命：{best['3連単']}"
        )

        st.write(
            f"AI確率：**{float(best['AI確率']):.2f}%**"
        )

        if "信頼度" in best:

            st.write(
                f"信頼度：**{float(best['信頼度']):.2f}**"
            )

        # =====================================================
        # 2番手・3番手
        # =====================================================
        if len(result) >= 2:

            second = result.iloc[1]

            st.info(
                f"🥈 2番手：{second['3連単']} "
                f"（AI確率 {float(second['AI確率']):.2f}%）"
            )

        if len(result) >= 3:

            third = result.iloc[2]

            st.info(
                f"🥉 3番手：{third['3連単']} "
                f"（AI確率 {float(third['AI確率']):.2f}%）"
            )

    # =========================================================
    # 各着順のAI評価
    # =========================================================
    st.subheader("🏆 各着順のAI評価")

    place_rows = []

    for lane in sorted(df["枠"].unique()):

        lane = int(lane)

        # ---------------------------------------------
        # 1着になる組み合わせ
        # 例：1-2-3、1-3-2、1-4-2 ...
        # ---------------------------------------------
        first = result[
            result["3連単"].astype(str).str.startswith(
                f"{lane}-"
            )
        ]["1着AI"]

        # ---------------------------------------------
        # 2着になる組み合わせ
        # 例：2-1-3、3-1-2、4-1-3 ...
        # ---------------------------------------------
        second = result[
            result["3連単"].astype(str).str.contains(
                f"-{lane}-"
            )
        ]["2着AI"]

        # ---------------------------------------------
        # 3着になる組み合わせ
        # 例：2-3-1、4-5-1 ...
        # ---------------------------------------------
        third = result[
            result["3連単"].astype(str).str.endswith(
                f"-{lane}"
            )
        ]["3着AI"]

        first_ai = (
            float(first.max())
            if not first.empty
            else 0
        )

        second_ai = (
            float(second.max())
            if not second.empty
            else 0
        )

        third_ai = (
            float(third.max())
            if not third.empty
            else 0
        )

        racer = df[
            df["枠"] == lane
        ]

        if racer.empty:
            continue

        racer = racer.iloc[0]

        place_rows.append(
            {
                "枠": lane,
                "選手名": racer.get(
                    "選手名",
                    "-"
                ),
                "選手番号": racer.get(
                    "選手番号",
                    "-"
                ),
                "1着AI": round(
                    first_ai,
                    2
                ),
                "2着AI": round(
                    second_ai,
                    2
                ),
                "3着AI": round(
                    third_ai,
                    2
                ),
            }
        )

    place_df = pd.DataFrame(
        place_rows
    )

    st.dataframe(
        place_df,
        use_container_width=True,
        hide_index=True,
    )


# =============================================================
# 過去レース検証
# =============================================================
st.divider()

st.subheader("📊 過去レース検証")

if st.button(
    "過去14日を検証",
    use_container_width=True
):

    with st.spinner(
        "過去14日分のレース結果を取得しています..."
    ):

        try:

            backtest = data.backtest_races(
                td,
                14
            )

        except Exception as e:

            st.error(
                f"過去レース検証でエラーが発生しました。\n\n{e}"
            )

            st.stop()

    if not backtest:

        st.warning(
            "過去レースのデータがありません。"
        )

    else:

        backtest_df = pd.DataFrame(
            backtest
        )

        st.dataframe(
            backtest_df,
            use_container_width=True,
            hide_index=True,
        )
