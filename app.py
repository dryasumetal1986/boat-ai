import streamlit as st
import requests
import pandas as pd
from datetime import date, timedelta
from itertools import permutations

st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO",
    layout="wide"
)

API = "https://boatraceopenapi.github.io/api/v1/{year}/{ymd}.json"


# =========================
# データ取得
# =========================

@st.cache_data(ttl=180)
def get_data(d):
    url = API.format(
        year=d.year,
        ymd=f"{d.year:04d}{d.month:02d}{d.day:02d}"
    )

    try:
        r = requests.get(url, timeout=20)

        if r.status_code == 404:
            return None

        r.raise_for_status()
        return r.json()

    except Exception:
        return None


def get_race(data, sid, rno):
    return data["programs"]["stadiums"][sid]["races"][str(rno)]


def num(x, default=0):
    try:
        return float(x)
    except:
        return default


# =========================
# 直前情報
# =========================

def preview_map(race):
    out = {}

    for x in race.get("preview", {}).get("racers", []):
        c = x.get("course_number")

        if c is not None:
            out[str(c)] = x

    return out


# =========================
# 選手データ
# =========================

def make_rows(race):

    pm = preview_map(race)

    rows = []

    for x in race.get("racers", []):

        c = x.get("entry_number")

        if c is None:
            continue

        p = pm.get(str(c), {})

        rows.append({
            "枠": c,
            "コース": p.get("course_number", c),
            "選手": x.get("name", ""),
            "番号": x.get("number", ""),
            "級": x.get("rank_number", ""),
            "全国勝率": num(
                x.get("national_win_rate")
            ),
            "当地勝率": num(
                x.get("local_win_rate")
            ),
            "モーター2連率": num(
                x.get("motor_top_2_percent")
            ),
            "ST": num(
                p.get("start_timing")
            ),
            "展示": num(
                p.get("exhibition_time")
            )
        })

    rows.sort(key=lambda x: x["枠"])

    # ST順位
    st_order = sorted(
        rows,
        key=lambda x:
        x["ST"] if x["ST"] > 0 else 99
    )

    # 展示順位
    ex_order = sorted(
        rows,
        key=lambda x:
        x["展示"] if x["展示"] > 0 else 99
    )

    for i, x in enumerate(st_order, 1):
        x["ST順位"] = i

    for i, x in enumerate(ex_order, 1):
        x["展示順位"] = i

    return rows


# =========================
# 過去データ学習
# =========================

@st.cache_data(ttl=900)
def history(target, days=10):

    pc = {}
    vc = {}
    ve = {}
    vs = {}

    total = 0

    for k in range(1, days + 1):

        d = target - timedelta(days=k)

        data = get_data(d)

        # データがない日はスキップ
        if not data:
            continue

        stadiums = data.get(
            "programs",
            {}
        ).get(
            "stadiums",
            {}
        )

        for sid, sdata in stadiums.items():

            races = sdata.get(
                "races",
                {}
            )

            for race in races.values():

                rr = race.get(
                    "result",
                    {}
                ).get(
                    "racers",
                    []
                )

                if len(rr) < 6:
                    continue

                pm = preview_map(race)

                ex_order = sorted(
                    [
                        (
                            cc,
                            num(
                                pp.get(
                                    "exhibition_time"
                                )
                            )
                        )
                        for cc, pp in pm.items()
                    ],
                    key=lambda z:
                    z[1] if z[1] > 0 else 99
                )

                st_order = sorted(
                    [
                        (
                            cc,
                            num(
                                pp.get(
                                    "start_timing"
                                )
                            )
                        )
                        for cc, pp in pm.items()
                    ],
                    key=lambda z:
                    z[1] if z[1] > 0 else 99
                )

                ex_rank = {
                    cc: i
                    for i, (cc, _) in
                    enumerate(ex_order, 1)
                }

                st_rank = {
                    cc: i
                    for i, (cc, _) in
                    enumerate(st_order, 1)
                }

                for r in rr:

                    n = r.get("number")
                    place = r.get("place_number")
                    course = r.get("course_number")

                    if (
                        n is None
                        or course is None
                        or place is None
                    ):
                        continue

                    course = int(course)

                    key = (
                        str(n),
                        course
                    )

                    pc.setdefault(
                        key,
                        [0, 0, 0, 0]
                    )

                    vc.setdefault(
                        (sid, course),
                        [0, 0, 0, 0]
                    )

                    pc[key][0] += 1
                    vc[(sid, course)][0] += 1

                    if place in (1, 2, 3):

                        pc[key][place] += 1

                        vc[
                            (sid, course)
                        ][place] += 1

                    c = str(course)

                    if c in pm:

                        er = ex_rank.get(c, 6)
                        sr = st_rank.get(c, 6)

                        vk = (
                            sid,
                            er
                        )

                        sk = (
                            sid,
                            sr
                        )

                        ve.setdefault(
                            vk,
                            [0, 0]
                        )

                        vs.setdefault(
                            sk,
                            [0, 0]
                        )

                        ve[vk][0] += 1
                        vs[sk][0] += 1

                        if place == 1:

                            ve[vk][1] += 1
                            vs[sk][1] += 1

                total += 1

    return {
        "pc": pc,
        "vc": vc,
        "ve": ve,
        "vs": vs,
        "total": total
    }


