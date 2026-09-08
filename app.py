import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from itertools import permutations
from sklearn.ensemble import RandomForestClassifier

st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO",
    page_icon="🚤",
    layout="wide"
)

API = "https://boatraceopenapi.github.io/api/v1"

STADIUMS = {
    "01":"桐生","02":"戸田","03":"江戸川","04":"平和島",
    "05":"多摩川","06":"浜名湖","07":"蒲郡","08":"常滑",
    "09":"津","10":"三国","11":"びわこ","12":"住之江",
    "13":"尼崎","14":"鳴門","15":"丸亀","16":"児島",
    "17":"宮島","18":"徳山","19":"下関","20":"若松",
    "21":"芦屋","22":"福岡","23":"唐津","24":"大村"
}

NAME_TO_NO = {v:k for k,v in STADIUMS.items()}


# =========================
# API取得
# =========================

@st.cache_data(ttl=300)
def get_day(day):
    url = f"{API}/{day:%Y/%Y%m%d}.json"
    try:
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None


# =========================
# 開催会場
# =========================

def get_holding(day):
    result = {}
    stadiums = day.get("programs", {}).get("stadiums", {})

    for no, stadium in stadiums.items():
        races = stadium.get("races", {})
        nums = []

        for race_no in races:
            try:
                nums.append(int(race_no))
            except:
                pass

        if nums:
            result[str(no).zfill(2)] = sorted(nums)

    return result


# =========================
# レース取得
# =========================

def get_race(day, stadium_no, race_no):
    stadiums = day.get("programs", {}).get("stadiums", {})

    stadium = None

    for k, v in stadiums.items():
        if str(k).zfill(2) == str(stadium_no).zfill(2):
            stadium = v
            break

    if stadium is None:
        return None

    races = stadium.get("races", {})

    for k, v in races.items():
        try:
            if int(k) == int(race_no):
                return v
        except:
            pass

    return None


# =========================
# 6艇データ作成
# =========================

def make_race_df(day, stadium_no, race_no):
    race = get_race(day, stadium_no, race_no)

    if not race:
        return None

    racers = race.get("racers", {})
    preview = race.get("preview", {}).get("racers", {})

    rows = []

    for k, r in sorted(
        racers.items(),
        key=lambda x: int(x[0])
    ):
        try:
            boat = int(k)
        except:
            continue

        p = preview.get(str(k), preview.get(boat, {}))

        rows.append({
            "stadium": int(stadium_no),
            "boat": boat,
            "name": r.get("name", ""),
            "national_win": r.get("national_win_rate", 0),
            "national_top2": r.get("national_top_2_percent", 0),
            "national_top3": r.get("national_top_3_percent", 0),
            "local_win": r.get("local_win_rate", 0),
            "local_top2": r.get("local_top_2_percent", 0),
            "local_top3": r.get("local_top_3_percent", 0),
            "motor_top2": r.get("motor_top_2_percent", 0),
            "motor_top3": r.get("motor_top_3_percent", 0),
            "boat_top2": r.get("boat_top_2_percent", 0),
            "boat_top3": r.get("boat_top_3_percent", 0),
            "avg_st": r.get("average_start_timing", 0),
            "course": p.get("course_number", boat),
            "st": p.get("start_timing", 0),
            "exhibition": p.get("exhibition_time", 0)
        })

    if len(rows) < 6:
        return None

    return pd.DataFrame(rows[:6])


# =========================
# 過去データ
# =========================

@st.cache_data(ttl=3600)
def make_history(end_day, days=14):
    rows = []

    for i in range(days):
        d = end_day - timedelta(days=i)
        data = get_day(d)

        if not data:
            continue

        stadiums = data.get(
            "programs", {}
        ).get("stadiums", {})

        for stadium_no, stadium in stadiums.items():
            races = stadium.get("races", {})

            for race_no, race in races.items():
                racers = race.get("racers", {})
                result = race.get("result", {})
                result_racers = result.get("racers", {})
                preview = race.get("preview", {}).get("racers", {})

                if not racers:
                    continue

                for k, r in racers.items():
                    try:
                        boat = int(k)
                    except:
                        continue

                    rr = result_racers.get(
                        str(k),
                        result_racers.get(boat, {})
                    )

                    try:
                        place = int(
                            rr.get("place_number", 99)
                        )
                    except:
                        place = 99

                    p = preview.get(
                        str(k),
                        preview.get(boat, {})
                    )

                    rows.append({
                        "date": d,
                        "stadium": int(stadium_no),
                        "race": int(race_no),
                        "boat": boat,
                        "national_win": r.get(
                            "national_win_rate", 0
                        ),
                        "national_top2": r.get(
                            "national_top_2_percent", 0
                        ),
                        "national_top3": r.get(
                            "national_top_3_percent", 0
                        ),
                        "local_win": r.get(
                            "local_win_rate", 0
                        ),
                        "local_top2": r.get(
                            "local_top_2_percent", 0
                        ),
                        "local_top3": r.get(
                            "local_top_3_percent", 0
                        ),
                        "motor_top2": r.get(
                            "motor_top_2_percent", 0
                        ),
                        "motor_top3": r.get(
                            "motor_top_3_percent", 0
                        ),
                        "boat_top2": r.get(
                            "boat_top_2_percent", 0
                        ),
                        "boat_top3": r.get(
                            "boat_top_3_percent", 0
                        ),
                        "avg_st": r.get(
                            "average_start_timing", 0
                        ),
                        "course": p.get(
                            "course_number", boat
                        ),
                        "st": p.get(
                            "start_timing", 0
                        ),
                        "exhibition": p.get(
                            "exhibition_time", 0
                        ),
                        "place": place
                    })

    return pd.DataFrame(rows)


