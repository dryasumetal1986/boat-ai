import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import date, timedelta
from sklearn.ensemble import RandomForestClassifier

# =========================
# 基本設定
# =========================
st.set_page_config(
    page_title="やっちゃんの競艇AI予想 PRO",
    layout="wide"
)

st.title("🚤 やっちゃんの競艇AI予想 PRO")

API = "https://boatraceopenapi.github.io/api/v1"

STADIUMS = {
    1:"桐生", 2:"戸田", 3:"江戸川", 4:"平和島",
    5:"多摩川", 6:"浜名湖", 7:"蒲郡", 8:"常滑",
    9:"津", 10:"三国", 11:"びわこ", 12:"住之江",
    13:"尼崎", 14:"鳴門", 15:"丸亀", 16:"児島",
    17:"宮島", 18:"徳山", 19:"下関", 20:"若松",
    21:"芦屋", 22:"福岡", 23:"唐津", 24:"大村"
}

# =========================
# API取得
# =========================
@st.cache_data(ttl=300)
def get_data(d):
    # ★重要：APIの日付形式は YYYY/YYYYMMDD
    url = f"{API}/{d:%Y/%Y%m%d}.json"

    r = requests.get(url, timeout=15)
    r.raise_for_status()

    return r.json()


# =========================
# 指定レース取得
# =========================
def get_race(data, stadium, race_no):
    races = data.get("races", [])

    for r in races:
        no = r.get("raceNumber", r.get("race_no", r.get("number")))

        try:
            if int(no) == int(race_no):
                return r
        except:
            pass

    return None


# =========================
# 天候など
# =========================
def weather_info(race):
    weather = race.get("weather", {}) or {}

    return (
        weather.get("temperature", ""),
        weather.get("windSpeed", ""),
        weather.get("windDirection", "")
    )


# =========================
# 選手データ → DataFrame
# =========================
def make_race_df(race):
    racers = race.get("racers", [])

    rows = []

    for i, x in enumerate(racers):
        if i >= 6:
            break

        rows.append({
            "枠": i + 1,
            "選手名": (
                x.get("name")
                or x.get("racerName")
                or x.get("playerName")
                or ""
            ),
            "全国勝率": float(x.get("nationalWinRate") or 0),
            "全国2連率": float(x.get("nationalSecondRate") or 0),
            "当地勝率": float(x.get("localWinRate") or 0),
            "モーター2連率": float(x.get("motorSecondRate") or 0),
            "平均ST": float(x.get("averageST") or x.get("st") or 0),
            "展示": float(
                x.get("exhibitionTime")
                or x.get("exhibition")
                or 0
            )
        })

    return pd.DataFrame(rows)


# =========================
# 結果から1着ラベル
# =========================
def add_result_label(df, race):
    result = race.get("result", {}) or {}
    result_racers = result.get("racers", []) or []

    first_name = ""

    for x in result_racers:
        rank = x.get("rank", x.get("着順", x.get("result")))

        try:
            if int(rank) == 1:
                first_name = (
                    x.get("name")
                    or x.get("racerName")
                    or x.get("playerName")
                    or ""
                )
                break
        except:
            pass

    df = df.copy()
    df["1着"] = (df["選手名"] == first_name).astype(int)

    return df