def rate(dic, key, pos, base):

    a = dic.get(key)

    if not a or a[0] == 0:
        return base

    r = a[pos] / a[0]

    w = min(
        a[0] / 25,
        1
    )

    return (
        base * (1 - w)
        + r * w
    )


# =========================
# AI予想
# =========================

def ai(rows, sid, h, wind=0, wave=0):

    result = []

    for x in rows:

        c = int(x["コース"])

        p1 = [
            0.36,
            0.18,
            0.14,
            0.11,
            0.08,
            0.06
        ][min(c - 1, 5)]

        p2 = [
            0.22,
            0.22,
            0.19,
            0.16,
            0.12,
            0.09
        ][min(c - 1, 5)]

        p3 = [
            0.18,
            0.20,
            0.20,
            0.17,
            0.14,
            0.11
        ][min(c - 1, 5)]

        nat = x["全国勝率"]
        local = x["当地勝率"]
        motor = x["モーター2連率"]
        stv = x["ST"]
        ex = x["展示"]

        # 全国勝率
        p1 *= (
            0.70
            + nat * 0.12
        )

        # 当地勝率
        p1 *= (
            0.90
            + local * 0.05
        )

        # モーター
        p1 *= (
            0.90
            + motor / 100 * 0.30
        )

        # ST
        if stv > 0:

            p1 *= max(
                0.75,
                1.10 - stv * 3
            )

        # 展示
        if ex > 0:

            p1 *= max(
                0.82,
                1.08 - (ex - 6.7) * 0.8
            )

        # 選手×コース
        p1 *= (
            0.75
            +
            rate(
                h["pc"],
                (
                    str(x["番号"]),
                    c
                ),
                1,
                0.20
            )
            / 0.20
            * 0.25
        )

        # 場×コース
        base_course = [
            0.36,
            0.18,
            0.14,
            0.11,
            0.08,
            0.06
        ][min(c - 1, 5)]

        venue_rate = rate(
            h["vc"],
            (
                sid,
                c
            ),
            1,
            base_course
        )

        p1 *= (
            0.80
            +
            venue_rate
            / max(base_course, 0.01)
            * 0.20
        )

        # 展示順位
        p1 *= [
            1.12,
            1.07,
            1.03,
            0.98,
            0.94,
            0.90
        ][x["展示順位"] - 1]

        # ST順位
        p1 *= [
            1.08,
            1.05,
            1.02,
            0.99,
            0.95,
            0.92
        ][x["ST順位"] - 1]

        # 風
        if wind >= 5:

            if c == 1:
                p1 *= 1.04

            elif c >= 4:
                p1 *= 0.97

        # 波
        if wave >= 5:

            if c <= 2:
                p1 *= 1.02

            else:
                p1 *= 0.98

        # 2着
        p2 *= (
            0.80
            + nat * 0.08
        )

        p2 *= (
            0.90
            + motor / 100 * 0.20
        )

        # 3着
        p3 *= (
            0.82
            + nat * 0.06
        )

        p3 *= (
            0.92
            + motor / 100 * 0.15
        )

        result.append({
            **x,
            "1着率": p1,
            "2着率": p2,
            "3着率": p3
        })

    # 確率化
    for key in (
        "1着率",
        "2着率",
        "3着率"
    ):

        s = sum(
            x[key]
            for x in result
        )

        if s > 0:

            for x in result:
                x[key] /= s

    return result


# =========================
# 3連単120通り
# =========================

