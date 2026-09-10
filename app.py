import streamlit as st
import streamlit.components.v1 as components
from datetime import (
    datetime,
    timedelta,
    timezone,
)

from data import (
    VENUES,
    get_race,
    get_trifecta_odds,
)

from ai import (
    predict_race,
    value_candidates,
)

from backtest import (
    run_backtest,
    TARGET_RACES,
)


# =========================================================
# 基本設定
# =========================================================

st.set_page_config(
    page_title="やっちゃんの競艇AI予想PRO",
    page_icon="🚤",
    layout="centered",
)


JST = timezone(
    timedelta(hours=9)
)


def today_jst():
    return datetime.now(JST).date()


# =========================================================
# Session State
# =========================================================

if "prediction" not in st.session_state:
    st.session_state.prediction = None

if "backtest" not in st.session_state:
    st.session_state.backtest = None

if "bt_page" not in st.session_state:
    st.session_state.bt_page = 1

if "scroll_request" not in st.session_state:
    st.session_state.scroll_request = False


# =========================================================
# タイトル
# =========================================================

st.title(
    "🚤 やっちゃんの競艇AI予想PRO"
)

st.caption(
    "AI予想 × 実オッズ × 期待値分析"
)


# =========================================================
# 開催場・レース
# =========================================================

venue = st.selectbox(
    "開催場",
    list(VENUES.keys()),
)

race_no = st.selectbox(
    "レース",
    range(1, 13),
    format_func=lambda x:
        f"{x}R",
)


# =========================================================
# AI予想開始
# =========================================================

if st.button(
    "🚀 AI予想開始",
    use_container_width=True,
):

    date_str = today_jst().isoformat()

    with st.status(
        "🤖 AI予想を開始しています…",
        expanded=True,
    ) as status:

        st.write(
            "📡 レース情報を取得中…"
        )

        race = get_race(
            date_str,
            venue,
            race_no,
        )

        if not race:

            status.update(
                label=(
                    "❌ レース情報を取得できませんでした"
                ),
                state="error",
            )

            st.error(
                "レース情報を取得できませんでした。"
            )

        elif len(
            race.get("boats", [])
        ) != 6:

            status.update(
                label=(
                    "❌ 6艇のデータを取得できませんでした"
                ),
                state="error",
            )

            st.error(
                "6艇のデータを取得できませんでした。"
            )

        else:

            st.write(
                "🤖 AI評価を計算中…"
            )

            prediction = predict_race(
                race
            )

            st.write(
                "💰 公式3連単オッズを取得中…"
            )

            odds = get_trifecta_odds(
                date_str,
                race["venue_id"],
                race_no,
            )

            st.write(
                f"📊 公式オッズ "
                f"{len(odds)}/120通りを確認中…"
            )

            candidates = value_candidates(
                prediction,
                odds,
                min_prob=0.006,
                limit=8,
            )

            st.session_state.prediction = {
                "race": race,
                "pred": prediction,
                "odds": odds,
                "candidates": candidates,
            }

            status.update(
                label="✅ AI予想が完了しました！",
                state="complete",
                expanded=False,
            )


# =========================================================
# AI結果
# =========================================================

result = st.session_state.prediction


