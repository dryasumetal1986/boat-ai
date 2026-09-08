import streamlit as st
import requests
import pandas as pd
from datetime import date, timedelta
from itertools import permutations

st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO",
    layout="wide"
)

STADIUMS = {
    1:"桐生",2:"戸田",3:"江戸川",4:"平和島",
    5:"多摩川",6:"浜名湖",7:"蒲郡",8:"常滑",
    9:"津",10:"三国",11:"びわこ",12:"住之江",
    13:"尼崎",14:"鳴門",15:"丸亀",16:"児島",
    17:"宮島",18:"徳山",19:"下関",20:"若松",
    21:"芦屋",22:"福岡",23:"唐津",24:"大村"
}

TECH = {
    1:"逃げ",
    2:"差し",
    3:"まくり",
    4:"まくり差し",
    5:"抜き",
    6:"恵まれ"
}


# =========================
# データ取得
# =========================

@st.cache_data(ttl=180)
def get_data(d):
    url = (
        f"https://boatraceopenapi.github.io/api/v1/"
        f"{d:%Y}/{d:%Y%m%d}.json"
    )
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.json()


def get_race(data, sid, rno):
    try:
        return data["programs"]["stadiums"][str(sid)]["races"][str(rno)]
    except Exception:
        return None


# =========================
# 数値変換
# =========================

def num(v, default=0.0):
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def racer_number(r):
    return str(
        r.get("number")
        or r.get("registration_number")
        or r.get("player_number")
        or ""
    )


# =========================
# 6艇データを整理
# =========================

def make_current_rows(race):
    racers = race.get("racers", {})
    preview = race.get("preview", {})
    rows = []

    for key, r in racers.items():
        if not isinstance(r, dict):
            continue

        try:
            entry = int(key)
        except Exception:
            entry = int(num(r.get("entry_number"), 0))

        p = {}

        if isinstance(preview, dict):
            p = preview.get(str(entry), {})
            if not p:
                p = preview.get(entry, {})

        if not isinstance(p, dict):
            p = {}

        course = num(
            p.get("course_number"),
            entry
        )

        st_time = num(
            p.get("start_timing"),
            r.get("average_start_timing", 0)
        )

        ex_time = num(
            p.get("exhibition_time"),
            0
        )

        rows.append({
            "枠": entry,
            "コース": int(course) if course else entry,
            "選手": r.get("name", ""),
            "選手番号": racer_number(r),
            "級": r.get("rank_number", ""),
            "全国勝率": num(r.get("national_win_rate")),
            "全国2連率": num(r.get("national_top_2_percent")),
            "当地勝率": num(r.get("local_win_rate")),
            "モーター2連率": num(r.get("motor_top_2_percent")),
            "ST": st_time,
            "展示": ex_time
        })

    rows.sort(key=lambda x: x["枠"])

    if rows:
        st_vals = [x["ST"] for x in rows]
        ex_vals = [x["展示"] for x in rows]

        for x in rows:
            x["ST順位"] = (
                sorted(st_vals).index(x["ST"]) + 1
                if x["ST"] > 0 else 6
            )
            x["展示順位"] = (
                sorted(ex_vals).index(x["展示"]) + 1
                if x["展示"] > 0 else 6
            )

    return rows


# =========================
# 過去データ学習
# =========================