def combos(rows):

    out = []

    for a, b, c in permutations(
        range(6),
        3
    ):

        score = (
            rows[a]["1着率"]
            *
            rows[b]["2着率"]
            *
            rows[c]["3着率"]
        )

        # 1コース1着を少し評価
        if rows[a]["コース"] == 1:
            score *= 1.05

        out.append({
            "買い目":
            f'{rows[a]["枠"]}-'
            f'{rows[b]["枠"]}-'
            f'{rows[c]["枠"]}',

            "確率": score
        })

    out.sort(
        key=lambda x:
        x["確率"],
        reverse=True
    )

    total = sum(
        x["確率"]
        for x in out
    )

    if total > 0:

        for x in out:

            x["確率"] = (
                x["確率"]
                / total
                * 100
            )

    return out


# =========================
# 実際の結果
# =========================

def actual_result(race):

    rr = race.get(
        "result",
        {}
    ).get(
        "racers",
        []
    )

    if len(rr) < 3:
        return None

    try:

        top = sorted(
            rr,
            key=lambda x:
            num(
                x.get(
                    "place_number"
                ),
                99
            )
        )

        return tuple(
            str(
                top[i][
                    "course_number"
                ]
            )
            for i in range(3)
        )

    except:
        return None


# =========================
# バックテスト
# =========================

@st.cache_data(ttl=1800)
def backtest(target, count=30):

    races = []

    # 過去10日を調査
    for days_ago in range(1, 11):

        d = (
            target
            - timedelta(
                days=days_ago
            )
        )

        data = get_data(d)

        # 404などはスキップ
        if not data:
            continue

        stadiums = data.get(
            "programs",
            {}
        ).get(
            "stadiums",
            {}
        )

        for sid, sdata in stadiums.items():

            for rn, race in sdata.get(
                "races",
                {}
            ).items():

                if actual_result(
                    race
                ) is None:
                    continue

                rows = make_rows(
                    race
                )

                if len(rows) != 6:
                    continue

                races.append({
                    "date": d,
                    "sid": sid,
                    "race": int(rn),
                    "data": race
                })

        if len(races) >= count:
            break

    races.sort(
        key=lambda x:
        (
            x["date"],
            x["race"]
        ),
        reverse=True
    )

    races = races[:count]

    results = []

    for item in races:

        d = item["date"]
        sid = item["sid"]
        race = item["data"]

        # このレースより前のデータだけ
        h = history(
            d,
            10
        )

        rows = make_rows(
            race
        )

        if len(rows) != 6:
            continue

        result_info = race.get(
            "result",
            {}
        )

        wind = num(
            result_info.get(
                "wind_speed"
            )
        )

        wave = num(
            result_info.get(
                "wave_height"
            )
        )

        pred = ai(
            rows,
            sid,
            h,
            wind,
            wave
        )

        cb = combos(
            pred
        )

        actual = actual_result(
            race
        )

        if not actual or not cb:
            continue

        first = max(
            pred,
            key=lambda x:
            x["1着率"]
        )

        second = max(
            pred,
            key=lambda x:
            x["2着率"]
        )

        third = max(
            pred,
            key=lambda x:
            x["3着率"]
        )

        actual_str = "-".join(
            actual
        )

        top5 = [
            x["買い目"]
            for x in cb[:5]
        ]

        top10 = [
            x["買い目"]
            for x in cb[:10]
        ]

        results.append({

            "日付": d,

            "場": sid,

            "R": item["race"],

            "1着予測":
            first["枠"],

            "2着予測":
            second["枠"],

            "3着予測":
            third["枠"],

            "実際1着":
            actual[0],

            "実際2着":
            actual[1],

            "実際3着":
            actual[2],

            "3連単実績":
            actual_str,

            "上位1点":
            cb[0]["買い目"],

            "上位5点的中":
            actual_str in top5,

            "上位10点的中":
            actual_str in top10,

            "本命的中":
            cb[0]["買い目"]
            == actual_str
        })

    return pd.DataFrame(
        results
    )


# =========================
# メイン画面
# =========================

st.title(
    "🚤 やっちゃんの競艇AI予想 PRO"
)

st.caption(
    "全24場対応・過去データ学習・"
    "展示/ST・3連単120通り"
)

target = st.date_input(
    "レース日",
    date.today()
)

data = get_data(
    target
)

if data is None:

    st.warning(
        f"{target.strftime('%Y/%m/%d')}"
        " のデータがAPIにありません。"
    )

    st.info(
        "APIにまだ公開されていない日付、"
        "またはデータ未更新の日付の可能性があります。"
    )

    st.stop()


stadiums = data.get(
    "programs",
    {}
).get(
    "stadiums",
    {}
)

if not stadiums:

    st.warning(
        "場データがありません。"
    )

    st.stop()


sid = st.selectbox(
    "競艇場",
    list(stadiums.keys())
)


