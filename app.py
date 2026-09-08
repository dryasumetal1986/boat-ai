import streamlit as st
import requests,pandas as pd,numpy as np
from datetime import date,timedelta
from sklearn.ensemble import RandomForestClassifier

st.set_page_config(page_title="やっちゃんの競艇AI予想 PRO",layout="wide")
st.title("🚤 やっちゃんの競艇AI予想 PRO")

API="https://boatraceopenapi.github.io/api/v1"

STADIUMS={
1:"桐生",2:"戸田",3:"江戸川",4:"平和島",5:"多摩川",6:"浜名湖",
7:"蒲郡",8:"常滑",9:"津",10:"三国",11:"びわこ",12:"住之江",
13:"尼崎",14:"鳴門",15:"丸亀",16:"児島",17:"宮島",18:"徳山",
19:"下関",20:"若松",21:"芦屋",22:"福岡",23:"唐津",24:"大村"
}

# -------------------------
# API
# -------------------------
@st.cache_data(ttl=300)
def api(d):
    u=f"{API}/{d:%Y/%Y%m%d}.json"
    r=requests.get(u,timeout=20)
    r.raise_for_status()
    return r.json()

def n(x):
    try:return float(x or 0)
    except:return 0

def race_no(r):
    for k in ["raceNumber","race_no","number","race"]:
        if k in r:
            try:return int(r[k])
            except:pass
    return None

def stadium_no(r):
    for k in ["stadiumNumber","stadium_no","stadium","venue","place"]:
        if k in r:
            try:return int(r[k])
            except:pass
    return None

# -------------------------
# APIの中からレースを探す
# -------------------------
def find_races(obj,stno=None):
    out=[]

    if isinstance(obj,dict):
        # レースらしいデータ
        if "racers" in obj:
            s=stadium_no(obj)
            if stno is None or s==stno:
                out.append(obj)

        for v in obj.values():
            out += find_races(v,stno)

    elif isinstance(obj,list):
        for v in obj:
            out += find_races(v,stno)

    return out

def get_race(data,stno,rno):
    races=find_races(data,stno)

    for r in races:
        if race_no(r)==rno:
            return r

    # 場番号がJSON内に無い場合
    races=find_races(data)

    for r in races:
        if race_no(r)==rno:
            return r

    return None

# -------------------------
# 選手
# -------------------------
def make_df(r):
    rows=[]

    for i,x in enumerate((r.get("racers",[]) or [])[:6]):
        rows.append({
            "枠":i+1,
            "選手名":x.get("name") or x.get("racerName") or x.get("playerName") or "",
            "全国勝率":n(x.get("nationalWinRate")),
            "全国2連率":n(x.get("nationalSecondRate") or x.get("nationalTop2Rate")),
            "当地勝率":n(x.get("localWinRate")),
            "モーター2連率":n(x.get("motorSecondRate") or x.get("motorTop2Rate")),
            "平均ST":n(x.get("averageST") or x.get("avgST") or x.get("st")),
            "展示":n(x.get("exhibitionTime") or x.get("exhibition"))
        })

    return pd.DataFrame(rows)

# -------------------------
# 結果
# -------------------------
def label(df,r):
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

# -------------------------
# 特徴量
# -------------------------
F=[
"枠","全国勝率","全国2連率","当地勝率","モーター2連率",
"平均ST","展示","ST順位","展示順位",
"全国勝率差","全国2連率差","当地勝率差","モーター2連率差",
"ST差","展示差"
]

def feat(df):
    df=df.copy()

    for c in ["枠","全国勝率","全国2連率","当地勝率","モーター2連率","平均ST","展示"]:
        df[c]=pd.to_numeric(df[c],errors="coerce").fillna(0)

    if all(c in df for c in ["日付","場","レース"]):
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

# -------------------------
# 過去データ
# -------------------------
@st.cache_data(ttl=3600)
def history(td,days=14):

    rows=[]
    ok=0
    races_ok=0

    for i in range(1,days+1):
        d=td-timedelta(days=i)

        try:
            data=api(d)
        except:
            continue

        races=find_races(data)

        if races:
            ok+=1

        for r in races:
            s=stadium_no(r)
            rn=race_no(r)

            if s is None or rn is None:
                continue

            if not(1<=s<=24 and 1<=rn<=12):
                continue

            try:
                df=make_df(r)

                if len(df)!=6:
                    continue

                df=label(df,r)

                if df["1着"].sum()!=1:
                    continue

                df["日付"]=d
                df["場"]=s
                df["レース"]=rn

                rows.append(df)
                races_ok+=1

            except:
                pass

    if not rows:
        return pd.DataFrame(),ok,races_ok

    return pd.concat(rows,ignore_index=True),ok,races_ok