@st.cache_data(ttl=600)
def build_history(target_date, days=10):

    course = {}
    venue_course = {}
    venue_ex = {}
    venue_st = {}
    races = 0

    for dno in range(1, days + 1):

        d = target_date - timedelta(days=dno)

        try:
            data = get_data(d)
        except Exception:
            continue

        stadiums = (
            data.get("programs", {})
            .get("stadiums", {})
        )

        for sid, stadium in stadiums.items():

            races_data = stadium.get("races", {})

            for rno, race in races_data.items():

                result = race.get("result", {})
                result_racers = result.get("racers", {})

                if not result_racers:
                    continue

                racers = race.get("racers", {})
                preview = race.get("preview", {})

                result_rows = []

                for key, rr in result_racers.items():

                    if not isinstance(rr, dict):
                        continue

                    try:
                        place = int(
                            num(rr.get("place_number"), 0)
                        )
                    except Exception:
                        place = 0

                    if place < 1 or place > 6:
                        continue

                    try:
                        entry = int(key)
                    except Exception:
                        entry = int(
                            num(rr.get("entry_number"), 0)
                        )

                    pr = racers.get(str(entry), {})
                    if not isinstance(pr, dict):
                        pr = {}

                    pv = preview.get(str(entry), {})
                    if not isinstance(pv, dict):
                        pv = {}

                    course_no = int(
                        num(
                            pv.get("course_number"),
                            entry
                        )
                    )

                    st_time = num(
                        pv.get("start_timing"),
                        pr.get("average_start_timing", 0)
                    )

                    ex_time = num(
                        pv.get("exhibition_time"),
                        0
                    )

                    number = racer_number(pr)

                    result_rows.append({
                        "number": number,
                        "course": course_no,
                        "place": place,
                        "st": st_time,
                        "ex": ex_time
                    })

                if len(result_rows) < 6:
                    continue

                races += 1

                # 全6艇を学習対象にする
                for x in result_rows:

                    key = (x["number"], x["course"])

                    if key not in course:
                        course[key] = {
                            "n": 0,
                            "p1": 0,
                            "p2": 0,
                            "p3": 0
                        }

                    course[key]["n"] += 1

                    if x["place"] == 1:
                        course[key]["p1"] += 1
                    if x["place"] == 2:
                        course[key]["p2"] += 1
                    if x["place"] == 3:
                        course[key]["p3"] += 1

                # 場×コース
                skey = (int(sid), x["course"])

                # 各艇について記録
                for x in result_rows:

                    skey = (int(sid), x["course"])

                    if skey not in venue_course:
                        venue_course[skey] = {
                            "n": 0,
                            "p1": 0,
                            "p2": 0,
                            "p3": 0
                        }

                    venue_course[skey]["n"] += 1

                    if x["place"] == 1:
                        venue_course[skey]["p1"] += 1
                    if x["place"] == 2:
                        venue_course[skey]["p2"] += 1
                    if x["place"] == 3:
                        venue_course[skey]["p3"] += 1

                # 展示順位
                ex_values = [
                    x["ex"] for x in result_rows
                    if x["ex"] > 0
                ]

                st_values = [
                    x["st"] for x in result_rows
                    if x["st"] > 0
                ]

                for x in result_rows:

                    ex_rank = 6
                    st_rank = 6

                    if x["ex"] > 0 and ex_values:
                        ex_rank = (
                            sorted(ex_values)
                            .index(x["ex"]) + 1
                        )

                    if x["st"] > 0 and st_values:
                        st_rank = (
                            sorted(st_values)
                            .index(x["st"]) + 1
                        )

                    ekey = (int(sid), ex_rank)
                    tkey = (int(sid), st_rank)

                    if ekey not in venue_ex:
                        venue_ex[ekey] = {
                            "n": 0,
                            "p1": 0,
                            "p2": 0,
                            "p3": 0
                        }

                    if tkey not in venue_st:
                        venue_st[tkey] = {
                            "n": 0,
                            "p1": 0,
                            "p2": 0,
                            "p3": 0
                        }

                    venue_ex[ekey]["n"] += 1
                    venue_st[tkey]["n"] += 1

                    if x["place"] == 1:
                        venue_ex[ekey]["p1"] += 1
                        venue_st[tkey]["p1"] += 1

                    if x["place"] == 2:
                        venue_ex[ekey]["p2"] += 1
                        venue_st[tkey]["p2"] += 1

                    if x["place"] == 3:
                        venue_ex[ekey]["p3"] += 1
                        venue_st[tkey]["p3"] += 1

    return {
        "course": course,
        "venue_course": venue_course,
        "venue_ex": venue_ex,
        "venue_st": venue_st,
        "races": races
    }


