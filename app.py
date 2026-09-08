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
1:"逃げ",2:"差し",3:"まくり",
4:"まくり差し",5:"抜き",6:"恵まれ"
}

def n(x):
try:
return float(x)
except:
return 0

@st.cache_data(ttl=180)
def get_data(d):
u=API+"/"+d.strftime("%Y/%Y%m%d")+".json"
r=requests.get(u,timeout=20)
r.raise_for_status()
return r.json()

def get_race(data,sno,rno):
s=data.get("programs",{}).get("stadiums",{}).get(str(sno))
if not s:
return None
return s.get("races",{}).get(str(rno))

def weather(race):
p=race.get("preview",{})
r=race.get("result",{})

def v(k):  
    x=r.get(k)  
    if x is not None:  
        return x  
    return p.get(k)  

return {  
    "wind":n(v("wind_speed")),  
    "direction":v("wind_direction_number"),  
    "wave":n(v("wave_height")),  
    "air":n(v("air_temperature")),  
    "water":n(v("water_temperature"))  
}

def direction(x):
d={
1:"北",2:"北東",3:"東",4:"南東",
5:"南",6:"南西",7:"西",8:"北西"
}
try:
return d.get(int(x),"コード"+str(x))
except:
return "不明"

def make_df(race):
rs=race.get("racers",{})
ps=race.get("preview",{}).get("racers",{})
rows=[]

