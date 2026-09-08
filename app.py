import streamlit as st
import requests
import pandas as pd
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo

st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO",
    page_icon="🚤",
    layout="wide"
)

API = "https://boatraceopenapi.github.io/api/v1"

STADIUMS = {
    1:"桐生",2:"戸田",3:"江戸川",4:"平和島",
    5:"多摩川",6:"浜名湖",7:"蒲郡",8:"常滑",
    9:"津",10:"三国",11:"びわこ",12:"住之江",
    13:"尼崎",14:"鳴門",15:"丸亀",16:"児島",
    17:"宮島",18:"徳山",19:"下関",20:"若松",
    21:"芦屋",22:"福岡",23:"唐津",24:"大村"
}

def racers(x):
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        return list(x.values())
    return []

@st.cache_data(ttl=180)
def get_data(d):
    u = API + "/" + d.strftime("%Y/%Y%m%d") + ".json"
    try:
        r = requests.get(u, timeout=15)
        if r.status_code != 200:
            return {}
        return r.json()
    except:
        return {}

def pmap(race):
    out = {}
    ps = race.get("preview", {}).get("racers", {})
    for p in racers(ps):
        e = p.get("entry_number")
        c = p.get("course_number")

        if e is not None:
            out[str(e)] = p

        if c is not None:
            out.setdefault(str(c), p)

    return out

def make_df(race):
    rows = []
    rs = race.get("racers", {})
    pm = pmap(race)

    for lane in range(1, 7):
        r = rs.get(str(lane), {})
        if not isinstance(r, dict):
            r = {}

        pv = pm.get(str(lane), {})

        rows.append({
            "艇": lane,
            "選手": r.get("name", "不明"),
            "級別": r.get("rank_number", ""),
            "全国勝率": r.get("national_win_rate", 0),
            "全国2連率": r.get("national_top_2_percent", 0),
            "当地勝率": r.get("local_win_rate", 0),
            "モーター2連率": r.get("motor_top_2_percent", 0),
            "平均ST": r.get("average_start_timing", 0),
            "展示": pv.get("exhibition_time", 0),
            "展示ST": pv.get("start_timing", 0)
        })

    return pd.DataFrame(rows)

def make_learning_data(target_date):
    data = []

    for n in range(1, 15):
        d = target_date - timedelta(days=n)
        js = get_data(d)

        if not js:
            continue

        stadiums = js.get("programs", {}).get("stadiums", {})

        for sid, stadium in stadiums.items():
            races = stadium.get("races", {})

            for rid, race in races.items():
                result = race.get("result", {})
                result_racers = racers(result.get("racers", {}))

                winner = None

                for x in result_racers:
                    if str(x.get("place_number")) == "1":
                        winner = str(
                            x.get("course_number")
                            or x.get("entry_number")
                            or ""
                        )
                        break

                if not winner:
                    continue

                rs = race.get("racers", {})

                for lane in range(1, 7):
                    r = rs.get(str(lane), {})

                    if not isinstance(r, dict):
                        continue

                    pm = pmap(race)
                    pv = pm.get(str(lane), {})

                    try:
                        course = lane
                        win = float(r.get("national_win_rate") or 0)
                        motor = float(r.get("motor_top_2_percent") or 0)
                        stv = float(
                            r.get("average_start_timing") or 0
                        )
                        ex = float(
                            pv.get("exhibition_time") or 0
                        )
                    except:
                        continue

                    data.append({
                        "course": course,
                        "win": win,
                        "motor": motor,
                        "st": stv,
                        "exhibition": ex,
                        "target": 1 if str(lane) == winner else 0
                    })

    return pd.DataFrame(data)

def course_first_rate(df):
    result = {}

    for c in range(1, 7):
        x = df[df["course"] == c]

        if len(x) == 0:
            result[c] = 0
        else:
            result[c] = float(x["target"].mean())

    return result

def learn_weights(ldf):
    default = {
        "course": 1.0,
        "win": 1.0,
        "motor": 1.0,
        "st": 1.0,
        "exhibition": 1.0
    }

    if ldf.empty:
        return default, 0.0

    weights = {}

    base = ldf["target"].mean()

    if base <= 0:
        return default, 0.0

    cr = course_first_rate(ldf)

    c1 = cr.get(1, base)

    weights["course"] = max(
        0.7,
        min(1.5, c1 / base)
    )

    avg_win = ldf["win"].mean()

    if avg_win > 0:
        weights["win"] = 1.0

    avg_motor = ldf["motor"].mean()

    if avg_motor > 0:
        weights["motor"] = 1.0

    avg_st = ldf["st"].mean()

    if avg_st > 0:
        weights["st"] = 1.0

    avg_ex = ldf["exhibition"].mean()

    if avg_ex > 0:
        weights["exhibition"] = 1.0

    correct = 0
    total = 0

    for _, row in ldf.iterrows():
        score = (
            row["course"] * weights["course"]
            + row["win"] * weights["win"] * 0.1
            + row["motor"] * weights["motor"] * 0.03
        )

        if row["st"] > 0:
            score += (0.2 - row["st"]) * weights["st"]

        if row["exhibition"] > 0:
            score += (
                6.8 - row["exhibition"]
            ) * weights["exhibition"]

        pred = 1 if score > 1.0 else 0

        if pred == row["target"]:
            correct += 1

        total += 1

    acc = correct / total if total else 0

    return weights, acc