# =========================
# 平滑した確率
# =========================

def rate(d, key, field, default):

    x = d.get(key)

    if not x:
        return default

    n = x.get("n", 0)

    if n <= 0:
        return default

    raw = x.get(field, 0) / n

    # 少ないデータは全体平均へ寄せる
    weight = min(n / 30.0, 1.0)

    return default * (1 - weight) + raw * weight


# =========================
# AIスコア
# =========================

def make_ai_scores(rows, sid, history, wind, wave):

    # コース基本値
    base_p1 = {
        1: 0.55,
        2: 0.15,
        3: 0.10,
        4: 0.10,
        5: 0.06,
        6: 0.04
    }

    base_p2 = {
        1: 0.18,
        2: 0.27,
        3: 0.20,
        4: 0.17,
        5: 0.11,
        6: 0.07
    }

    base_p3 = {
        1: 0.10,
        2: 0.20,
        3: 0.25,
        4: 0.22,
        5: 0.15,
        6: 0.08
    }

    result = []

    # 全国勝率などの順位を作る
    nw = sorted(
        [x["全国勝率"] for x in rows],
        reverse=True
    )
    lw = sorted(
        [x["当地勝率"] for x in rows],
        reverse=True
    )
    motor = sorted(
        [x["モーター2連率"] for x in rows],
        reverse=True
    )

    for x in rows:

        lane = x["コース"]

        p1 = base_p1.get(lane, 0.05)
        p2 = base_p2.get(lane, 0.10)
        p3 = base_p3.get(lane, 0.10)

        # 選手の基本能力
        if x["全国勝率"] > 0:
            p1 *= 1 + (x["全国勝率"] - 5.0) * 0.07
            p2 *= 1 + (x["全国勝率"] - 5.0) * 0.04
            p3 *= 1 + (x["全国勝率"] - 5.0) * 0.03

        if x["当地勝率"] > 0:
            p1 *= 1 + (x["当地勝率"] - 5.0) * 0.04

        if x["モーター2連率"] > 0:
            p1 *= 1 + (x["モーター2連率"] - 35) * 0.006
            p2 *= 1 + (x["モーター2連率"] - 35) * 0.004
            p3 *= 1 + (x["モーター2連率"] - 35) * 0.003

        # ST
        if x["ST"] > 0:
            if x["ST"] <= 0.12:
                p1 *= 1.10
            elif x["ST"] <= 0.15:
                p1 *= 1.06
            elif x["ST"] >= 0.22:
                p1 *= 0.94

        # 展示
        if x["展示"] > 0:
            if x["展示"] <= 6.70:
                p1 *= 1.07
                p2 *= 1.04
            elif x["展示"] <= 6.75:
                p1 *= 1.04
            elif x["展示"] >= 6.90:
                p1 *= 0.95

        # 選手×コース
        number = x["選手番号"]
        ck = (number, lane)

        p1 *= (
            1 + 0.45 *
            (rate(history["course"], ck, "p1", base_p1.get(lane, 0.05))
             / max(base_p1.get(lane, 0.05), 0.01) - 1)
        )

        p2 *= (
            1 + 0.25 *
            (rate(history["course"], ck, "p2", base_p2.get(lane, 0.10))
             / max(base_p2.get(lane, 0.10), 0.01) - 1)
        )

        p3 *= (
            1 + 0.20 *
            (rate(history["course"], ck, "p3", base_p3.get(lane, 0.10))
             / max(base_p3.get(lane, 0.10), 0.01) - 1)
        )

        # 場×コース
        vk = (sid, lane)

        p1 *= (
            1 + 0.20 *
            (rate(history["venue_course"], vk, "p1",
                  base_p1.get(lane, 0.05))
             / max(base_p1.get(lane, 0.05), 0.01) - 1)
        )

        p2 *= (
            1 + 0.12 *
            (rate(history["venue_course"], vk, "p2",
                  base_p2.get(lane, 0.10))
             / max(base_p2.get(lane, 0.10), 0.01) - 1)
        )

        p3 *= (
            1 + 0.10 *
            (rate(history["venue_course"], vk, "p3",
                  base_p3.get(lane, 0.10))
             / max(base_p3.get(lane, 0.10), 0.01) - 1)
        )

        # 展示順位
        if x["展示順位"] == 1:
            p1 *= 1.08
            p2 *= 1.04
        elif x["展示順位"] == 2:
            p1 *= 1.04
        elif x["展示順位"] >= 5:
            p1 *= 0.96

        # 場ごとの展示順位学習
        ek = (sid, x["展示順位"])

        p1 *= (
            1 + 0.15 *
            (rate(history["venue_ex"], ek, "p1",
                  base_p1.get(lane, 0.05))
             / max(base_p1.get(lane, 0.05), 0.01) - 1)
        )

        # ST順位
        if x["ST順位"] == 1:
            p1 *= 1.06
        elif x["ST順位"] == 2:
            p1 *= 1.03
        elif x["ST順位"] >= 5:
            p1 *= 0.97

        tk = (sid, x["ST順位"])

        p1 *= (
            1 + 0.10 *
            (rate(history["venue_st"], tk, "p1",
                  base_p1.get(lane, 0.05))
             / max(base_p1.get(lane, 0.05), 0.01) - 1)
        )

        # 風・波
        if wind >= 5:
            if lane == 1:
                p1 *= 0.95
            if lane in [2, 3, 4]:
                p2 *= 1.03
                p3 *= 1.03

        elif wind >= 3:
            if lane == 1:
                p1 *= 0.98
            if lane in [2, 3, 4]:
                p2 *= 1.02

        if wave >= 5:
            if lane == 1:
                p1 *= 0.96
            if lane in [3, 4]:
                p2 *= 1.03
                p3 *= 1.03

        elif wave >= 3:
            if lane in [3, 4]:
                p2 *= 1.02

        result.append({
            **x,
            "1着スコア": p1,
            "2着スコア": p2,
            "3着スコア": p3
        })

    # それぞれ正規化
    for field in ["1着スコア", "2着スコア", "3着スコア"]:
        total = sum(x[field] for x in result)

        for x in result:
            x[field] = (
                x[field] / total
                if total > 0 else 1 / 6
            )

    return result


