import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timedelta, timezone

from data import (
    VENUES,
    get_race,
    get_trifecta_odds,
)

from ai import (
    predict_race,
    recommend_bets,
)

from backtest import (
    run_backtest,
    TARGET_RACES,
)


st.set_page_config(
    page_title="やっちゃんの競艇AI予想PRO",
    page_icon="🚤",
    layout="centered",
)


JST = timezone(
    timedelta(hours=9)
)


def today_jst():
    return datetime.now(
        JST
    ).date()


def scroll_to_results():
    components.html(
        """
        <script>
        (function () {
            let count = 0;
            const max_count = 30;

            function go() {
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
                        return;
                    }
                } catch (e) {}

                count += 1;

                if (count < max_count) {
                    setTimeout(go, 100);
                }
            }

            setTimeout(go, 100);
        })();
        </script>
        """,
        height=1,
    )


defaults = {
    "prediction": None,
    "backtest": None,
    "bt_page": 1,
    "scroll_request": False,
}


for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


st.title(
    "🚤 やっちゃんの競艇AI予想PRO"
)

st.caption(
    "AI的中率重視 × 実データ × 3連単3点"
)


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


if st.button(
    "🚀 AI予想開始",
    use_container_width=True,
):
    ds = today_jst().isoformat()

    with st.spinner(
        "🔄 AI予想を計算中…"
    ):
        race = get_race(
            ds,
            venue,
            race_no,
        )

        if race:
            pred = predict_race(
                race
            )

            odds = get_trifecta_odds(
                ds,
                race["venue_id"],
                race_no,
            )

            bets = recommend_bets(
                pred,
                odds,
            )

            st.session_state.prediction = {
                "race": race,
                "pred": pred,
                "odds": odds,
                "bets": bets,
            }

        else:
            st.session_state.prediction = None

            st.error(
                "当日の6艇データを取得できませんでした。"
                "API側にデータがまだ公開されていない可能性があります。"
            )


x = st.session_state.prediction


if x:
    race = x["race"]
    pred = x["pred"]
    odds = x["odds"]
    bets = x["bets"]

    date_text = race[
        "date"
    ]

    y, m, d = date_text.split(
        "-"
    )

    st.subheader(
        f"{y}年{m}月{d}日 "
        f"{venue} {race_no}R"
    )

    st.write(
        f"🎯 **本命 {pred['main']}号艇**"
    )

    st.write(
        f"🔥 **対抗 {pred['counter']}号艇**"
    )

    st.write(
        f"💥 **穴 {pred['hole']}号艇**"
    )

    stars = max(
        1,
        min(
            5,
            round(
                pred["confidence"]
                / 20
            ),
        ),
    )

    st.write(
        f"AI信頼度 "
        f"{'⭐' * stars}"
        f"（{pred['confidence']:.1f}%）"
    )

    st.markdown(
        "### 🎯 AIが選んだ3連単3点"
    )

    st.caption(
        "的中率を最優先。"
        "オッズ・期待値は買い目選択には使用せず、"
        "参考情報として表示しています。"
    )

    labels = [
        "◎ 本線",
        "○ 対抗",
        "▲ 穴",
    ]

    for i, bet in enumerate(
        bets
    ):
        a, b, c = bet[
            "combo"
        ]

        prob = bet[
            "prob"
        ]

        odd = bet[
            "odds"
        ]

        if odd > 0:
            odd_text = (
                f"{odd:.1f}倍"
            )
        else:
            odd_text = (
                "オッズ取得なし"
            )

        st.markdown(
            f"**{labels[i]} "
            f"{a}-{b}-{c}**"
        )

        st.write(
            f"AI確率 "
            f"**{prob * 100:.2f}%**"
            f"　"
            f"公式オッズ "
            f"**{odd_text}**"
        )

        if odd > 0:
            ev = bet["ev"]

            if ev >= 0:
                st.caption(
                    f"参考EV "
                    f"+{ev * 100:.1f}%"
                )
            else:
                st.caption(
                    f"参考EV "
                    f"{ev * 100:.1f}%"
                )

    if len(odds) < 120:
        st.warning(
            f"公式オッズ "
            f"{len(odds)}/120通り取得"
        )

    else:
        st.caption(
            "公式3連単オッズ "
            "120/120通り取得"
        )

    st.markdown(
        "### 🚤 6艇AI評価"
    )

    for boat in pred[
        "ranking"
    ]:
        p = pred[
            "first_probs"
        ][boat]

        score = pred[
            "scores"
        ][boat]

        name = next(
            (
                b["name"]
                for b in race[
                    "boats"
                ]
                if b["boat"] == boat
            ),
            f"{boat}号艇",
        )

        st.write(
            f"**{boat}号艇 {name}**　"
            f"1着AI確率 "
            f"**{p * 100:.1f}%**　"
            f"AIスコア "
            f"{score:.2f}"
        )

    st.markdown(
        "### 📊 AI確率ランキング"
    )

    for i, boat in enumerate(
        pred["ranking"],
        1,
    ):
        st.write(
            f"{i}. {boat}号艇　"
            f"{pred['first_probs'][boat] * 100:.1f}%"
        )


