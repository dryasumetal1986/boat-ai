import streamlit as st,requests,pandas as pd
from datetime import date,timedelta,datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="やっちゃんの競艇AI予想 PRO",page_icon="🚤",layout="wide")
API="https://boatraceopenapi.github.io/api/v1"

STADIUMS={1:"桐生",2:"戸田",3:"江戸川",4:"平和島",5:"多摩川",6:"浜名湖",7:"蒲郡",8:"常滑",9:"津",10:"三国",11:"びわこ",12:"住之江",13:"尼崎",14:"鳴門",15:"丸亀",16:"児島",17:"宮島",18:"徳山",19:"下関",20:"若松",21:"芦屋",22:"福岡",23:"唐津",24:"大村"}

def n(x):
    try:return float(x)
    except:return 0

@st.cache_data(ttl=180)
def get_data(d):
    u=f"{API}/{d:%Y/%Y%m%d}.json"
    r=requests.get(u,timeout=20)
    r.raise_for_status()
    return r.json()

def get_race(data,sno,rno):
    s=data.get("programs",{}).get("stadiums",{}).get(str(sno))
    return s.get("races",{}).get(str(rno)) if s else None

def weather(race):
    p=race.get("preview",{})
    r=race.get("result",{})
    def v(k):return r.get(k) if r.get(k) is not None else p.get(k)
    return {"wind":n(v("wind_speed")),"direction":v("wind_direction_number"),
            "wave":n(v("wave_height")),"air":n(v("air_temperature")),
            "water":n(v("water_temperature"))}

def direction(x):
    d={1:"北",2:"北東",3:"東",4:"南東",5:"南",6:"南西",7:"西",8:"北西"}
    try:return d.get(int(x),"不明")
    except:return "不明"

def racers(x):
    if isinstance(x,list):return x
    if isinstance(x,dict):return list(x.values())
    return []

def pmap(race):
    out={}
    for p in racers(race.get("preview",{}).get("racers",{})):
        e=p.get("entry_number")
        c=p.get("course_number")
        if e is not None:out[str(e)]=p
        if c is not None:out.setdefault(str(c),p)
    return out

def make_df(race):
    rs=race.get("racers",{})
    pm=pmap(race)
    rows=[]
    for lane in range(1,7):
        r=rs.get(str(lane),{}) if isinstance(rs,dict) else {}
        p=pm.get(str(lane),{})
        if not r:continue
        rows.append({
            "枠":lane,"選手名":r.get("name","不明"),
            "選手番号":str(r.get("number","")),"級別":r.get("rank_number",""),
            "全国勝率":n(r.get("national_win_rate")),
            "全国2連率":n(r.get("national_top_2_percent")),
            "当地勝率":n(r.get("local_win_rate")),
            "モーター2連率":n(r.get("motor_top_2_percent")),
            "平均ST":n(r.get("average_start_timing")),
            "展示タイム":n(p.get("exhibition_time"))
        })
    return pd.DataFrame(rows)

@st.cache_data(ttl=600)
def make_learning_data(td):
    rows=[]
    for i in range(1,15):
        d=td-timedelta(days=i)
        if d<date(2026,1,1):continue
        try:data=get_data(d)
        except:continue
        for sno,s in data.get("programs",{}).get("stadiums",{}).items():
            for rno,race in s.get("races",{}).items():
                rr=race.get("result",{}).get("racers",{})
                winner=""
                for r in racers(rr):
                    if str(r.get("place_number"))=="1":
                        winner=str(r.get("number",""));break
                if not winner:continue
                pm=pmap(race)
                rs=race.get("racers",{})
                if not isinstance(rs,dict):continue
                for lane in range(1,7):
                    r=rs.get(str(lane),{})
                    p=pm.get(str(lane),{})
                    if not r:continue
                    rows.append({
                        "日付":d,"場":int(sno),"レース":int(rno),"枠":lane,
                        "選手番号":str(r.get("number","")),
                        "全国勝率":n(r.get("national_win_rate")),
                        "全国2連率":n(r.get("national_top_2_percent")),
                        "当地勝率":n(r.get("local_win_rate")),
                        "モーター2連率":n(r.get("motor_top_2_percent")),
                        "平均ST":n(r.get("average_start_timing")),
                        "展示タイム":n(p.get("exhibition_time")),
                        "1着":int(str(r.get("number",""))==winner)
                    })
    return pd.DataFrame(rows)