# =========================
# AI特徴量
# =========================

FEATURES = [
    "stadium",
    "boat",
    "course",
    "national_win",
    "national_top2",
    "national_top3",
    "local_win",
    "local_top2",
    "local_top3",
    "motor_top2",
    "motor_top3",
    "boat_top2",
    "boat_top3",
    "avg_st",
    "st",
    "exhibition"
]


def make_x(df):
    x = df[FEATURES].copy()

    x = x.replace(
        [np.inf, -np.inf],
        np.nan
    )

    return x.fillna(0)


# =========================
# AI学習
# =========================

def train_ai(history):
    if history.empty:
        return None

    history = history[
        history["place"].between(1, 6)
    ].copy()

    models = {}

    for target in [1, 2, 3]:
        y = (
            history["place"] == target
        ).astype(int)

        model = RandomForestClassifier(
            n_estimators=250,
            max_depth=10,
            min_samples_leaf=3,
            random_state=42,
            n_jobs=-1,
            class_weight="balanced"
        )

        model.fit(make_x(history), y)
        models[target] = model

    return models


# =========================
# 未知データ検証
# =========================

def validate(history):
    if history.empty:
        return None

    dates = sorted(history["date"].unique())

    if len(dates) < 5:
        return None

    test_dates = dates[-3:]

    train = history[
        ~history["date"].isin(test_dates)
    ]

    test = history[
        history["date"].isin(test_dates)
    ]

    models = train_ai(train)

    if models is None:
        return None

    x = make_x(test)

    p = models[1].predict_proba(x)[:, 1]

    temp = test.copy()
    temp["prob"] = p

    top = (
        temp
        .sort_values(
            ["date","stadium","race","prob"],
            ascending=[True,True,True,False]
        )
        .groupby(
            ["date","stadium","race"]
        )
        .first()
        .reset_index()
    )

    accuracy = (
        top["place"] == 1
    ).mean()

    eps = 1e-7

    y = (
        test["place"] == 1
    ).astype(int)

    logloss = -np.mean(
        y * np.log(p + eps)
        + (1-y) * np.log(1-p + eps)
    )

    return accuracy, logloss, len(test_dates)


# =========================
# レース予想
# =========================

def predict_race(df, models):
    x = make_x(df)

    result = df.copy()

    result["p1"] = models[1].predict_proba(x)[:, 1]
    result["p2"] = models[2].predict_proba(x)[:, 1]
    result["p3"] = models[3].predict_proba(x)[:, 1]

    result["score"] = (
        result["p1"] * 0.5
        + result["p2"] * 0.3
        + result["p3"] * 0.2
    )

    ranking = (
        result
        .sort_values(
            "score",
            ascending=False
        )
        .reset_index(drop=True)
    )

    combos = []

    for a, b, c in permutations(
        ranking["boat"].tolist(),
        3
    ):
        ra = result[
            result.boat == a
        ].iloc[0]

        rb = result[
            result.boat == b
        ].iloc[0]

        rc = result[
            result.boat == c
        ].iloc[0]

        score = (
            ra["p1"]
            * rb["p2"]
            * rc["p3"]
        )

        combos.append(
            (f"{a}-{b}-{c}", score)
        )

    combos.sort(
        key=lambda x: x[1],
        reverse=True
    )

    return ranking, combos


# =========================
# 画面
# =========================

st.title(
    "🚤 やっちゃんの競艇AI予想 PRO"
)

st.caption(
    "24場対応・当日全レース対応・強化AI"
)


# =========================
# 日付
# =========================

selected_date = st.sidebar.date_input(
    "📅 日付",
    datetime.now().date()
)

