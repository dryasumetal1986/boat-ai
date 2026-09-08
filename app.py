import streamlit as st
import requests,pandas as pd,numpy as np
from datetime import date,timedelta
from sklearn.ensemble import RandomForestClassifier

st.set_page_config(page_title="やっちゃんの競艇AI予想 PRO",layout="wide")
st.title("🚤 やっちゃんの競艇AI予想 PRO")

API="https://boatraceopenapi.github.io/api/v1"
STADIUMS={1:"桐生",2:"戸田",3:"江戸川",4:"平和島",5:"多摩川",6:"浜名湖",7:"蒲郡",8:"常滑",9:"津",10:"三国",11:"びわこ",12:"住之江",13:"尼崎",14:"鳴門",15:"丸亀",16:"児島",17:"宮島",18:"徳山",19:"下関",20:"若松",21:"芦屋",22:"福岡",23:"唐津",24:"大村"}

# -----------------------------
# Session State
# -----------------------------
for k,v in {
    "model":None,"model_date":None,"train_rows":0,
    "days":0,"accuracy":0.0,"trained":False
}.items():
    if k not in st.session_state: st.session_state[k]=v

# -----------------------------
# API
# -----------------------------
@st.cache_data(ttl=300)
def get_data(d):
    url=f"{API}/{d:%Y/%Y%m%d}.json"
    r=requests.get(url,timeout=15)
    r.raise_for_status()
    return r.json()

def val(x):
    try:return float(x or 0)
    except:return 0.0

def get_no(r):
    try:return int(r.get("raceNumber") or r.get("race_no") or r.get("number"))
    except:return None

def get_st(r):
    try:return int(r.get("stadiumNumber") or r.get("stadium_no") or r.get("stadium") or r.get("venue") or r.get("place"))
    except:return None

# -----------------------------
# レース検索
# -----------------------------
def find_race(data,st_no,race_no):
    races=data.get("races",[]) or []
    if isinstance(races,list):
        for r in races:
            if get_st(r)==st_no and get_no(r)==race_no:return r
    return None

# -----------------------------
# 選手データ
# -----------------------------
def race_df(r):
    rows=[]
    for i,x in enumerate((r.get("racers",[]) or [])[:6]):
        rows.append({
            "枠":i+1,
            "選手名":x.get("name") or x.get("racerName") or x.get("playerName") or "",
            "全国勝率":val(x.get("nationalWinRate")),
            "全国2連率":val(x.get("nationalSecondRate") or x.get("nationalTop2Rate")),
            "当地勝率":val(x.get("localWinRate")),
            "モーター2連率":val(x.get("motorSecondRate") or x.get("motorTop2Rate")),
            "平均ST":val(x.get("averageST") or x.get("avgST") or x.get("st")),
            "展示":val(x.get("exhibitionTime") or x.get("exhibition"))
        })
    return pd.DataFrame(rows)

# -----------------------------
# 1着結果
# -----------------------------
def add_label(df,r):
    rr=(r.get("result",{}) or {}).get("racers",[]) or []
    winner=""
    for x in rr:
        try:
            if int(x.get("rank") or x.get("着順") or x.get("result"))==1:
                winner=x.get("name") or x.get("racerName") or x.get("playerName") or ""
                break
        except:pass
    df=df.copy()
    df["1着"]=(df["選手名"].astype(str)==str(winner)).astype(int)
    return df

# -----------------------------
# 特徴量
# -----------------------------
FEATURES=[
    "枠","全国勝率","全国2連率","当地勝率","モーター2連率",
    "平均ST","展示","ST順位","展示順位",
    "全国勝率差","全国2連率差","当地勝率差","モーター2連率差",
    "ST差","展示差"
]

