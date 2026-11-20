"""Lean for every unplayed game, from the model that held up on unseen seasons.

Trains the boosted-tree model from learn_weights.py on every completed game
since 2018, then scores each unplayed game (lineups and grades from each team's
most recent game). Output: results/UPCOMING_LEANS.md. A lean is points the
model expects the home side to beat (+) or miss (-) the spread by. Games with no
line posted yet get no lean.
"""
import os
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from learn_weights import frame, PAIRS
from twins import load, upcoming_cell

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    c, feats = frame()
    tr = c[c.season >= 2018]
    med = tr[feats].astype(float).median()
    m = HistGradientBoostingRegressor(max_depth=3, learning_rate=0.03, max_iter=300, l2_regularization=5.0)
    m.fit(tr[feats].astype(float).fillna(med), tr.result_vs_line)
    allc = load()
    up = allc[allc.off_points.isna() & allc.line.notna()].game_id.unique()
    rows = []
    for gid in up:
        t = upcoming_cell(allc, gid)
        t["rest_diff"] = t.off_rest - t.def_rest
        for o, d in PAIRS:
            t[f"pair_{o}_vs_{d}"] = pd.to_numeric(t[f"off_{o}"], errors="coerce") - pd.to_numeric(t[f"def_{d}"], errors="coerce")
        X = t[feats].apply(pd.to_numeric, errors="coerce").astype(float).fillna(med)
        p = m.predict(X)
        h = t.off_home.values == 1
        if h.sum() != 1:
            continue
        home, away = t[h].iloc[0], t[~h].iloc[0]
        edge = p[h][0] - p[~h][0]
        rows.append({"date": home.gameday, "game": f"{away.offense} at {home.offense}", "home_line": home.line,
                     "lean_pts": round(edge, 1), "side": home.offense if edge > 0 else away.offense,
                     "home_QB": home.off_QB1_player_display_name, "away_QB": away.off_QB1_player_display_name})
    r = pd.DataFrame(rows).sort_values(["date", "lean_pts"], key=lambda s: s.abs() if s.name == "lean_pts" else s,
                                       ascending=[True, False])
    L = ["# Leans for unplayed games", "",
         "Experimental. From the model that covered 54.2% on 917 unseen games (2023-2026). "
         "Lean = points the home side is expected to beat (+) or miss (-) the spread by. "
         "In testing, only the strongest fifth of leans (about 2 points or more either way) did clearly better.", "",
         "| Date | Game | Home line | Lean | Side | QBs (home v away) |", "| --- | --- | --- | --- | --- | --- |"]
    for _, x in r.iterrows():
        L.append(f"| {x.date} | {x.game} | {x.home_line:+.1f} | {x.lean_pts:+.1f} | {x.side} | {x.home_QB} v {x.away_QB} |")
    open(os.path.join(ROOT, "results", "UPCOMING_LEANS.md"), "w").write("\n".join(L))
    print(r.to_string(index=False))


if __name__ == "__main__":
    main()
