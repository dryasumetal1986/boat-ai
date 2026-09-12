import traceback
from datetime import date, timedelta

import streamlit as st

import data
from ai import predict, combo_text
from backtest import run_backtest


# =========================================================
# ページ設定
# =========================================================

st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO",
    page_icon="🚤",
    layout="centered",
)


# =========================================================
# タイトル
# =========================================================

st.title("🚤 やっちゃんの競艇AI予想 PRO")

st.caption(
    "AI的中率重視 × 実データ × 3連単3点"
)


# =========================================================
# セッション初期値
# =========================================================

today = date.today()
yesterday = today - timedelta(days=1)

if "race_day" not in st.session_state:
    st.session_state.race_day = today

if "venue" not in st.session_state:
    st.session_state.venue = "選択してください"

if "race" not in st.session_state:
    st.session_state.race = "選択してください"

if "bt_day" not in st.session_state:
    st.session_state.bt_day = yesterday

if "count" not in st.session_state:
    st.session_state.count = 100


# =========================================================
# 開催日
# =========================================================

race_day = st.date_input(
    "開催日",
    key="race_day",
)


# =========================================================
# 開催場
# =========================================================

venue_names = [
    "選択してください"
] + list(
    data.STADIUMS.values()
)

venue_name = st.selectbox(
    "開催場",
    venue_names,
    key="venue",
)


# =========================================================
# レース
# =========================================================

race_options = [
    "選択してください"
]

stadium_no = None

if venue_name != "選択してください":

    stadium_no = data.STADIUM_BY_NAME.get(
        venue_name
    )

    try:

        race_numbers = (
            data.get_races_for_stadium(
                race_day,
                stadium_no,
            )
        )

        for race_no in race_numbers:

            # APIからintで返ってきてもOK
            # dictで返ってきてもOK
            if isinstance(
                race_no,
                dict
            ):

                value = race_no.get(
                    "race_number",
                    race_no.get(
                        "race_no",
                        0
                    )
                )

            else:
                value = race_no

            try:
                value = int(value)

            except Exception:
                continue

            if 1 <= value <= 12:
                race_options.append(
                    value
                )

    except Exception as e:

        st.error(
            "レース一覧の取得に失敗しました。"
        )

        with st.expander(
            "🔎 詳細エラー"
        ):
            st.code(
                traceback.format_exc()
            )


race_display_options = [
    "選択してください"
]

for race_no in race_options[1:]:

    race_display_options.append(
        str(race_no)
    )


selected_race = st.selectbox(
    "レース",
    race_display_options,
)


# =========================================================
# AI予想
# =========================================================

if st.button(
    "🎯 AI予想を実行",
    use_container_width=True,
):

    if (
        venue_name
        == "選択してください"
    ):

        st.warning(
            "開催場を選択してください。"
        )

    elif (
        selected_race
        == "選択してください"
    ):

        st.warning(
            "レースを選択してください。"
        )

    else:

        try:

            stadium_no = (
                data.STADIUM_BY_NAME[
                    venue_name
                ]
            )

            race_no = int(
                selected_race
            )

            # -------------------------------------------------
            # レース本体取得
            # -------------------------------------------------

            race = data.get_race(
                race_day,
                stadium_no,
                race_no,
            )

            if not isinstance(
                race,
                dict
            ):

                raise ValueError(
                    "レースデータがdict形式ではありません。"
                    f"\n実際の型: {type(race)}"
                )

            # -------------------------------------------------
            # DataFrame変換
            # -------------------------------------------------

            df = data.race_to_df(
                race
            )

            if df is None or df.empty:

                raise ValueError(
                    "出走表DataFrameを作成できませんでした。"
                    f"\nDataFrame型: {type(df)}"
                    f"\n行数: "
                    f"{0 if df is None else len(df)}"
                )

            # -------------------------------------------------
            # 通常は6艇
            # -------------------------------------------------

            if len(df) != 6:

                raise ValueError(
                    "通常の予想対象である6艇データを取得できませんでした。"
                    f"\n取得艇数: {len(df)}"
                    f"\n艇番: "
                    f"{df['boat'].tolist()}"
                )

            # -------------------------------------------------
            # AI予想
            # -------------------------------------------------

            pred = predict(
                df,
                stadium_no=stadium_no,
            )

            if not isinstance(
                pred,
                dict
            ):

                raise ValueError(
                    "AI予想結果がdict形式ではありません。"
                    f"\n実際の型: {type(pred)}"
                )

            # -------------------------------------------------
            # 軸
            # -------------------------------------------------

            axis = pred.get(
                "axis"
            )

            st.subheader(
                f"🎯 AI軸：{axis}号艇"
            )

            # -------------------------------------------------
            # 3点
            # -------------------------------------------------

            tickets = pred.get(
                "tickets",
                []
            )

            if not isinstance(
                tickets,
                list
            ):

                raise ValueError(
                    "ticketsがlist形式ではありません。"
                    f"\n実際の型: {type(tickets)}"
                )

            for ticket in tickets:

                if not isinstance(
                    ticket,
                    dict
                ):
                    continue

                label = str(
                    ticket.get(
                        "label",
                        ""
                    )
                )

                combo = ticket.get(
                    "combo",
                    ()
                )

                score = ticket.get(
                    "score",
                    0
                )

                try:

                    text = combo_text(
                        combo
                    )

                except Exception:

                    text = str(
                        combo
                    )

                if label == "本線":
                    st.success(
                        f"本線　{text}"
                    )

                elif label == "対抗":
                    st.info(
                        f"対抗　{text}"
                    )

                elif label == "穴":
                    st.warning(
                        f"穴　{text}"
                    )

                else:
                    st.write(
                        f"{label}　{text}"
                    )

            # -------------------------------------------------
            # 確率
            # -------------------------------------------------

            three_probability = pred.get(
                "three_point_probability",
                0
            )

            axis_first = pred.get(
                "axis_first_probability",
                0
            )

            axis_top3 = pred.get(
                "axis_top3_probability",
                0
            )

            st.write(
                f"3点合計AI確率："
                f"{three_probability:.2f}%"
            )

            st.write(
                f"軸1着AI確率："
                f"{axis_first:.2f}%"
            )

            st.write(
                f"軸3着内AI確率："
                f"{axis_top3:.2f}%"
            )

            # -------------------------------------------------
            # 詳細
            # -------------------------------------------------

            with st.expander(
                "出走表データ"
            ):

                st.dataframe(
                    df,
                    use_container_width=True,
                )

            with st.expander(
                "AI内部ランキング"
            ):

                ranking = pred.get(
                    "ranking",
                    []
                )

                if ranking:
                    st.dataframe(
                        ranking,
                        use_container_width=True,
                    )

        except Exception as e:

            st.error(
                "出走表データが正しく取得できませんでした。"
            )

            st.error(
                str(e)
            )

            # -------------------------------------------------
            # 今回は原因特定のため表示
            # -------------------------------------------------

            with st.expander(
                "🔎 詳細エラーを見る"
            ):

                st.code(
                    traceback.format_exc()
                )

                st.write(
                    "【確認情報】"
                )

                st.write(
                    "開催日:",
                    race_day
                )

                st.write(
                    "開催場:",
                    venue_name
                )

                st.write(
                    "会場番号:",
                    stadium_no
                )

                st.write(
                    "レース:",
                    selected_race
                )