st.divider()


st.subheader(
    "📊 AI予想バックテスト"
)

st.caption(
    "全国24場。現在日は除外し、"
    "前日から2026年1月1日まで検証。"
    "本線・対抗・穴の3点を各100円で購入。"
)


target = st.selectbox(
    "検証レース数",
    TARGET_RACES,
    format_func=lambda x:
        f"{x}レース",
)


if st.button(
    "🔍 バックテスト開始",
    use_container_width=True,
):
    progress = st.progress(
        0
    )

    status = st.empty()

    def update_progress(
        count,
        total,
        days,
    ):
        ratio = (
            count / total
            if total > 0
            else 0
        )

        progress.progress(
            min(
                1.0,
                ratio,
            )
        )

        status.caption(
            f"検証中："
            f"{count}/{total}レース "
            f"（{days}日分を確認）"
        )

    with st.spinner(
        "🔄 全国24場を高速検証中…"
    ):
        result = run_backtest(
            target,
            today_jst(),
            progress_callback=(
                update_progress
            ),
        )

    progress.empty()
    status.empty()

    st.session_state.backtest = result

    st.session_state.bt_page = 1


bt = st.session_state.backtest


if bt:
    st.write(
        f"**検証レース数："
        f"{bt['count']}レース**"
    )

    st.write(
        f"**3点合計的中率 "
        f"{bt['three_bet_hit_rate']:.1f}%**"
    )

    st.write(
        f"**本線的中率 "
        f"{bt['main_ticket_hit_rate']:.1f}%**"
    )

    st.write(
        f"**対抗的中率 "
        f"{bt['counter_ticket_hit_rate']:.1f}%**"
    )

    st.write(
        f"**穴的中率 "
        f"{bt['hole_ticket_hit_rate']:.1f}%**"
    )

    st.write(
        f"**本命1着率 "
        f"{bt['main_win_rate']:.1f}%**"
    )

    st.write(
        f"**本命3連対率 "
        f"{bt['main_top3_rate']:.1f}%**"
    )

    st.write(
        f"**AI上位3艇全艇3連対率 "
        f"{bt['top3_all_top3_rate']:.1f}%**"
    )

    st.write(
        f"**AI3艇BOX的中率 "
        f"{bt['box_hit_rate']:.1f}%**"
    )

    st.write(
        f"**3連単完全的中率 "
        f"{bt['exact_hit_rate']:.1f}%**"
    )

    st.write(
        f"**回収率 "
        f"{bt['recovery']:.1f}%**"
    )

    st.write(
        f"**投資 "
        f"{bt['investment']:,.0f}円**"
    )

    st.write(
        f"**払戻 "
        f"{bt['return']:,.0f}円**"
    )

    st.markdown(
        '<div id="backtest-results-anchor"></div>',
        unsafe_allow_html=True,
    )

    st.subheader(
        "📋 検証結果"
    )

    rows = bt[
        "rows"
    ]

    per_page = 10

    pages = max(
        1,
        (
            len(rows)
            + per_page
            - 1
        )
        // per_page,
    )

    page = min(
        max(
            1,
            st.session_state.bt_page,
        ),
        pages,
    )

    start = (
        page - 1
    ) * per_page

    end = (
        page
        * per_page
    )

    page_rows = rows[
        start:end
    ]

    for r in page_rows:
        a, b, c = r[
            "actual"
        ]

        if r[
            "exact_hit"
        ]:
            exact_text = (
                "✅ 3点内的中"
            )
        else:
            exact_text = (
                "❌ 不的中"
            )

        st.markdown(
            f"**{r['date']}　"
            f"{r['venue']} "
            f"{r['race_no']}R**  \n"
            f"AI："
            f"◎ {r['tickets'][0][0]}-"
            f"{r['tickets'][0][1]}-"
            f"{r['tickets'][0][2]}　"
            f"○ {r['tickets'][1][0]}-"
            f"{r['tickets'][1][1]}-"
            f"{r['tickets'][1][2]}　"
            f"▲ {r['tickets'][2][0]}-"
            f"{r['tickets'][2][1]}-"
            f"{r['tickets'][2][2]}  \n"
            f"結果：🏁 **{a}-{b}-{c}**　"
            f"{exact_text}"
        )

    c1, c2, c3 = st.columns(
        [1, 2, 1]
    )

    with c1:
        if page > 1:
            if st.button(
                "◀ 前へ",
                use_container_width=True,
            ):
                st.session_state.bt_page = (
                    page - 1
                )

                st.session_state.scroll_request = (
                    True
                )

                st.rerun()

    with c2:
        st.markdown(
            f"""
            <div style="
                text-align:center;
                padding-top:8px;
                font-weight:bold;
            ">
                {page} / {pages}ページ
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        if page < pages:
            if st.button(
                "次へ ▶",
                use_container_width=True,
            ):
                st.session_state.bt_page = (
                    page + 1
                )

                st.session_state.scroll_request = (
                    True
                )

                st.rerun()

    if st.session_state.scroll_request:
        st.session_state.scroll_request = False
        scroll_to_results()
