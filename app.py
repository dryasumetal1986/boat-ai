import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from itertools import permutations
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, log_loss

st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO",
    page_icon="🚤",
    layout="wide"
)

API = "https://boatraceopenapi.github.io/api/v1"

# 競艇場
STADIUMS = {
    "01": "桐生",
    "02": "戸田",
    "03": "江戸川",
    "04": "平和島",
    "05": "多摩川",
    "06": "浜名湖",
    "07": "蒲郡",
    "08": "常滑",
    "09": "津",
    "10": "三国",
    "11": "びわこ",
    "12": "住之江",
    "13": "尼崎",
    "14": "鳴門",
    "15": "丸亀",
    "16": "児島",
    "17": "宮島",
    "18": "徳山",
    "19": "下関",
    "20": "若松",
    "21": "芦屋",
    "22": "福岡",
    "23": "唐津",
    "24": "大村"
}

NAME_TO_NO = {v: k for k, v in STADIUMS.items()}

# =========================
# API
# =========================

@st.cache_data(ttl=300)
def get_day(date):
    url = f"{API}/{date:%Y/%Y%m%d}.json"
    try:
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def get_stadiums(day):
    if not day:
        return {}

    try:
        stadiums = day["programs"]["stadiums"]
    except Exception:
        return {}

    result = {}

    for no, data in stadiums.items():
        if not data:
            continue

        races = data.get("races", {})
        if not races:
            continue

        valid_races = []

        for race_no, race in races.items():
            try:
                racers = race.get("racers", {})
                if len(racers) >= 6:
                    valid_races.append(int(race_no))
            except Exception:
                pass

        if valid_races:
            result[str(no).zfill(2)] = sorted(valid_races)

    return result


# =========================
# 現在レースのデータ
# =========================

def make_race_df(day, stadium_no, race_no):
    try:
        race = (
            day["programs"]
            ["stadiums"][str(stadium_no)]
            ["races"][str(race_no)]
        )
    except Exception:
        return None

    racers = race.get("racers", {})
    preview = race.get("preview", {})
    preview_racers = preview.get("racers", {})

    rows = []

    for boat_no in range(1, 7):
        r = racers.get(str(boat_no), {})
        p = preview_racers.get(str(boat_no), {})

        if not r:
            continue

        rows.append({
            "枠": boat_no,
            "選手名": r.get("name", ""),
            "全国勝率": float(r.get("national_win_rate", 0) or 0),
            "全国2連率": float(r.get("national_top_2_percent", 0) or 0),
            "当地勝率": float(r.get("local_win_rate", 0) or 0),
            "当地2連率": float(r.get("local_top_2_percent", 0) or 0),
            "モーター2連率": float(r.get("motor_top_2_percent", 0) or 0),
            "ボート2連率": float(r.get("boat_top_2_percent", 0) or 0),
            "平均ST": float(r.get("average_start_timing", 0) or 0),
            "展示": float(p.get("exhibition_time", 0) or 0),
            "コース": int(p.get("course_number", boat_no) or boat_no),
        })

    if len(rows) != 6:
        return None

    df = pd.DataFrame(rows)

    df["ST順位"] = df["平均ST"].rank(method="min")
    df["展示順位"] = df["展示"].replace(0, np.nan).rank(method="min")

    for c in [
        "全国勝率",
        "全国2連率",
        "当地勝率",
        "モーター2連率",
        "ST順位",
        "展示順位"
    ]:
        df[c] = df[c].fillna(df[c].median())

    return df


# =========================
# 学習用
# =========================

