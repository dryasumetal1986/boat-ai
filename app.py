import streamlit as st
import requests,pandas as pd,numpy as np
from datetime import date,timedelta
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score,log_loss

st.set_page_config(page_title="やっちゃんの競艇AI予想 PRO",layout="wide")
st.title("🚤 やっちゃんの競艇AI予想 PRO")

API="https://boatraceopenapi.github.io/api/v1"

STADIUMS={
1:"桐生",2:"戸田",3:"江戸川",4:"平和島",5:"多摩川",6:"浜名湖",
7:"蒲郡",8:"常滑",9:"津",10:"三国",11:"びわこ",12:"住之江",
13:"尼崎",14:"鳴門",15:"丸亀",16:"児島",17:"宮島",18:"徳山",
19:"下関",20:"若松",21:"芦屋",22:"福岡",23:"唐津",24:"大村"
}

F=[
"枠","全国勝率","全国2連率","当地勝率","当地2連率",
"モーター2連率","ボート2連率","平均ST","展示",
"ST順位","展示順位","全国勝率差","全国2連率差",
"当地勝率差","モーター2連率差","ST差","展示差"
]

for k,v in {
"model":None,"rows":0,"days":0,"races":0,
"val_acc":0.0,"val_logloss":0.0
}.items():
    if k not in st.session_state:
        st.session_state[k]=v

# =========================
# API
# =========================
@st.cache_data(ttl=300)
def get_data(d):
    u=f"{API}/{d:%Y/%Y%m%d}.json"
    r=requests.get(u,timeout=20)
    r.raise_for_status()
    return r.json()

def get_race(data,stno,rno):
    try:
        return data["programs"]["stadiums"][str(stno)]["races"][str(rno)]
    except:
        return None

# =========================
# レース → 6艇
# =========================
def make_df(race):

    racers=race.get("racers",{})

    if isinstance(racers,list):
        racers={str(i+1):x for i,x in enumerate(racers)}

    rows=[]

    for k in range(1,7):

        x=racers.get(str(k),{})

        rows.append({
            "枠":k,
            "選手名":x.get("name",""),
            "全国勝率":x.get("national_win_rate",0),
            "全国2連率":x.get("national_top_2_percent",0),
            "当地勝率":x.get("local_win_rate",0),
            "当地2連率":x.get("local_top_2_percent",0),
            "モーター2連率":x.get("motor_top_2_percent",0),
            "ボート2連率":x.get("boat_top_2_percent",0),
            "平均ST":x.get("average_start_timing",0),
            "展示":0
        })

    df=pd.DataFrame(rows)

    preview=race.get("preview",{})

    if isinstance(preview,dict):

        pr=preview.get("racers",{})

        if isinstance(pr,list):
            pr={str(i+1):x for i,x in enumerate(pr)}

        for i in range(1,7):
            x=pr.get(str(i),{})
            df.loc[df["枠"]==i,"展示"]=x.get(
                "exhibition_time",0
            )

    return df

# =========================
# 1着ラベル
# =========================
def add_label(df,race):

    result=race.get("result",{})

    rr=result.get("racers",{}) if isinstance(result,dict) else {}

    if isinstance(rr,list):
        rr={str(i+1):x for i,x in enumerate(rr)}

    df=df.copy()
    df["1着"]=0

    for k,x in rr.items():

        try:
            if int(x.get("place_number",99))==1:
                df.loc[
                    df["枠"]==int(k),"1着"
                ]=1
        except:
            pass

    return df

# =========================
# 特徴量
# =========================
def features(df):

    df=df.copy()

    cols=[
        "枠","全国勝率","全国2連率","当地勝率",
        "当地2連率","モーター2連率","ボート2連率",
        "平均ST","展示"
    ]

    for c in cols:
        df[c]=pd.to_numeric(
            df[c],errors="coerce"
        ).fillna(0)

    df["ST順位"]=df["平均ST"].replace(
        0,np.nan
    ).rank(method="min").fillna(6)

    df["展示順位"]=df["展示"].replace(
        0,np.nan
    ).rank(method="min").fillna(6)

    for c in [
        "全国勝率","全国2連率",
        "当地勝率","モーター2連率"
    ]:
        df[c+"差"]=df[c]-df[c].mean()

    df["ST差"]=df["平均ST"].mean()-df["平均ST"]
    df["展示差"]=df["展示"].mean()-df["展示"]

    return df

