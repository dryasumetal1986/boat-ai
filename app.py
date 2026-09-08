import streamlit as st
import requests
import pandas as pd
from datetime import date, timedelta
from itertools import permutations

st.set_page_config(page_title="やっちゃんの競艇AI予想 PRO", layout="wide")

STADIUMS = {
    1:"桐生",2:"戸田",3:"江戸川",4:"平和島",5:"多摩川",6:"浜名湖",
    7:"蒲郡",8:"常滑",9:"津",10:"三国",11:"びわこ",12:"住之江",
    13:"尼崎",14:"鳴門",15:"丸亀",16:"児島",17:"宮島",18:"徳山",
    19:"下関",20:"若松",21:"芦屋",22:"福岡",23:"唐津",24:"大村"
}

@st.cache_data(ttl=180)
def get_data(d):
    url = f"https://boatraceopenapi.github.io/api/v1/{d:%Y}/{d:%Y%m%d}.json"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.json()

def get_race(data, sid, rno):
    return data.get("programs", {}).get("stadiums", {}).get(
        str(sid), {}
    ).get("races", {}).get(str(rno))

def n(v, default=0.0):
    try:
        return float(v)
    except:
        return default

def get_preview(preview, entry):
    if not isinstance(preview, dict):
        return {}
    return preview.get(str(entry), preview.get(entry, {})) or {}

def current_rows(race):
    racers = race.get("racers", {})
    preview = race.get("preview", {})
    out = []

    for k, r in racers.items():
        if not isinstance(r, dict):
            continue

        entry = int(n(k, 0))
        p = get_preview(preview, entry)

        course = int(n(p.get("course_number"), entry))
        stt = n(
            p.get("start_timing"),
            n(r.get("average_start_timing"))
        )
        ex = n(p.get("exhibition_time"))

        out.append({
            "枠": entry,
            "コース": course,
            "選手": r.get("name", ""),
            "番号": str(r.get("number", "")),
            "級": r.get("rank_number", ""),
            "全国勝率": n(r.get("national_win_rate")),
            "当地勝率": n(r.get("local_win_rate")),
            "モーター2連率": n(r.get("motor_top_2_percent")),
            "ST": stt,
            "展示": ex
        })

    out.sort(key=lambda x: x["枠"])

    sv = sorted([x["ST"] for x in out if x["ST"] > 0])
    ev = sorted([x["展示"] for x in out if x["展示"] > 0])

    for x in out:
        x["ST順位"] = sv.index(x["ST"]) + 1 if x["ST"] > 0 else 6
        x["展示順位"] = ev.index(x["展示"]) + 1 if x["展示"] > 0 else 6

    return out

@st.cache_data(ttl=900)
def history(target, days=10):
    pc = {}
    vc = {}
    ve = {}
    vs = {}
    races = 0

    for i in range(1, days + 1):
        d = target - timedelta(days=i)

        try:
            data = get_data(d)
        except:
            continue

        stadiums = data.get("programs", {}).get("stadiums", {})

        for sid, sd in stadiums.items():
            for race in sd.get("races", {}).values():

                rr = race.get("result", {}).get("racers", {})
                prog = race.get("racers", {})
                prev = race.get("preview", {})

                if not rr:
                    continue

                items = []

                for k, res in rr.items():
                    if not isinstance(res, dict):
                        continue

                    place = int(n(res.get("place_number"), 0))

                    if place < 1 or place > 6:
                        continue

                    entry = int(n(k, 0))
                    pr = prog.get(str(entry), {}) or {}
                    pv = get_preview(prev, entry)

                    course = int(
                        n(pv.get("course_number"), entry)
                    )

                    stt = n(
                        pv.get("start_timing"),
                        n(pr.get("average_start_timing"))
                    )

                    ex = n(pv.get("exhibition_time"))

                    items.append({
                        "num": str(pr.get("number", "")),
                        "course": course,
                        "place": place,
                        "st": stt,
                        "ex": ex
                    })

                if len(items) < 6:
                    continue

                races += 1

                ev = sorted([x["ex"] for x in items if x["ex"] > 0])
                sv = sorted([x["st"] for x in items if x["st"] > 0])

                for x in items:

                    for store, key in [
                        (pc, (x["num"], x["course"])),
                        (vc, (int(sid), x["course"]))
                    ]:
                        if key not in store:
                            store[key] = {
                                "n": 0,
                                "p1": 0,
                                "p2": 0,
                                "p3": 0
                            }

                        store[key]["n"] += 1

                        if x["place"] == 1:
                            store[key]["p1"] += 1
                        if x["place"] == 2:
                            store[key]["p2"] += 1
                        if x["place"] == 3:
                            store[key]["p3"] += 1

                    er = ev.index(x["ex"]) + 1 if x["ex"] > 0 and ev else 6
                    sr = sv.index(x["st"]) + 1 if x["st"] > 0 and sv else 6

                    for store, key in [
                        (ve, (int(sid), er)),
                        (vs, (int(sid), sr))
                    ]:
                        if key not in store:
                            store[key] = {
                                "n": 0,
                                "p1": 0,
                                "p2": 0,
                                "p3": 0
                            }

                        store[key]["n"] += 1

                        if x["place"] == 1:
                            store[key]["p1"] += 1
                        if x["place"] == 2:
                            store[key]["p2"] += 1
                        if x["place"] == 3:
                            store[key]["p3"] += 1

    return {
        "pc": pc,
        "vc": vc,
        "ve": ve,
        "vs": vs,
        "races": races
    }