if result:

    race = result["race"]
    prediction = result["pred"]
    odds = result["odds"]
    candidates = result["candidates"]

    year, month, day = (
        race["date"].split("-")
    )

    st.subheader(
        f"{year}年{month}月{day}日 "
        f"{race['venue']} "
        f"{race['race_no']}R"
    )

    st.write(
        f"🎯 **本命 "
        f"{prediction['main']}号艇**"
    )

    st.write(
        f"🔥 **対抗 "
        f"{prediction['counter']}号艇**"
    )

    st.write(
        f"💥 **穴 "
        f"{prediction['hole']}号艇**"
    )

    confidence = prediction[
        "confidence"
    ]

    star_count = max(
        1,
        min(
            5,
            round(
                confidence / 20
            ),
        ),
    )

    st.write(
        f"AI信頼度 "
        f"{'⭐' * star_count} "
        f"（{confidence:.1f}%）"
    )

    # =====================================================
    # 本命軸
    # =====================================================

    st.markdown(
        "### 🎯 本命軸の最有力三連単"
    )

    main_combo = prediction[
        "main_best_combo"
    ]

    a, b, c = main_combo

    st.write(
        f"**{a}-{b}-{c}**　"
        f"AI確率 "
        f"{prediction['main_best_combo_prob'] * 100:.2f}%"
    )

    # =====================================================
    # EV
    # =====================================================

    st.markdown(
        "### 💰 期待値の高い三連単"
    )

    st.caption(
        "公式BOATRACEの3連単実オッズを使用"
    )

    st.caption(
        "的中率を最優先し、"
        "期待値を補助評価しています。"
    )

    if len(odds) == 120:

        st.success(
            "公式オッズ 120/120通り取得"
        )

    else:

        st.warning(
            f"公式オッズ取得 "
            f"{len(odds)}/120通り"
        )

    if candidates:

        for item in candidates:

            x, y, z = item["combo"]

            st.write(
                f"🔥 **{x}-{y}-{z}**　"
                f"オッズ "
                f"{item['odds']:.1f}倍　"
                f"AI確率 "
                f"{item['prob'] * 100:.2f}%　"
                f"EV "
                f"**+{item['ev'] * 100:.1f}%**"
            )

            st.caption(
                f"市場確率 "
                f"{item['market_prob'] * 100:.2f}% / "
                f"AIとの差 "
                f"+{item['edge'] * 100:.2f}pt"
            )

    else:

        st.info(
            "条件を満たすプラス期待値の買い目はありません。"
        )

    # =====================================================
    # 6艇AI評価
    # =====================================================

    st.markdown(
        "### 🚤 6艇AI評価"
    )

    for no in prediction["ranking"]:

        probability = prediction[
            "first_probs"
        ][no]

        score = prediction[
            "scores"
        ][no]

        name = next(
            (
                boat["name"]
                for boat in race["boats"]
                if boat["boat"] == no
            ),
            f"{no}号艇",
        )

        st.write(
            f"**{no}号艇 {name}**　"
            f"1着AI確率 "
            f"**{probability * 100:.1f}%**　"
            f"AIスコア {score:.2f}"
        )

    # =====================================================
    # ランキング
    # =====================================================

    st.markdown(
        "### 📊 AI確率ランキング"
    )

    for rank, no in enumerate(
        prediction["ranking"],
        1,
    ):

        probability = prediction[
            "first_probs"
        ][no]

        st.write(
            f"{rank}. {no}号艇　"
            f"{probability * 100:.1f}%"
        )


# =========================================================
# 区切り
# =========================================================

st.divider()


# =========================================================
# バックテスト
# =========================================================

st.subheader(
    "📊 AI予想バックテスト"
)

st.caption(
    "全国24場。現在日は除外し、"
    "前日から2026年1月1日まで遡って検証。"
)


target = st.selectbox(
    "検証レース数",
    TARGET_RACES,
    format_func=lambda x:
        f"{x}レース",
)


# =========================================================
# バックテスト開始
# =========================================================

if st.button(
    "🔍 バックテスト開始",
    use_container_width=True,
):

    with st.status(
        "📊 バックテストを開始しています…",
        expanded=True,
    ) as status:

        st.write(
            "📡 全国24場のデータを検索中…"
        )

        st.write(
            "📅 前日から過去へ遡ってレースを確認中…"
        )

        st.write(
            f"🤖 {target}レースをAI予想中…"
        )

        st.write(
            "📈 的中率・回収率を集計中…"
        )

        st.session_state.backtest = (
            run_backtest(
                target,
                today_jst(),
            )
        )

        st.session_state.bt_page = 1

        st.session_state.scroll_request = False

        status.update(
            label=(
                "✅ バックテスト完了！ "
                f"{st.session_state.backtest['count']}"
                "レースを検証"
            ),
            state="complete",
            expanded=False,
        )


# =========================================================
# バックテスト結果
# =========================================================

backtest = st.session_state.backtest