# =========================
# 120通り
# =========================

def trifecta_scores(rows):

    combos = []

    for a, b, c in permutations(range(6), 3):

        score = (
            rows[a]["1着スコア"] *
            rows[b]["2着スコア"] *
            rows[c]["3着スコア"]
        )

        # 1コース1着を少しだけ優先
        if rows[a]["コース"] == 1:
            score *= 1.05

        # 2・3着の内側〜中コースを少し評価
        if rows[b]["コース"] in [2, 3, 4]:
            score *= 1.02

        if rows[c]["コース"] in [2, 3, 4, 5]:
            score *= 1.01

        combos.append({
            "買い目": (
                f'{rows[a]["枠"]}-'
                f'{rows[b]["枠"]}-'
                f'{rows[c]["枠"]}'
            ),
            "1着": rows[a]["選手"],
            "2着": rows[b]["選手"],
            "3着": rows[c]["選手"],
            "スコア": score
        })

    combos.sort(
        key=lambda x: x["スコア"],
        reverse=True
    )

    total = sum(x["スコア"] for x in combos)

    for x in combos:
        x["確率"] = (
            x["スコア"] / total * 100
            if total > 0 else 0
        )

    return combos


# =========================
# メイン画面
# =========================

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

stadiums = (
    data.get("programs", {})
    .get("stadiums", {})
)

if not stadiums:
    st.error("競艇場データがありません")
    st.stop()

available = []

for sid in stadiums:
    try:
        sid2 = int(sid)

        if stadiums[sid].get("races", {}):
            available.append(sid2)

    except Exception:
        pass

available = sorted(available)

