import streamlit as st
import pandas as pd
from datetime import date

import data
from ai import score, tri_ai


STADIUMS = {
    1:"桐生", 2:"戸田", 3:"江戸川", 4:"平和島",
    5:"多摩川", 6:"浜名湖", 7:"蒲郡", 8:"常滑",
    9:"津", 10:"三国", 11:"びわこ", 12:"住之江",
    13:"尼崎", 14:"鳴門", 15:"丸亀", 16:"児島",
    17:"宮島", 18:"徳山", 19:"下関", 20:"若松",
    21:"芦屋", 22:"福岡", 23:"唐津", 24:"大村"
}


st.set_page_config(
    page_title="競艇AI予想",
    layout="wide"
)


st.title("🚤 やっちゃんのAI予想PRO")


# =========================================================
# 条件
# =========================================================

c1, c2, c3 = st.columns(3)

with c1:
    td = st.date_input(
        "開催日",
        value=date.today()
    )

with c2:
    sno = st.selectbox(
        "競艇場",
        list(STADIUMS.keys()),
        format_func=lambda x: STADIUMS[x]
    )

with c3:
    rno = st.selectbox(
        "レース",
        range(1, 13),
        format_func=lambda x: f"{x}R"
    )


# =========================================================
# 予想
# =========================================================

if st.button(
    "🚤 AI予想を実行",
    type="primary"
):

    try:

        with st.spinner("データ取得中..."):

            raw = data.get_data(td)

            race = data.get_race(
                raw,
                sno,
                rno
            )

            if race is None:
                st.error(
                    "指定したレースのデータが見つかりません。"
                )
                st.stop()

            rows = data.get_race_rows(
                race,
                sno,
                rno,
                td
            )

            if not rows:
                st.error(
                    "選手データを取得できませんでした。"
                )
                st.stop()

            df = pd.DataFrame(rows)

            df["学習AI"] = df.apply(
                score,
                axis=1
            )

            # 過去データ
            history = pd.DataFrame(
                data.history14(td)
            )

            result, boat_probs = tri_ai(
                df,
                history
            )


    except Exception as e:

        st.error(
            f"エラー：{e}"
        )

        st.stop()


    # =====================================================
    # 選手データ
    # =====================================================

    st.subheader("📋 選手データ")

    cols = [
        "枠",
        "選手名",
        "級別",
        "全国勝率",
        "全国2連率",
        "当地勝率",
        "モーター2連率",
        "平均ST",
        "展示進入",
        "展示ST",
        "展示タイム",
        "学習AI"
    ]

    cols = [
        c for c in cols
        if c in df.columns
    ]

    st.dataframe(
        df[cols],
        use_container_width=True,
        hide_index=True
    )


    # =====================================================
    # データ取得状況
    # =====================================================

    st.subheader("🔎 データ取得状況")

    check = pd.DataFrame({
        "項目": [
            "全国勝率",
            "全国2連率",
            "当地勝率",
            "モーター2連率",
            "平均ST",
            "展示ST",
            "展示タイム"
        ],
        "取得数": [
            int((df["全国勝率"] > 0).sum()),
            int((df["全国2連率"] > 0).sum()),
            int((df["当地勝率"] > 0).sum()),
            int((df["モーター2連率"] > 0).sum()),
            int((df["平均ST"] > 0).sum()),
            int((df["展示ST"] > 0).sum()),
            int((df["展示タイム"] > 0).sum())
        ]
    })

    st.dataframe(
        check,
        use_container_width=True,
        hide_index=True
    )


    # =====================================================
    # AI予想
    # =====================================================

    st.subheader("🤖 3連単AI予想")

    st.dataframe(
        result,
        use_container_width=True,
        hide_index=True
    )


    # =====================================================
    # 上位予想
    # =====================================================

    st.subheader("🏆 AI上位5点")

    st.dataframe(
        result.head(5),
        use_container_width=True,
        hide_index=True
    )


    # =====================================================
    # 枠別AI確率
    # =====================================================

    st.subheader("📊 1着AI確率")

    prob_df = pd.DataFrame({
        "枠": list(range(1, 7)),
        "AI確率": [
            boat_probs.get(i, 0) * 100
            for i in range(1, 7)
        ]
    })

    prob_df["AI確率"] = (
        prob_df["AI確率"]
        .round(1)
    )

    st.bar_chart(
        prob_df.set_index("枠")
    )


    st.success(
        "AI予想が完了しました。"
    )
