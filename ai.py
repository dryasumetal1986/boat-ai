import itertools
import numpy as np
import pandas as pd


def combo_text(c):
    return "-".join(map(str, c))


def _norm(df, col):
    if col not in df.columns:
        return pd.Series(0.0, index=df.index)
    s = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
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
        x[c] = _norm(df, c)
    x["st"] = 1 - x["start_timing"]
    x["exh"] = 1 - x["exhibition_time"]
    return x


def _soft(v, t=.075):
    v = np.asarray(v, dtype=float)
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
            .12*r.st + .08*r.exh +
            .06*r.course_number
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
    return float(v)


def _bonus(b, c, s, t, axis):
    role = (
        np.clip(s[b] - t[b], -.30, .30) +
        np.clip(t[c] - s[c], -.30, .30)
    ) / 2
    gap = np.clip(s[b] - t[c], -.30, .30)
    weight = .025
    if axis == 5:
        weight = .031
    return .035 * gap + weight * role


def _main_counter(ranked, f, s, t):
    original = ranked[0]
    original_axis = original[0][0]
    candidate_axis = original_axis

    # 5号艇救済
    if original_axis != 5:
        if f[original_axis] - f[5] <= .025:
            b5 = next(
                (x for x in ranked if x[0][0] == 5),
                None
            )
            if b5 and b5[1] >= original[1] - .035:
                candidate_axis = 5

    pool = [
        x for x in ranked[:10]
        if x[0][0] == candidate_axis
    ]

    if not pool:
        pool = [
            x for x in ranked
            if x[0][0] == candidate_axis
        ]

    adj = sorted(
        pool,
        key=lambda x: x[1] + _bonus(
            x[0][1],
            x[0][2],
            s,
            t,
            candidate_axis
        ),
        reverse=True
    )

    main = adj[0]
    counter = next(
        (x for x in adj if x[0] != main[0]),
        None
    )

    # 本線が弱くなりすぎたら元へ戻す
    if main[1] < original[1] - .045:
        main = original

        # ★重要：
        # 戻した場合は「元の軸」の候補から対抗を選ぶ
        original_pool = [
            x for x in ranked[:10]
            if x[0][0] == original_axis
            and x[0] != original[0]
        ]

        if not original_pool:
            original_pool = [
                x for x in ranked
                if x[0][0] == original_axis
                and x[0] != original[0]
            ]

        counter = original_pool[0] if original_pool else None

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

    if axis != 1:
        top = f[boats[0]] if boats else 0
        if f[1] >= top - .08:
            boats.append(1)

    candidates = []

    for a in boats[:4]:
        best = next(
            (
                x for x in ranked
                if x[0][0] == a
                and x[0] not in used
            ),
            None
        )

        if best:
            score = .70*f[a] + .30*best[1]
            candidates.append((score, best))

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda x: x[0]
    )[1]


def predict(df):
    if len(df) != 6:
        raise ValueError("予想には6艇のデータが必要です。")

    x = _prepare(df)
    f, s, t = _scores(x)

    raw = [
        (
            (a, b, c),
            _raw(a, b, c, f, s, t)
        )
        for a, b, c in itertools.permutations(
            range(1, 7), 3
        )
    ]

    raw.sort(key=lambda x: x[1], reverse=True)
    probs = _soft([x[1] for x in raw])

    ranked = [
        (x[0], x[1], float(probs[i]))
        for i, x in enumerate(raw)
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
        ranked,
        main,
        counter,
        f
    )

    if hole is None:
        hole = next(
            x for x in ranked
            if x[0] not in {
                main[0],
                counter[0]
            }
        )

    tickets = [
        {
            "label": "本線",
            "combo": main[0],
            "score": float(main[1]),
            "probability": float(main[2])
        },
        {
            "label": "対抗",
            "combo": counter[0],
            "score": float(counter[1]),
            "probability": float(counter[2])
        },
        {
            "label": "穴",
            "combo": hole[0],
            "score": float(hole[1]),
            "probability": float(hole[2])
        }
    ]

    # 軸は1着スコア1位
    fr = sorted(
        f.items(),
        key=lambda x: x[1],
        reverse=True
    )

    axis = int(fr[0][0])

    axis_probs = _soft(
        [f[b] for b in range(1, 7)],
        .10
    )

    axis_first = axis_probs[axis - 1]

    top3 = sum(
        axis_probs[b - 1]
        for b, _ in fr[:3]
    )

    gap = (
        ranked[0][1] - ranked[1][1]
        if len(ranked) > 1
        else 0
    )

    confidence = np.clip(
        50 + gap * 100,
        0,
        99
    )

    return {
        "axis": axis,
        "axis_first_probability": round(
            float(axis_first) * 100,
            2
        ),
        "axis_top3_probability": round(
            float(top3) * 100,
            2
        ),
        "confidence": round(
            float(confidence),
            2
        ),
        "tickets": tickets
        }