def hist_rate(store, key, field, base):
    z = store.get(key)

    if not z or z["n"] <= 0:
        return base

    w = min(z["n"] / 25, 1)

    return base * (1 - w) + (z[field] / z["n"]) * w

def ai(rows, sid, h, wind, wave):

    b1 = {1:.55, 2:.15, 3:.10, 4:.10, 5:.06, 6:.04}
    b2 = {1:.18, 2:.27, 3:.20, 4:.17, 5:.11, 6:.07}
    b3 = {1:.10, 2:.20, 3:.25, 4:.22, 5:.15, 6:.08}

    out = []

    for x in rows:

        lane = x["コース"]

        p1 = b1.get(lane, .05)
        p2 = b2.get(lane, .10)
        p3 = b3.get(lane, .10)

        p1 *= max(.55, 1 + (x["全国勝率"] - 5) * .06)
        p2 *= max(.65, 1 + (x["全国勝率"] - 5) * .035)
        p3 *= max(.70, 1 + (x["全国勝率"] - 5) * .025)

        if x["当地勝率"]:
            p1 *= max(.75, 1 + (x["当地勝率"] - 5) * .035)

        if x["モーター2連率"]:
            p1 *= max(
                .75,
                1 + (x["モーター2連率"] - 35) * .005
            )
            p2 *= max(
                .80,
                1 + (x["モーター2連率"] - 35) * .003
            )

        if x["ST"] > 0:
            if x["ST"] <= .12:
                p1 *= 1.09
            elif x["ST"] <= .15:
                p1 *= 1.05
            elif x["ST"] >= .22:
                p1 *= .94

        if x["展示"] > 0:
            if x["展示"] <= 6.70:
                p1 *= 1.07
                p2 *= 1.04
                p3 *= 1.02
            elif x["展示"] <= 6.75:
                p1 *= 1.04
                p2 *= 1.02
            elif x["展示"] >= 6.90:
                p1 *= .95

        ck = (x["番号"], lane)
        vk = (sid, lane)
        ek = (sid, x["展示順位"])
        sk = (sid, x["ST順位"])

        p1 *= 1 + .35 * (
            hist_rate(
                h["pc"], ck, "p1", p1
            ) / max(p1, .001) - 1
        )

        p2 *= 1 + .20 * (
            hist_rate(
                h["pc"], ck, "p2", p2
            ) / max(p2, .001) - 1
        )

        p3 *= 1 + .15 * (
            hist_rate(
                h["pc"], ck, "p3", p3
            ) / max(p3, .001) - 1
        )

        p1 *= 1 + .15 * (
            hist_rate(
                h["vc"], vk, "p1", b1.get(lane, .05)
            ) / max(b1.get(lane, .05), .01) - 1
        )

        p2 *= 1 + .10 * (
            hist_rate(
                h["vc"], vk, "p2", b2.get(lane, .10)
            ) / max(b2.get(lane, .10), .01) - 1
        )

        p3 *= 1 + .08 * (
            hist_rate(
                h["vc"], vk, "p3", b3.get(lane, .10)
            ) / max(b3.get(lane, .10), .01) - 1
        )

        if x["展示順位"] == 1:
            p1 *= 1.06
            p2 *= 1.03
        elif x["展示順位"] >= 5:
            p1 *= .97

        if x["ST順位"] == 1:
            p1 *= 1.05
        elif x["ST順位"] >= 5:
            p1 *= .97

        p1 *= 1 + .10 * (
            hist_rate(
                h["ve"], ek, "p1", b1.get(lane, .05)
            ) / max(b1.get(lane, .05), .01) - 1
        )

        p1 *= 1 + .07 * (
            hist_rate(
                h["vs"], sk, "p1", b1.get(lane, .05)
            ) / max(b1.get(lane, .05), .01) - 1
        )

        if wind >= 5:
            if lane == 1:
                p1 *= .95
            if lane in [2, 3, 4]:
                p2 *= 1.03
                p3 *= 1.03

        elif wind >= 3 and lane in [2, 3, 4]:
            p2 *= 1.02

        if wave >= 5:
            if lane == 1:
                p1 *= .96
            if lane in [3, 4]:
                p2 *= 1.03
                p3 *= 1.03

        out.append({
            **x,
            "p1": max(p1, .001),
            "p2": max(p2, .001),
            "p3": max(p3, .001)
        })

    for f in ["p1", "p2", "p3"]:

        s = sum(x[f] for x in out)

        for x in out:
            x[f] = x[f] / s if s else 1 / 6

    return out

