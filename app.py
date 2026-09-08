import streamlit as st
import requests
import pandas as pd
from datetime import date, timedelta
from itertools import permutations

st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO",
    layout="wide"
)

BASE = "https://boatraceopenapi.github.io/api/v1"


@st.cache_data(ttl=180)
def get_data(d):
    url = (
        f"{BASE}/{d.year:04d}/"
        f"{d.year:04d}{d.month:02d}{d.day:02d}.json"
    )

    try:
        r = requests.get(url, timeout=20)

        if r.status_code != 200:
            return None

        return r.json()

    except Exception:
        return None


def n(x, default=0.0):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default


def get_race(data, sid, rno):
    return (
        data
        .get("programs", {})
        .get("stadiums", {})
        .get(sid, {})
        .get("races", {})
        .get(str(rno), {})
    )


def normalize_racers(obj):
    """
    APIのracersが
    ・リスト
    ・辞書
    のどちらでも処理できるようにする
    """

    if isinstance(obj, list):
        return [
            x for x in obj
            if isinstance(x, dict)
        ]

    if isinstance(obj, dict):
        out = []

        for key, value in obj.items():

            if isinstance(value, dict):
                item = dict(value)

                if "entry_number" not in item:
                    try:
                        item["entry_number"] = int(key)
                    except Exception:
                        pass

                out.append(item)

        return out

    return []


def pmap(race):
    """
    直前情報を枠番ベースで取得する。
    APIのデータ形式が違っても落ちないようにする。
    """

    out = {}

    preview = race.get("preview", {})

    if not isinstance(preview, dict):
        return out

    racers = normalize_racers(
        preview.get("racers", [])
    )

    for p in racers:

        if not isinstance(p, dict):
            continue

        entry = p.get("entry_number")
        course = p.get("course_number")

        if entry is None and course is not None:
            entry = course

        if entry is None:
            continue

        out[str(entry)] = p

    return out


def make_rows(race):

    pm = pmap(race)

    racers = normalize_racers(
        race.get("racers", [])
    )

    rows = []

    for x in racers:

        if not isinstance(x, dict):
            continue

        entry = x.get("entry_number")

        if entry is None:
            continue

        p = pm.get(
            str(entry),
            {}
        )

        if not isinstance(p, dict):
            p = {}

        course = p.get(
            "course_number",
            entry
        )

        try:
            course = int(course)
        except Exception:
            course = int(entry)

        rows.append({
            "枠": int(entry),
            "コース": course,
            "選手": x.get("name", ""),
            "番号": x.get("number", ""),
            "級": x.get("rank_number", ""),
            "全国勝率": n(
                x.get("national_win_rate")
            ),
            "当地勝率": n(
                x.get("local_win_rate")
            ),
            "モーター2連率": n(
                x.get("motor_top_2_percent")
            ),
            "ST": n(
                p.get("start_timing")
            ),
            "展示": n(
                p.get("exhibition_time")
            )
        })

    rows.sort(
        key=lambda x: x["枠"]
    )

    if not rows:
        return []

    st_order = sorted(
        rows,
        key=lambda x:
        x["ST"] if x["ST"] > 0 else 99
    )

    ex_order = sorted(
        rows,
        key=lambda x:
        x["展示"] if x["展示"] > 0 else 99
    )

    for i, x in enumerate(
        st_order,
        1
    ):
        x["ST順位"] = i

    for i, x in enumerate(
        ex_order,
        1
    ):
        x["展示順位"] = i

    return rows