races = stadiums[sid].get(
    "races",
    {}
)

if not races:

    st.warning(
        "レースデータがありません。"
    )

    st.stop()


rno = st.selectbox(
    "レース",
    sorted(
        [
            int(x)
            for x in races.keys()
        ]
    )
)


race = get_race(
    data,
    sid,
    rno
)


result_data = race.get(
    "result",
    {}
)

wind = num(
    result_data.get(
        "wind_speed"
    )
)

wave = num(
    result_data.get(
        "wave_height"
    )
)


st.write(
    f"🌬️ 風速: {wind} m　"
    f"🌊 波高: {wave} cm"
)


# =========================
# 選手データ
# =========================

rows = make_rows(
    race
)

st.subheader(
    "選手データ"
)

st.dataframe(
    pd.DataFrame(rows),
    use_container_width=True
)


# =========================
# 学習
# =========================

h = history(
    target,
    10
)

st.info(
    "📚 過去10日間・全24場で学習した"
    f"レース数：{h['total']}"
)


# =========================
# AI
# =========================

pred = ai(
    rows,
    sid,
    h,
    wind,
    wave
)

st.subheader(
    "🤖 AI評価"
)


show = pd.DataFrame([

    {
        "枠": x["枠"],
        "コース": x["コース"],
        "選手": x["選手"],

        "1着率":
        f'{x["1着率"] * 100:.1f}%',

        "2着率":
        f'{x["2着率"] * 100:.1f}%',

        "3着率":
        f'{x["3着率"] * 100:.1f}%',

        "ST順位":
        x["ST順位"],

        "展示順位":
        x["展示順位"]
    }

    for x in pred
])


st.dataframe(
    show,
    use_container_width=True
)


# =========================
# 3連単
# =========================

cb = combos(
    pred
)

st.subheader(
    "🎯 3連単AIランキング TOP10"
)


st.dataframe(

    pd.DataFrame([

        {
            "順位":
            i + 1,

            "買い目":
            x["買い目"],

            "AI確率":
            f'{x["確率"]:.2f}%'
        }

        for i, x
        in enumerate(cb[:10])
    ]),

    use_container_width=True
)


st.success(
    f"🔥 本命：{cb[0]['買い目']}"
)

st.info(
    f"🥈 対抗：{cb[1]['買い目']}"
)

st.warning(
    f"🎲 穴：{cb[4]['買い目']}"
)


# =========================
# 実際の結果
# =========================

ar = actual_result(
    race
)

if ar:

    st.subheader(
        "🏁 実際の結果"
    )

    st.write(
        " → ".join(ar)
    )


# =========================
# バックテスト
# =========================

st.divider()

st.subheader(
    "📊 AIバックテスト"
)

st.write(
    "過去30レースを使い、"
    "各レースより前の10日間だけで"
    "学習して検証します。"
)


if st.button(
    "🚀 過去30レースを検証する"
):

    with st.spinner(
        "過去レースを取得して"
        "AIを検証中..."
    ):

        bt = backtest(
            target,
            30
        )


    if bt.empty:

        st.warning(
            "検証できる過去レースがありません。"
        )

    else:

        total = len(bt)

        first_hit = (
            (
                bt["1着予測"]
                ==
                bt["実際1着"]
            ).mean()
            * 100
        )

        second_hit = (
            (
                bt["2着予測"]
                ==
                bt["実際2着"]
            ).mean()
            * 100
        )

        third_hit = (
            (
                bt["3着予測"]
                ==
                bt["実際3着"]
            ).mean()
            * 100
        )

        top1_hit = (
            bt["本命的中"].mean()
            * 100
        )

        top5_hit = (
            bt["上位5点的中"].mean()
            * 100
        )

        top10_hit = (
            bt["上位10点的中"].mean()
            * 100
        )


        st.success(
            f"検証レース数：{total}レース"
        )


        c1, c2, c3 = st.columns(3)

        c1.metric(
            "1着的中率",
            f"{first_hit:.1f}%"
        )

        c2.metric(
            "2着的中率",
            f"{second_hit:.1f}%"
        )

        c3.metric(
            "3着的中率",
            f"{third_hit:.1f}%"
        )


        c4, c5, c6 = st.columns(3)

        c4.metric(
            "3連単 1点",
            f"{top1_hit:.1f}%"
        )

        c5.metric(
            "3連単 TOP5",
            f"{top5_hit:.1f}%"
        )

        c6.metric(
            "3連単 TOP10",
            f"{top10_hit:.1f}%"
