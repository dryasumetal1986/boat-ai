import itertools
import math
import numpy as np
import pandas as pd

BOATS = (1, 2, 3, 4, 5, 6)


def _norm_series(s, higher=True):
    x = pd.to_numeric(s, errors="coerce").fillna(0.0).astype(float)
    if len(x) == 0:
        return x
    lo, hi = float(x.min()), float(x.max())
    if hi - lo < 1e-12:
        z = pd.Series(0.5, index=x.index)
    else:
        z = (x - lo) / (hi - lo)
    return z if higher else 1.0 - z


def _prepare(df):
    x = df.copy().reset_index(drop=True)
    for c in [
        "national_win_rate", "national_top_2_percent", "national_top_3_percent",
        "local_win_rate", "local_top_2_percent", "local_top_3_percent",
        "motor_top_2_percent", "motor_top_3_percent",
        "boat_top_2_percent", "boat_top_3_percent",
        "average_start_timing", "start_timing", "exhibition_time",
        "course_number",
    ]:
        if c not in x.columns:
            x[c] = 0.0
        x[c] = pd.to_numeric(x[c], errors="coerce")

    x["win_n"] = _norm_series(x["national_win_rate"])
    x["win_l"] = _norm_series(x["local_win_rate"])
    x["top2_n"] = _norm_series(x["national_top_2_percent"])
    x["top2_l"] = _norm_series(x["local_top_2_percent"])
    x["top3_n"] = _norm_series(x["national_top_3_percent"])
    x["top3_l"] = _norm_series(x["local_top_3_percent"])
    x["motor2"] = _norm_series(x["motor_top_2_percent"])
    x["motor3"] = _norm_series(x["motor_top_3_percent"])
    x["boat2"] = _norm_series(x["boat_top_2_percent"])
    x["boat3"] = _norm_series(x["boat_top_3_percent"])
    x["st"] = _norm_series(x["start_timing"], higher=False)

    exh = pd.to_numeric(x["exhibition_time"], errors="coerce")
    valid_exh = exh.replace(0, np.nan)
    med = float(valid_exh.median()) if valid_exh.notna().any() else 0.0
    exh = exh.replace(0, np.nan).fillna(med)
    x["exh"] = _norm_series(exh, higher=False)

    x["course"] = 1.0 - (pd.to_numeric(x["course_number"], errors="coerce").fillna(3.5) - 1.0) / 5.0
    x["course"] = x["course"].clip(0.0, 1.0)

    x["first_score"] = (
        .22*x["win_n"] + .13*x["win_l"] + .13*x["top2_n"] + .08*x["top2_l"]
        + .10*x["motor2"] + .06*x["boat2"] + .12*x["st"] + .10*x["exh"] + .06*x["course"]
    )
    x["second_score"] = (
        .18*x["top2_n"] + .14*x["top2_l"] + .16*x["top3_n"] + .10*x["top3_l"]
        + .14*x["motor2"] + .08*x["motor3"] + .10*x["boat2"] + .10*x["st"]
    )

    # EXPERIMENT ONLY:
    # Baseline ST weight was 0.10. This version tests 0.07 to reduce
    # possible over-reliance on raw ST when selecting the 3rd-place boat.
    x["third_score"] = (
        .18*x["top3_n"] + .14*x["top3_l"] + .16*x["motor3"] + .12*x["boat3"]
        + .12*x["top2_n"] + .10*x["top2_l"] + .07*x["st"] + .08*x["exh"]
    )
    return x


def _softmax(values, temp=0.075):
    a = np.asarray(values, dtype=float)
    if len(a) == 0:
        return np.array([])
    t = max(float(temp), 1e-6)
    z = (a - np.max(a)) / t
    e = np.exp(np.clip(z, -60, 60))
    return e / max(float(e.sum()), 1e-12)


def _combo_score(rowmap, combo):
    a, b, c = combo
    ra, rb, rc = rowmap[a], rowmap[b], rowmap[c]
    score = 1.00*ra.first_score + .72*rb.second_score + .58*rc.third_score
    if a == 1:
        score += .055
    elif a == 2:
        score += .025
    if b == 1:
        score += .020
    return float(score)


def _ordering_bonus(rowmap, combo):
    a, b, c = combo
    rb, rc = rowmap[b], rowmap[c]
    gap = float(rb.second_score - rc.third_score)
    bonus = .045 * max(0.0, gap)
    if b in (1, 2, 3):
        bonus += .025
    return float(bonus)


def _venue_profile(stadium_no):
    profiles = {
        1:(.010,.000), 2:(.006,.000), 3:(.008,.000), 4:(.006,.000),
        5:(.010,.000), 6:(.006,.000), 7:(.006,.000), 8:(.008,.000),
        9:(.008,.000), 10:(.008,.000), 11:(.010,.000), 12:(.008,.000),
        13:(.008,.000), 14:(.008,.000), 15:(.008,.000), 16:(.008,.000),
        17:(.008,.000), 18:(.008,.000), 19:(.008,.000), 20:(.010,.000),
        21:(.008,.000), 22:(.008,.000), 23:(.008,.000), 24:(.008,.000),
    }
    return profiles.get(int(stadium_no or 0), (.008, .0))