@st.cache_data(ttl=900)
def history(target, days=10):

    pc = {}
    vc = {}
    ve = {}
    vs = {}

    total = 0

    for k in range(
        1,
        days + 1
    ):

        d = target - timedelta(
            days=k
        )

        data = get_data(d)

        if not data:
            continue

        stadiums = (
            data
            .get("programs", {})
            .get("stadiums", {})
        )

        if not isinstance(
            stadiums,
            dict
        ):
            continue

        for sid, sd in stadiums.items():

            races = sd.get(
                "races",
                {}
            )

            if not isinstance(
                races,
                dict
            ):
                continue

            for race in races.values():

                if not isinstance(
                    race,
                    dict
                ):
                    continue

                rr = normalize_racers(
                    race
                    .get("result", {})
                    .get("racers", [])
                )

                if len(rr) < 6:
                    continue

                pm = pmap(race)

                ex_list = []
                st_list = []

                for entry, p in pm.items():

                    if not isinstance(
                        p,
                        dict
                    ):
                        continue

                    ex_list.append(
                        (
                            entry,
                            n(
                                p.get(
                                    "exhibition_time"
                                )
                            )
                        )
                    )

                    st_list.append(
                        (
                            entry,
                            n(
                                p.get(
                                    "start_timing"
                                )
                            )
                        )

                    )

                ex_list.sort(
                    key=lambda z:
                    z[1] if z[1] > 0 else 99
                )

                st_list.sort(
                    key=lambda z:
                    z[1] if z[1] > 0 else 99
                )

                ex_rank = {
                    c: i
                    for i, (c, _) in enumerate(
                        ex_list,
                        1
                    )
                }

                st_rank = {
                    c: i
                    for i, (c, _) in enumerate(
                        st_list,
                        1
                    )
                }

                for r in rr:

                    numid = r.get(
                        "number"
                    )

                    place = r.get(
                        "place_number"
                    )

                    course = r.get(
                        "course_number"
                    )

                    if (
                        numid is None
                        or course is None
                        or place is None
                    ):
                        continue

                    try:
                        course = int(course)
                        place = int(place)
                    except Exception:
                        continue

                    key = (
                        str(numid),
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

                    if place in (
                        1,
                        2,
                        3
                    ):
                        pc[key][place] += 1
                        vc[
                            (sid, course)
                        ][place] += 1

                    c = str(course)

                    if c in pm:

                        a = (
                            sid,
                            ex_rank.get(
                                c,
                                6
                            )
                        )

                        b = (
                            sid,
                            st_rank.get(
                                c,
                                6
                            )
                        )

                        ve.setdefault(
                            a,
                            [0, 0]
                        )

                        vs.setdefault(
                            b,
                            [0, 0]
                        )

                        ve[a][0] += 1
                        vs[b][0] += 1

                        if place == 1:
                            ve[a][1] += 1
                            vs[b][1] += 1

                total += 1

    return {
        "pc": pc,
        "vc": vc,
        "ve": ve,
        "vs": vs,
        "total": total
    }


def hist_rate(
    dic,
    key,
    pos,
    base
):

    a = dic.get(key)

    if not a or a[0] == 0:
        return base

    w = min(
        a[0] / 25,
        1
    )

    return (
        base * (1 - w)
        + (a[pos] / a[0]) * w
    )


def ai(
    rows,
    sid,
    h,
    wind=0,
    wave=0
):

    ans = []

    base1 = [
        0.36,
        0.18,
        0.14,
        0.11,
        0.08,
        0.06
    ]

    base2 = [
        0.22,
        0.22,
        0.19,
        0.16,
        0.12,
        0.09
    ]

    base3 = [
        0.18,
        0.20,
        0.20,
        0.17,
        0.14,
        0.11
    ]

    for x in rows:

        c = max(
            1,
            min(
                6,
                int(x["コース"])
            )
        )

        p1 = base1[c - 1]
        p2 = base2[c - 1]
        p3 = base3[c - 1]

        nat = x["全国勝率"]
        local = x["当地勝率"]
        motor = x["モーター2連率"]

        p1 *= (
            0.70
            + nat * 0.12
        )

        p1 *= (
            0.90
            + local * 0.05
        )

        p1 *= (
            0.90
            + motor / 100 * 0.30
        )

        if x["ST"] > 0:

            p1 *= max(
                0.75,
                1.10
                - x["ST"] * 3
            )

        if x["展示"] > 0:

            p1 *= max(
                0.82,
                1.08
                - (
                    x["展示"] - 6.7
                ) * 0.8
            )

        player_rate = hist_rate(
            h["pc"],
            (
                str(x["番号"]),
                c
            ),
            1,
            0.20
        )

        p1 *= (
            0.75
            + player_rate
            / 0.20
            * 0.25
        )

        venue_rate = hist_rate(
            h["vc"],
            (
                sid,
                c
            ),
            1,
            base1[c - 1]
        )

        p1 *= (
            0.80
            + venue_rate
            / max(
                base1[c - 1],
                0.01
            )
            * 0.20
        )

        ex_rank = x.get(
            "展示順位",
            6
        )

        st_rank = x.get(
            "ST順位",
            6
        )

        ex_bonus = [
            1.12,
            1.07,
            1.03,
            0.98,
            0.94,
            0.90
        ]

        st_bonus = [
            1.08,
            1.05,
            1.02,
            0.99,
            0.95,
            0.92
        ]

        ex_rank = max(
            1,
            min(6, ex_rank)
        )

        st_rank = max(
            1,
            min(6, st_rank)
        )

        p1 *= ex_bonus[
            ex_rank - 1
        ]

        p1 *= st_bonus[
            st_rank - 1
        ]

        if wind >= 5:

            if c == 1:
                p1 *= 1.04

            elif c >= 4:
                p1 *= 0.97

        if wave >= 5:

            if c <= 2:
                p1 *= 1.02

            else:
                p1 *= 0.98

        p2 *= (
            0.80
            + nat * 0.08
        )

        p2 *= (
            0.90
            + motor / 100 * 0.20
        )

        p3 *= (
            0.82
            + nat * 0.06
        )

        p3 *= (
            0.92
            + motor / 100 * 0.15
        )

        ans.append({
            **x,
            "1着率": p1,
            "2着率": p2,
            "3着率": p3
        })

    for key in (
        "1着率",
        "2着率",
        "3着率"
    ):

        s = sum(
            x[key]
            for x in ans
        )

        if s > 0:

            for x in ans:
                x[key] /= s

    return ans


def combos(rows):

    out = []

    if len(rows) < 6:
        return out

    for a, b, c in permutations(
        range(6),
        3
    ):

        score = (
            rows[a]["1着率"]
            * rows[b]["2着率"]
            * rows[c]["3着率"]
        )

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


def actual(race):

    result = race.get(
        "result",
        {}
    )

    rr = normalize_racers(
        result.get(
            "racers",
            []
        )
    )

    if len(rr) < 3:
        return None

    try:

        rr = sorted(
            rr,
            key=lambda x:
            n(
                x.get(
                    "place_number"
                ),
                99
            )
        )

        ans = []

        for i in range(3):

            course = rr[i].get(
                "course_number"
            )

            if course is None:
                return None

            ans.append(
                str(course)
            )

        return tuple(ans)

    except Exception:
        return None


# =========================
# メイン
# =========================

st.title(
    "🚤 やっちゃんの競艇AI予想 PRO"
)

st.caption(
    "全24場・過去データ学習・"
    "展示/ST・3連単120通り"
)


target = st.date_input(
    "レース日",
    date.today()
)


data = get_data(
    target
)

if not data:

    st.warning(
        f"{target.strftime('%Y/%m/%d')}"
        " のデータがありません。"
    )

    st.stop()


stadiums = (
    data
    .get("programs", {})
    .get("stadiums", {})
)


if not isinstance(
    stadiums,
    dict
) or not stadiums:

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


if not isinstance(
    races,
    dict
) or not races:

    st.warning(
        "レースデータがありません。"
    )

    st.stop()


race_numbers = []

for x in races.keys():

    try:
        race_numbers.append(
            int(x)
        )
    except Exception:
        pass


race_numbers.sort()


if not race_numbers:

    st.warning(
        "レース番号がありません。"
    )

    st.stop()


rno = st.selectbox(
    "レース",
    race_numbers
)


race = get_race(
    data,
    sid,
    rno
)


if not race:

    st.error(
        "レースデータを取得できませんでした。"
    )

    st.stop()


# =========================
# 直前情報・結果
# =========================

res = race.get(
    "result",
    {}
)

if not isinstance(
    res,
    dict
):
    res = {}


wind = n(
    res.get("wind_speed")
)

wave = n(
    res.get("wave_height")
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


if not rows:

    st.error(
        "選手データを取得できませんでした。"
    )

    st.stop()


st.subheader(
    "👤 選手データ"
)

st.dataframe(
    pd.DataFrame(rows),
    use_container_width=True
)


# =========================
# 過去学習
# =========================

with st.spinner(
    "過去10日間のデータを学習中..."
):

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
        "全国勝率":
            x["全国勝率"],
        "当地勝率":
            x["当地勝率"],
        "モーター2連率":
            x["モーター2連率"],
        "ST":
            x["ST"],
        "展示":
            x["展示"],
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


if cb:

    st.subheader(
        "🎯 3連単AIランキング TOP10"
    )

    top10 = pd.DataFrame([

        {
            "順位":
                i + 1,
            "買い目":
                x["買い目"],
            "AI確率":
                f'{x["確率"]:.2f}%'
        }

        for i, x in enumerate(
            cb[:10]
        )

    ])

    st.dataframe(
        top10,
        use_container_width=True
    )

    st.success(
        f"🔥 本命：{cb[0]['買い目']}"
    )

    if len(cb) >= 2:

        st.info(
            f"🥈 対抗：{cb[1]['買い目']}"
        )

    if len(cb) >= 5:

        st.warning(
            f"🎲 穴：{cb[4]['買い目']}"
        )


# =========================
# 実際の結果
# =========================

ar = actual(
    race
)

if ar:

    st.subheader(
        "🏁 実際の結果"
    )

    st.write(
        " → ".join(ar)
    )

else:

    st.caption(
        "🏁 このレースはまだ確定結果がありません。"
    )
