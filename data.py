import requests
import streamlit as st
from datetime import date,timedelta

API="https://boatraceopenapi.github.io/api/v1"

@st.cache_data(ttl=180)
def get_data(d):
    u=f"{API}/{d:%Y/%Y%m%d}.json"
    r=requests.get(u,timeout=20)
    r.raise_for_status()
    return r.json()

def racers(x):
    if isinstance(x,list):
        return x
    if isinstance(x,dict):
        return list(x.values())
    return []

def pmap(race):
    out={}
    for p in racers(race.get("preview",{}).get("racers",{})):
        e=p.get("entry_number")
        c=p.get("course_number")
        if e is not None:
            out[str(e)]=p
        if c is not None:
            out.setdefault(str(c),p)
    return out

def get_race(data,sno,rno):
    s=data.get("programs",{}).get("stadiums",{}).get(str(sno))
    if not s:
        return None
    return s.get("races",{}).get(str(rno))

def history14(td):
    rows=[]
    for i in range(1,15):
        d=td-timedelta(days=i)
        if d<date(2026,1,1):
            continue
        try:
            data=get_data(d)
        except:
            continue
        for sno,s in data.get("programs",{}).get("stadiums",{}).items():
            for rno,race in s.get("races",{}).items():
                rr=race.get("result",{}).get("racers",{})
                places={}
                for x in racers(rr):
                    p=str(x.get("place_number",""))
                    if p in ["1","2","3"]:
                        places[p]=str(x.get("number",""))
                if "1" not in places:
                    continue
                rs=race.get("racers",{})
                if not isinstance(rs,dict):
                    continue
                for lane in range(1,7):
                    r=rs.get(str(lane),{})
                    if not r:
                        continue
                    no=str(r.get("number",""))
                    rows.append({
                        "日付":d,
                        "場":int(sno),
                        "レース":int(rno),
                        "枠":lane,
                        "選手番号":no,
                        "1着":int(no==places.get("1")),
                        "2着":int(no==places.get("2")),
                        "3着":int(no==places.get("3"))
                    })
    return rows