@st.cache_data(ttl=3600)
def history(days=14):

    all_rows = []

    today = datetime.now().date()

    for i in range(days):
        d = today - timedelta(days=i + 1)
        day = get_day(d)

        if not day:
            continue

        try:
            stadiums = day["programs"]["stadiums"]
        except Exception:
            continue

        for stadium_no, stadium_data in stadiums.items():

            if not stadium_data:
                continue

            races = stadium_data.get("races", {})

            for race_no, race in races.items():

                try:
                    racers = race.get("racers", {})
                    result = race.get("result", {})
                    result_racers = result.get("racers", {})

                    if len(racers) != 6:
                        continue

                    if len(result_racers) != 6:
                        continue

                    preview = race.get("preview", {})
                    preview_racers = preview.get("racers", {})

                    places = []

                    for boat_no in range(1, 7):

                        r = racers.get(str(boat_no), {})
                        p = preview_racers.get(str(boat_no), {})
                        rr = result_racers.get(str(boat_no), {})

                        place = rr.get("place_number")

                        if place is None:
                            continue

                        try:
                            place = int(place)
                        except Exception:
                            continue

                        places.append(place)

                        all_rows.append({
                            "枠": boat_no,
                            "選手名": r.get("name", ""),
                            "全国勝率": float(r.get("national_win_rate", 0) or 0),
                            "全国2連率": float(r.get("national_top_2_percent", 0) or 0),
                            "当地勝率": float(r.get("local_win_rate", 0) or 0),
                            "当地2連率": float(r.get("local_top_2_percent", 0) or 0),
                            "モーター2連率": float(r.get("motor_top_2_percent", 0) or 0),
                            "ボート2連率": float(r.get("boat_top_2_percent", 0) or 0),
                            "平均ST": float(r.get("average_start_timing", 0) or 0),
                            "展示": float(p.get("exhibition_time", 0) or 0),
                            "着順": place,
                            "会場": int(stadium_no),
                            "日付": d,
                            "1着": 1 if place == 1 else 0,
                            "2着": 1 if place == 2 else 0,
                            "3着": 1 if place == 3 else 0,
                        })

                    if sorted(places) != [1, 2, 3, 4, 5, 6]:
                        # 不完全な結果を除外
                        continue

                except Exception:
                    continue

    if not all_rows:
        return pd.DataFrame()

    return pd.DataFrame(all_rows)


# =========================
# 特徴量
# =========================

BASE = [
    "枠",
    "全国勝率",
    "全国2連率",
    "当地勝率",
    "当地2連率",
    "モーター2連率",
    "ボート2連率",
    "平均ST",
    "展示",
    "ST順位",
    "展示順位",
    "全国勝率差",
    "全国2連率差",
    "当地勝率差",
    "モーター2連率差",
    "ST差",
    "展示差",
    "会場",
    "コース力",
    "選手コース力"
]


def make_features(df, full_df=None):

    x = df.copy()

    x["ST順位"] = x["平均ST"].rank(method="min")
    x["展示順位"] = x["展示"].replace(0, np.nan).rank(method="min")

    x["全国勝率差"] = x["全国勝率"] - x["全国勝率"].mean()
    x["全国2連率差"] = x["全国2連率"] - x["全国2連率"].mean()
    x["当地勝率差"] = x["当地勝率"] - x["当地勝率"].mean()
    x["モーター2連率差"] = x["モーター2連率"] - x["モーター2連率"].mean()

    x["ST差"] = x["平均ST"] - x["平均ST"].mean()
    x["展示差"] = x["展示"] - x["展示"].replace(0, np.nan).mean()

    # 枠そのもののコース力
    course_rate = {
        1: 0.58,
        2: 0.16,
        3: 0.12,
        4: 0.08,
        5: 0.04,
        6: 0.02
    }

    x["コース力"] = x["枠"].map(course_rate).fillna(0)

    # 過去データから会場×枠の強さ
    x["選手コース力"] = 0.0

    if full_df is not None and len(full_df) > 0:

        tmp = full_df.copy()

        # 会場×枠
        venue_course = (
            tmp.groupby(["会場", "枠"])["1着"]
            .mean()
            .to_dict()
        )

        for idx in x.index:
            key = (
                int(x.loc[idx, "会場"]),
                int(x.loc[idx, "枠"])
            )
            x.loc[idx, "コース力"] = venue_course.get(
                key,
                course_rate.get(int(x.loc[idx, "枠"]), 0)
            )

        # 選手×枠
        player_course = (
            tmp.groupby(["選手名", "枠"])["1着"]
            .mean()
            .to_dict()
        )

        for idx in x.index:
            key = (
                x.loc[idx, "選手名"],
                int(x.loc[idx, "枠"])
            )
            x.loc[idx, "選手コース力"] = player_course.get(key, 0.0)

    return x[BASE].fillna(0)


# =========================
# AI学習
# =========================

