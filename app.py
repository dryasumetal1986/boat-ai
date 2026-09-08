import streamlit as st,requests,pandas as pd
from datetime import date,timedelta
from itertools import permutations
from sklearn.ensemble import RandomForestClassifier

st.set_page_config(page_title="やっちゃんの競艇AI PRO",page_icon="🚤",layout="wide")

API="https://boatraceopenapi.github.io/api/v1"
STADIUMS={1:"桐生",2:"戸田",3:"江戸川",4:"平和島",5:"多摩川",6:"浜名湖",7:"蒲郡",8:"常滑",9:"津",10:"三国",11:"びわこ",12:"住之江",13:"尼崎",14:"鳴門",15:"丸亀",16:"児島",17:"宮島",18:"徳山",19:"下関",20:"若松",21:"芦屋",22:"福岡",23:"唐津",24:"大村"}

def n(x):
    try:return float(x)
    except:return 0

@st.cache_data(ttl=300)
def get_data(d):
    r=requests.get(f"{API}/{d:%Y/%m/%d}.json",timeout=15)
    r.raise_for_status()
    return r.json()

def get_race(data,sno,rno):
    return data.get("programs",{}).get("stadiums",{}).get(str(sno),{}).get("races",{}).get(str(rno))

def weather(r):
    p=r.get("preview",{});q=r.get("result",{})
    def v(k):return q.get(k) if q.get(k)!=None else p.get(k)
    return {"wind":n(v("wind_speed")),"wave":n(v("wave_height")),"air":n(v("air_temperature")),"water":n(v("water_temperature")),"dir":v("wind_direction_number")}

def direction(x):
    return {1:"北",2:"北東",3:"東",4:"南東",5:"南",6:"南西",7:"西",8:"北西"}.get(int(x) if str(x).isdigit() else 0,"不明")

def race_df(r):
    rr=r.get("racers",{});pp=r.get("preview",{}).get("racers",{});a=[]
    for lane in range(1,7):
        x=rr.get(str(lane),{});p=pp.get(str(lane),{})
        if x:
            a.append({
                "枠":lane,
                "選手名":x.get("name","不明"),
                "級別":x.get("rank_number",""),
                "選手番号":str(x.get("number","")),
                "全国勝率":n(x.get("national_win_rate")),
                "全国2連率":n(x.get("national_top_2_percent")),
                "当地勝率":n(x.get("local_win_rate")),
                "モーター2連率":n(x.get("motor_top_2_percent")),
                "平均ST":n(x.get("average_start_timing")),
                "展示タイム":n(p.get("exhibition_time"))
            })
    return pd.DataFrame(a)

@st.cache_data(ttl=3600)
def learning_data(td,days):
    a=[]
    for i in range(1,days+1):
        d=td-timedelta(days=i)
        if d<date(2026,1,1):continue
        try:data=get_data(d)
        except:continue
        ss=data.get("programs",{}).get("stadiums",{})
        for sno,s in ss.items():
            for rno,r in s.get("races",{}).items():
                rr=r.get("result",{}).get("racers",{})
                win=""
                for x in rr.values():
                    if str(x.get("place_number"))=="1":
                        win=str(x.get("number",""));break
                if not win:continue
                racers=r.get("racers",{})
                pre=r.get("preview",{}).get("racers",{})
                for lane in range(1,7):
                    x=racers.get(str(lane),{})
                    p=pre.get(str(lane),{})
                    if not x:continue
                    a.append({
                        "日付":d,
                        "場":int(sno),
                        "レース":int(rno),
                        "枠":lane,
                        "全国勝率":n(x.get("national_win_rate")),
                        "全国2連率":n(x.get("national_top_2_percent")),
                        "当地勝率":n(x.get("local_win_rate")),
                        "モーター2連率":n(x.get("motor_top_2_percent")),
                        "平均ST":n(x.get("average_start_timing")),
                        "展示タイム":n(p.get("exhibition_time")),
                        "1着":int(str(x.get("number",""))==win)
                    })
    return pd.DataFrame(a)

FEATURES=["枠","全国勝率","全国2連率","当地勝率","モーター2連率","平均ST","展示タイム","ST順位","展示順位","勝率順位","モーター順位","全国勝率差","モーター差","ST差","展示差"]

def features(df):
    df=df.copy()
    df["ST順位"]=df["平均ST"].replace(0,99).rank(method="min")
    df["展示順位"]=df["展示タイム"].replace(0,99).rank(method="min")
    df["勝率順位"]=(-df["全国勝率"]).rank(method="min")
    df["モーター順位"]=(-df["モーター2連率"]).rank(method="min")
    df["全国勝率差"]=df["全国勝率"]-df["全国勝率"].mean()
    df["モーター差"]=df["モーター2連率"]-df["モーター2連率"].mean()
    sm=df["平均ST"].replace(0,pd.NA).mean()
    em=df["展示タイム"].replace(0,pd.NA).mean()
    df["ST差"]=sm-df["平均ST"] if pd.notna(sm) else 0
    df["展示差"]=em-df["展示タイム"] if pd.notna(em) else 0
    return df.fillna(0)

