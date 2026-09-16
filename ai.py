import itertools
import numpy as np
import pandas as pd

BOATS=(1,2,3,4,5,6)

def combo_text(combo):
    return "-".join(str(int(x)) for x in combo)

def _norm_series(series,higher=True):
    x=pd.to_numeric(series,errors="coerce").fillna(0.0).astype(float)
    lo=float(x.min()); hi=float(x.max())
    if hi-lo<1e-12:
        return pd.Series(0.5,index=x.index)
    z=(x-lo)/(hi-lo)
    return z if higher else 1.0-z

def _prepare(df):
    x=df.copy().sort_values("boat").reset_index(drop=True)
    x["win_n"]=_norm_series(x["national_win_rate"])
    x["win_l"]=_norm_series(x["local_win_rate"])
    x["top2_n"]=_norm_series(x["national_top_2_percent"])
    x["top3_n"]=_norm_series(x["national_top_3_percent"])
    x["top2_l"]=_norm_series(x["local_top_2_percent"])
    x["top3_l"]=_norm_series(x["local_top_3_percent"])
    x["motor2"]=_norm_series(x["motor_top_2_percent"])
    x["motor3"]=_norm_series(x["motor_top_3_percent"])
    x["boat2"]=_norm_series(x["boat_top_2_percent"])
    x["boat3"]=_norm_series(x["boat_top_3_percent"])
    x["st"]=_norm_series(x["average_start_timing"],higher=False)
    e=pd.to_numeric(x["exhibition_time"],errors="coerce")
    v=e[e>0]
    med=float(v.median()) if len(v)>0 else 1.0
    x["exh"]=_norm_series(e.replace(0,np.nan).fillna(med),higher=False)
    c=pd.to_numeric(x["course_number"],errors="coerce")
    c=c.fillna(pd.to_numeric(x["boat"],errors="coerce"))
    x["course"]=(1.0-(c-1.0)/10.0).clip(0.4,1.0)

    x["first_score"]=(
        .22*x["win_n"]+.13*x["win_l"]+.13*x["top2_n"]+.08*x["top2_l"]+
        .10*x["motor2"]+.06*x["boat2"]+.12*x["st"]+.10*x["exh"]+.06*x["course"]
    )
    x["second_score"]=(
        .18*x["top2_n"]+.14*x["top2_l"]+.16*x["top3_n"]+.10*x["top3_l"]+
        .14*x["motor2"]+.08*x["motor3"]+.10*x["boat2"]+.10*x["st"]
    )

    # ★今回の実験はここだけ：third_score の national 2連対率 0.12 → 0.15
    x["third_score"]=(
        .18*x["top3_n"]+.14*x["top3_l"]+.16*x["motor3"]+.12*x["boat3"]+
        .15*x["top2_n"]+.10*x["top2_l"]+.10*x["st"]+.08*x["exh"]
    )
    return x

def _softmax(values,temperature=.075):
    values=np.asarray(values,dtype=float)
    if len(values)==0:return np.array([])
    t=max(float(temperature),.001)
    s=values/t;s-=np.max(s)
    e=np.exp(s); total=e.sum()
    return e/total if total>0 else np.ones(len(values))/len(values)

def _combo_score(a,b,c,first_score,second_score,third_score):
    s=1.00*first_score[a]+.72*second_score[b]+.58*third_score[c]
    if a==1:s+=.055
    elif a==2:s+=.025
    if b==1:s+=.020
    return float(s)

def _ordering_bonus(second_boat,third_boat,second_score,third_score):
    ss=float(second_score[second_boat]); ts=float(third_score[third_boat])
    sr=float(np.clip(second_score[second_boat]-third_score[second_boat],-.30,.30))
    tr=float(np.clip(third_score[third_boat]-second_score[third_boat],-.30,.30))
    gap=float(np.clip(ss-ts,-.30,.30))
    return .045*gap+.025*((sr+tr)/2.0)

def _select_main_counter(ranked,first_score,second_score,third_score):
    if not ranked:raise ValueError("予想候補がありません。")
    original=ranked[0]; original_axis=int(original[0][0]); candidate=original

    if original_axis!=5 and 5 in first_score:
        gap=float(first_score[original_axis])-float(first_score[5])
        if gap<=.025:
            c5=[i for i in ranked if int(i[0][0])==5]
            if c5 and float(c5[0][2])>=float(original[2])-.035:
                candidate=c5[0]

    axis=int(candidate[0][0])
    same=[i for i in ranked if int(i[0][0])==axis]
    if len(same)<2:
        return (candidate,same[1]) if len(same)>1 else (candidate,candidate)

    adj=[]
    for combo,prob,raw in same[:10]:
        bonus=_ordering_bonus(combo[1],combo[2],second_score,third_score)
        adj.append({"combo":combo,"prob":float(prob),"raw":float(raw),
                    "adjusted":float(raw)+float(bonus)})
    adj.sort(key=lambda z:(z["adjusted"],z["raw"]),reverse=True)
    m=adj[0]
    cs=[z for z in adj if z["combo"]!=m["combo"]]
    if not cs:return candidate,same[1]
    c=cs[0]
    main=(m["combo"],m["prob"],m["raw"]); counter=(c["combo"],c["prob"],c["raw"])
    if m["raw"]<float(candidate[2])-.045:
        main=candidate
        fb=[i for i in ranked if i[0]!=main[0] and int(i[0][0])==axis]
        if fb:counter=fb[0]
    return main,counter

