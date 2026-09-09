import pandas as pd
from itertools import permutations

def score(r):
    s=r["全国勝率"]*10
    s+=r["全国2連率"]*.25
    s+=r["当地勝率"]*5
    s+=r["モーター2連率"]*.12

    st=r["平均ST"]

    if 0<st<=.12:
        s+=12
    elif st<=.15 and st>0:
        s+=8
    elif st<=.18 and st>0:
        s+=4
    elif st>=.22:
        s-=4

    s+={1:20,2:8,3:6,4:7,5:2,6:0}.get(
        int(r["枠"]),0
    )

    ex=r["展示タイム"]

    if 0<ex<=6.70:
        s+=6
    elif ex<=6.75 and ex>0:
        s+=4
    elif ex<=6.80 and ex>0:
        s+=2
    elif ex>=6.90:
        s-=2

    return round(s,1)


def tri_ai(df,history):

    scores={
        int(r["枠"]):float(r["学習AI"])
        for _,r in df.iterrows()
    }

    nums={
        int(r["枠"]):str(r["選手番号"])
        for _,r in df.iterrows()
    }

    out=[]

    for a,b,c in permutations(scores,3):

        s=(
            scores[a]
            +scores[b]*.72
            +scores[c]*.48
        )

        for lane,mul,col in [
            (a,18,"1着"),
            (b,12,"2着"),
            (c,8,"3着")
        ]:

            h=history[
                history["選手番号"]==nums[lane]
            ]

            if not h.empty:
                s+=h[col].mean()*mul

        if a==1:
            s+=4

        if a in [3,4]:
            s+=1

        if b in [2,3,4]:
            s+=1

        out.append({
            "3連単":f"{a}-{b}-{c}",
            "AIスコア":round(s,1)
        })

    df2=pd.DataFrame(out)

    df2=df2.sort_values(
        "AIスコア",
        ascending=False
    ).reset_index(drop=True)

    mx=df2["AIスコア"].max()
    mn=df2["AIスコア"].min()

    if mx>mn:
        df2["信頼度"]=(
            (df2["AIスコア"]-mn)
            /(mx-mn)*100
        ).round(1)
    else:
        df2["信頼度"]=50.0

    df2["穴度"]=(
        100-df2["信頼度"]
    ).round(1)

    df2.insert(
        0,
        "順位",
        range(1,len(df2)+1)
    )

    return df2