if not available:
    st.error("開催中の競艇場がありません")
    st.stop()

stadium = st.selectbox(
    "競艇場",
    available,
    format_func=lambda x:
        f"{x} {STADIUMS.get(x, x)}"
)

races = stadiums[str(stadium)].get(
    "races", {}
)

race_numbers = sorted(
    [int(x) for x in races.keys()]
)

race_no = st.selectbox(
    "レース",
    race_numbers,
    format_func=lambda x:
        f"{x}R"
)

race = get_race(
    data,
    stadium,
    race_no
)

if race is None:
    st.error("レースデータを取得できませんでした")
    st.stop()

st.success(
    f"{STADIUMS.get(stadium, stadium)} "
    f"{race_no}R データ取得成功"
)


# =========================
# 天候
# =========================

preview = race.get("preview", {})

wind = 0
wave = 0
wind_direction = ""

if isinstance(preview, dict):

    wind = num(
        preview.get("wind_speed"),
        0
    )

    wave = num(
        preview.get("wave_height"),
        0
    )

    wind_direction = str(
        preview.get("wind_direction_number", "")
    )

result_data = race.get("result", {})

# 結果側に天候しかない場合も補完
if isinstance(result_data, dict):

    if wind == 0:
        wind = num(
            result_data.get("wind_speed"),
            0
        )

    if wave == 0:
        wave = num(
            result_data.get("wave_height"),
            0
        )

st.write("### 🌤 直前情報")

c1, c2, c3 = st.columns(3)

c1.metric(
    "風速",
    f"{wind:.1f} m"
)

c2.metric(
    "波高",
    f"{wave:.1f} cm"
)

c3.metric(
    "風向番号",
    wind_direction or "-"
)


# =========================
# 選手データ
# =========================

rows = make_current_rows(race)

if not rows:
    st.warning(
        "選手データがありません"
    )
    st.stop()

st.write("### 🚤 出走選手")

display_df = pd.DataFrame(rows)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)


# =========================
# 過去学習
# =========================

with st.spinner(
    "過去データを学習中…"
):

    history = build_history(
        target,
        10
    )

st.info(
    f"📚 過去10日間・全24場から "
    f"{history['races']}レースを学習"
)


# =========================
# AI予想
# =========================

ai_rows = make_ai_scores(
    rows,
    stadium,
    history,
    wind,
    wave
)

st.write("## 🤖 AI評価")

ai_table = []

for x in ai_rows:

    ai_table.append({
        "枠": x["枠"],
        "コース": x["コース"],
        "選手": x["選手"],
        "全国勝率": round(x["全国勝率"], 2),
        "当地勝率": round(x["当地勝率"], 2),
        "モーター2連率": round(
            x["モーター2連率"], 1
        ),
        "ST": round(x["ST"], 2),
        "ST順位": x["ST順位"],
        "展示": round(x["展示"], 2),
        "展示順位": x["展示順位"],
        "1着率": round(
            x["1着スコア"] * 100,
            1
        ),
        "2着率": round(
            x["2着スコア"] * 100,
            1
        ),
        "3着率": round(
            x["3着スコア"] * 100,
            1
        )
    })

ai_df = pd.DataFrame(ai_table)

st.dataframe(
    ai_df,
    use_container_width=True,
    hide_index=True
)


# =========================
# 1着候補
# =========================

ranked = sorted(
    ai_rows,
    key=lambda x: x["1着スコア"],
    reverse=True
)

st.write("### 🥇 1着候補")

for i, x in enumerate(
    ranked[:3],
    1
):

    st.write(
        f"**{i}位 "
        f"{x['枠']}号艇 {x['選手']}** "
        f"1着率 {x['1着スコア']*100:.1f}%"
    )


# =========================
# 3連単120通り
# =========================

combos = trifecta_scores(
    ai_rows
)

st.write("## 🎯 AI 3連単ランキング")

top10 = pd.DataFrame(
    [
        {
            "順位": i + 1,
    