def train_ai(df):

    x = make_features(df, df)

    m1 = RandomForestClassifier(
        n_estimators=100,
        max_depth=12,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1
    )

    m2 = RandomForestClassifier(
        n_estimators=100,
        max_depth=12,
        min_samples_leaf=3,
        random_state=43,
        n_jobs=-1
    )

    m3 = RandomForestClassifier(
        n_estimators=100,
        max_depth=12,
        min_samples_leaf=3,
        random_state=44,
        n_jobs=-1
    )

    m1.fit(x, df["1着"])
    m2.fit(x, df["2着"])
    m3.fit(x, df["3着"])

    return m1, m2, m3


# =========================
# 検証
# =========================

def validate(df):

    dates = sorted(df["日付"].unique())

    if len(dates) < 5:
        return None

    test_dates = dates[-3:]

    train_df = df[~df["日付"].isin(test_dates)].copy()
    test_df = df[df["日付"].isin(test_dates)].copy()

    if len(train_df) == 0 or len(test_df) == 0:
        return None

    x_train = make_features(train_df, train_df)
    x_test = make_features(test_df, train_df)

    model = RandomForestClassifier(
        n_estimators=80,
        max_depth=12,
        min_samples_leaf=3,
        random_state=99,
        n_jobs=-1
    )

    model.fit(x_train, train_df["1着"])

    pred = model.predict(x_test)
    proba = model.predict_proba(x_test)[:, 1]

    acc = accuracy_score(test_df["1着"], pred)

    try:
        ll = log_loss(test_df["1着"], proba)
    except Exception:
        ll = 0

    return acc, ll, len(test_dates)


# =========================
# 画面
# =========================

st.title("🚤 やっちゃんの競艇AI予想 PRO")

# セッション
if "models" not in st.session_state:
    st.session_state.models = None

if "learned_df" not in st.session_state:
    st.session_state.learned_df = None

if "selected_day" not in st.session_state:
    st.session_state.selected_day = None

# -------------------------
# 日付
# -------------------------

st.sidebar.header("🏟️ レース選択")

selected_date = st.sidebar.date_input(
    "📅 日付",
    datetime.now().date()
)

# -------------------------
# その日の開催場を取得
# -------------------------

day = get_day(selected_date)

holding = get_stadiums(day)

if not holding:
    st.error("⚠️ この日の開催データを取得できませんでした。")
    st.stop()

stadium_names = [
    f"{STADIUMS[no]}（{len(races)}R開催）"
    for no, races in holding.items()
]

selected_stadium_label = st.sidebar.selectbox(
    "🏟️ 競艇場",
    stadium_names
)

selected_stadium_name = selected_stadium_label.split("（")[0]
selected_stadium_no = NAME_TO_NO[selected_stadium_name]

# -------------------------
# その会場の開催レースだけ表示
# -------------------------

available_races = holding[selected_stadium_no]

selected_race = st.sidebar.selectbox(
    "🏁 レース",
    available_races,
    format_func=lambda x: f"{x}R"
)

st.sidebar.success(
    f"選択中：{selected_stadium_name} {selected_race}R"
)

st.sidebar.caption(
    f"📡 当日開催：{len(holding)}会場"
)

# -------------------------
# 学習
# -------------------------

st.subheader("🧠 AI学習")

if st.button(
    "🧠 AIを学習・実戦検証する",
    use_container_width=True
):

    with st.spinner("📡 過去データを取得・AIを学習中です…"):

        df = history(14)

        if df.empty:
            st.error("学習データを取得できませんでした。")
            st.stop()

        st.session_state.learned_df = df

        result = validate(df)

        m1, m2, m3 = train_ai(df)

        st.session_state.models = (m1, m2, m3)

    st.success(
        f"🎉 強化AI学習完了！ "
        f"{df['日付'].nunique()}日・"
        f"{len(df)//6}R・"
        f"{len(df)}行"
    )

    if result:
        acc, ll, days = result

        st.subheader("🧪 未知データでの実戦検証")

        c1, c2, c3 = st.columns(3)

        c1.metric("検証期間", f"{days}日")
        c2.metric("1着判定精度", f"{acc*100:.1f}%")
        c3.metric("LogLoss", f"{ll:.3f}")

        st.caption(
            "直近3日を学習から完全に除外して検証しています。"
        )

# -------------------------
# 学習状況
# -------------------------