def basic_score(r):
    s=r["全国勝率"]*10+r["全国2連率"]*.25+r["当地勝率"]*5+r["モーター2連率"]*.12
    stt=r["平均ST"]
    if 0<stt<=.12:s+=12
    elif stt<=.15 and stt>0:s+=8
    elif stt<=.18 and stt>0:s+=4
    elif stt>=.22:s-=4
    s+={1:20,2:8,3:6,4:7,5:2,6:0}.get(int(r["枠"]),0)
    ex=r["展示タイム"]
    if 0<ex<=6.70:s+=6
    elif ex<=6.75 and ex>0:s+=4
    elif ex<=6.80 and ex>0:s+=2
    elif ex>=6.90:s-=2
    return s

def weather_bonus(r,w):
    lane=int(r["枠"]);b=0
    if w["wind"]>=5:
        if lane==1:b-=3
        elif lane in [3,4]:b+=2
    elif w["wind"]>=3 and lane in [3,4]:b+=1
    if w["wave"]>=5:
        if lane==1:b-=2
        elif lane in [3,4]:b+=1
    elif w["wave"]>=3 and lane in [3,4]:b+=1
    return b

def stadium_bonus(no,lane):
    if no in [8,18,19,21,24] and lane==1:return 4
    if no==2:
        if lane in [2,3,4]:return 2
        if lane==1:return -1
    if no==3 and lane in [3,4]:return 2
    if no==4 and lane in [2,3,4]:return 1
    return 0

@st.cache_data(ttl=600)
def learn_weights(td):
    h=make_learning_data(td)
    if h.empty:return {"course":1,"win":1,"motor":1,"st":1,"ex":1,"accuracy":0,"races":0}
    h["ST評価"]=h["平均ST"].apply(lambda x:12 if 0<x<=.12 else 8 if x<=.15 else 4 if x<=.18 else -4 if x>=.22 else 0)
    h["展示評価"]=h["展示タイム"].apply(lambda x:6 if 0<x<=6.70 else 4 if x<=6.75 else 2 if x<=6.80 else -2 if x>=6.90 else 0)
    ws={}
    for name,col in [("course","枠"),("win","全国勝率"),("motor","モーター2連率"),("st","ST評価"),("ex","展示評価")]:
        a=h.loc[h["1着"]==1,col].mean();b=h.loc[h["1着"]==0,col].mean()
        ratio=a/b if pd.notna(a) and pd.notna(b) and b!=0 else 1
        ws[name]=round(min(1.5,max(.7,ratio)),3)
    correct=races=0
    for _,g in h.groupby(["日付","場","レース"]):
        if len(g)<2:continue
        score=(g["全国勝率"]*10*ws["win"]+
               g["モーター2連率"]*.12*ws["motor"]+
               g["ST評価"]*ws["st"]+g["展示評価"]*ws["ex"]+
               g["枠"].map({1:20,2:8,3:6,4:7,5:2,6:0})*ws["course"])
        correct+=int(g.loc[score.idxmax(),"1着"]==1);races+=1
    ws["accuracy"]=round(correct/races*100,1) if races else 0
    ws["races"]=races
    return ws

def final_score(r,w,no,ws):
    s=(r["全国勝率"]*10*ws["win"]+r["全国2連率"]*.25+
       r["当地勝率"]*5+r["モーター2連率"]*.12*ws["motor"])
    stt=r["平均ST"]
    if stt>0:s+=(12 if stt<=.12 else 8 if stt<=.15 else 4 if stt<=.18 else -4 if stt>=.22 else 0)*ws["st"]
    lane=int(r["枠"])
    s+={1:20,2:8,3:6,4:7,5:2,6:0}[lane]*ws["course"]
    cr=r.get("コース1着率",0)
    s+=12 if cr>=50 else 9 if cr>=40 else 6 if cr>=30 else 3 if cr>=20 else 1 if cr>0 else 0
    ex=r["展示タイム"]
    if ex>0:s+=(6 if ex<=6.70 else 4 if ex<=6.75 else 2 if ex<=6.80 else -2 if ex>=6.90 else 0)*ws["ex"]
    return round(s+weather_bonus(r,w)+stadium_bonus(no,lane),1)

st.title("🚤 やっちゃんの競艇AI予想 PRO")
st.write("実レース結果からAIの重みを自動調整する検証型AI")
st.warning("非公式APIを利用しています。最新情報は公式BOATRACEでも確認してください。")

# 日本時間の「今日」を取得
today=datetime.now(ZoneInfo("Asia/Tokyo")).date()

# 日付が変わった時だけ自動で当日にする
if st.session_state.get("_日付更新確認") != today:
    st.session_state["開催日"] = today
    st.session_state["_日付更新確認"] = today

