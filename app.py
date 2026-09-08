import streamlit as st
import requests
import pandas as pd
from datetime import date,timedelta

st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO",
    page_icon="🚤",
    layout="wide"
)

API="https://boatraceopenapi.github.io/api/v1"

STADIUMS={
1:"桐生",2:"戸田",3:"江戸川",4:"平和島",5:"多摩川",6:"浜名湖",
7:"蒲郡",8:"常滑",9:"津",10:"三国",11:"びわこ",12:"住之江",
13:"尼崎",14:"鳴門",15:"丸亀",16:"児島",17:"宮島",18:"徳山",
19:"下関",20:"若松",21:"芦屋",22:"福岡",23:"唐津",24:"大村"
}

TECH={
1:"逃げ",
2:"差し",
3:"まくり",
4:"まくり差し",
5:"抜き",
6:"恵まれ"
}

def num(x):
    try:return float(x)
    except:return 0

@st.cache_data(ttl=180)
def get_data(d):
    y=d.strftime("%Y")
    ymd=d.strftime("%Y%m%d")
    u=API+"/"+y+"/"+ymd+".json"
    r=requests.get(u,timeout=20)
    r.raise_for_status()
    return r.json()

def get_race(data,stadium,race_no):
    ss=data.get("programs",{}).get("stadiums",{})
    s=ss.get(str(stadium))
    if not s:return None
    return s.get("races",{}).get(str(race_no))

def weather(race):
    p=race.get("preview",{})
    r=race.get("result",{})
    return {
        "風速":num(r.get("wind_speed",p.get("wind_speed"))),
        "風向":r.get("wind_direction_number",p.get("wind_direction_number")),
        "波高":num(r.get("wave_height",p.get("wave_height"))),
        "気温":num(r.get("air_temperature",p.get("air_temperature"))),
        "水温":num(r.get("water_temperature",p.get("water_temperature")))
    }

def wind_name(x):
    d={
    1:"北",2:"北東",3:"東",4:"南東",
    5:"南",6:"南西",7:"西",8:"北西"
    }
    try:return d.get(int(x),"不明")
    except:return "不明"

def course_stats(td):
    out={}
    for i in range(1,15):
        d=td-timedelta(days=i)
        if d<date(2026,1,1):continue
        try:data=get_data(d)
        except:continue

        ss=data.get("programs",{}).get("stadiums",{})
        for s in ss.values():
            for race in s.get("races",{}).values():
                for r in race.get("result",{}).get("racers",{}).values():
                    pn=str(r.get("number",""))
                    try:c=int(r.get("course_number"))
                    except:continue
                    if not pn or c<1 or c>6:continue

                    k=(pn,c)
                    if k not in out:out[k]=[0,0]
                    out[k][0]+=1

                    try:
                        if int(r.get("place_number"))==1:
                            out[k][1]+=1
                    except:pass
    return out

def technique_stats(td):
    out={}
    for i in range(1,15):
        d=td-timedelta(days=i)
        if d<date(2026,1,1):continue
        try:data=get_data(d)
        except:continue

        ss=data.get("programs",{}).get("stadiums",{})
        for s in ss.values():
            for race in s.get("races",{}).values():
                result=race.get("result",{})
                try:t=int(result.get("technique_number"))
                except:continue
                if t not in TECH:continue

                winner=None
                for r in result.get("racers",{}).values():
                    try:
                        if int(r.get("place_number"))==1:
                            winner=r
                            break
                    except:pass

                if winner is None:continue
                pn=str(winner.get("number",""))
                if not pn:continue

                k=(pn,t)
                out[k]=out.get(k,0)+1
    return out

def make_df(race):
    rs=race.get("racers",{})
    ps=race.get("preview",{}).get("racers",{})
    rows=[]

    for lane in range(1,7):
        r=rs.get(str(lane),{})
        p=ps.get(str(lane),{})
        if not r:continue

        rows.append({
        "枠":lane,
        "選手名":r.get("name","不明"),
        "選手番号":str(r.get("number","")),
        "級別":r.get("rank_number",""),
        "全国勝率":num(r.get("national_win_rate")),
        "全国2連率":num(r.get("national_top_2_percent")),
        "当地勝率":num(r.get("local_win_rate")),
        "モーター2連率":num(r.get("motor_top_2_percent")),
        "平均ST":num(r.get("average_start_timing")),
        "展示タイム":num(p.get("exhibition_time"))
        })
    return pd.DataFrame(rows)

