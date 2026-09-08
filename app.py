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

BASE=[
"枠","全国勝率","全国2連率","当地勝率","当地2連率",
"モーター2連率","ボート2連率","平均ST","展示",
"ST順位","展示順位","全国勝率差","全国2連率差",
"当地勝率差","モーター2連率差","ST差","展示差",
"会場","コース力","選手コース力"
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
# 数値
# =========================
def num(x):
    try:
        return float(x)
    except:
        return 0.0

# =========================
# 6艇
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
            "全国勝率":num(x.get("national_win_rate")),
            "全国2連率":num(x.get("national_top_2_percent")),
            "当地勝率":num(x.get("local_win_rate")),
            "当地2連率":num(x.get("local_top_2_percent")),
            "モーター2連率":num(x.get("motor_top_2_percent")),
            "ボート2連率":num(x.get("boat_top_2_percent")),
            "平均ST":num(x.get("average_start_timing")),
            "展示":0
        })

    df=pd.DataFrame(rows)

    # 直前情報
    preview=race.get("preview",{})

    if isinstance(preview,dict):

        pr=preview.get("racers",{})

        if isinstance(pr,list):
            pr={str(i+1):x for i,x in enumerate(pr)}

        for i in range(1,7):
            x=pr.get(str(i),{})

            df.loc[
                df["枠"]==i,
                "展示"
            ]=num(x.get("exhibition_time"))

    return df

# =========================
# 結果
# =========================
def add_result(df,race):

    result=race.get("result",{})
    rr=result.get("racers",{}) if isinstance(result,dict) else {}

    if isinstance(rr,list):
        rr={str(i+1):x for i,x in enumerate(rr)}

    df=df.copy()

    df["着順"]=0

    for k,x in rr.items():

        try:
            df.loc[
                df["枠"]==int(k),
                "着順"
            ]=int(x.get("place_number",0))
        except:
            pass

    df["1着"]=(df["着順"]==1).astype(int)
    df["2着"]=(df["着順"]==2).astype(int)
    df["3着"]=(df["着順"]==3).astype(int)

    return df

# =========================
# コース別成績を過去データから作る
# =========================
def course_strength(h):

    # 場＋枠ごとの1着率
    a=h.groupby(["場","枠"])["1着"].mean()

    # 選手＋枠ごとの1着率
    b=h.groupby(["選手名","枠"])["1着"].mean()

    return a,b

# =========================
# 特徴量
# =========================
def make_features(df,cs=None,ps=None):

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

    # 会場
    if "場" in df:

        df["会場"]=pd.to_numeric(
            df["場"],errors="coerce"
        ).fillna(0)

    else:
        df["会場"]=0

    # 場×枠
    if cs is not None:

        df["コース力"]=[
            cs.get((int(s),int(k)),0.17)
            for s,k in zip(
                df.get("場",[0]*len(df)),
                df["枠"]
            )
        ]

    else:
        df["コース力"]=0.17

    # 選手×枠
    if ps is not None:

        df["選手コース力"]=[
            ps.get((str(p),int(k)),0.17)
            for p,k in zip(
                df["選手名"],
                df["枠"]
            )
        ]

    else:
        df["選手コース力"]=0.17

    return df

# =========================
# 過去14日
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

                    df=add_result(df,race)

                    if df["着順"].sum()!=21:
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
# モデル
# =========================
def model_new():

    return RandomForestClassifier(
        n_estimators=180,
        max_depth=10,
        min_samples_leaf=2,
        max_features="sqrt",
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )

