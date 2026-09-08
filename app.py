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

def n(x, d=0):
    try:
        return float(x)
    except:
        return d

@st.cache_data(ttl=180)
def api(d):
    u = f"https://boatraceopenapi.github.io/api/v1/{d:%Y}/{d:%Y%m%d}.json"
    r = requests.get(u, timeout=20)
    r.raise_for_status()
    return r.json()

def get_race(data, sid, rno):
    try:
        return data["programs"]["stadiums"][str(sid)]["races"][str(rno)]
    except:
        return None

def entries(race):
    ans = []
    rs = race.get("racers", {})
    ps = race.get("preview", {}).get("racers", {})
    for lane in range(1,7):
        a = rs.get(str(lane), {})
        b = ps.get(str(lane), {})
        ans.append({
            "lane":lane,
            "name":a.get("name",""),
            "number":a.get("number",0),
            "national":n(a.get("national_win_rate")),
            "local":n(a.get("local_win_rate")),
            "motor":n(a.get("motor_top_2_percent")),
            "nat2":n(a.get("national_top_2_percent")),
            "st":n(b.get("start_timing",
                    a.get("average_start_timing",.18)),.18),
            "ex":n(b.get("exhibition_time"),6.8)
        })
    return ans

def get_weather(race):
    x = race.get("result", {})
    return {
        "wind":n(x.get("wind_speed")),
        "wave":n(x.get("wave_height")),
        "air":n(x.get("air_temperature")),
        "water":n(x.get("water_temperature"))
    }

@st.cache_data(ttl=900)
def history(target, days):
    out = []
    for z in range(1, days+1):
        d = target - timedelta(days=z)
        try:
            data = api(d)
        except:
            continue

        stadiums = data.get("programs",{}).get("stadiums",{})
        for sid, sd in stadiums.items():
            for rid, race in sd.get("races",{}).items():
                rr = race.get("result",{}).get("racers",{})
                if len(rr) < 6:
                    continue

                prog = race.get("racers",{})
                pre = race.get("preview",{}).get("racers",{})

                # 展示順位・ST順位をレース内で計算
                exs = [n(pre.get(str(i),{}).get("exhibition_time"),6.8)
                       for i in range(1,7)]
                sts = [n(pre.get(str(i),{}).get(
                    "start_timing",
                    prog.get(str(i),{}).get("average_start_timing",.18)),.18)
                       for i in range(1,7)]

                exrank = {
                    i: sorted(exs).index(exs[i-1])+1 for i in range(1,7)
                }
                strank = {
                    i: sorted(sts).index(sts[i-1])+1 for i in range(1,7)
                }

                for lane in range(1,7):
                    a = prog.get(str(lane),{})
                    b = pre.get(str(lane),{})
                    c = rr.get(str(lane),{})
                    place = int(c.get("place_number",0) or 0)

                    if place not in [1,2,3]:
                        continue

                    out.append({
                        "stadium":int(sid),
                        "lane":lane,
                        "number":a.get("number",0),
                        "national":n(a.get("national_win_rate")),
                        "local":n(a.get("local_win_rate")),
                        "motor":n(a.get("motor_top_2_percent")),
                        "st":n(b.get("start_timing",
                              a.get("average_start_timing",.18)),.18),
                        "ex":n(b.get("exhibition_time"),6.8),
                        "exrank":exrank[lane],
                        "strank":strank[lane],
                        "place":place
                    })
    return pd.DataFrame(out)

def stats(df):
    s = {}
    if df.empty:
        return s

    # 場×コース
    for (stad,lane),g in df.groupby(["stadium","lane"]):
        total=len(g)
        if total >= 5:
            s[("sl",stad,lane)] = [
                len(g[g.place==p])/total for p in [1,2,3]
            ]

    # 選手×コース
    for (num,lane),g in df.groupby(["number","lane"]):
        total=len(g)
        if total >= 3:
            s[("pl",num,lane)] = [
                len(g[g.place==p])/total for p in [1,2,3]
            ]

    # 場×展示順位
    for (stad,r),g in df.groupby(["stadium","exrank"]):
        total=len(g)
        if total >= 5:
            s[("ex",stad,r)] = [
                len(g[g.place==p])/total for p in [1,2,3]
            ]

    # 場×ST順位
    for (stad,r),g in df.groupby(["stadium","strank"]):
        total=len(g)
        if total >= 5:
            s[("st",stad,r)] = [
                len(g[g.place==p])/total for p in [1,2,3]
            ]

    return s

def rank(v, reverse=False):
    a=sorted(v, reverse=not reverse)
    if len(a)<=1:
        return 50
    return 100-a.index(v[0]) * 20

