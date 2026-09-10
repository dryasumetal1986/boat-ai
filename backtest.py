from datetime import timedelta
import pandas as pd
import streamlit as st
import data
from ai import tri_ai

START_DATE = data.API_START_DATE
PAGE_SIZE = 10


def get_actual_order(race):
    return data.get_result_order(race)


def get_payout(race, order):
    p = data.get_result(race).get("payouts", {})
    p = p.get("trifecta", []) if isinstance(p, dict) else []
    if len(order) < 3:
        return 0
    target = "-".join(map(str, order[:3]))
    for x in p:
        if str(x.get("combination", "")).strip() == target:
            try:
                return int(x.get("amount", 0))
            except:
                return 0
    return 0


def get_top3(ai):
    scores = ai.get("scores", {})
    if isinstance(scores, pd.Series):
        scores = scores.to_dict()
    if not isinstance(scores, dict):
        return []

    a = []
    for boat, score in scores.items():
        try:
            b = int(boat)
            s = float(score)
            if 1 <= b <= 6:
                a.append((b, s))
        except:
            pass

    a.sort(key=lambda x: x[1], reverse=True)
    return [b for b, _ in a[:3]]


def fix_picks(main, counter, hole, top3):
    used = []

    for value in [main, counter, hole]:
        try:
            value = int(value)
        except:
            value = 0

        if value not in used and 1 <= value <= 6:
            used.append(value)

    for b in top3 + list(range(1, 7)):
        if len(used) >= 3:
            break
        if b not in used:
            used.append(b)

    return used[0], used[1], used[2]


def make_bets(a, b, c):
    return list({
        (a, b, c),
        (a, c, b),
        (b, a, c),
        (b, c, a),
        (c, a, b),
        (c, b, a),
    })


def analyze_race(stadium, race_no, race):
    rows = data.get_race_rows(race)

    if rows is None:
        return None
    if isinstance(rows, pd.DataFrame) and rows.empty:
        return None
    if not isinstance(rows, pd.DataFrame) and not rows:
        return None

    try:
        history = data.history14(
            stadium, race_no, race.get("date")
        )
        ai = tri_ai(rows, history, stadium)
        main = int(ai["main"])
        counter = int(ai["counter"])
        hole = int(ai["hole"])
    except:
        return None

    top3 = get_top3(ai)

    if len(top3) < 3:
        return None

    main, counter, hole = fix_picks(
        main, counter, hole, top3
    )

    order = get_actual_order(race)

    if len(order) < 3:
        return None

    actual3 = set(order[:3])
    bets = make_bets(main, counter, hole)
    hit = tuple(order[:3]) in bets

    return {
        "日付": race.get("date", ""),
        "場": data.stadium_name(stadium),
        "R": f"{race_no}R",
        "本命": main,
        "対抗": counter,
        "穴": hole,
        "実着順": "-".join(map(str, order[:3])),
        "3連単配当": get_payout(race, order),
        "本命1着": order[0] == main,
        "本命3連対": main in actual3,
        "AI上位3艇3連対": any(
            b in actual3 for b in top3
        ),
        "AI買い的中": hit,
    }


def get_completed(date):
    raw = data.get_data(date)
    if not raw:
        return []

    result = []

    for stadium, race_no, race in data.all_races_for_date(raw):
        try:
            if len(get_actual_order(race)) >= 3:
                result.append(
                    (stadium, race_no, race)
                )
        except:
            pass

    return result


def run_backtest(count):
    d = data.jst_today() - timedelta(days=1)
    result = []

    while d >= START_DATE and len(result) < count:
        for stadium, race_no, race in get_completed(d):
            if len(result) >= count:
                break

            x = analyze_race(
                stadium, race_no, race
            )
            if x:
                result.append(x)

        d -= timedelta(days=1)

    return pd.DataFrame(result)


def metrics(df):
    n = len(df)
    invest = n * 600

    payout = int(
        df.loc[
            df["AI買い的中"],
            "3連単配当"
        ].sum()
    )

    return {
        "roi": payout / invest * 100 if invest else 0,
        "main_win": df["本命1着"].mean() * 100,
        "main_top3": df["本命3連対"].mean() * 100,
        "ai_top3": df["AI上位3艇3連対"].mean() * 100,
        "ai_hit": df["AI買い的中"].mean() * 100,
        "invest": invest,
        "payout": payout,
    }