if st.session_state.learned_df is not None:

    df = st.session_state.learned_df

    st.subheader("📊 AI学習状況")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "学習日数",
        f"{df['日付'].nunique()}日"
    )

    c2.metric(
        "学習レース",
        f"{len(df)//6}R"
    )

    c3.metric(
        "学習データ",
        f"{len(df):,}行"
    )

# -------------------------
# レース予想
# -------------------------

st.divider()

st.header(
    f"🏁 {selected_stadium_name} {selected_race}R"
)

if st.button(
    "🚀 結果検索・AI予想",
    use_container_width=True
):

    if st.session_state.models is None:
        st.warning(
            "⚠️ 先に「🧠 AIを学習・実戦検証する」を押してください。"
        )
        st.stop()

    race_df = make_race_df(
        day,
        selected_stadium_no,
        selected_race
    )

    if race_df is None:
        st.error(
            "⚠️ このレースの6艇データを取得できませんでした。"
        )
        st.stop()

    models = st.session_state.models

    # 会場番号
    race_df["会場"] = int(selected_stadium_no)

    x = make_features(
        race_df,
        st.session_state.learned_df
    )

    p1 = models[0].predict_proba(x)[:, 1]
    p2 = models[1].predict_proba(x)[:, 1]
    p3 = models[2].predict_proba(x)[:, 1]

    # 各順位内で正規化
    p1 = p1 / p1.sum()
    p2 = p2 / p2.sum()
    p3 = p3 / p3.sum()

    race_df["1着確率"] = p1
    race_df["2着確率"] = p2
    race_df["3着確率"] = p3

    st.subheader("🥇🥈🥉 AI順位予想")

    display_df = race_df[
        [
            "枠",
            "選手名",
            "全国勝率",
            "当地勝率",
            "モーター2連率",
            "展示",
            "1着確率",
            "2着確率",
            "3着確率"
        ]
    ].copy()

    display_df = display_df.sort_values(
        "1着確率",
        ascending=False
    )

    for c in ["1着確率", "2着確率", "3着確率"]:
        display_df[c] = (
            display_df[c] * 100
        ).round(1).astype(str) + "%"

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    # -------------------------
    # 3連単120通り
    # -------------------------

    boats = list(range(1, 7))

    rankings = []

    for a, b, c in permutations(boats, 3):

        pa = race_df.loc[
            race_df["枠"] == a,
            "1着確率"
        ].iloc[0]

        pb = race_df.loc[
            race_df["枠"] == b,
            "2着確率"
        ].iloc[0]

        pc = race_df.loc[
            race_df["枠"] == c,
            "3着確率"
        ].iloc[0]

        score = (
            pa ** 1.15
            * pb ** 1.00
            * pc ** 0.90
        )

        rankings.append({
            "3連単": f"{a}-{b}-{c}",
            "AIスコア": score,
            "1着確率": pa,
            "2着確率": pb,
            "3着確率": pc
        })

    ranking_df = pd.DataFrame(rankings)

    ranking_df = ranking_df.sort_values(
        "AIスコア",
        ascending=False
    ).reset_index(drop=True)

    st.subheader("🎯 AI 3連単ランキング")

    top10 = ranking_df.head(10).copy()

    top10["AIスコア"] = (
        top10["AIスコア"] * 10000
    ).round(2)

    top10["確率目安"] = (
        top10["AIスコア"] /
        top10["AIスコア"].sum() * 100
    ).round(1).astype(str) + "%"

    st.dataframe(
        top10[
            ["3連単", "AIスコア", "確率目安"]
        ],
        use_container_width=True,
        hide_index=True
    )

    # 本命
    best = ranking_df.iloc[0]["3連単"]

    st.success(
        f"🔥 AI本命：{best}"
    )

    # 上位3点
    st.write("### ⭐ AI上位3点")

    for i, row in ranking_df.head(3).iterrows():

        medal = ["🥇", "🥈", "🥉"][i]

        st.write(
            f"{medal} **{row['3連単']}**"
        )

# -------------------------
# 注意
# -------------------------

st.divider()

st.caption(
    "※AI予想は過去データから算出した参考値です。"
    "的中・回収を保証するものではありません。"
)

st.caption(
    "※開催会場・レースは選択した日付のAPIデータから自動取得しています。"
)