def features(df):
    df=df.copy()
    nums=["枠","全国勝率","全国2連率","当地勝率","モーター2連率","平均ST","展示"]
    for c in nums:
        df[c]=pd.to_numeric(df[c],errors="coerce").fillna(0)

    if all(c in df.columns for c in ["日付","場","レース"]):
        g=df.groupby(["日付","場","レース"])

        df["ST順位"]=df["平均ST"].replace(0,np.nan).groupby(
            [df["日付"],df["場"],df["レース"]]).rank().fillna(6)

        df["展示順位"]=df["展示"].replace(0,np.nan).groupby(
            [df["日付"],df["場"],df["レース"]]).rank().fillna(6)

        for c in ["全国勝率","全国2連率","当地勝率","モーター2連率"]:
            df[c+"差"]=df[c]-g[c].transform("mean")

        df["ST差"]=g["平均ST"].transform("mean")-df["平均ST"]
        df["展示差"]=g["展示"].transform("mean")-df["展示"]

    else:
        df["ST順位"]=df["平均ST"].replace(0,np.nan).rank().fillna(6)
        df["展示順位"]=df["展示"].replace(0,np.nan).rank().fillna(6)

        for c in ["全国勝率","全国2連率","当地勝率","モーター2連率"]:
            df[c+"差"]=df[c]-df[c].mean()

        df["ST差"]=df["平均ST"].mean()-df["平均ST"]
        df["展示差"]=df["展示"].mean()-df["展示"]

    return df

# -----------------------------
# 学習データ
# -----------------------------
@st.cache_data(ttl=3600)
def history_data(td,days=14):
    all_data=[];ok=0

    for i in range(1,days+1):
        d=td-timedelta(days=i)
        try:data=get_data(d)
        except:continue

        races=data.get("races",[]) or []
        if not isinstance(races,list):continue

        day_count=0

        for r in races:
            s=get_st(r);n=get_no(r)
            if s is None or n is None:continue
            if not(1<=s<=24 and 1<=n<=12):continue

            try:
                df=race_df(r)
                if len(df)<6:continue
                df=add_label(df,r)
                if df["1着"].sum()!=1:continue

                df["日付"]=d
                df["場"]=s
                df["レース"]=n
                all_data.append(df)
                day_count+=6
            except:continue

        if day_count:ok+=1

    if not all_data:return pd.DataFrame(),ok
    return pd.concat(all_data,ignore_index=True),ok

# -----------------------------
# AI
# -----------------------------
def train(h):
    if len(h)<30 or h["1着"].nunique()<2:return None,0

    h=features(h)
    X=h[FEATURES].replace([np.inf,-np.inf],np.nan).fillna(0)
    y=h["1着"]

    dates=sorted(h["日付"].unique())

    if len(dates)>=5:
        cut=max(1,int(len(dates)*.8))
        tr=set(dates[:cut])
        va=set(dates[cut:])
        a=h["日付"].isin(tr)
        b=h["日付"].isin(va)
        X1,y1=X[a],y[a]
        X2,y2=X[b],y[b]
    else:
        cut=int(len(h)*.8)
        X1,y1=X.iloc[:cut],y.iloc[:cut]
        X2,y2=X.iloc[cut:],y.iloc[cut:]

    if len(X1)<20 or y1.nunique()<2:return None,0

    model=RandomForestClassifier(
        n_estimators=100,
        max_depth=8,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )
    model.fit(X1,y1)

    acc=model.score(X2,y2) if len(X2) else 0
    return model,acc

# -----------------------------
# 1着予想
# -----------------------------
def predict(model,df):
    f=features(df)
    X=f[FEATURES].replace([np.inf,-np.inf],np.nan).fillna(0)
    p=model.predict_proba(X)
    idx=list(model.classes_).index(1)
    df=df.copy()
    df["1着確率"]=p[:,idx]
    return df.sort_values("1着確率",ascending=False).reset_index(drop=True)

# -----------------------------
# 3連単
# -----------------------------
def trifecta(df):
    boats=df["枠"].tolist()
    p=dict(zip(df["枠"],df["1着確率"]))
    rows=[]

    for a in boats:
        r1=[x for x in boats if x!=a]
        t1=sum(p[x] for x in r1)

        for b in r1:
            r2=[x for x in r1 if x!=b]
            t2=sum(p[x] for x in r2)

            for c in r2:
                score=p[a]*(p[b]/t1 if t1 else 0)*(p[c]/t2 if t2 else 0)
                rows.append({"3連単":f"{a}-{b}-{c}","AIスコア":score})

    return pd.DataFrame(rows).sort_values("AIスコア",ascending=False).reset_index(drop=True)

# =========================================================
# 設定
# =========================================================
st.sidebar.header("⚙️ レース設定")