def train_model(h):
    h=h.sort_values("日付").reset_index(drop=True)
    cut=int(len(h)*.8)
    tr=h.iloc[:cut]
    va=h.iloc[cut:]

    model=RandomForestClassifier(
        n_estimators=160,
        max_depth=7,
        min_samples_leaf=4,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )

    model.fit(features(tr)[FEATURES],tr["1着"])

    correct=races=0

    for _,g in va.groupby(["日付","場","レース"]):
        if len(g)<2:continue
        z=features(g)
        p=model.predict_proba(z[FEATURES])[:,list(model.classes_).index(1)]
        if int(g.iloc[p.argmax()]["1着"])==1:correct+=1
        races+=1

    acc=round(correct/races*100,1) if races else 0
    return model,acc,races

def predict(model,df):
    z=features(df)
    p=model.predict_proba(z[FEATURES])[:,list(model.classes_).index(1)]
    df=df.copy()
    df["1着確率"]=(p*100).round(1)
    return df.sort_values("1着確率",ascending=False).reset_index(drop=True)

def trifecta(df):
    p=dict(zip(df["枠"],df["1着確率"]/100))
    a=[]
    for x,y,z in permutations(df["枠"],3):
        a.append({"買い目":f"{x}-{y}-{z}","スコア":p[x]*p[y]*p[z]})
    return pd.DataFrame(a).sort_values("スコア",ascending=False).reset_index(drop=True)

st.title("🚤 やっちゃんの競艇AI予想 PRO")
st.caption("高速版｜機械学習＋過去データ分析")

st.warning("非公式APIを利用しています。最新情報は公式BOATRACEでも確認してください。")

if "model" not in st.session_state:
    st.session_state.model=None
if "accuracy" not in st.session_state:
    st.session_state.accuracy=0
if "races" not in st.session_state:
    st.session_state.races=0

c1,c2,c3=st.columns(3)

with c1:
    td=st.date_input("開催日",date.today(),min_value=date(2026,1,1))

with c2:
    sname=st.selectbox("競艇場",list(STADIUMS.values()))

with c3:
    rno=st.selectbox("レース",range(1,13),format_func=lambda x:f"{x}R")

sno=list(STADIUMS)[list(STADIUMS.values()).index(sname)]

c1,c2=st.columns(2)

with c1:
    if st.button("🧠 AIを学習する",use_container_width=True):
        with st.spinner("📚 過去30日を取得・学習中..."):
            h=learning_data(td,30)
            if len(h)<100:
                st.error("学習データが不足しています")
            else:
                model,acc,nr=train_model(h)
                st.session_state.model=model
                st.session_state.accuracy=acc
                st.session_state.races=nr
                st.success(f"学習完了！ {len(h)}件のデータを使用")

with c2:
    run=st.button("🚀 結果検索・AI予想",type="primary",use_container_width=True)

if run:

    if st.session_state.model is None:
        st.warning("先に「🧠 AIを学習する」を1回押してください")
        st.stop()

    with st.spinner("🚤 レースデータ取得中..."):
        try:
            data=get_data(td)
        except Exception as e:
            st.error("データ取得に失敗しました")
            st.code(str(e))
            st.stop()

    race=get_race(data,sno,rno)

    if not race:
        st.error("このレースのデータがありません")
        st.stop()

    df=race_df(race)

    if df.empty:
        st.error("出走表がありません")
        st.stop()

    w=weather(race)
    df=predict(st.session_state.model,df)

    st.subheader(f"🌬️ {sname} {rno}R")

    a,b,c,d,e=st.columns(5)
    a.metric("風速",f"{w['wind']}m")
    b.metric("風向",direction(w["dir"]))
    c.metric("波高",f"{w['wave']}cm")
    d.metric("気温",f"{w['air']}℃")
    e.metric("水温",f"{w['water']}℃")

    st.subheader("🧠 AI検証")
    a,b=st.columns(2)
    a.metric("検証レース数",st.session_state.races)
    b.metric("1着予測的中率",f"{st.session_state.accuracy}%")

    st.subheader("🤖 AI評価")

    show=["枠","選手名","級別","全国勝率","全国2連率","当地勝率","モーター2連率","平均ST","展示タイム","1着確率"]

    st.dataframe(
        df[show],
        use_container_width=True,
        hide_index=True
    )

    st.subheader("🏆 AI順位")

    for i in range(min(3,len(df))):
        r=df.iloc[i]
        label=["🥇 本命","🥈 対抗","🥉 穴"][i]
        st.write(f"{label}　{int(r['枠'])}号艇 {r['選手名']}　{r['1着確率']:.1f}%")

    t=trifecta(df)

    st.subheader("🎯 3連単ランキング")

    out=t.head(10).copy()
    out["AIスコア"]=(out["スコア"]*100).round(3)

    st.dataframe(
        out[["買い目","AIスコア"]],
        use_container_width=True,
        hide_index=True
    )

    if len(t)>0:
        st.success(f"本線　{t.iloc[0]['買い目']}")
    if len(t)>1:
        st.info(f"対抗　{t.iloc[1]['買い目']}")
    if len(t)>2:
        st.warning(f"穴　{t.iloc[2]['買い目']}")

    st.caption("※AIは統計・機械学習による予想です。的中・利益を保証するものではありません。")

else:
    st.info("初回だけ「🧠 AIを学習する」を押してください。学習後は「🚀 結果検索・AI予想」です。")
