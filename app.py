import streamlit as st
from datetime import date, timedelta

import data
from ai import predict
from backtest import run_backtest


# =========================================================
# ページ設定
# =========================================================

st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO",
    page_icon="🎯",
    layout="centered"
)


# =========================================================
# デザイン
# =========================================================

st.markdown("""
<style>
.block-container{
    padding-top:1.2rem;
    max-width:900px;
}
h1{
    font-size:2.4rem;
}
.ticket{
    padding:12px 14px;
    border:1px solid #444;
    border-radius:10px;
    margin:8px 0;
}
.big{
    font-size:1.55rem;
    font-weight:700;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# 起動時の初期化
# =========================================================
#
# 新しいStreamlitセッションで最初に1回だけ実行。
# 前回の開催場・レース・日付などを引き継がず、
# 毎回「初期状態」からスタートする。
#
# =========================================================

if "app_initialized" not in st.session_state:

    # 既存セッションに残っている選択状態を削除
    st.session_state.pop("race_day", None)
    st.session_state.pop("venue", None)
    st.session_state.pop("race", None)
    st.session_state.pop("bt_day", None)

    # 初期値
    today = date.today()

    st.session_state["race_day"] = today
    st.session_state["venue"] = "選択してください"
    st.session_state["race"] = "選択してください"
    st.session_state["bt_day"] = today - timedelta(days=1)

    # バックテスト件数も初期化
    st.session_state["count"] = 100

    # 初期化済みフラグ
    st.session_state["app_initialized"] = True


today = date.today()


# =========================================================
# タイトル
# =========================================================

st.title("やっちゃんの競艇AI予想 PRO")
st.caption("AI的中率重視 × 実データ × 3連単3点")


# =========================================================
# AI予想
# =========================================================

st.header("🎯 AI予想")


# ---------------------------------------------------------
# 開催日
# ---------------------------------------------------------

race_day = st.date_input(
    "開催日",
    value=st.session_state["race_day"],
    max_value=today,
    key="race_day"
)


# ---------------------------------------------------------
# 開催場
# ---------------------------------------------------------

venue_names = [
    "選択してください"
] + list(data.STADIUM_BY_NAME.keys())

venue_name = st.selectbox(
    "開催場",
    venue_names,
    key="venue"
)


# ---------------------------------------------------------
# レース
# ---------------------------------------------------------

if venue_name != "選択してください":

    venue_no = data.STADIUM_BY_NAME[venue_name]

    try:
        race_numbers = data.get_races_for_stadium(
            race_day,
            venue_no
        )

    except Exception as e:
        race_numbers = []

        st.error(
            f"出走表データの取得に失敗しました。\n\n{e}"
        )

    race_options = [
        "選択してください"
    ] + [str(x) for x in race_numbers]

else:

    venue_no = None

    race_options = [
        "選択してください"
    ]


race_choice = st.selectbox(
    "レース",
    race_options,
    key="race"
)


# =========================================================
# AI予想実行
# =========================================================

if st.button(
    "🎯 AI予想を実行",
    use_container_width=True
):

    if venue_no is None or race_choice == "選択してください":

        st.warning(
            "開催場とレースを選択してください。"
        )

    else:

        with st.spinner(
            "出走表・直前情報を取得してAI予想を計算しています…"
        ):

            try:

                race_no = int(race_choice)

                race = data.get_race(
                    race_day,
                    venue_no,
                    race_no
                )

                df = data.race_to_df(race)

                if df.empty or len(df) != 6:
                    raise ValueError(
                        "6艇分の出走表データを正しく取得できませんでした。"
                    )

                if set(df["boat"].astype(int)) != set(range(1, 7)):
                    raise ValueError(
                        "艇番が1〜6として取得できていません。"
                    )

                pred = predict(df)

            except Exception as e:

                st.error(
                    "出走表データが正しく取得できませんでした。\n\n"
                    f"{e}"
                )

            else:

                # -------------------------------------------------
                # レース情報
                # -------------------------------------------------

                st.success(
                    f"{race_day:%Y年%m月%d日} "
                    f"{venue_name}{race_no}R"
                )

                st.metric(
                    "AI最有力軸",
                    f"{pred['axis']}号艇",
                    f"信頼度 {pred['confidence']:.1f}%"
                )

                st.caption(
                    "※艇番は1〜6号艇で統一しています。"
                    "選手登録番号・モーター番号・ボート番号は"
                    "艇番として使いません。"
                )


                # -------------------------------------------------
                # 3連単3点
                # -------------------------------------------------

                for ticket in pred["tickets"]:

                    combo = "-".join(
                        map(str, ticket["combo"])
                    )

                    st.markdown(
                        f"""
                        <div class="ticket">
                            <b>{ticket["label"]}</b>
                            <span class="big">{combo}</span><br>
                            AI確率 {ticket["prob"] * 100:.2f}%
                        </div>
                        """,
                        unsafe_allow_html=True
                    )


                # -------------------------------------------------
                # 出走表
                # -------------------------------------------------

                with st.expander("出走表を確認"):

                    cols = [
                        "boat",
                        "name",
                        "racer_number",
                        "national_win_rate",
                        "local_win_rate",
                        "motor_top_2_percent",
                        "boat_top_2_percent",
                        "course_number",
                        "exhibition_time",
                        "start_timing"
                    ]

                    show = df[cols].copy()

                    show.columns = [
                        "艇番",
                        "選手",
                        "登録番号",
                        "全国勝率",
                        "当地勝率",
                        "モーター2連率",
                        "ボート2連率",
                        "進入",
                        "展示",
                        "ST"
                    ]

                    st.dataframe(
                        show,
                        hide_index=True,
                        use_container_width=True
                    )


                # -------------------------------------------------
                # オッズ
                # -------------------------------------------------

                st.info(
                    "公式オッズは現在のv1データに含まれないため、"
                    "この版ではAI確率のみ表示しています。"
                )


# =========================================================
# 区切り
# =========================================================

st.divider()


# =========================================================
# バックテスト
# =========================================================

st.header("📈 バックテスト")


# ---------------------------------------------------------
# バックテスト日
# ---------------------------------------------------------

bt_default = today - timedelta(days=1)

bt_day = st.date_input(
    "バックテスト日",
    value=st.session_state["bt_day"],
    max_value=bt_default,
    key="bt_day"
)


# ---------------------------------------------------------
# 検証レース数
# ---------------------------------------------------------

count = st.selectbox(
    "検証レース数",
    [100, 200, 300, 500, 1000],
    index=0,
    key="count"
)


st.caption(
    "昨日を起点に、必要なレース数に達するまで"
    "過去へ自動的に遡ります。全24場を対象にします。"
)


# =========================================================
# バックテスト開始
# =========================================================

if st.button(
    "🚀 バックテスト開始",
    use_container_width=True
):

    progress_bar = st.progress(0)
    status = st.empty()


    def progress(
        day_no,
        max_days,
        found,
        current_day
    ):

        progress_bar.progress(
            min(day_no / max_days, 1.0)
        )

        status.write(
            f"全24場の過去レースを解析しています… "
            f"{found}/{count}件 / {current_day}"
        )


    try:

        summary, rows = run_backtest(
            bt_day,
            count,
            progress=progress
        )

    except Exception as e:

        status.empty()

        st.error(
            f"バックテストに失敗しました: {e}"
        )

    else:

        progress_bar.progress(1.0)
        status.empty()


        if not rows:

            st.error(
                "有効な結果データを1レースも取得できませんでした。"
                "API接続または日付を確認してください。"
            )

        else:

            # -------------------------------------------------
            # 結果タイトル
            # -------------------------------------------------

            st.subheader(
                f"検証結果：{summary['検証数']}レース"
            )


            # -------------------------------------------------
            # 基本的中率
            # -------------------------------------------------

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "3点的中率",
                f"{summary['3点的中率']:.1f}%"
            )

            c2.metric(
                "軸1着率",
                f"{summary['軸1着率']:.1f}%"
            )

            c3.metric(
                "軸3着内率",
                f"{summary['軸3着内率']:.1f}%"
            )


            # -------------------------------------------------
            # 各チケット
            # -------------------------------------------------

            c4, c5, c6 = st.columns(3)

            c4.metric(
                "本線",
                f"{summary['本線的中率']:.1f}%"
            )

            c5.metric(
                "対抗",
                f"{summary['対抗的中率']:.1f}%"
            )

            c6.metric(
                "穴",
                f"{summary['穴的中率']:.1f}%"
            )


            # -------------------------------------------------
            # 回収関連
            # -------------------------------------------------

            c7, c8, c9 = st.columns(3)

            c7.metric(
                "投資",
                f"{summary['投資']:,}円"
            )

            c8.metric(
                "払戻",
                f"{summary['払戻']:,}円"
            )

            c9.metric(
                "回収率",
                f"{summary['回収率']:.1f}%"
            )


            # -------------------------------------------------
            # 詳細結果
            # -------------------------------------------------

            st.dataframe(
                rows,
                hide_index=True,
                use_container_width=True
            )
