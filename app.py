import streamlit as st
import pandas as pd
from datetime import date,datetime
from zoneinfo import ZoneInfo
from data import get_data,get_race,history14
from ai import score,tri_ai

STADIUMS={
1:"桐生",2:"戸田",3:"江戸川",4:"平和島",
5:"多摩川",6:"浜名湖",7:"蒲郡",8:"常滑",
9:"津",10:"三国",11:"びわこ",12:"住之江",
13:"尼崎",14:"鳴門",15:"丸亀",16:"児島",
17:"宮島",18:"徳山",19:"下関",20:"若松",
21:"芦屋",22:"福岡",23:"唐津",24:"大村"
}

st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO",
    page_icon="🚤",
    layout="wide"
)

st.title("🚤 やっちゃんの競艇AI予想 PRO")
st.write("過去データを使って3連単120通りを評価するAI")

today=datetime.now(
    ZoneInfo("Asia/Tokyo")
).date()

c1,c2,c3=st.columns(3)

with c1:
    td=st.date_input(
        "開催日",
        today,
        min_value=date(2026,1,1)
    )

with c2:
    name=st.selectbox(
        "競艇場",
        list(STADIUMS.values())
    )

with c3:
    rno=st.selectbox(
        "レース",
        range(1,13),
        format_func=lambda x:f"{x}R"
    )

sno=list(STADIUMS)[
    list(STADIUMS.values()).index(name)
]

if st.button(
    "🚀 AI予想を実行",
    type="primary"
):

    try:
        data=get_data(td)
        race=get_race(data,sno,rno)

    except Exception as e:
        st.error("データ取得に失敗しました")
        st.code(str(e))
        st.stop()

    if race is None:
        st.error("このレースのデータがありません")
        st.stop()

    rows=[]
    rs=race.get("racers",{})

    for lane in range(1,7):

        r=(
            rs.get(str(lane),{})
            if isinstance(rs,dict)
            else {}
        )

        if not r:
            continue

        rows.append({
            "枠":lane,
            "選手名":r.get("name","不明"),
            "選手番号":str(r.get("number","")),
            "級別":r.get("rank_number",""),
            "全国勝率":float(
                r.get("national_win_rate") or 0
            ),
            "全国2連率":float(
                r.get("national_top_2_percent") or 0
            ),
            "当地勝率":float(
                r.get("local_win_rate") or 0
            ),
            "モーター2連率":float(
                r.get("motor_top_2_percent") or 0
            ),
            "平均ST":float(
                r.get("average_start_timing") or 0
            ),
            "展示タイム":float(
                r.get("exhibition_time") or 0
            )
        })

    df=pd.DataFrame(rows)

    if df.empty:
        st.error("出走表がありません")
        st.stop()

    df["学習AI"]=df.apply(
        score,
        axis=1
    )

    df=df.sort_values(
        "学習AI",
        ascending=False
    ).reset_index(drop=True)

    st.subheader(
        f"🤖 {name} {rno}R AI評価"
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    st.subheader("🏆 AI順位")

    for i,row in df.head(3).iterrows():

        label=[
            "🥇 本命",
            "🥈 対抗",
            "🥉 穴"
        ][i]

        st.write(
            f"{label} "
            f"{int(row['枠'])}号艇 "
            f"{row['選手名']}　"
            f"AI {row['学習AI']}"
        )

    history=pd.DataFrame(
        history14(td)
    )

    if len(df)>=3:

        tri=tri_ai(
            df,
            history
        )

        st.subheader(
            "🔥 120通り3連単AI"
        )

        top=tri.iloc[0]
        second=tri.iloc[1]
        third=tri.iloc[2]
        hole=tri.iloc[-1]

        a,b,c,d=st.columns(4)

        with a:
            st.metric(
                "🥇 AI本線",
                top["3連単"],
                f"信頼度 {top['信頼度']}%"
            )

        with b:
            st.metric(
                "🥈 AI対抗",
                second["3連単"],
                f"信頼度 {second['信頼度']}%"
            )

        with c:
            st.metric(
                "🎯 AI押さえ",
                third["3連単"],
                f"信頼度 {third['信頼度']}%"
            )

        with d:
            st.metric(
                "💥 AI穴",
                hole["3連単"],
                f"穴度 {hole['穴度']}%"
            )

        st.subheader(
            "📈 120通りAIランキング TOP10"
        )

        top10=tri.head(10).copy()

        st.dataframe(
            top10,
            use_container_width=True,
            hide_index=True
        )

        st.subheader(
            "📊 上位4点"
        )

        st.write(
            f"🥇 本線：{top['3連単']} "
            f"（信頼度 {top['信頼度']}%）"
        )

        st.write(
            f"🥈 対抗：{second['3連単']} "
            f"（信頼度 {second['信頼度']}%）"
        )

        st.write(
            f"🎯 押さえ：{third['3連単']} "
            f"（信頼度 {third['信頼度']}%）"
        )

        st.write(
            f"💥 穴：{hole['3連単']} "
            f"（穴度 {hole['穴度']}%）"
        )

else:

    st.info(
        "開催日・競艇場・レースを選んで"
        "「AI予想を実行」を押してください。"
    )