def add_history(df,cs,ts):
    rates=[]
    starts=[]
    tech_cols={
    1:"逃げ回数",2:"差し回数",3:"まくり回数",
    4:"まくり差し回数",5:"抜き回数",6:"恵まれ回数"
    }

    for _,row in df.iterrows():
        pn=str(row["選手番号"])
        c=int(row["枠"])
        x=cs.get((pn,c),[0,0])
        starts.append(x[0])
        rates.append(round(x[1]/x[0]*100,1) if x[0] else 0)

    df["コース出走数"]=starts
    df["コース1着率"]=rates

    for n,col in tech_cols.items():
        df[col]=[
            ts.get((str(p),n),0)
            for p in df["選手番号"]
        ]

    best=[]
    bestn=[]
    total=[]

    for _,r in df.iterrows():
        vals={n:int(r[col]) for n,col in tech_cols.items()}
        total.append(sum(vals.values()))

        if sum(vals.values())==0:
            best.append("データなし")
            bestn.append(0)
        else:
            n=max(vals,key=vals.get)
            best.append(TECH[n])
            bestn.append(vals[n])

    df["決まり手合計"]=total
    df["得意決まり手"]=best
    df["最多決まり手回数"]=bestn
    return df

def tech_bonus(row):
    lane=int(row["枠"])
    t=row["得意決まり手"]

    if lane==1 and t=="逃げ":return 8
    if lane==2 and t=="差し":return 8
    if lane in [3,4] and t in ["まくり","まくり差し"]:
        return 7
    if lane==5 and t=="まくり差し":return 5
    if lane==6 and t=="まくり差し":return 4
    return 0

def weather_bonus(row,w):
    b=0
    lane=int(row["枠"])
    t=row["得意決まり手"]

    if w["風速"]>=5:
        if lane==1:b-=3
        if t in ["まくり","まくり差し"]:b+=2
    elif w["風速"]>=3:
        if t in ["まくり","まくり差し"]:b+=1

    if w["波高"]>=5:
        if lane==1:b-=2
        if t=="まくり差し":b+=2
    elif w["波高"]>=3:
        if t=="まくり差し":b+=1

    return b

def stadium_bonus(no,lane):
    if no in [8,18,19,21,24] and lane==1:return 4
    if no==3 and lane in [3,4]:return 2
    if no==2 and lane in [2,3,4]:return 2
    if no==2 and lane==1:return -1
    if no==4 and lane in [2,3,4]:return 1
    return 0

def score(r,w,no):
    s=0

    s+=r["全国勝率"]*10
    s+=r["全国2連率"]*.25
    s+=r["当地勝率"]*5
    s+=r["モーター2連率"]*.12

    stt=r["平均ST"]
    if stt>0:
        if stt<=.12:s+=12
        elif stt<=.15:s+=8
        elif stt<=.18:s+=4
        elif stt>=.22:s-=4

    lane=int(r["枠"])
    s+={1:20,2:8,3:6,4:7,5:2,6:0}.get(lane,0)

    cr=r["コース1着率"]
    if cr>=50:s+=12
    elif cr>=40:s+=9
    elif cr>=30:s+=6
    elif cr>=20:s+=3
    elif cr>0:s+=1

    s+=tech_bonus(r)
    s+=weather_bonus(r,w)
    s+=stadium_bonus(no,lane)

    ex=r["展示タイム"]
    if ex>0:
        if ex<=6.70:s+=6
        elif ex<=6.75:s+=4
        elif ex<=6.80:s+=2
        elif ex>=6.90:s-=2

    return s

st.title("🚤 やっちゃんの競艇AI予想 PRO")
st.write("全国24場対応の競艇予想支援アプリ")

st.warning(
    "非公式APIを利用しています。"
    "最新情報は必ず公式BOATRACEで確認してください。"
)

c1,c2,c3=st.columns(3)

with c1:
    td=st.date_input(
        "開催日",
        value=date.today(),
        min_value=date(2026,1,1)
    )

with c2:
    stadium_name=st.selectbox(
        "競艇場",
        list(STADIUMS.values())
    )

with c3:
    race_no=st.selectbox(
        "レース",
        list(range(1,13)),
        format_func=lambda x:str(x)+"R"
    )

stadium_no=list(STADIUMS.keys())[
    list(STADIUMS.values()).index(stadium_name)
]