c1,c2,c3=st.columns(3)

with c1:
    td=st.date_input(
        "開催日",
        min_value=date(2026,1,1),
        key="開催日"
    )

with c2:
    sname=st.selectbox("競艇場",list(STADIUMS.values()))

with c3:
    rno=st.selectbox("レース",range(1,13),format_func=lambda x:f"{x}R")

sno=list(STADIUMS)[list(STADIUMS.values()).index(sname)]

if st.button("🚀 AI予想を実行",type="primary"):
    try:
        with st.spinner("🚤 レースデータ取得中..."):
            data=get_data(td)
    except Exception as e:
        st.error("データ取得に失敗しました")
        st.code(str(e));st.stop()

    race=get_race(data,sno,rno)
    if race is None:
        st.error("このレースのデータがありません");st.stop()

    df=make_df(race)
    if df.empty:
        st.error("出走表がありません");st.stop()

    w=weather(race)

    with st.spinner("📚 過去14日からAIを学習中..."):
        ws=learn_weights(td)

    st.subheader("🧠 過去14日AI学習結果")
    a,b,c=st.columns(3)
    with a:st.metric("検証レース数",str(ws["races"]))
    with b:st.metric("1着予測的中率",str(ws["accuracy"])+"%")
    with c:st.metric("全国勝率の学習係数",str(ws["win"]))
    st.write(f"コース係数：{ws['course']}　モーター係数：{ws['motor']}　ST係数：{ws['st']}　展示係数：{ws['ex']}")

    with st.spinner("📊 コース実績を計算中..."):
        hist=make_learning_data(td)

    df["コース1着率"]=0.0;df["コース出走数"]=0

    if not hist.empty:
        for i in df.index:
            h=hist[(hist["選手番号"]==str(df.loc[i,"選手番号"]))&(hist["枠"]==int(df.loc[i,"枠"]))]
            df.loc[i,"コース出走数"]=len(h)
            if len(h):df.loc[i,"コース1着率"]=round(h["1着"].mean()*100,1)

    df["基本AI"]=df.apply(basic_score,axis=1)
    df["風波補正"]=df.apply(lambda r:weather_bonus(r,w),axis=1)
    df["場補正"]=df["枠"].apply(lambda x:stadium_bonus(sno,int(x)))
    df["学習AI"]=df.apply(lambda r:final_score(r,w,sno,ws),axis=1)

    mx=df["学習AI"].max()
    df["AI1着評価"]=(df["学習AI"]/mx*100).round(1) if mx>0 else 0
    df=df.sort_values("AI1着評価",ascending=False).reset_index(drop=True)

    st.subheader(f"🌬️ {sname} {rno}R コンディション")
    a,b,c,d,e=st.columns(5)
    with a:st.metric("風速",f"{w['wind']} m")
    with b:st.metric("風向",direction(w["direction"]))
    with c:st.metric("波高",f"{w['wave']} cm")
    with d:st.metric("気温",f"{w['air']} ℃")
    with e:st.metric("水温",f"{w['water']} ℃")

    st.subheader("🤖 AI評価")
    show=["枠","選手名","級別","全国勝率","全国2連率","当地勝率","モーター2連率","平均ST","展示タイム","コース1着率","コース出走数","基本AI","風波補正","場補正","学習AI","AI1着評価"]
    st.dataframe(df[show],use_container_width=True,hide_index=True)

    st.subheader("🏆 AI順位")
    for i in range(min(3,len(df))):
        r=df.iloc[i]
        st.write(f"{['🥇 本命','🥈 対抗','🥉 穴'][i]} {int(r['枠'])}号艇 {r['選手名']}　AI {r['AI1着評価']}")

    if len(df)>=3:
        x,y,z=[int(df.iloc[i]["枠"]) for i in range(3)]
        st.subheader("🎯 推奨3連単")
        st.success(f"本線  {x}-{y}-{z}")
        st.info(f"押さえ  {x}-{z}-{y}")
        st.warning(f"穴  {y}-{x}-{z}")

    st.subheader("🧠 AIの考え方")
    st.write("今回のAIは、過去14日の実レース結果を使って全国勝率・モーター・ST・展示・コースの影響度を調整しています。")
    st.write(f"過去検証の1着予測的中率：{ws['accuracy']}%")
    st.caption("この学習は簡易的な統計モデルです。的中や利益を保証するものではありません。")
else:
    st.info("開催日・競艇場・レースを選んで「AI予想を実行」を押してください。")んー