day = get_day(selected_date)

if not day:
    st.error(
        "⚠️ この日のデータを取得できませんでした"
    )
    st.stop()


# =========================
# 開催会場
# =========================

holding = get_holding(day)

if not holding:
    st.warning(
        "⚠️ この日の開催会場が見つかりません"
    )
    st.stop()

st.sidebar.markdown(
    f"### 📡 {len(holding)}会場開催"
)

stadium_options = list(holding.keys())

stadium_no = st.sidebar.selectbox(
    "🏟️ 競艇場",
    stadium_options,
    format_func=lambda x:
        f"{STADIUMS.get(x,x)}（{len(holding[x])}R）"
)


# =========================
# レース
# =========================

race_no = st.sidebar.selectbox(
    "🏁 レース",
    holding[stadium_no],
    format_func=lambda x:
        f"{x}R"
)

stadium_name = STADIUMS.get(
    stadium_no,
    stadium_no
)

st.sidebar.success(
    f"選択中：{stadium_name} {race_no}R"
)


# =========================
# レースデータ
# =========================

race_df = make_race_df(
    day,
    stadium_no,
    race_no
)

if race_df is None:
    st.error(
        "⚠️ このレースの6艇データを取得できませんでした"
    )
    st.stop()


st.subheader(
    f"🏁 {stadium_name} {race_no}R"
)

display_df = race_df[
    [
        "boat",
        "name",
        "course",
        "st",
        "exhibition",
        "national_win",
        "national_top2",
        "local_win",
        "motor_top2"
    ]
].copy()

display_df.columns = [
    "艇",
    "選手",
    "コース",
    "ST",
    "展示",
    "全国勝率",
    "全国2連率",
    "当地勝率",
    "モーター2連率"
]

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)


# =========================
# セッション
# =========================

if "models" not in st.session_state:
    st.session_state.models = None

if "history" not in st.session_state:
    st.session_state.history = None


# =========================
# AI学習
# =========================

if st.sidebar.button(
    "🧠 AIを学習する",
    use_container_width=True
):

    with st.spinner(
        "過去14日分を学習中..."
    ):
        history = make_history(
            selected_date,
            14
        )

        models = train_ai(history)

        st.session_state.history = history
        st.session_state.models = models

    if models is not None:

        races = history[
            ["date","stadium","race"]
        ].drop_duplicates()

        st.success(
            f"🎉 AI学習完了！ "
            f"{history['date'].nunique()}日・"
            f"{len(races)}R・"
            f"{len(history)}行"
        )

    else:
        st.error("AI学習に失敗しました")


# =========================
# 検証
# =========================

if st.session_state.history is not None:

    val = validate(
        st.session_state.history
    )

    if val:

        accuracy, logloss, days = val

        st.subheader(
            "🧪 未知データでの実戦検証"
        )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "検証期間",
            f"{days}日"
        )

        c2.metric(
            "1着判定精度",
            f"{accuracy*100:.1f}%"
        )

        c3.metric(
            "LogLoss",
            f"{logloss:.3f}"
        )


# =========================
# AI予想
# =========================

if st.sidebar.button(
    "🚤 このレースをAI予想",
    use_container_width=True
):

    if st.session_state.models is None:

        st.warning(
            "先に「🧠 AIを学習する」を押してください"
        )

    else:

        ranking, combos = predict_race(
            race_df,
            st.session_state.models
        )

        st.subheader(
            "🥇🥈🥉 AI順位予想"
        )

        for i, row in ranking.iterrows():

            st.write(
                f"**{i+1}位："
                f"{int(row['boat'])}号艇 "
                f"{row['name']}**"
            )

        st.subheader(
            "🎯 AI 3連単ランキング"
        )

        for i, (combo, score) in enumerate(
            combos[:10],
            1
        ):
            st.write(
                f"**{i}位　{combo}** "
                f"　AIスコア {score:.5f}"
            )

        st.success(
            f"🔥 AI本命：{combos[0][0]}"
        )


# =========================
# AI学習状況
# =========================

if st.session_state.history is not None:

    h = st.session_state.history

    st.subheader(
        "📊 AI学習状況"
    )

    c1, c2, c3, c4 = st.columns(4)

    races = h[
        ["date","stadium","race"]
    ].drop_duplicates()

    c1.metric(
        "学習日数",
        f"{h['date'].nunique()}日"
    )

    c2.metric(
        "レース数",
        f"{len(races)}R"
    )

    c3.metric(
        "艇データ",
        f"{len(h)}行"
    )

    val = validate(h)

    if val:
        c4.metric(
            "未知データ精度",
            f"{val[0]*100:.1f}%"
    )