td=st.sidebar.date_input("日付",date.today())

st_no=st.sidebar.selectbox(
    "競艇場",
    list(STADIUMS),
    format_func=lambda x:f"{x} {STADIUMS[x]}"
)

race_no=st.sidebar.selectbox("レース",range(1,13))

# =========================================================
# 学習
# =========================================================
if st.button("🧠 AIを学習する",use_container_width=True):

    st.session_state["model"]=None
    st.session_state["trained"]=False

    with st.spinner("過去14日分を取得してAI学習中..."):

        h,days=history_data(td,14)

        st.session_state["train_rows"]=len(h)
        st.session_state["days"]=days

        if len(h)<30:

            st.error("❌ 学習データが不足しています")

            st.info(
                f"取得日数：{days}日 / "
                f"学習データ：{len(h)}行"
            )

        else:

            model,acc=train(h)

            if model is None:

                st.error("❌ AIモデルを作成できませんでした")

            else:

                st.session_state["model"]=model
                st.session_state["model_date"]=td
                st.session_state["accuracy"]=acc
                st.session_state["trained"]=True

                st.success(
                    f"🎉 AI学習完了！ "
                    f"{days}日 / {len(h)}行"
                )

# =========================================================
# 学習状況
# =========================================================
if st.session_state.get("trained",False):

    c1,c2,c3=st.columns(3)

    c1.metric(
        "学習データ",
        f"{st.session_state.get('train_rows',0):,}行"
    )

    c2.metric(
        "取得日数",
        f"{st.session_state.get('days',0)}日"
    )

    c3.metric(
        "検証精度",
        f"{st.session_state.get('accuracy',0):.1%}"
    )

# =========================================================
# 予想
# =========================================================
if st.button("🚀 結果検索・AI予想",use_container_width=True):

    model=st.session_state.get("model")

    if model is None:

        st.warning("⚠️ 先に「🧠 AIを学習する」を押してください")

    elif st.session_state.get("model_date")!=td:

        st.warning("⚠️ 日付が変わっています。もう一度AI学習してください")

    else:

        with st.spinner("レースデータ取得中..."):

            try:

                data=get_data(td)
                race=find_race(data,st_no,race_no)

                if race is None:

                    st.error(
                        f"❌ {STADIUMS[st_no]} {race_no}Rが見つかりません"
                    )

                else:

                    df=race_df(race)

                    if len(df)<6:

                        st.error("❌ 6艇分のデータを取得できません")

                    else:

                        st.subheader(
                            f"🏁 {STADIUMS[st_no]} {race_no}R"
                        )

                        w=race.get("weather",{}) or {}

                        st.caption(
                            f"🌤 気温 {w.get('temperature','')}℃ / "
                            f"風速 {w.get('windSpeed','')} / "
                            f"風向 {w.get('windDirection','')}"
                        )

                        result=predict(model,df)

                        view=result.copy()
                        view["1着確率"]=(view["1着確率"]*100).round(1)

                        st.subheader("🥇 AI 1着予想")

                        st.dataframe(
                            view[
                                [
                                    "枠","選手名",
                                    "全国勝率","全国2連率",
                                    "当地勝率","モーター2連率",
                                    "平均ST","展示","1着確率"
                                ]
                            ],
                            use_container_width=True,
                            hide_index=True
                        )

                        tri=trifecta(result)

                        st.subheader("🎯 AI 3連単ランキング")

                        show=tri.head(10).copy()
                        show["AIスコア"]=(show["AIスコア"]*100).round(2)

                        st.dataframe(
                            show,
                            use_container_width=True,
                            hide_index=True
                        )

                        if len(tri):

                            st.success(
                                f"🔥 AI本命：{tri.iloc[0]['3連単']}"
                            )

                            if len(tri)>1:
                                st.write(
                                    f"🥈 対抗：{tri.iloc[1]['3連単']}"
                                )

                            if len(tri)>2:
                                st.write(
                                    f"🥉 穴候補：{tri.iloc[2]['3連単']}"
                                )

            except Exception as e:

                st.error("❌ データ取得・予想中にエラーが発生しました")
                st.caption(str(e))

st.divider()

st.caption(
    "※AIスコアは過去データから算出した予測値で、的中を保証するものではありません。"
        )