# =========================
# 過去データ
# =========================
@st.cache_data(ttl=3600)
def history(td,days=14):

    rows=[]
    ok_days=0
    ok_races=0

    for n in range(1,days+1):

        d=td-timedelta(days=n)

        try:
            data=get_data(d)
            stadiums=data["programs"]["stadiums"]
        except:
            continue

        day_races=0

        for sn,stadium in stadiums.items():

            races=stadium.get("races",{})

            if not isinstance(races,dict):
                continue

            for rn,race in races.items():

                try:

                    df=make_df(race)

                    if len(df)!=6:
                        continue

                    df=add_label(df,race)

                    if df["1着"].sum()!=1:
                        continue

                    df["日付"]=d
                    df["場"]=int(sn)
                    df["レース"]=int(rn)

                    rows.append(df)
                    day_races+=1

                except:
                    pass

        if day_races:
            ok_days+=1
            ok_races+=day_races

    if not rows:
        return pd.DataFrame(),ok_days,ok_races

    return pd.concat(rows,ignore_index=True),ok_days,ok_races

# =========================
# AI
# =========================
def new_model():

    return RandomForestClassifier(
        n_estimators=160,
        max_depth=9,
        min_samples_leaf=2,
        max_features="sqrt",
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )

def make_xy(df):

    x=features(df)

    X=x[F].replace(
        [np.inf,-np.inf],np.nan
    ).fillna(0)

    y=x["1着"]

    return X,y

# =========================
# サイドバー
# =========================
st.sidebar.header("🏟️ レース選択")

td=st.sidebar.date_input(
    "📅 日付",
    date.today()
)

stno=st.sidebar.selectbox(
    "🏟️ 競艇場",
    list(STADIUMS.keys()),
    format_func=lambda x:
        f"{x}  {STADIUMS[x]}"
)

rno=st.sidebar.selectbox(
    "🏁 レース",
    range(1,13),
    format_func=lambda x:f"{x}R"
)

st.sidebar.info(
    f"選択中：{STADIUMS[stno]} {rno}R"
)

# =========================
# API確認
# =========================
with st.expander("🔧 API診断"):

    if st.button("APIを確認する"):

        try:

            d=td-timedelta(days=1)
            data=get_data(d)
            stadiums=data["programs"]["stadiums"]

            count=sum(
                len(x.get("races",{}))
                for x in stadiums.values()
            )

            st.success("API接続成功！")
            st.write("確認日：",d)
            st.write("競艇場数：",len(stadiums))
            st.write("発見レース数：",count)

        except Exception as e:

            st.error("API取得エラー")
            st.code(str(e))

# =========================
# AI学習・本番検証
# =========================
if st.button(
    "🧠 AIを学習・実戦検証する",
    use_container_width=True
):

    with st.spinner(
        "過去14日分を取得してAIを検証中..."
    ):

        h,days,races=history(td,14)

    st.session_state["model"]=None
    st.session_state["rows"]=len(h)
    st.session_state["days"]=days
    st.session_state["races"]=races

    if len(h)<100:

        st.error("❌ 学習データが不足しています")

        st.info(
            f"取得日数：{days}日 / "
            f"発見レース：{races}R / "
            f"学習データ：{len(h)}行"
        )

    else:

        # 日付順
        h=h.sort_values("日付")

        dates=sorted(h["日付"].unique())

        # 最後3日を完全な未知データにする
        val_dates=dates[-3:]

        train=h[
            ~h["日付"].isin(val_dates)
        ].copy()

        valid=h[
            h["日付"].isin(val_dates)
        ].copy()

        Xtr,ytr=make_xy(train)
        Xva,yva=make_xy(valid)

        test_model=new_model()
        test_model.fit(Xtr,ytr)

        pv=test_model.predict_proba(Xva)

        idx=list(
            test_model.classes_
        ).index(1)

        pred=pv[:,idx]

        val_acc=accuracy_score(
            yva,
            (pred>=0.5).astype(int)
        )

        try:
            val_ll=log_loss(
                yva,
                pv,
                labels=test_model.classes_
            )
        except:
            val_ll=0

        # 全データで最終モデル
        X,y=make_xy(h)

        final_model=new_model()
        final_model.fit(X,y)

        st.session_state["model"]=final_model
        st.session_state["val_acc"]=val_acc
        st.session_state["val_logloss"]=val_ll

        st.success(
            f"🎉 AI学習完了！ "
            f"{days}日・{races}R・{len(h)}行"
        )

        st.subheader("🧪 未知データでの実戦検証")

        a,b,c=st.columns(3)

        a.metric(
            "検証期間",
            f"{len(val_dates)}日"
        )

        b.metric(
            "1着判定精度",
            f"{val_acc:.1%}"
        )

        c.metric(
            "LogLoss",
            f"{val_ll:.3f}"
        )

        st.caption(
            "直近3日をAIから隠して検証した数字です。"
            "これまでの83.4%より実戦性能に近い評価です。"
        )