if st.button("🚀 AI予想を実行",type="primary"):

    try:
        with st.spinner("🚤 レースデータ取得中..."):
            data=get_data(td)
    except Exception as e:
        st.error("データ取得に失敗しました")
        st.code(str(e))
        st.stop()

    race=get_race(data,stadium_no,race_no)

    if race is None:
        st.error("このレースのデータがありません")
        st.stop()

    df=make_df(race)

    if df.empty:
        st.error("出走表がありません")
        st.stop()

    w=weather(race)

    with st.spinner("📊 過去14日分を分析中..."):
        cs=course_stats(td)
        ts=technique_stats(td)

    df=add_history(df,cs,ts)

    df["決まり手補正"]=df.apply(
        tech_bonus,
        axis=1
    )

    df["風波補正"]=df.apply(
        lambda r:weather_bonus(r,w),
        axis=1
    )

    df["場補正"]=df["枠"].apply(
        lambda x:stadium_bonus(stadium_no,int(x))
    )

    df["AIスコア"]=df.apply(
        lambda r:score(r,w,stadium_no),
        axis=1
    )

    mx=df["AIスコア"].max()

    df["AI1着評価"]=(
        df["AIスコア"]/mx*100
    ).round(1) if mx>0 else 0

    df=df.sort_values(
        "AI1着評価",
        ascending=False
    ).reset_index(drop=True)

    st.subheader(
        stadium_name+" "+str(race_no)+"R"
    )

    st.subheader("🌬️ レースコンディション")

    w1,w2,w3,w4,w5=st.columns(5)

    with w1:
        st.metric("風速",str(w["風速"])+" m")

    with w2:
        st.metric("風向",wind_name(w["風向"]))

    with w3:
        st.metric("波高",str(w["波高"])+" cm")

    with w4:
        st.metric("気温",str(w["気温"])+" ℃")

    with w5:
        st.metric("水温",str(w["水温"])+" ℃")

    st.subheader("📋 AI評価")

    cols=[
    "枠","選手名","級別",
    "全国勝率","当地勝率","モーター2連率",
    "平均ST","展示タイム",
    "コース1着率","コース出走数",
    "逃げ回数","差し回数","まくり回数",
    "まくり差し回数","抜き回数","恵まれ回数",
    "決まり手合計","得意決まり手",
    "最多決まり手回数",
    "決まり手補正","風波補正","場補正",
    "AI1着評価"
    ]

    st.dataframe(
        df[cols],
        use_container_width=True,
        hide_index=True
    )

    top=df.iloc[0]

    st.subheader("🏆 AI注目選手")

    st.success(
        "本命 "+
        str(int(top["枠"]))+"号艇 "+
        str(top["選手名"])+
        "　得意決まり手 "+
        str(top["得意決まり手"])+
        "　"+str(int(top["最多決まり手回数"]))+
        "回　AI評価 "+
        str(top["AI1着評価"])
    )

    if len(df)>=2:
        r=df.iloc[1]
        st.info(
            "対抗 "+
            str(int(r["枠"]))+"号艇 "+
            str(r["選手名"])+
            "　"+str(r["得意決まり手"])
        )

    if len(df)>=3:
        r=df.iloc[2]
        st.info(
            "穴 "+
            str(int(r["枠"]))+"号艇 "+
            str(r["選手名"])+
            "　"+str(r["得意決まり手"])
        )

    if len(df)>=3:

        a=int(df.iloc[0]["枠"])
        b=int(df.iloc[1]["枠"])
        c=int(df.iloc[2]["枠"])

        st.subheader("🎯 推奨3連単")

        st.write(
            "本線 "+
            str(a)+"-"+str(b)+"-"+str(c)
        )

        st.write(
            "押さえ "+
            str(a)+"-"+str(c)+"-"+str(b)
        )

        st.write(
            "穴 "+
            str(b)+"-"+str(a)+"-"+str(c)
        )

    st.subheader("🧠 AI分析")

    st.write("・選手能力")
    st.write("・コース別1着率")
    st.write("・決まり手実績")
    st.write("・風速 / 風向")
    st.write("・波高")
    st.write("・気温 / 水温")
    st.write("・競艇場別補正")
    st.write("・展示タイム")

    st.divider()

    st.caption(
        "AI評価は独自計算による予想値です。"
        "的中や利益を保証するものではありません。"
    )

else:
    st.info("競艇場とレースを選んでください")