# =========================
# 特徴量作成
# =========================
def make_features(df):
    df = df.copy()

    numeric_cols = [
        "枠",
        "全国勝率",
        "全国2連率",
        "当地勝率",
        "モーター2連率",
        "平均ST",
        "展示"
    ]

    for c in numeric_cols:
        if c not in df.columns:
            df[c] = 0

        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # 枠ごとのワンホット
    for i in range(1, 7):
        df[f"枠{i}"] = (df["枠"] == i).astype(int)

    # レース内順位・平均との差
    if all(c in df.columns for c in ["日付", "場", "レース"]):
        group_cols = ["日付", "場", "レース"]
        g = df.groupby(group_cols)

        st_tmp = df["平均ST"].replace(0, np.nan)

        df["ST順位"] = (
            st_tmp
            .groupby([df[c] for c in group_cols])
            .rank(method="min")
            .fillna(6)
        )

        ex_tmp = df["展示"].replace(0, np.nan)

        df["展示順位"] = (
            ex_tmp
            .groupby([df[c] for c in group_cols])
            .rank(method="min")
            .fillna(6)
        )

        for c in [
            "全国勝率",
            "全国2連率",
            "当地勝率",
            "モーター2連率"
        ]:
            df[f"{c}差"] = df[c] - g[c].transform("mean")

        # ST・展示は小さいほど有利
        df["ST差"] = g["平均ST"].transform("mean") - df["平均ST"]
        df["展示差"] = g["展示"].transform("mean") - df["展示"]

    else:
        df["ST順位"] = (
            df["平均ST"]
            .replace(0, np.nan)
            .rank(method="min")
            .fillna(6)
        )

        df["展示順位"] = (
            df["展示"]
            .replace(0, np.nan)
            .rank(method="min")
            .fillna(6)
        )

        for c in [
            "全国勝率",
            "全国2連率",
            "当地勝率",
            "モーター2連率"
        ]:
            df[f"{c}差"] = df[c] - df[c].mean()

        df["ST差"] = df["平均ST"].mean() - df["平均ST"]
        df["展示差"] = df["展示"].mean() - df["展示"]

    return df


FEATURES = [
    "枠",
    "枠1", "枠2", "枠3", "枠4", "枠5", "枠6",
    "全国勝率",
    "全国2連率",
    "当地勝率",
    "モーター2連率",
    "平均ST",
    "展示",
    "ST順位",
    "展示順位",
    "全国勝率差",
    "全国2連率差",
    "当地勝率差",
    "モーター2連率差",
    "ST差",
    "展示差"
]


# =========================
# 過去データ作成
# =========================
@st.cache_data(ttl=3600)
def learning_data(target_date, days=21):

    all_rows = []
    success_days = 0

    for i in range(1, days + 1):

        d = target_date - timedelta(days=i)

        try:
            data = get_data(d)
        except Exception:
            continue

        day_rows = 0

        for stadium_no in range(1, 25):

            # APIによって場番号が race 内に無い場合があるので
            # races を直接走査
            races = data.get("races", []) or []

            for race in races:

                # 場番号確認
                s = (
                    race.get("stadium")
                    or race.get("stadiumNumber")
                    or race.get("venue")
                    or race.get("place")
                )

                try:
                    if int(s) != stadium_no:
                        continue
                except:
                    continue

                race_no = (
                    race.get("raceNumber")
                    or race.get("race_no")
                    or race.get("number")
                )

                try:
                    race_no = int(race_no)
                except:
                    continue

                if race_no < 1 or race_no > 12:
                    continue

                try:
                    rdf = make_race_df(race)

                    if len(rdf) < 6:
                        continue

                    rdf = add_result_label(rdf, race)

                    rdf["日付"] = d
                    rdf["場"] = stadium_no
                    rdf["レース"] = race_no

                    all_rows.append(rdf)
                    day_rows += len(rdf)

                except Exception:
                    continue

        if day_rows > 0:
            success_days += 1

    if not all_rows:
        return pd.DataFrame(), success_days

    h = pd.concat(all_rows, ignore_index=True)

    return h, success_days