def model(rows, stt, sid, weather):
    vals={}
    nat=[x["national"] for x in rows]
    loc=[x["local"] for x in rows]
    mot=[x["motor"] for x in rows]
    sts=[x["st"] for x in rows]
    exs=[x["ex"] for x in rows]

    p1=[];p2=[];p3=[]

    for i,x in enumerate(rows):
        rn=sorted(nat,reverse=True).index(x["national"])
        rl=sorted(loc,reverse=True).index(x["local"])
        rm=sorted(mot,reverse=True).index(x["motor"])
        rs=sorted(sts).index(x["st"])
        re=sorted(exs).index(x["ex"])

        ability=100-rn*8-rl*5-rm*5-rs*4-re*4
        lane=x["lane"]

        base={
            1:18,2:9,3:6,4:7,5:3,6:1
        }[lane]

        # 場×コース
        a=stt.get(("sl",sid,lane),[.10,.15,.16])

        # 選手×コース
        b=stt.get(("pl",x["number"],lane),a)

        q=[a[j]*.65+b[j]*.35 for j in range(3)]

        # 場×展示順位
        er=sorted(exs).index(x["ex"])+1
        exstat=stt.get(("ex",sid,er),[.10,.15,.16])

        # 場×ST順位
        sr=sorted(sts).index(x["st"])+1
        ststat=stt.get(("st",sid,sr),[.10,.15,.16])

        p1.append(max(1,ability+base+q[0]*100*.35+
                      exstat[0]*100*.12+ststat[0]*100*.13))
        p2.append(max(1,ability*.65+q[1]*100*.35+
                      exstat[1]*100*.15+ststat[1]*100*.15))
        p3.append(max(1,ability*.55+q[2]*100*.35+
                      exstat[2]*100*.18+ststat[2]*100*.18))

    # 風・波補正
    for i,x in enumerate(rows):
        if weather["wind"]>=4:
            if x["lane"]==1:
                p1[i]-=4
            if x["lane"] in [3,4]:
                p2[i]+=2
                p3[i]+=1

        if weather["wave"]>=4:
            if x["lane"]==1:
                p1[i]-=3
            if x["lane"] in [3,4]:
                p2[i]+=2
                p3[i]+=2

    return p1,p2,p3

def combinations(rows,p1,p2,p3):
    a=[]
    for x,y,z in permutations(range(6),3):
        score=p1[x]*p2[y]*p3[z]

        # 2着は2～4コースを少し評価
        if rows[y]["lane"] in [2,3,4]:
            score*=1.04

        # 3着は2～5コースを少し評価
        if rows[z]["lane"] in [2,3,4,5]:
            score*=1.03

        a.append({
            "bet":f"{rows[x]['lane']}-{rows[y]['lane']}-{rows[z]['lane']}",
            "score":score
        })

    d=pd.DataFrame(a)
    d["prob"]=d.score/d.score.sum()*100
    return d.sort_values("score",ascending=False).reset_index(drop=True)

# ---------------- UI ----------------

st.title("🚤 やっちゃんの競艇AI予想 PRO")
st.caption("AI 2.1｜全24場・場別学習・展示順位・ST順位・120通り評価")

st.warning("⚠️ 予想は分析用です。的中・利益を保証するものではありません。")

target=st.date_input("開催日",date.today())

c1,c2=st.columns(2)

with c1:
    sid=st.selectbox(
        "競艇場",
        list(STADIUMS),
        format_func=lambda x:f"{x} {STADIUMS[x]}"
    )

with c2:
    rno=st.selectbox("レース",range(1,13))

try:
    data=api(target)
    race=get_race(data,sid,rno)
except Exception:
    st.error("データ取得エラー。少し待って再読み込みしてください。")
    st.stop()

if not race:
    st.warning("このレースのデータがありません。")
    st.stop()

rows=entries(race)
weather=get_weather(race)

st.subheader(f"🌤️ {STADIUMS[sid]} {rno}R")
st.write(
    f"風 {weather['wind']:.0f}m　"
    f"波 {weather['wave']:.0f}cm　"
    f"気温 {weather['air']:.1f}℃　"
    f"水温 {weather['water']:.1f}℃"
)

hist=history(target,14)
stt=stats(hist)

p1,p2,p3=model(rows,stt,sid,weather)

comb=combinations(rows,p1,p2,p3)

# 評価表
table=[]

for i,x in enumerate(rows):
    er=sorted([q["ex"] for q in rows]).index(x["ex"])+1
    sr=sorted([q["st"] for q in rows]).index(x["st"])+1

    table.append({
        "枠":x["lane"],
        "選手":x["name"],
        "全国勝率":round(x["national"],2),
        "当地勝率":round(x["local"],2),
        "モーター2連率":round(x["motor"],1),
        "ST":round(x["st"],2),
        "展示":round(x["ex"],2),
        "展示順位":er,
        "ST順位":sr,
        "1着指数":round(p1[i],1),
        "2着指数":round(p2[i],1),
        "3着指数":round(p3[i],1)
    })

st.subheader("🤖 AI評価")
st.dataframe(pd.DataFrame(table),use_container_width=True)

# 着順候補
st.subheader("🏆 着順別候補")

cols=st.columns(3)

for col,pos,arr in zip(cols,["🥇 1着","🥈 2着","🥉 3着"],[p1,p2,p3]):
    order=sorted(range(6),key=lambda i:arr[i],reverse=True)[:3]
    with col:
        st.write(pos)
        for i in order:
            st.write(
                f"{rows[i]['lane']}号艇 {rows[i]['name']} "
                f"({arr[i]:.1f})"
            )

# 3連単
st.subheader("🎯 3連単AIランキング")

show=comb.head(10).copy()
show["AI確率(%)"]=show["prob"].round(2)

st.dataframe(
    show[["bet","AI確率(%)"]].rename(
        columns={"bet":"3連単"}
    ),
    use_container_width=True
)

st.success(
    f"🔥 AI本命：{comb.iloc[0]['bet']} "
    f"（{comb.iloc[0]['prob']:.2f}%）"
)

st.subheader("🧠 学習状況")
st.write(f"過去14日間の学習データ：**{len(hist):,}件**")
st.write("今回のAIは、選択した競艇場の過去データを優先して評価しています。")

st.caption(
    "※ データは非公式Boatrace Open APIを利用しています。"
    )