def xy(df,cs=None,ps=None,target="1着"):

    x=make_features(df,cs,ps)

    X=x[BASE].replace(
        [np.inf,-np.inf],np.nan
    ).fillna(0)

    y=x[target]

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
# 学習
# =========================
if st.button(
    "🧠 AIを学習・実戦検証する",
    use_container_width=True
):

    with st.spinner(
        "過去14日分を分析しています..."
    ):

        h,days,races=history(td,14)

    if len(h)<100:

        st.error("❌ 学習データが不足しています")

        st.info(
            f"取得日数：{days}日 / "
            f"発見レース：{races}R / "
            f"学習データ：{len(h)}行"
        )

    else:

        h=h.sort_values("日付")

        dates=sorted(h["日付"].unique())
        vd=dates[-3:]

        train=h[
            ~h["日付"].isin(vd)
        ].copy()

        valid=h[
            h["日付"].isin(vd)
        ].copy()

        cs,ps=course_strength(train)

        # ---------------------
        # 1着モデル
        # ---------------------
        X1,y1=xy(
            train,cs,ps,"1着"
        )

        m1=model_new()
        m1.fit(X1,y1)

        Xv,yv=xy(
            valid,cs,ps,"1着"
        )

        pv=m1.predict_proba(Xv)

        i1=list(
            m1.classes_
        ).index(1)

        p1=pv[:,i1]

        acc=accuracy_score(
            yv,
            (p1>=0.5).astype(int)
        )

        ll=log_loss(
            yv,
            pv,
            labels=m1.classes_
        )

        # ---------------------
        # 2着モデル
        # ---------------------
        X2,y2=xy(
            train,cs,ps,"2着"
        )

        m2=model_new()
        m2.fit(X2,y2)

        # ---------------------
        # 3着モデル
        # ---------------------
        X3,y3=xy(
            train,cs,ps,"3着"
        )

        m3=model_new()
        m3.fit(X3,y3)

        # ---------------------
        # 全期間で最終モデル
        # ---------------------
        cs_all,ps_all=course_strength(h)

        X1a,y1a=xy(
            h,cs_all,ps_all,"1着"
        )

        X2a,y2a=xy(
            h,cs_all,ps_all,"2着"
        )

        X3a,y3a=xy(
            h,cs_all,ps_all,"3着"
        )

        fm1=model_new()
        fm2=model_new()
        fm3=model_new()

        fm1.fit(X1a,y1a)
        fm2.fit(X2a,y2a)
        fm3.fit(X3a,y3a)

        st.session_state["model"]=(fm1,fm2,fm3)
        st.session_state["cs"]=cs_all
        st.session_state["ps"]=ps_all

        st.session_state["rows"]=len(h)
        st.session_state["days"]=days
        st.session_state["races"]=races
        st.session_state["val_acc"]=acc
        st.session_state["val_logloss"]=ll

        st.success(
            f"🎉 強化AI学習完了！ "
            f"{days}日・{races}R・{len(h)}行"
        )

        st.subheader("🧪 未知3日間での実戦検証")

        a,b,c=st.columns(3)

        a.metric(
            "検証期間",
            f"{len(vd)}日"
        )

        b.metric(
            "1着判定精度",
            f"{acc:.1%}"
        )

        c.metric(
            "LogLoss",
            f"{ll:.3f}"
        )

        st.caption(
            "直近3日を学習から完全に除外して検証しています。"
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

    models=st.session_state.get("model")

    if models is None:

        st.warning(
            "先にAIを学習してください"
        )

    else:

        try:

            data=get_data(td)
            race=get_race(data,stno,rno)

            if race is None:

                st.error(
                    f"{STADIUMS[stno]} {rno}Rが見つかりません"
                )

            else:

                df=make_df(race)

                if len(df)!=6:

                    st.error(
                        "6艇のデータを取得できません"
                    )

                else:

                    m1,m2,m3=models

                    cs=st.session_state.get("cs")
                    ps=st.session_state.get("ps")

                    df["場"]=stno

                    ff=make_features(
                        df,cs,ps
                    )

                    X=ff[BASE].replace(
                        [np.inf,-np.inf],
                        np.nan
                    ).fillna(0)

                    # 1着
                    p=m1.predict_proba(X)
                    idx=list(
                        m1.classes_
                    ).index(1)

                    df["1着確率"]=p[:,idx]

                    # 2着
                    p=m2.predict_proba(X)
                    idx=list(
                        m2.classes_
                    ).index(1)

                    df["2着確率"]=p[:,idx]

                    # 3着
                    p=m3.predict_proba(X)
                    idx=list(
                        m3.classes_
                    ).index(1)

                    df["3着確率"]=p[:,idx]

                    # ---------------------
                    # 予想表示
                    # ---------------------
                    st.subheader(
                        f"🏁 {STADIUMS[stno]} {rno}R"
                    )

                    show=df.sort_values(
                        "1着確率",
                        ascending=False
                    ).copy()

                    show["1着確率"]*=100
                    show["2着確率"]*=100
                    show["3着確率"]*=100

                    st.subheader(
                        "🥇🥈🥉 AI順位予想"
                    )

                    st.dataframe(
                        show[
                            [
                                "枠","選手名",
                                "全国勝率",
                                "当地勝率",
                                "モーター2連率",
                                "平均ST","展示",
                                "1着確率",
                                "2着確率",
                                "3着確率"
                            ]
                        ].round(2),
                        use_container_width=True,
                        hide_index=True
                    )

                    # ---------------------
                    # 120通り
                    # ---------------------
                    out=[]

                    for a in range(1,7):

                        for b in range(1,7):

                            for c in range(1,7):

                                if len({a,b,c})<3:
                                    continue

                                pa=float(
                                    df.loc[
                                        df["枠"]==a,
                                        "1着確率"
                                    ].iloc[0]
                                )

                                pb=float(
                                    df.loc[
                                        df["枠"]==b,
                                        "2着確率"
                                    ].iloc[0]
                                )

                                pc=float(
                                    df.loc[
                                        df["枠"]==c,
                                        "3着確率"
                                    ].iloc[0]
                                )

                                # 3連単専用スコア
                                score=(
                                    pa**1.15*
                                    pb**1.00*
                                    pc**0.90
                                )

                                out.append({
                                    "3連単":
                                        f"{a}-{b}-{c}",
                                    "1着P":pa*100,
                                    "2着P":pb*100,
                                    "3着P":pc*100,
                                    "AIスコア":
                                        score*100
                                })

                    tri=pd.DataFrame(out)

                    tri=tri.sort_values(
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
                            str(
                                tri.iloc[0]["3連単"]
                            )
                        )

                        st.info(
                            "💡 上位3点："+
                            " / ".join(
                                tri["3連単"].head(3)
                            )
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