# =========================
# AI学習
# =========================
def train_model(h):

    h = make_features(h)

    X = h[FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    y = h["1着"].astype(int)

    if len(h) < 30:
        return None, 0, 0

    if y.nunique() < 2:
        return None, 0, 0

    # 日付単位で80:20分割
    dates = sorted(h["日付"].dropna().unique())

    if len(dates) >= 5:
        cut = max(1, int(len(dates) * 0.8))

        train_dates = set(dates[:cut])
        val_dates = set(dates[cut:])

        train_mask = h["日付"].isin(train_dates)
        val_mask = h["日付"].isin(val_dates)

        X_train = X[train_mask]
        y_train = y[train_mask]

        X_val = X[val_mask]
        y_val = y[val_mask]

    else:
        cut = int(len(h) * 0.8)

        X_train = X.iloc[:cut]
        y_train = y.iloc[:cut]

        X_val = X.iloc[cut:]
        y_val = y.iloc[cut:]

    if len(X_train) < 20 or y_train.nunique() < 2:
        return None, 0, 0

    model = RandomForestClassifier(
        n_estimators=120,
        max_depth=8,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    accuracy = 0

    if len(X_val) > 0 and y_val.nunique() >= 1:
        accuracy = model.score(X_val, y_val)

    return model, accuracy, len(X_val)


# =========================
# 1着確率
# =========================
def predict_first(model, rdf):

    f = make_features(rdf)

    X = f[FEATURES].replace(
        [np.inf, -np.inf],
        np.nan
    ).fillna(0)

    prob = model.predict_proba(X)

    classes = list(model.classes_)

    if 1 in classes:
        idx = classes.index(1)
        p = prob[:, idx]
    else:
        p = np.zeros(len(f))

    result = rdf.copy()
    result["1着確率"] = p

    return result.sort_values(
        "1着確率",
        ascending=False
    ).reset_index(drop=True)


# =========================
# 3連単ランキング
# =========================
def trifecta_rank(df):

    boats = df["枠"].tolist()
    probs = dict(
        zip(
            df["枠"],
            df["1着確率"]
        )
    )

    rows = []

    for a in boats:

        p1 = probs[a]

        remaining1 = [
            x for x in boats
            if x != a
        ]

        total1 = sum(
            probs[x]
            for x in remaining1
        )

        for b in remaining1:

            p2 = (
                probs[b] / total1
                if total1 > 0 else 0
            )

            remaining2 = [
                x for x in remaining1
                if x != b
            ]

            total2 = sum(
                probs[x]
                for x in remaining2
            )

            for c in remaining2:

                p3 = (
                    probs[c] / total2
                    if total2 > 0 else 0
                )

                score = p1 * p2 * p3

                rows.append({
                    "3連単": f"{a}-{b}-{c}",
                    "AIスコア": score
                })

    return (
        pd.DataFrame(rows)
        .sort_values(
            "AIスコア",
            ascending=False
        )
        .reset_index(drop=True)
    )


# =========================
# UI
# =========================
st.sidebar.header("設定")

target_date = st.sidebar.date_input(
    "日付",
    value=date.today()
)

stadium_no = st.sidebar.selectbox(
    "競艇場",
    list(STADIUMS.keys()),
    format_func=lambda x: f"{x} {STADIUMS[x]}"
)

race_no = st.sidebar.selectbox(
    "レース",
    list(range(1, 13))
)

st.sidebar.caption("学習期間：過去21日")


# =========================
# 学習ボタン
# =========================
if st.button("🧠 AIを学習する", use_container_width=True):

    with st.spinner("過去データを取得してAIを学習中..."):

        h, success_days = learning_data(
            target_date,
            21
        )

        if len(h) == 0:

            st.error(
                "過去データを取得できませんでした。"
            )

            st.info(
                "API側にデータが無い日、またはAPIの一時的なエラーの可能性があります。"
            )

        else:

            model, accuracy, val_rows = train_model(h)

            if model is None:

                st.error(
                    f"学習データが不足しています。"
                    f"取得日数={success_days}日 / "
                    f"取得行数={len(h)}行"
                )

                st.info(
                    "APIから取得できた過去データが少ない可能性があります。"
                )

            else:

                st.session_state["model"] = model
                st.session_state["model_date"] = target_date
                st.session_state["accuracy"] = accuracy
                st.session_state["train_rows"] = len(h)
                st.session_state["success_days"] = success_days
                st.session_state["val_rows"] = val_rows

                st.success(
                    f"AI学習完了！ "
                    f"{success_days}日分 / {len(h)}行"
                )


# =========================
# 学習状態
# =========================
if "model" in st.session_state:

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "学習データ",
        f"{st.session_state['train_rows']:,}行"
    )

    c2.metric(
        "取得日数",
        f"{st.session_state['success_days']}日"
    )

    c3.metric(
        "検証精度",
        f"{st.session_state['accuracy']:.1%}"
    )


# =========================
# 予想ボタン
# =========================
if st.button(
    "🚀 結果検索・AI予想",
    use_container_width=True
):

    if "model" not in st.session_state:

        st.warning(
            "先に「🧠 AIを学習する」を押してください。"
        )

    elif st.session_state.get("model_date") != target_date:

        st.warning(
            "選択した日付がAI学習時の日付と違います。"
            "その日付で再度AI学習してください。"
        )

    else:

        with st.spinner("レース結果を取得中..."):

            try:
                data = get_data(target_date)

                races = data.get("races", []) or []

                race = None

                for r in races:

                    s = (
                        r.get("stadium")
                        or r.get("stadiumNumber")
                        or r.get("venue")
                        or r.get("place")
                    )

                    rn = (
                        r.get("raceNumber")
                        or r.get("race_no")
                        or r.get("number")
                    )

                    try:
                        if (
                            int(s) == stadium_no
                            and int(rn) == race_no
                        ):
                            race = r
                            break
                    except:
                        continue

                if race is None:

                    st.error(
                        "指定したレースのデータが見つかりません。"
                    )

                else:

                    rdf = make_race_df(race)

                    if len(rdf) < 6:

                        st.error(
                            "6艇分のデータを取得できませんでした。"
                        )

                    else:

                        # -------------------------
                        # 天候
                        # -------------------------
                        temp, wind, wind_dir = weather_info(race)

                        st.subheader(
                            f"🏁 {STADIUMS[stadium_no]} "
                            f"{race_no}R"
                        )

                        st.caption(
                            f"気温 {temp}℃ / "
                            f"風速 {wind} / "
                            f"風向 {wind_dir}"
                        )

                        # -------------------------
                        # AI予想
                        # -------------------------
                        result = predict_first(
                            st.session_state["model"],
                            rdf
                        )

                        result["1着確率"] = (
                            result["1着確率"] * 100
                        ).round(1)

                        st.subheader("🥇 AI 1着予想")

                        st.dataframe(
                            result[
                                [
                                    "枠",
                                    "選手名",
                                    "全国勝率",
                                    "全国2連率",
                                    "当地勝率",
                                    "モーター2連率",
                                    "平均ST",
                                    "展示",
                                    "1着確率"
                                ]
                            ],
                            use_container_width=True,
                            hide_index=True
                        )

                        # -------------------------
                        # 3連単
                        # -------------------------
                        tri = trifecta_rank(
                            result.assign(
                                **{
                                    "1着確率":
                                    result["1着確率"] / 100
                                }
                            )
                        )

                        st.subheader("🎯 AI 3連単ランキング")

                        top = tri.head(10).copy()

                        top["AIスコア"] = (
                            top["AIスコア"] * 100
                        ).round(2)

                        st.dataframe(
                            top,
                            use_container_width=True,
                            hide_index=True
                        )

                        # -------------------------
                        # 本命
                        # -------------------------
                        best = tri.iloc[0]["3連単"]

                        st.success(
                            f"🔥 AI本命：{best}"
                        )

            except Exception as e:

                st.error(
                    f"データ取得エラー：{e}"
                )


st.divider()

st.caption(
    "※AIスコアは過去データから算出した予測値であり、舟券の的中を保証するものではありません。"
                )