def _venue_axis_bonus(stadium_no, boat):
    # Kept identical to the 14.1% baseline.
    p = {
        1: {1:.010,2:.006,3:.002,4:.000,5:-.002,6:-.004},
        2: {1:.010,2:.006,3:.002,4:.000,5:-.002,6:-.004},
        3: {1:.010,2:.006,3:.002,4:.000,5:-.002,6:-.004},
        4: {1:.010,2:.006,3:.002,4:.000,5:-.002,6:-.004},
        5: {1:.010,2:.006,3:.002,4:.000,5:-.002,6:-.004},
        6: {1:.010,2:.006,3:.002,4:.000,5:-.002,6:-.004},
        7: {1:.010,2:.006,3:.002,4:.000,5:-.002,6:-.004},
        8: {1:.010,2:.006,3:.002,4:.000,5:-.002,6:-.004},
        9: {1:.010,2:.006,3:.002,4:.000,5:-.002,6:-.004},
        10:{1:.010,2:.006,3:.002,4:.000,5:-.002,6:-.004},
        11:{1:.010,2:.006,3:.002,4:.000,5:-.002,6:-.004},
        12:{1:.010,2:.006,3:.002,4:.000,5:-.002,6:-.004},
        13:{1:.010,2:.006,3:.002,4:.000,5:-.002,6:-.004},
        14:{1:.010,2:.006,3:.002,4:.000,5:-.002,6:-.004},
        15:{1:.010,2:.006,3:.002,4:.000,5:-.002,6:-.004},
        16:{1:.010,2:.006,3:.002,4:.000,5:-.002,6:-.004},
        17:{1:.010,2:.006,3:.002,4:.000,5:-.002,6:-.004},
        18:{1:.010,2:.006,3:.002,4:.000,5:-.002,6:-.004},
        19:{1:.010,2:.006,3:.002,4:.000,5:-.002,6:-.004},
        20:{1:.010,2:.006,3:.002,4:.000,5:-.002,6:-.004},
        21:{1:.010,2:.006,3:.002,4:.000,5:-.002,6:-.004},
        22:{1:.010,2:.006,3:.002,4:.000,5:-.002,6:-.004},
        23:{1:.010,2:.006,3:.002,4:.000,5:-.002,6:-.004},
        24:{1:.010,2:.006,3:.002,4:.000,5:-.002,6:-.004},
    }
    return profiles.get(int(stadium_no or 0), {}).get(int(boat), 0.0)


def _apply_venue_adjustment(scores, combos, stadium_no):
    axis_adj, _ = _venue_profile(stadium_no)
    out = np.asarray(scores, dtype=float).copy()
    for i, combo in enumerate(combos):
        a = int(combo[0])
        out[i] += axis_adj if a == 1 else 0.0
        out[i] += _venue_axis_bonus(stadium_no, a)
    return out


def _select_main_counter(ranking, rowmap):
    main = ranking[0]
    counter = None
    for combo in ranking[1:]:
        if combo[0] != main[0]:
            counter = combo
            break
    if counter is None:
        for combo in ranking[1:]:
            if combo != main:
                counter = combo
                break
    return main, counter or ranking[1]


def _select_hole(ranking, main, counter, rowmap):
    used_axes = {main[0], counter[0]}
    candidates = []
    for combo in ranking:
        if combo in (main, counter):
            continue
        a, b, c = combo
        score = 0.0
        if a not in used_axes:
            score += .025
        if c == 2:
            score += .018
        first_diff = abs(rowmap[a].first_score - rowmap[main[0]].first_score)
        score += .035 * float(np.clip(first_diff, 0, 1))
        score += .035 * float(rowmap[c].third_score)
        candidates.append((score, combo))
    if candidates:
        candidates.sort(key=lambda z: z[0], reverse=True)
        return candidates[0][1]
    return ranking[2]


def predict(df, stadium_no=None):
    if df is None or len(df) < 3:
        raise ValueError("有効な艇データが3艇未満です")
    x = df.copy().reset_index(drop=True)
    if "boat" in x.columns:
        x["boat"] = pd.to_numeric(x["boat"], errors="coerce").astype(int)
    else:
        x["boat"] = np.arange(1, len(x) + 1)
    x = x[x["boat"].isin(BOATS)].copy().reset_index(drop=True)
    if len(x) < 3:
        raise ValueError("有効な艇データが3艇未満です")
    active = tuple(int(v) for v in x["boat"].tolist())
    x = _prepare(x)
    rowmap = {int(r.boat): r for _, r in x.iterrows()}

    combos = list(itertools.permutations(active, 3))
    raw = np.array([_combo_score(rowmap, c) + _ordering_bonus(rowmap, c) for c in combos], dtype=float)
    probs = _softmax(_apply_venue_adjustment(raw, combos, stadium_no), temp=.075)
    order = np.argsort(-probs)
    ranking = [combos[i] for i in order]
    main, counter = _select_main_counter(ranking, rowmap)
    hole = _select_hole(ranking, main, counter, rowmap)

    first_raw = np.array([rowmap[b].first_score for b in active], dtype=float)
    first_prob = _softmax(first_raw, temp=.10)
    axis_top3 = float(sum(sorted(first_prob, reverse=True)[:3]))
    confidence = float(max(probs))

    return {
        "main": tuple(main),
        "counter": tuple(counter),
        "hole": tuple(hole),
        "tickets": [tuple(main), tuple(counter), tuple(hole)],
        "ranking": ranking,
        "combo_probs": {tuple(c): float(p) for c, p in zip(combos, probs)},
        "first_probs": {int(b): float(p) for b, p in zip(active, first_prob)},
        "axis_top3": axis_top3,
        "confidence": confidence,
        "prepared": x,
    }


def combo_text(combo):
    return "-".join(str(int(v)) for v in combo)