for lane in range(1,7):  
    r=rs.get(str(lane),{})  
    p=ps.get(str(lane),{})  

    if not r:  
        continue  

    rows.append({  
        "枠":lane,  
        "選手名":r.get("name","不明"),  
        "選手番号":str(r.get("number","")),  
        "級別":r.get("rank_number",""),  
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

    if d<date(2026,1,1):  
        continue  

    try:  
        data=get_data(d)  
    except:  
        continue  

    ss=data.get("programs",{}).get("stadiums",{})  

    for sno,s in ss.items():  

        for rno,race in s.get("races",{}).items():  

            res=race.get("result",{})  
            rr=res.get("racers",{})  
            preview=race.get("preview",{}).get("racers",{})  

            winner=None  

            for r in rr.values():  
                try:  
                    if int(r.get("place_number"))==1:  
                        winner=str(r.get("number",""))  
                        break  
                except:  
                    pass  

            if not winner:  
                continue  

            for lane in range(1,7):  

                r=race.get("racers",{}).get(str(lane),{})  
                p=preview.get(str(lane),{})  

                if not r:  
                    continue  

                rows.append({  
                    "日付":d,  
                    "場":int(sno),  
                    "レース":int(rno),  
                    "枠":lane,  
                    "選手番号":str(r.get("number","")),  
                    "全国勝率":n(r.get("national_win_rate")),  
                    "全国2連率":n(r.get("national_top_2_percent")),  
                    "当地勝率":n(r.get("local_win_rate")),  
                    "モーター2連率":n(r.get("motor_top_2_percent")),  
                    "平均ST":n(r.get("average_start_timing")),  
                    "展示タイム":n(p.get("exhibition_time")),  
                    "1着":1 if str(r.get("number",""))==winner else 0  
                })  

return pd.DataFrame(rows)

def basic_score(r,w):

s=0  

s+=r["全国勝率"]*10  
s+=r["全国2連率"]*.25  
s+=r["当地勝率"]*5  
s+=r["モーター2連率"]*.12  

stt=r["平均ST"]  

if stt>0:  
    if stt<=.12:  
        s+=12  
    elif stt<=.15:  
        s+=8  
    elif stt<=.18:  
        s+=4  
    elif stt>=.22:  
        s-=4  

lane=int(r["枠"])  
s+={1:20,2:8,3:6,4:7,5:2,6:0}.get(lane,0)  

ex=r["展示タイム"]  

if ex>0:  
    if ex<=6.70:  
        s+=6  
    elif ex<=6.75:  
        s+=4  
    elif ex<=6.80:  
        s+=2  
    elif ex>=6.90:  
        s-=2  

return s

def weather_bonus(r,w):

b=0  
lane=int(r["枠"])  

if w["wind"]>=5:  

    if lane==1:  
        b-=3  

    if lane in [3,4]:  
        b+=2  

elif w["wind"]>=3:  

    if lane in [3,4]:  
        b+=1  

if w["wave"]>=5:  

    if lane==1:  
        b-=2  

    if lane in [3,4]:  
        b+=1  

elif w["wave"]>=3:  

    if lane in [3,4]:  
        b+=1  

return b

def stadium_bonus(no,lane):

if no in [8,18,19,21,24] and lane==1:  
    return 4  

if no==2 and lane in [2,3,4]:  
    return 2  

if no==2 and lane==1:  
    return -1  

if no==3 and lane in [3,4]:  
    return 2  

if no==4 and lane in [2,3,4]:  
    return 1  

return 0

def add_features(df):

df=df.copy()  

df["ST評価"]=0  
df["展示評価"]=0  

for i in df.index:  

    stt=df.loc[i,"平均ST"]  

    if stt>0:  
        if stt<=.12:  
            df.loc[i,"ST評価"]=12  
        elif stt<=.15:  
            df.loc[i,"ST評価"]=8  
        elif stt<=.18:  
            df.loc[i,"ST評価"]=4  
        elif stt>=.22:  
            df.loc[i,"ST評価"]=-4  

    ex=df.loc[i,"展示タイム"]  

    if ex>0:  
        if ex<=6.70:  
            df.loc[i,"展示評価"]=6  
        elif ex<=6.75:  
            df.loc[i,"展示評価"]=4  
        elif ex<=6.80:  
            df.loc[i,"展示評価"]=2  
        elif ex>=6.90:  
            df.loc[i,"展示評価"]=-2  

return df

@st.cache_data(ttl=600)
def learn_weights(td):

hist=make_learning_data(td)  

if hist.empty:  
    return {  
        "course":1.0,  
        "win":1.0,  
        "motor":1.0,  
        "st":1.0,  
        "ex":1.0,  
        "accuracy":0,  
        "races":0  
    }  

hist=add_features(hist)  

groups=[  
    ("course","枠"),  
    ("win","全国勝率"),  
    ("motor","モーター2連率"),  
    ("st","ST評価"),  
    ("ex","展示評価")  
]  

weights={}  

for name,col in groups:  

    if hist[col].nunique()<2:  
        weights[name]=1.0  
        continue  

    a=hist[hist["1着"]==1][col].mean()  
    b=hist[hist["1着"]==0][col].mean()  

    if pd.isna(a) or pd.isna(b) or b==0:  
        weights[name]=1.0  
        continue  

    ratio=a/b  

    if ratio<0.7:  
        ratio=.70  

    if ratio>1.5:  
        ratio=1.5  

    weights[name]=round(ratio,3)  

correct=0  
races=0  

for _,g in hist.groupby(["日付","場","レース"]):  

    if len(g)<2:  
        continue  

    g=g.copy()  

    g["score"]=(  
        g["全国勝率"]*10*weights["win"]+  
        g["モーター2連率"]*.12*weights["motor"]+  
        g["ST評価"]*weights["st"]+  
        g["展示評価"]*weights["ex"]+  
        g["枠"].map({1:20,2:8,3:6,4:7,5:2,6:0})*weights["course"]  
    )  

    pred=g.loc[g["score"].idxmax(),"1着"]  

    if pred==1:  
        correct+=1  

    races+=1  

weights["accuracy"]=round(correct/races*100,1) if races else 0  
weights["races"]=races  

return weights

def final_score(r,w,no,weights):

s=0  

s+=r["全国勝率"]*10*weights["win"]  
s+=r["全国2連率"]*.25  
s+=r["当地勝率"]*5  
s+=r["モーター2連率"]*.12*weights["motor"]  

stt=r["平均ST"]  

if stt>0:  
    if stt<=.12:  
        s+=12*weights["st"]  
    elif stt<=.15:  
        s+=8*weights["st"]  
    elif stt<=.18:  
        s+=4*weights["st"]  
    elif stt>=.22:  
        s-=4*weights["st"]  

lane=int(r["枠"])  

s+={1:20,2:8,3:6,4:7,5:2,6:0}.get(lane,0)*weights["course"]  

cr=r.get("コース1着率",0)  

if cr>=50:  
    s+=12  
elif cr>=40:  
    s+=9  
elif cr>=30:  
    s+=6  
elif cr>=20:  
    s+=3  
elif cr>0:  
    s+=1  

ex=r["展示タイム"]  

if ex>0:  
    if ex<=6.70:  
        s+=6*weights["ex"]  
    elif ex<=6.75:  
        s+=4*weights["ex"]  
    elif ex<=6.80:  
        s+=2*weights["ex"]  
    elif ex>=6.90:  
        s-=2  

s+=weather_bonus(r,w)  
s+=stadium_bonus(no,lane)  

return round(s,1)

st.title("🚤 やっちゃんの競艇AI予想 PRO")

st.write(
"実レース結果からAIの重みを自動調整する検証型AI"
)

st.warning(
"非公式APIを利用しています。最新情報は公式BOATRACEでも確認してください。"
)

c1,c2,c3=st.columns(3)

with c1:
td=st.date_input(
"開催日",
value=date.today(),
min_value=date(2026,1,1)
)

with c2:
sname=st.selectbox(
"競艇場",
list(STADIUMS.values())
)

with c3:
rno=st.selectbox(
"レース",
range(1,13),
format_func=lambda x:str(x)+"R"
)

sno=list(STADIUMS.keys())[
list(STADIUMS.values()).index(sname)
]

if st.button("🚀 AI予想を実行",type="primary"):

try:  

    with st.spinner("🚤 レースデータ取得中..."):  
        data=get_data(td)  

except Exception as e:  

    st.error("データ取得に失敗しました")  
    st.code(str(e))  
    st.stop()  

race=get_race(data,sno,rno)  

if race is None:  

    st.error("このレースのデータがありません")  
    st.stop()  

df=make_df(race)  

if df.empty:  

    st.error("出走表がありません")  
    st.stop()  

w=weather(race)  

with st.spinner("📚 過去14日からAIを学習中..."):  

    weights=learn_weights(td)  

st.subheader("🧠 過去14日AI学習結果")  

a,b,c=st.columns(3)  

with a:  
    st.metric(  
        "検証レース数",  
        str(weights["races"])  
    )  

with b:  
    st.metric(  
        "1着予測的中率",  
        str(weights["accuracy"])+"%"  
    )  

with c:  
    st.metric(  
        "全国勝率の学習係数",  
        str(weights["win"])  
    )  

st.write(  
    "コース係数："+str(weights["course"])+  
    "　モーター係数："+str(weights["motor"])+  
    "　ST係数："+str(weights["st"])+  
    "　展示係数："+str(weights["ex"])  
)  

df["コース1着率"]=0.0  
df["コース出走数"]=0  

with st.spinner("📊 コース実績を計算中..."):  

    hist=make_learning_data(td)  

if not hist.empty:  

    for i in df.index:  

        pn=str(df.loc[i,"選手番号"])  
        lane=int(df.loc[i,"枠"])  

        h=hist[  
            (hist["選手番号"]==pn)&  
            (hist["枠"]==lane)  
        ]  

        df.loc[i,"コース出走数"]=len(h)  

        if len(h)>0:  
            df.loc[i,"コース1着率"]=round(  
                h["1着"].mean()*100,1  
            )  

df["基本AI"]=df.apply(  
    lambda r:round(basic_score(r,w),1),  
    axis=1  
)  

df["風波補正"]=df.apply(  
    lambda r:weather_bonus(r,w),  
    axis=1  
)  

df["場補正"]=df["枠"].apply(  
    lambda x:stadium_bonus(sno,int(x))  
)  

df["学習AI"]=df.apply(  
    lambda r:final_score(r,w,sno,weights),  
    axis=1  
)  

mx=df["学習AI"].max()  

if mx>0:  
    df["AI1着評価"]=(df["学習AI"]/mx*100).round(1)  
else:  
    df["AI1着評価"]=0  

df=df.sort_values(  
    "AI1着評価",  
    ascending=False  
).reset_index(drop=True)  

st.subheader(  
    "🌬️ "+sname+" "+str(rno)+"R コンディション"  
)  

a,b,c,d,e=st.columns(5)  

with a:  
    st.metric("風速",str(w["wind"])+" m")  

with b:  
    st.metric("風向",direction(w["direction"]))  

with c:  
    st.metric("波高",str(w["wave"])+" cm")  

with d:  
    st.metric("気温",str(w["air"])+" ℃")  

with e:  
    st.metric("水温",str(w["water"])+" ℃")  

st.subheader("🤖 AI評価")  

show=[  
    "枠",  
    "選手名",  
    "級別",  
    "全国勝率",  
    "全国2連率",  
    "当地勝率",  
    "モーター2連率",  
    "平均ST",  
    "展示タイム",  
    "コース1着率",  
    "コース出走数",  
    "基本AI",  
    "風波補正",  
    "場補正",  
    "学習AI",  
    "AI1着評価"  
]  

st.dataframe(  
    df[show],  
    use_container_width=True,  
    hide_index=True  
)  

st.subheader("🏆 AI順位")  

for i in range(min(3,len(df))):  

    r=df.iloc[i]  

    if i==0:  
        label="🥇 本命"  
    elif i==1:  
        label="🥈 対抗"  
    else:  
        label="🥉 穴"  

    st.write(  
        label+" "+  
        str(int(r["枠"]))+"号艇 "+  
        str(r["選手名"])+  
        "　AI "+str(r["AI1着評価"])  
    )  

if len(df)>=3:  

    x=int(df.iloc[0]["枠"])  
    y=int(df.iloc[1]["枠"])  
    z=int(df.iloc[2]["枠"])  

    st.subheader("🎯 推奨3連単")  

    st.success(  
        "本線  "+str(x)+"-"+str(y)+"-"+str(z)  
    )  

    st.info(  
        "押さえ  "+str(x)+"-"+str(z)+"-"+str(y)  
    )  

    st.warning(  
        "穴  "+str(y)+"-"+str(x)+"-"+str(z)  
    )  

st.subheader("🧠 AIの考え方")  

st.write(  
    "今回のAIは、過去14日の実レース結果を使って"  
    "全国勝率・モーター・ST・展示・コースの影響度を調整しています。"  
)  

st.write(  
    "過去検証の1着予測的中率："+  
    str(weights["accuracy"])+"%"  
)  

st.caption(  
    "この学習は簡易的な統計モデルです。"  
    "的中や利益を保証するものではありません。"  
)

else:

st.info(  
    "開催日・競艇場・レースを選んで「AI予想を実行」を押してください。"  
)

こ
