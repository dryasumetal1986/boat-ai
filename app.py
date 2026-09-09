import streamlit as st
import pandas as pd

import data
from ai import tri_ai


# =========================================================
# ページ設定
# =========================================================

st.set_page_config(
    page_title="やっちゃんのAI予想PRO",
    page_icon="🚤",
    layout="wide",
)


# =========================================================
# タイトル
# =========================================================

st.title("🚤 やっちゃんのAI予想PRO")
st.caption(
    "出走表・直前情報・過去データを使ったAI予想"
)


# =========================================================
# 日付
# =========================================================

today = pd.Timestamp.now().date()

target_date = st.date_input(
    "開催日",
    value=today,
)


# =========================================================
# 場・R選択
# =========================================================

col1, col2 = st.columns(2)

with col1:

    stadium_options = {
        f"{no:02d} {name}": no
        for no, name in data.STADIUMS.items()
    }

    selected_stadium = st.selectbox(
        "レース場",
        list(stadium_options.keys()),
    )

    stadium_no = stadium_options[
        selected_stadium
    ]

with col2:

    race_no = st.selectbox(
        "レース",
        list(range(1, 13)),
        format_func=lambda x: f"{x}R",
    )


# =========================================================
# 予想開始
# =========================================================

if st.button(
    "🚤 このレースをAI予想",
    type="primary",
    use_container_width=True,
):

    # -----------------------------------------------------
    # API取得
    # -----------------------------------------------------

    try:

        raw = data.get_data(
            target_date
        )

    except Exception as e:

        st.error(
            "開催日のデータを取得できませんでした。"
        )

        st.code(
            str(e)
        )

        st.stop()

    # -----------------------------------------------------
    # 指定場・指定Rを取得
    # -----------------------------------------------------

    try:

        race = data.get_race(
            raw,
            stadium_no,
            race_no,
        )

    except Exception as e:

        st.error(
            "指定したレースのデータが見つかりません。"
        )

        st.warning(
            f"{data.stadium_name(stadium_no)} "
            f"{race_no}R"
        )

        st.code(
            str(e)
        )

        st.stop()

    # -----------------------------------------------------
    # 最終検証
    # -----------------------------------------------------

    valid, message = data.validate_race(
        race,
        stadium_no,
        race_no,
        target_date,
    )

    if not valid:

        st.error(
            "レースデータの整合性チェックに失敗しました。"
        )

        st.code(
            message
        )

        st.stop()

    # -----------------------------------------------------
    # 6選手をDataFrame化
    # -----------------------------------------------------

    try:

        df = data.get_race_rows(
            race,
            stadium_no,
            race_no,
            target_date,
        )

    except Exception as e:

        st.error(
            "出走選手データの作成に失敗しました。"
        )

        st.code(
            str(e)
        )

        st.stop()

    # -----------------------------------------------------
    # 6艇最終チェック
    # -----------------------------------------------------

    if len(df) != 6:

        st.error(
            f"出走選手が6人ではありません。取得={len(df)}"
        )

        st.stop()

    # =====================================================
    # 選択レース確認
    # =====================================================

    st.success(
        f"✅ {target_date} "
        f"{data.stadium_name(stadium_no)} "
        f"{race_no}R を正しく取得しました"
    )

    # -----------------------------------------------------
    # 取得確認
    # -----------------------------------------------------

    check_col1, check_col2, check_col3 = st.columns(3)

    with check_col1:
        st.metric(
            "場",
            data.stadium_name(stadium_no),
        )

    with check_col2:
        st.metric(
            "レース",
            f"{race_no}R",
        )

    with check_col3:
        st.metric(
            "出走艇数",
            f"{len(df)}艇",
        )

    # =====================================================
    # 出走選手
    # =====================================================

    st.subheader("🚤 出走選手")

    display_df = df[
        [
            "枠",
            "選手名",
            "展示進入",
            "全国勝率",
            "全国2連率",
            "当地勝率",
            "当地2連率",
            "モーター2連率",
            "平均ST",
            "展示ST",
            "展示タイム",
        ]
    ].copy()

    display_df = display_df.rename(
        columns={
            "枠": "艇",
            "選手名": "選手",
            "展示進入": "進入",
            "全国勝率": "全国勝率",
            "全国2連率": "全国2連率%",
            "当地勝率": "当地勝率",
            "当地2連率": "当地2連率%",
            "モーター2連率": "モーター2連率%",
            "平均ST": "平均ST",
            "展示ST": "展示ST",
            "展示タイム": "展示タイム",
        }
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

    # =====================================================
    # 過去データ
    # =====================================================

    with st.spinner(
        "過去データを読み込んでAIを学習しています..."
    ):

        try:

            history = data.history14(
                target_date
            )

        except Exception:

            history = pd.DataFrame()

    # =====================================================
    # AI予想
    # =====================================================

    try:

        result, boat_probs = tri_ai(
            df,
            history,
        )

    except Exception as e:

        st.error(
            "AI予想の計算中にエラーが発生しました。"
        )

        st.code(
            str(e)
        )

        st.stop()

    # =====================================================
    # 本命
    # =====================================================

    st.subheader("🎯 AI本命")

    best = result.iloc[0]

    st.markdown(
        f"""
        ## 🚤 {best["買い目"]}
        ### AI確率 {best["確率"]:.2f}%
        """
    )

    # =====================================================
    # 3連単ランキング
    # =====================================================

    st.subheader("🏆 AI 3連単ランキング")

    top5 = result.head(5).copy()

    top5["確率"] = top5[
        "確率"
    ].map(
        lambda x: f"{x:.2f}%"
    )

    top5 = top5[
        [
            "順位",
            "買い目",
            "確率",
        ]
    ]

    st.dataframe(
        top5,
        use_container_width=True,
        hide_index=True,
    )

    # =====================================================
    # 1着確率
    # =====================================================

    st.subheader("📊 各艇の1着確率")

    prob_display = boat_probs.copy()

    prob_display["1着確率"] = (
        prob_display["1着確率"]
        .map(lambda x: f"{x:.2f}%")
    )

    prob_display["AIスコア"] = (
        prob_display["AIスコア"]
        .map(lambda x: f"{x:.2f}")
    )

    prob_display = prob_display.rename(
        columns={
            "枠": "艇",
            "選手名": "選手",
        }
    )

    st.dataframe(
        prob_display[
            [
                "艇",
                "選手",
                "1着確率",
                "AIスコア",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    # =====================================================
    # グラフ
    # =====================================================

    chart_df = boat_probs[
        [
            "枠",
            "1着確率",
        ]
    ].copy()

    chart_df = chart_df.set_index(
        "枠"
    )

    st.bar_chart(
        chart_df
    )

    # =====================================================
    # データ取得確認
    # =====================================================

    st.subheader("🔍 データ取得確認")

    check = pd.DataFrame(
        [
            {
                "項目": "開催日",
                "値": str(target_date),
            },
            {
                "項目": "場",
                "値": (
                    f"{stadium_no:02d} "
                    f"{data.stadium_name(stadium_no)}"
                ),
            },
            {
                "項目": "レース",
                "値": f"{race_no}R",
            },
            {
                "項目": "API場番号",
                "値": str(
                    race.get(
                        "stadium_number"
                    )
                ),
            },
            {
                "項目": "APIレース番号",
                "値": str(
                    race.get(
                        "race_number"
                    )
                ),
            },
            {
                "項目": "API開催日",
                "値": str(
                    race.get(
                        "date"
                    )
                ),
            },
            {
                "項目": "選手数",
                "値": str(
                    len(df)
                ),
            },
        ]
    )

    st.dataframe(
        check,
        use_container_width=True,
        hide_index=True,
    )

    # =====================================================
    # 注意
    # =====================================================

    st.caption(
        "※ AI確率は予測モデルによる参考値です。"
    )
