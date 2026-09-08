import streamlit as st
import requests
import pandas as pd
from datetime import date

st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO",
    layout="wide"
)

STADIUMS = {
    1:"桐生",2:"戸田",3:"江戸川",4:"平和島",
    5:"多摩川",6:"浜名湖",7:"蒲郡",8:"常滑",
    9:"津",10:"三国",11:"びわこ",12:"住之江",
    13:"尼崎",14:"鳴門",15:"丸亀",16:"児島",
    17:"宮島",18:"徳山",19:"下関",20:"若松",
    21:"芦屋",22:"福岡",23:"唐津",24:"大村"
}

@st.cache_data(ttl=180)
def get_data(d):
    url = f"https://boatraceopenapi.github.io/api/v1/{d:%Y}/{d:%Y%m%d}.json"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.json()

def get_race(data, sid, rno):
    try:
        return data["programs"]["stadiums"][str(sid)]["races"][str(rno)]
    except Exception:
        return None

st.title("🚤 やっちゃんの競艇AI予想 PRO")

target = st.date_input("開催日", date.today())

try:
    data = get_data(target)
except Exception as e:
    st.error(f"データ取得エラー：{e}")
    st.stop()

stadiums = data.get("programs", {}).get("stadiums", {})

if not stadiums:
    st.error("競艇場データがありません")
    st.stop()

available = []

for sid in stadiums:
    try:
        sid2 = int(sid)
        races = stadiums[sid].get("races", {})
        if races:
            available.append(sid2)
    except:
        pass

available = sorted(available)

stadium = st.selectbox(
    "競艇場",
    available,
    format_func=lambda x: f"{x} {STADIUMS.get(x,x)}"
)

races = stadiums[str(stadium)].get("races", {})

race_numbers = sorted([int(x) for x in races.keys()])

race_no = st.selectbox(
    "レース",
    race_numbers,
    format_func=lambda x: f"{x}R"
)

race = get_race(data, stadium, race_no)

if race is None:
    st.error("レースデータを取得できませんでした")
    st.stop()

st.success(f"{STADIUMS.get(stadium,stadium)} {race_no}R のデータ取得成功")

st.write("### APIから取得したレースデータ")

st.write(
    "データ項目：",
    list(race.keys())
)

# 出走選手
racers = race.get("racers", {})

if isinstance(racers, dict):
    rows = []

    for key, value in racers.items():
        if isinstance(value, dict):
            row = {"枠": key}
            row.update(value)
            rows.append(row)

    if rows:
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("racersの中に選手データがありません")
else:
    st.warning("racersデータがありません")

# 直前情報
preview = race.get("preview", {})

st.write("### 直前情報")

if preview:
    st.write(
        "previewの項目：",
        list(preview.keys())
    )
else:
    st.warning("previewデータがありません")

# 結果
result = race.get("result", {})

st.write("### レース結果")

if result:
    st.write(
        "resultの項目：",
        list(result.keys())
    )

    rr = result.get("racers", {})

    if rr:
        rows = []

        for key, value in rr.items():
            if isinstance(value, dict):
                row = {"枠": key}
                row.update(value)
                rows.append(row)

        if rows:
            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True
            )
else:
    st.info("このレースはまだ結果がありません")

st.caption(
    "※ データは非公式Boatrace Open APIを利用しています。"
)
