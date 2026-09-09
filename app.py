import streamlit as st
import pandas as pd

import data
from ai import score, tri_ai


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


st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO",
    layout="wide",
)

st.title("🚤 やっちゃんの競艇AI予想 PRO")
st.caption("AIスコア＋過去成績＋展示データによる3連単予想")


td = st.date_input(
    "開催日",
)

sno = st.selectbox(
    "競艇場",
    list(STADIUMS.keys()),
    format_func=lambda x: f"{x} {STADIUMS[x]}",
)

rno = st.selectbox(
    "レース",
    list(range(1, 13)),
)


if st.button("🔮 AI予想を計算", type="primary"):

    with st.spinner("データ取得中..."):

        try:
            all_data = data.get_data(td)
        except Exception as e:
            st.error("データ取得に失敗しました。")
            st.exception(e)
            st.stop()

        race = data.get_race(
            all_data,
            sno,
            rno,
        )

        if not race:
            st.error("このレースのデータがありません。")
            st.stop()

        racers_data = race.get(
            "racers",
            {},
        )

        preview_data = race.get(
            "preview",
            {},
        )

        if isinstance(racers_data, dict):
            racers_list = list(
                racers_data.values()
            )
        else:
            racers_list = racers_data

        if isinstance(preview_data, dict):
            preview_list = list(
                preview_data.values()
            )
        else:
            preview_list = preview_data

        preview_map = {}

        for p in preview_list:

            entry = str(
                p.get(
                    "entry_number",
                    "",
                )
            )

            course = p.get(
                "course_number",
                "",
            )

            preview_map[entry] = {
                "展示ST": p.get(
                    "start_timing",
                    0,
                ),
                "展示タイム": p.get(
                    "exhibition_time",
                    0,
                ),
                "展示進入": course,
            }


        rows = []

        for r in racers_list:

            lane = int(
                r.get(
                    "entry_number",
                    0,
                )
            )

            number = str(
                r.get(
                    "number",
                    "",
                )
            )

            p = preview_map.get(
                str(lane),
                {},
            )

            rows.append(
                {
                    "枠": lane,
                    "展示進入": p.get(
                        "展示進入",
                        lane,
                    ),
                    "選手名": r.get(
                        "name",
                        "",
                    ),
                    "選手番号": number,
                    "級別": r.get(
                        "rank_number",
                        "",
                    ),
                    "全国勝率": float(
                        r.get(
                            "national_win_rate",
                            0,
                        ) or 0
                    ),
                    "全国2連率": float(
                        r.get(
                            "national_top_2_percent",
                            0,
                        ) or 0
                    ),
                    "当地勝率": float(
                        r.get(
                            "local_win_rate",
                            0,
                        ) or 0
                    ),
                    "モーター2連率": float(
                        r.get(
                            "motor_top_2_percent",
                            0,
                        ) or 0
                    ),
                    "平均ST": float(
                        r.get(
                            "average_start_timing",
                            0,
                        ) or 0
                    ),
                    "展示ST": float(
                        p.get(
                            "展示ST",
                            0,
                        ) or 0
                    ),
                    "展示タイム": float(
                        p.get(
                            "展示タイム",
                            0,
                        ) or 0
                    ),
                }
            )


        df = pd.DataFrame(rows)

        if df.empty:
            st.error("選手データが取得できませんでした。")
            st.stop()


        df["学習AI"] = df.apply(
            score,
            axis=1,
        )


        history = pd.DataFrame(
            data.history14(td)
        )


        result = tri_ai(
            df,
            history,
        )


        if result.empty:
            st.error(
                "3連単予想を作成できませんでした。"
            )
            st.stop()


        st.subheader(
            f"🏁 {STADIUMS[sno]} {rno}R"
        )


        st.dataframe(
            df.sort_values(
                "学習AI",
                ascending=False,
            ),
            use_container_width=True,
            hide_index=True,
        )


        st.subheader("🎯 AI 3連単 TOP10")

        st.dataframe(
            result.head(10),
            use_container_width=True,
            hide_index=True,
        )


        best = result.iloc[0]

        st.success(
            f"🔥 本命：{best['3連単']}  "
            f"AIスコア {best['AIスコア']}"
        )


        second = result.iloc[1]

        st.info(
            f"🥈 対抗：{second['3連単']}  "
            f"AIスコア {second['AIスコア']}"
        )


        third = result.iloc[2]

        st.info(
            f"🥉 穴候補：{third['3連単']}  "
            f"AIスコア {third['AIスコア']}"
)
st.divider()

st.subheader("📊 過去レース検証")

if st.button("過去14日を検証"):

    with st.spinner("過去レースを取得中..."):

        bt = data.backtest_races(
            td,
            14,
        )

    if not bt:
        st.warning(
            "過去レースデータがありません。"
        )
    else:
        bt_df = pd.DataFrame(bt)

        st.write(
            f"検証レース数：{len(bt_df)}"
        )

        st.dataframe(
            bt_df,
            use_container_width=True,
            hide_index=True,
        )