# -------------------------
# 学習
# -------------------------
def train(h):

    if len(h)<30 or h["1着"].nunique()<2:
        return None,0

    h=feat(h)

    X=h[F].replace([np.inf,-np.inf],np.nan).fillna(0)
    y=h["1着"]

    m=RandomForestClassifier(
        n_estimators=100,
        max_depth=8,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )

    m.fit(X,y)

    return m,m.score(X,y)

# =====================================================
# 設定
# =====================================================
st.sidebar.header("⚙️ 設定")

td=st.sidebar.date_input("日付",date.today())

stno=st.sidebar.selectbox(
    "競艇場",
    list(STADIUMS),
    format_func=lambda x:f"{x} {STADIUMS[x]}"
)

rno=st.sidebar.selectbox("レース",range(1,13))

# =====================================================
# APIテスト
# =====================================================
with st.expander("🔧 API確認（エラー時はこちら）"):

    if st.button("API接続テスト"):

        try:
            d=td-timedelta(days=1)
            data=api(d)
            races=find_races(data)

            st.success("API接続成功")

            st.write("確認日：",d)
            st.write("JSON取得：OK")
            st.write("発見したレース数：",len(races))

            if races:
                st.json(races[0])

        except Exception as e:

            st.error("API取得失敗")
            st.code(str(e))

# =====================================================
# 学習
# =====================================================
if st.button("🧠 AIを学習する",use_container_width=True):

    with st.spinner("過去14日分を取得中..."):

        h,days,races=history(td,14)

    st.session_state["model"]=None

    if len(h)<30:

        st.error("❌ 学習データが不足しています")

        st.info(
            f"取得日数：{days}日 / "
            f"発見レース：{races}R / "
            f"学習データ：{len(h)}行"
        )

    else:

        model,acc=train(h)

        if model is None:

            st.error("AIモデルを作成できませんでした")

        else:

            st.session_state["model"]=model
            st.session_state["model_date"]=td
            st.session_state["accuracy"]=acc
            st.session_state["rows"]=len(h)
            st.session_state["days"]=days

            st.success(
                f"🎉 AI学習完了！ "
                f"{days}日 / {len(h)}行"
            )

# =====================================================
# 学習状況
# =====================================================
if st.session_state.get("model") is not None:

    a,b,c=st.columns(3)

    a.metric(
        "学習データ",
        f"{st.session_state.get('rows',0):,}行"
    )

    b.metric(
        "取得日数",
        f"{st.session_state.get('days',0)}日"
    )

    c.metric(
        "学習精度",
        f"{st.session_state.get('accuracy',0):.1%}"
    )

# =====================================================
# レース予想
# =====================================================
if st.button("🚀 結果検索・AI予想",use_container_width=True):

    model=st.session_state.get("model")

    if model is None:

        st.warning("先にAIを学習してください")

    else:

        try:

            data=api(td)
            race=get_race(data,stno,rno)

            if race is None:

                st.error(
                    f"{STADIUMS[stno]} {rno}Rが見つかりません"
                )

            else:

                df=make_df(race)

                if len(df)!=6:

                    st.error("6艇のデータを取得できません")

                else:

                    f=feat(df)

                    X=f[F].replace(
                        [np.inf,-np.inf],np.nan
                    ).fillna(0)

                    p=model.predict_proba(X)
                    idx=list(model.classes_).index(1)

                    df["1着確率"]=p[:,idx]*100
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
                                "全国勝率","全国2連率",
                                "当地勝率","モーター2連率",
                                "平均ST","展示","1着確率"
                            ]
                        ].round(1),
                        use_container_width=True,
                        hide_index=True
                    )

                    # 3連単
                    boats=df["枠"].tolist()
                    prob=dict(
                        zip(
                            df["枠"],
                            df["1着確率"]/100
                        )
                    )

                    out=[]

                    for a in boats:
                        for b in boats:
                            for c in boats:
                                if len({a,b,c})<3:continue

                                score=prob[a]*prob[b]*prob[c]

                                out.append(
                                    {
                                        "3連単":f"{a}-{b}-{c}",
                                        "AIスコア":score*100
                                    }
                                )

                    tri=pd.DataFrame(out).sort_values(
                        "AIスコア",
                        ascending=False
                    ).head(10)

                    st.subheader("🎯 AI 3連単")

                    st.dataframe(
                        tri.round(2),
                        use_container_width=True,
                        hide_index=True
                    )

                    if len(tri):

                        st.success(
                            f"🔥 AI本命：{tri.iloc[0]['3連単']}"
                        )

        except Exception as e:

            st.error("予想処理でエラーが発生しました")
            st.code(str(e))

st.divider()

st.caption(
    "※AI予想は過去データから算出した参考値です。的中を保証するものではありません。"
    )