# =========================
# 学習状況
# =========================
if st.session_state.get("model") is not None:

    st.subheader("📊 AI学習状況")

    a,b,c,d=st.columns(4)

    a.metric(
        "学習日数",
        f"{st.session_state.get('days',0)}日"
    )

    b.metric(
        "学習レース",
        f"{st.session_state.get('races',0)}R"
    )

    c.metric(
        "学習データ",
        f"{st.session_state.get('rows',0):,}行"
    )

    d.metric(
        "未知データ精度",
        f"{st.session_state.get('val_acc',0):.1%}"
    )

# =========================
# 予想
# =========================
if st.button(
    "🚀 結果検索・AI予想",
    use_container_width=True
):

    model=st.session_state.get("model")

    if model is None:

        st.warning(
            "先に「🧠 AIを学習・実戦検証する」を押してください"
        )

    else:

        try:

            data=get_data(td)
            race=get_race(data,stno,rno)

            if race is None:

                st.error(
                    f"{STADIUMS[stno]} {rno}Rのデータがありません"
                )

            else:

                df=make_df(race)

                if len(df)!=6:

                    st.error(
                        "6艇分のデータを取得できませんでした"
                    )

                else:

                    f=features(df)

                    X=f[F].replace(
                        [np.inf,-np.inf],np.nan
                    ).fillna(0)

                    p=model.predict_proba(X)

                    if 1 in model.classes_:

                        idx=list(
                            model.classes_
                        ).index(1)

                        df["1着確率"]=p[:,idx]*100

                    else:
                        df["1着確率"]=0

                    df=df.sort_values(
                        "1着確率",
                        ascending=False
                    )

                    st.subheader(
                        f"🏁 {STADIUMS[stno]} {rno}R"
                    )

                    st.subheader("🥇 AI 1着予想")

                    st.dataframe(
                        df[
                            [
                                "枠","選手名",
                                "全国勝率",
                                "全国2連率",
                                "当地勝率",
                                "当地2連率",
                                "モーター2連率",
                                "平均ST","展示",
                                "1着確率"
                            ]
                        ].round(2),
                        use_container_width=True,
                        hide_index=True
                    )

                    # =====================
                    # 3連単
                    # =====================
                    prob=dict(
                        zip(
                            df["枠"],
                            df["1着確率"]/100
                        )
                    )

                    boats=list(df["枠"])
                    result=[]

                    for a in boats:
                        for b in boats:
                            for c in boats:

                                if len({a,b,c})<3:
                                    continue

                                # 1着候補を強く評価
                                score=(
                                    prob[a]**1.2*
                                    prob[b]**1.0*
                                    prob[c]**0.8
                                )

                                result.append({
                                    "3連単":
                                        f"{a}-{b}-{c}",
                                    "AIスコア":
                                        score*100
                                })

                    tri=pd.DataFrame(
                        result
                    ).sort_values(
                        "AIスコア",
                        ascending=False
                    ).head(10)

                    st.subheader(
                        "🎯 AI 3連単ランキング"
                    )

                    st.dataframe(
                        tri.round(3),
                        use_container_width=True,
                        hide_index=True
                    )

                    if len(tri):

                        st.success(
                            "🔥 AI本命："+
                            str(tri.iloc[0]["3連単"])
                        )

        except Exception as e:

            st.error(
                "予想処理でエラーが発生しました"
            )

            st.code(str(e))

st.divider()

st.caption(
    "※AI予想は過去データから算出した参考値です。"
    "的中・回収を保証するものではありません。"
    )