def basic_score(row, c_rate):
    course = int(row["艇"])

    score = 0

    score += c_rate.get(course, 0) * 100

    try:
        score += float(row["全国勝率"]) * 8
    except:
        pass

    try:
        score += float(row["当地勝率"]) * 4
    except:
        pass

    try:
        score += float(row["モーター2連率"]) * 0.5
    except:
        pass

    try:
        stv = float(row["平均ST"])
        if stv > 0:
            score += (0.2 - stv) * 30
    except:
        pass

    try:
        ex = float(row["展示"])
        if ex > 0:
            score += (6.8 - ex) * 20
    except:
        pass

    return score

def learned_score(row, c_rate, weights):
    course = int(row["艇"])

    score = 0

    score += (
        c_rate.get(course, 0)
        * 100
        * weights["course"]
    )

    try:
        score += (
            float(row["全国勝率"])
            * 8
            * weights["win"]
        )
    except:
        pass

    try:
        score += (
            float(row["モーター2連率"])
            * 0.5
            * weights["motor"]
        )
    except:
        pass

    try:
        stv = float(row["平均ST"])

        if stv > 0:
            score += (
                (0.2 - stv)
                * 30
                * weights["st"]
            )
    except:
        pass

    try:
        ex = float(row["展示"])

        if ex > 0:
            score += (
                (6.8 - ex)
                * 20
                * weights["exhibition"]
            )
    except:
        pass

    return score

st.title("🚤 やっちゃんの競艇AI予想 PRO")
st.caption("過去データ学習 × 展示 × ST × モーター × 選手力")

today = datetime.now(
    ZoneInfo("Asia/Tokyo")
).date()

if st.session_state.get("_auto_date") != today:
    st.session_state["開催日"] = today
    st.session_state["_auto_date"] = today

c1, c2, c3 = st.columns(3)

with c1:
    td = st.date_input(
        "開催日",
        min_value=date(2026, 1, 1),
        key="開催日"
    )

with c2:
    stadium_id = st.selectbox(
        "競艇場",
        list(STADIUMS.keys()),
        format_func=lambda x: (
            f"{x} {STADIUMS[x]}"
        )
    )

with c3:
    race_no = st.selectbox(
        "レース",
        range(1, 13),
        format_func=lambda x: f"{x}R"
    )

data = get_data(td)

if not data:
    st.error(
        f"{td.strftime('%Y/%m/%d')} のデータを取得できませんでした。"
    )
    st.stop()

stadiums = data.get(
    "programs", {}
).get("stadiums", {})

stadium = (
    stadiums.get(str(stadium_id))
    or stadiums.get(stadium_id)
)

if not stadium:
    st.warning("この日の競艇場データがありません。")
    st.stop()

races = stadium.get("races", {})

race = (
    races.get(str(race_no))
    or races.get(race_no)
)

if not race:
    st.warning("このレースのデータがありません。")
    st.stop()

df = make_df(race)

st.subheader(
    f"{STADIUMS[stadium_id]} {race_no}R"
)

st.dataframe(
    df,
    use_container_width=True,
    hide_index=True
)

result = race.get("result", {})

if result:
    w = result.get("wind_speed")
    wd = result.get("wind_direction_number")
    wave = result.get("wave_height")
    air = result.get("air_temperature")
    water = result.get("water_temperature")

    st.subheader("🌤️ 天候・水面")

    a, b, c, d, e = st.columns(5)

    a.metric("風速", f"{w}m" if w is not None else "-")
    b.metric("風向", str(wd) if wd is not None else "-")
    c.metric("波高", f"{wave}cm" if wave is not None else "-")
    d.metric("気温", f"{air}℃" if air is not None else "-")
    e.metric("水温", f"{water}℃" if water is not None else "-")

ldf = make_learning_data(td)

c_rate = course_first_rate(ldf)

weights, acc = learn_weights(ldf)

st.subheader("📚 過去14日間 学習")

x1, x2 = st.columns(2)

with x1:
    st.metric(
        "学習データ数",
        f"{len(ldf):,}件"
    )

with x2:
    st.metric(
        "1着予測一致率",
        f"{acc * 100:.1f}%"
    )

st.subheader("📊 コース別1着率")

course_df = pd.DataFrame({
    "コース": [
        f"{x}コース" for x in range(1, 7)
    ],
    "1着率": [
        c_rate.get(x, 0)
        for x in range(1, 7)
    ]
})

course_df["1着率"] = (
    course_df["1着率"] * 100
).round(1)

st.dataframe(
    course_df,
    use_container_width=True,
    hide_index=True
)

df["基本AI"] = df.apply(
    lambda r: basic_score(r, c_rate),
    axis=1
)

df["学習AI"] = df.apply(
    lambda r: learned_score(
        r,
        c_rate,
        weights
    ),
    axis=1
)

ranked = df.sort_values(
    "学習AI",
    ascending=False
).reset_index(drop=True)

st.subheader("🤖 AIランキング")

show = ranked[
    [
        "艇",
        "選手",
        "級別",
        "全国勝率",
        "当地勝率",
        "モーター2連率",
        "平均ST",
        "展示",
        "基本AI",
        "学習AI"
    ]
].copy()

st.dataframe(
    show,
    use_container_width=True,
    hide_index=True
)

top3 = ranked.head(3)["艇"].tolist()

if len(top3) >= 3:
    a, b, c = top3

    st.subheader("🎯 AI三連単予想")

    st.success(
        f"本線　{a}-{b}-{c}"
    )

    st.info(
        f"押さえ {a}-{c}-{b}"
    )

    st.warning(
        f"穴　　{b}-{a}-{c}"
    )

st.caption(
    "※このAIは予測支援用です。投票は自己責任でお願いします。"
                               )