def combos(rows):

    ans = []

    for a, b, c in permutations(range(6), 3):

        q = (
            rows[a]["p1"] *
            rows[b]["p2"] *
            rows[c]["p3"]
        )

        if rows[a]["コース"] == 1:
            q *= 1.04

        ans.append(
            (
                q,
                f'{rows[a]["枠"]}-{rows[b]["枠"]}-{rows[c]["枠"]}'
            )
        )

    ans.sort(reverse=True)

    total = sum(x[0] for x in ans)

    return [
        (i + 1, k, q / total * 100)
        for i, (q, k) in enumerate(ans)
    ]


st.title("🚤 やっちゃんの競艇AI予想 PRO")

target = st.date_input(
    "開催日",
    date.today()
)

try:
    data = get_data(target)
except Exception as e:
    st.error(f"データ取得エラー：{e}")
    st.stop()

stadiums = data.get(
    "programs", {}
).get("stadiums", {})

available = sorted([
    int(k)
    for k, v in stadiums.items()
    if v.get("races")
])

if not available:
    st.error("開催場がありません")
    st.stop()

sid = st.selectbox(
    "競艇場",
    available,
    format_func=lambda x:
        f"{x} {STADIUMS.get(x, x)}"
)

race_map = stadiums[str(sid)].get(
    "races", {}
)

rno = st.selectbox(
    "レース",
    sorted(int(k) for k in race_map)
)

race = get_race(
    data,
    sid,
    rno
)

if not race:
    st.error("レースデータがありません")
    st.stop()

st.success(
    f"{STADIUMS.get(sid, sid)} {rno}R"
)

preview = race.get(
    "preview",
    {}
) or {}

wind = n(preview.get("wind_speed"))
wave = n(preview.get("wave_height"))

if not wind:
    wind = n(
        race.get("result", {}).get("wind_speed")
    )

if not wave:
    wave = n(
        race.get("result", {}).get("wave_height")
    )

c1, c2 = st.columns(2)

c1.metric(
    "風速",
    f"{wind:.1f} m"
)

c2.metric(
    "波高",
    f"{wave:.1f} cm"
)

rows = current_rows(race)

if not rows:
    st.error("選手データがありません")
    st.stop()

st.write("### 🚤 選手データ")

st.dataframe(
    pd.DataFrame(rows),
    use_container_width=True,
    hide_index=True
)

with st.spinner("過去データを学習中…"):
    h = history(target, 10)

st.info(
    f"📚 過去10日間・全24場 "
    f"{h['races']}レースを学習"
)

airows = ai(
    rows,
    sid,
    h,
    wind,
    wave
)

st.write("## 🤖 AI評価")

adf = pd.DataFrame([
    {
        "枠": x["枠"],
        "コース": x["コース"],
        "選手": x["選手"],
        "全国勝率": round(x["全国勝率"], 2),
        "当地勝率": round(x["当地勝率"], 2),
        "モーター2連率": round(
            x["モーター2連率"], 1
        ),
        "ST": round(x["ST"], 2),
        "展示": round(x["展示"], 2),
        "ST順位": x["ST順位"],
        "展示順位": x["展示順位"],
        "1着率": round(x["p1"] * 100, 1),
        "2着率": round(x["p2"] * 100, 1),
        "3着率": round(x["p3"] * 100, 1)
    }
    for x in airows
])

st.dataframe(
    adf,
    use_container_width=True,
    hide_index=True
)

cs = combos(airows)

st.write("## 🎯 AI 3連単ランキング")

st.dataframe(
    pd.DataFrame([
        {
            "順位": i,
            "買い目": k,
            "確率": f"{q:.2f}%"
        }
        for i, k, q in cs[:10]
    ]),
    use_container_width=True,
    hide_index=True
)

if cs:
    st.success(
        f"🔥 本命：{cs[0][1]} "
        f"{cs[0][2]:.2f}%"
    )

    st.info(
        f"対抗：{cs[1][1]} "
        f"{cs[1][2]:.2f}%"
    )

    st.warning(
        f"穴：{cs[4][1]} "
        f"{cs[4][2]:.2f}%"
    )

st.write("## 🏁 レース結果")

rr = race.get(
    "result", {}
).get("racers", {})

res = []

for k, v in rr.items():

    if isinstance(v, dict):
        res.append({
            "枠": k,
            "着順": v.get(
                "place_number", ""
            ),
            "選手": v.get(
                "name", ""
            )
        })

if res:

    res.sort(
        key=lambda x:
        n(x["着順"], 99)
    )

    st.dataframe(
        pd.DataFrame(res),
        use_container_width=True,
        hide_index=True
    )

    if len(res) >= 3:
        st.write(
            f"実際の3連単："
            f"**{res[0]['枠']}-"
            f"{res[1]['枠']}-"
            f"{res[2]['枠']}**"
        )

else:
    st.info(
        "このレースはまだ結果がありません"
    )

st.caption(
    "※ AIは過去データ・選手成績・コース・展示・ST・"
    "天候などから独自計算しています。"
    "的中・利益を保証するものではありません。"
)

st.caption(
    "※ データは非公式Boatrace Open APIを利用しています。"
                    )