# =========================================================
# 区切り
# =========================================================

st.divider()


# =========================================================
# バックテスト
# =========================================================

st.header(
    "📈 バックテスト"
)


bt_day = st.date_input(
    "バックテスト日",
    key="bt_day",
    max_value=yesterday,
)


count = st.selectbox(
    "検証レース数",
    [100, 200, 300, 500, 1000],
    key="count",
)


st.caption(
    "昨日を起点に、必要なレース数に達するまで過去へ自動的に遡ります。"
    "全24場を対象にします。"
)


if st.button(
    "📊 バックテスト実行",
    use_container_width=True,
):

    progress_bar = st.progress(
        0
    )

    status = st.empty()

    def progress_callback(
        day_index,
        max_days,
        found,
        current_day,
    ):

        ratio = (
            day_index
            / max_days
        )

        ratio = max(
            0.0,
            min(
                1.0,
                ratio
            )
        )

        progress_bar.progress(
            ratio
        )

        status.info(
            f"取得中："
            f"{current_day} / "
            f"有効レース {found} / "
            f"目標 {count}"
        )

    try:

        summary, rows, venue_rows = (
            run_backtest(
                bt_day,
                count,
                progress=progress_callback,
            )
        )

        progress_bar.progress(
            1.0
        )

        status.empty()

        if not rows:

            st.error(
                "有効な結果データを1レースも取得できませんでした。"
            )

            st.warning(
                "下の診断情報を確認してください。"
            )

        else:

            st.success(
                f"{len(rows)}レースの検証が完了しました。"
            )

            # -------------------------------------------------
            # サマリー
            # -------------------------------------------------

            col1, col2 = st.columns(2)

            with col1:

                st.metric(
                    "検証数",
                    summary["検証数"]
                )

                st.metric(
                    "3点的中率",
                    f'{summary["3点的中率"]:.2f}%'
                )

                st.metric(
                    "軸1着率",
                    f'{summary["軸1着率"]:.2f}%'
                )

                st.metric(
                    "軸3着内率",
                    f'{summary["軸3着内率"]:.2f}%'
                )

            with col2:

                st.metric(
                    "本線",
                    f'{summary["本線的中率"]:.2f}%'
                )

                st.metric(
                    "対抗",
                    f'{summary["対抗的中率"]:.2f}%'
                )

                st.metric(
                    "穴",
                    f'{summary["穴的中率"]:.2f}%'
                )

                st.metric(
                    "回収率",
                    f'{summary["回収率"]:.2f}%'
                )

            # -------------------------------------------------
            # 会場別
            # -------------------------------------------------

            st.subheader(
                "会場別成績"
            )

            if venue_rows:

                st.dataframe(
                    venue_rows,
                    use_container_width=True,
                )

            # -------------------------------------------------
            # 詳細
            # -------------------------------------------------

            st.subheader(
                "検証詳細"
            )

            st.dataframe(
                rows,
                use_container_width=True,
            )

    except Exception as e:

        progress_bar.empty()
        status.empty()

        st.error(
            "バックテスト中にエラーが発生しました。"
        )

        st.error(
            str(e)
        )

        with st.expander(
            "🔎 詳細エラーを見る"
        ):

            st.code(
                traceback.format_exc()
                )