def _venue_profile(stadium_no):
    p={7:.020,1:.015,20:.015,22:.015,2:.015,5:.010,11:.010,14:.010,
       13:.005,17:.005,18:.005,24:-.015,9:-.010,16:-.005,3:-.005}
    try:return float(p.get(int(stadium_no),0.0))
    except:return 0.0

def _venue_axis_bonus(stadium_no,axis):
    p={1:{4:-.008,5:-.012,6:-.012},20:{2:-.012},7:{1:.010},
       22:{1:.010},21:{1:.010},9:{2:-.010,5:-.010}}
    try:return float(p.get(int(stadium_no),{}).get(int(axis),0.0))
    except:return 0.0

def _apply_venue_adjustment(ranked,stadium_no):
    vb=_venue_profile(stadium_no); out=[]
    for combo,prob,raw in ranked:
        a=int(combo[0]); ab=vb*.70 if a in (1,2) else vb*.85
        out.append((combo,float(prob),float(raw)+ab+_venue_axis_bonus(stadium_no,a)))
    out.sort(key=lambda z:(z[2],z[1]),reverse=True)
    return out

def _select_hole(ranked,main,counter,first_score,third_score):
    used={main[0],counter[0]}
    cand=[i for i in ranked if i[0] not in used]
    if not cand:return ranked[1]
    ma=int(main[0][0]); rows=[]
    for item in cand:
        combo,raw=item[0],float(item[2]); a,b,c=map(int,combo)
        h=raw
        if a!=ma:h+=.025
        h+=.10*float(first_score[a])
        if c==2:h+=.018
        h+=.035*float(np.clip(first_score[c]-first_score[b],-.20,.20))
        h+=.035*float(third_score[c]) - (.015 if c==6 else 0.0)
        rows.append((h,item))
    rows.sort(key=lambda z:(z[0],float(z[1][2])),reverse=True)
    return rows[0][1]

def predict(df,stadium_no=None):
    if not isinstance(df,pd.DataFrame):raise ValueError("出走表データが不正です。")
    if not 3<=len(df)<=6:raise ValueError("3〜6艇分の出走表が必要です。")
    bs=pd.to_numeric(df["boat"],errors="coerce")
    if bs.isna().any():raise ValueError("艇番データが不正です。")
    active=tuple(sorted(set(bs.astype(int))))
    if not 3<=len(active)<=6:raise ValueError("予想対象艇数が不正です。")
    if not all(1<=b<=6 for b in active):raise ValueError("艇番が1〜6になっていません。")

    x=_prepare(df)
    fs=dict(zip(x.boat.astype(int),x.first_score.astype(float)))
    ss=dict(zip(x.boat.astype(int),x.second_score.astype(float)))
    ts=dict(zip(x.boat.astype(int),x.third_score.astype(float)))

    combos=[((a,b,c),_combo_score(a,b,c,fs,ss,ts))
            for a,b,c in itertools.permutations(active,3)]
    raw=np.array([s for _,s in combos],dtype=float)
    probs=_softmax(raw,.075)
    ranked=sorted([(co,float(p),float(s)) for (co,s),p in zip(combos,probs)],
                  key=lambda z:z[1],reverse=True)
    ranked=_apply_venue_adjustment(ranked,stadium_no)

    main,counter=_select_main_counter(ranked,fs,ss,ts)
    hole=_select_hole(ranked,main,counter,fs,ts)

    used={main[0],counter[0]}
    if hole[0] in used:
        alt=[i for i in ranked if i[0] not in used]
        if alt:hole=alt[0]

    if len({main[0],counter[0],hole[0]})<3:
        unique=[]
        for item in [main,counter,hole]+ranked:
            if item[0] not in [u[0] for u in unique]:
                unique.append(item)
            if len(unique)>=3:break
        main,counter,hole=unique[:3]

    fp=_softmax([fs[b] for b in active],.10)
    fr=sorted(zip(active,fp),key=lambda z:z[1],reverse=True)
    axis=int(main[0][0])
    axis_top3=float(sum(p for _,p in fr[:3]))
    margin=float(fr[0][1]-fr[1][1]) if len(fr)>=2 else 0.0
    confidence=min(95.0,max(55.0,62.0+margin*220.0))

    tickets=[
        {"label":"本線","combo":main[0],"prob":float(main[1])},
        {"label":"対抗","combo":counter[0],"prob":float(counter[1])},
        {"label":"穴","combo":hole[0],"prob":float(hole[1])},
    ]
    return {"tickets":tickets,"ranking":ranked,"confidence":round(confidence,1),
            "axis":axis,"axis_top3":axis_top3,"all_combos":ranked,"df":x}