def show_cards(df):
    pages = max(
        1,
        (len(df) + PAGE_SIZE - 1) // PAGE_SIZE
    )

    page = st.session_state.get(
        "backtest_page", 0
    )
    page = min(page, pages - 1)

    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, len(df))

    st.markdown(
        '<div id="backtest-top"></div>',
        unsafe_allow_html=True
    )
    st.subheader("📋 検証結果")
    st.caption(
        f"{start + 1}〜{end} / {len(df)}レース"
    )

    for _, r in df.iloc[start:end].iterrows():
        with st.container(border=True):
            st.markdown(
                f"**{r['日付']}｜{r['場']}｜{r['R']}**"
            )
            st.write(
                f"🎯 本命 **{r['本命']}**　"
                f"🔥 対抗 **{r['対抗']}**　"
                f"💥 穴 **{r['穴']}**"
            )
            st.write(
                f"🏁 実着順 **{r['実着順']}**"
            )
            st.write(
                f"💰 3連単配当 "
                f"**{int(r['3連単配当']):,}円**"
            )

            if r["AI買い的中"]:
                st.success("🎉 AI買い的中！")
            else:
                st.caption("AI買い：ハズレ")

    if pages > 1:
        st.divider()
        c1, c2 = st.columns(2)

        with c1:
            if st.button(
                "◀ 前へ",
                disabled=page == 0,
                use_container_width=True,
                key="bt_prev"
            ):
                st.session_state["backtest_page"] = page - 1
                st.session_state["scroll_bt"] = True
                st.rerun()

        with c2:
            if st.button(
                "次へ ▶",
                disabled=page >= pages - 1,
                use_container_width=True,
                key="bt_next"
            ):
                st.session_state["backtest_page"] = page + 1
                st.session_state["scroll_bt"] = True
                st.rerun()

        st.caption(
            f"ページ {page + 1} / {pages}"
        )

    if st.session_state.get("scroll_bt", False):
        st.session_state["scroll_bt"] = False

        st.components.v1.html(
            """
            <script>
            setTimeout(() => {
                const x =
                  window.parent.document
                  .getElementById("backtest-top");
                if (x) {
                    x.scrollIntoView({
                        behavior: "smooth",
                        block: "start"
                    });
                }
            }, 150);
            </script>
            """,
            height=0
        )


def render_backtest(stadium_no=None):
    st.divider()
    st.subheader("📊 AI予想バックテスト")
    st.caption(
        "🌎 全国24場を対象に、"
        "昨日から2026-01-01まで遡って検証"
    )

    count = st.selectbox(
        "検証レース数",
        [100, 300, 500, 1000],
        key="bt_count"
    )

    if st.button(
        "🚀 バックテスト開始",
        use_container_width=True,
        key="bt_start"
    ):
        st.session_state["backtest_page"] = 0
        st.session_state["scroll_bt"] = False

        with st.spinner(
            "全国24場の過去レースを検索中..."
        ):
            df = run_backtest(count)

        if df.empty:
            st.error(
                "検証できるレースがありませんでした。"
            )
            return

        st.session_state["backtest_df"] = df

        st.success(
            f"🎉 {len(df)}レースの検証が完了しました！"
        )

    df = st.session_state.get("backtest_df")

    if df is None or df.empty:
        return

    m = metrics(df)

    st.write(
        f"**{len(df)} / {len(df)} レース**"
    )

    st.metric(
        "💰 回収率",
        f"{m['roi']:.1f}%"
    )
    st.metric(
        "🎯 本命1着率",
        f"{m['main_win']:.1f}%"
    )
    st.metric(
        "🎯 本命3連対率",
        f"{m['main_top3']:.1f}%"
    )
    st.metric(
        "🔥 AI買い的中率",
        f"{m['ai_hit']:.1f}%"
    )

    st.write(
        f"投資金額 **{m['invest']:,}円**"
    )
    st.write(
        f"払戻金額 **{m['payout']:,}円**"
    )
    st.write(
        f"AI上位3艇3連対 "
        f"**{m['ai_top3']:.1f}%**"
    )
    st.write(
        f"3連単完全的中率 "
        f"**{m['ai_hit']:.1f}%**"
    )

    show_cards(df)