if backtest:

    st.write(
        f"**検証レース数："
        f"{backtest['count']}レース**"
    )

    st.write(
        f"**回収率 "
        f"{backtest['recovery']:.1f}%**"
    )

    st.write(
        f"**本命1着率 "
        f"{backtest['main_win_rate']:.1f}%**"
    )

    st.write(
        f"**本命3連対率 "
        f"{backtest['main_top3_rate']:.1f}%**"
    )

    st.write(
        f"**AI上位3艇全艇3連対率 "
        f"{backtest['top3_all_top3_rate']:.1f}%**"
    )

    st.write(
        f"**AI選出3艇BOX的中率 "
        f"{backtest['box_hit_rate']:.1f}%**"
    )

    st.write(
        f"**3連単完全的中率 "
        f"{backtest['exact_hit_rate']:.1f}%**"
    )

    st.write(
        f"**投資 "
        f"{backtest['investment']:,.0f}円**"
    )

    st.write(
        f"**払戻 "
        f"{backtest['return']:,.0f}円**"
    )

    # =====================================================
    # 検証結果アンカー
    # =====================================================

    st.markdown(
        """
        <div
            id="backtest-results-anchor"
            style="
                height:1px;
                margin:0;
                padding:0;
            ">
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader(
        "📋 検証結果"
    )

    # =====================================================
    # ページ
    # =====================================================

    rows = backtest["rows"]

    per_page = 10

    total_pages = max(
        1,
        (
            len(rows)
            + per_page
            - 1
        ) // per_page,
    )

    page = max(
        1,
        min(
            st.session_state.bt_page,
            total_pages,
        ),
    )

    st.session_state.bt_page = page

    start = (
        page - 1
    ) * per_page

    end = (
        start
        + per_page
    )

    page_rows = rows[
        start:end
    ]

    # =====================================================
    # 10レース表示
    # =====================================================

    for row in page_rows:

        actual = row["actual"]

        a, b, c = actual[:3]

        predicted = row[
            "predicted_combo"
        ]

        px, py, pz = predicted

        if row["exact_hit"]:

            result_text = (
                "✅ 3連単的中"
            )

        else:

            result_text = (
                "❌ 不的中"
            )

        if row["box_hit"]:

            box_text = (
                "　/　AI3艇BOX的中"
            )

        else:

            box_text = ""

        st.markdown(
            f"""
**{row['date']}　{row['venue']} {row['race_no']}R**

AI：🎯{row['main']}号艇　
🔥{row['counter']}号艇　
💥{row['hole']}号艇

予想：{px}-{py}-{pz}

結果：🏁 **{a}-{b}-{c}**　
{result_text}{box_text}
"""
        )

    # =====================================================
    # ページ移動
    # =====================================================

    st.write("")

    col1, col2, col3 = st.columns(
        [1, 2, 1]
    )

    # 前へ
    with col1:

        if page > 1:

            if st.button(
                "◀ 前へ",
                use_container_width=True,
                key="bt_prev",
            ):

                st.session_state.bt_page = (
                    page - 1
                )

                st.session_state.scroll_request = True

                st.rerun()

    # ページ番号
    with col2:

        st.markdown(
            f"""
            <div style="
                text-align:center;
                padding-top:8px;
                font-weight:bold;
            ">
                {page} / {total_pages}ページ
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 次へ
    with col3:

        if page < total_pages:

            if st.button(
                "次へ ▶",
                use_container_width=True,
                key="bt_next",
            ):

                st.session_state.bt_page = (
                    page + 1
                )

                st.session_state.scroll_request = True

                st.rerun()

    # =====================================================
    # 自動スクロール
    #
    # 重要:
    # 1回だけ実行。
    # 複数タイマーを使わない。
    # =====================================================

    if st.session_state.scroll_request:

        st.session_state.scroll_request = False

        components.html(
            """
            <script>
            setTimeout(function() {

                try {

                    const doc =
                        window.parent.document;

                    const target =
                        doc.getElementById(
                            "backtest-results-anchor"
                        );

                    if (target) {

                        target.scrollIntoView({
                            behavior: "smooth",
                            block: "start"
                        });

                    }

                } catch (e) {
                    console.log(e);
                }

            }, 350);
            </script>
            """,
            height=1,
    )
