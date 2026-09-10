import itertools
import numpy as np
import pandas as pd


def combo_text(c):
    return "-".join(map(str, c))


def _n(df, col):
    s = pd.to_numeric(df.get(col, 0), errors="coerce").fillna(0)
    if len(s) == 0:
        return s
    lo, hi = s.quantile(.05), s.quantile(.95)
    s = s.clip(lo, hi)
    if hi - lo < 1e-9:
        return pd.Series(.5, index=df.index)
    return (s - s.min()) / (s.max() - s.min())


def _prepare(df):
    x = pd.DataFrame(index=df.index)
    cols = [
        "national_win_rate", "national_top_2_percent",
        "national_top_3_percent", "local_win_rate",
        "local_top_2_percent", "local_top_3_percent",
        "motor_top_2_percent", "motor_top_3_percent",
        "boat_top_2_percent", "boat_top_3_percent",
        "start_timing", "exhibition_time", "course_number"
    ]
    for c in cols:
        x[c] = _n(df, c)
    x["st"] = 1 - x["start_timing"]
    x["exh"] = 1 - x["exhibition_time"]
    x["course"] = (1 - (
        pd.to_numeric(
            df.get("course_number", 1),
            errors="coerce"
        ).fillna(1) - 1
    ) / 5).clip(0, 1)
    return x


def _soft(v, t=.075):
    v = np.asarray(v, float)
    z = v / max(t, .001)
    z -= z.max()
    e = np.exp(z)
    return e / e.sum()


def _scores(x):
    f, s, t = {}, {}, {}

    for i in range(6):
        r = x.iloc[i]
        b = i + 1

        f[b] = (
            .24*r.national_win_rate +
            .13*r.local_win_rate +
            .13*r.national_top_2_percent +
            .08*r.local_top_2_percent +
            .10*r.motor_top_2_percent +
            .06*r.boat_top_2_percent +
            .12*r.st + .08*r.exh + .06*r.course
        )

        s[b] = (
            .18*r.national_top_2_percent +
            .14*r.local_top_2_percent +
            .16*r.national_top_3_percent +
            .10*r.local_top_3_percent +
            .14*r.motor_top_2_percent +
            .08*r.motor_top_3_percent +
            .10*r.boat_top_2_percent +
            .10*r.st
        )

        t[b] = (
            .18*r.national_top_3_percent +
            .14*r.local_top_3_percent +
            .16*r.motor_top_3_percent +
            .12*r.boat_top_3_percent +
            .12*r.national_top_2_percent +
            .10*r.local_top_2_percent +
            .10*r.st + .08*r.exh
        )

    return f, s, t


def _raw(a, b, c, f, s, t):
    v = f[a] + .72*s[b] + .58*t[c]
    if a == 1:
        v += .055
    elif a == 2:
        v += .025
    if b == 1:
        v += .020
    return v


def _bonus(b, c, s, t, axis):
    role = (
        np.clip(s[b]-t[b], -.30, .30) +
        np.clip(t[c]-s[c], -.30, .30)
    ) / 2
    gap = np.clip(s[b]-t[c], -.30, .30)
    rw = .031 if axis == 5 else .025
    return .035*gap + rw*role


def _main_counter(ranked, f, s, t):
    original = ranked[0]
    axis = original[0][0]
    candidate = axis

    if axis != 5 and f[axis] - f[5] <= .025:
        b5 = next(
            (x for x in ranked if x[0][0] == 5),
            None
        )
        if b5 and b5[1] >= original[1] - .035:
            candidate = 5

    pool = [x for x in ranked[:10] if x[0][0] == candidate]
    if not pool:
        pool = [x for x in ranked if x[0][0] == candidate]

    adj = sorted(
        pool,
        key=lambda x: x[1] + _bonus(
            x[0][1], x[0][2], s, t, candidate
        ),
        reverse=True
    )

    main = adj[0]

    if main[1] < original[1] - .045:
        main = original
        counter = next(
            (x for x in pool if x[0] != main[0]),
            None
        )
    else:
        counter = next(
            (x for x in adj if x[0] != main[0]),
            None
        )

    return main, counter


def _hole(ranked, main, counter, f):
    axis = ranked[0][0][0]
    used = {main[0]}
    if counter:
        used.add(counter[0])

    boats = sorted(
        [b for b in range(1, 7) if b != axis],
        key=lambda b: f[b],
        reverse=True
    )

    if axis != 1 and 1 not in boats:
        top = f[boats[0]] if boats else 0
        if f[1] >= top - .08:
            boats.append(1)

    cand = []

    for a in boats[:4]:
        best = next(
            (
                x for x in ranked
                if x[0][0] == a and x[0] not in used
            ),
            None
        )
        if best:
            score = .70*f[a] + .30*best[1]
            cand.append((score, best))

    if not cand:
        return None

    return max(cand, key=lambda x: x[0])[1]


def predict(df):
    if len(df) != 6:
        raise ValueError("予想には6艇のデータが必要です。")

    x = _prepare(df)
    f, s, t = _scores(x)

    raw = []
    for a, b, c in itertools.permutations(range(1, 7), 3):
        raw.append(((a, b, c), _raw(a, b, c, f, s, t)))

    raw.sort(key=lambda z: z[1], reverse=True)
    p = _soft([z[1] for z in raw])

    ranked = [
        (z[0], z[1], float(p[i]))
        for i, z in enumerate(raw)
    ]

    main, counter = _main_counter(
        ranked, f, s, t
    )

    if counter is None:
        counter = next(
            x for x in ranked
            if x[0] != main[0]
            and x[0][0] == main[0][0]
        )

    hole = _hole(
        ranked, main, counter, f
    )

    if hole is None:
        hole = next(
            x for x in ranked
            if x[0] not in {main[0], counter[0]}
        )

    tickets = [
        {
            "label": "本線",
            "combo": main[0],
            "score": float(main[1]),
            "probability": float(main[2]),
        },
        {
            "label": "対抗",
            "combo": counter[0],
            "score": float(counter[1]),
            "probability": float(counter[2]),
        },
        {
            "label": "穴",
            "combo": hole[0],
            "score": float(hole[1]),
            "probability": float(hole[2]),
        },
    ]

    # 軸は1着スコア1位で固定
    fr = sorted(
        f.items(),
        key=lambda z: z[1],
        reverse=True
    )
    axis = fr[0][0]

    probs = _soft(
        [f[b] for b in range(1, 7)],
        .10
    )

    axis_first = probs[axis - 1]
    top3 = sum(
        probs[b - 1]
        for b, _ in fr[:3]
    )

    gap = (
        ranked[0][1] - ranked[1][1]
        if len(ranked) > 1 else 0
    )

    confidence = np.clip(
        50 + gap*100,
        0,
        99
    )

    return {
        "axis": int(axis),
        "axis_first_probability": round(
            float(axis_first)*100, 2
        ),
        "axis_top3_probability": round(
            float(top3)*100, 2
        ),
        "confidence": round(
            float(confidence), 2
        ),
        "tickets": tickets,
    }
