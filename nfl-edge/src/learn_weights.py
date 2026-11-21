"""Which grading points and matchups move results AGAINST THE LINE?

Train on 2018-2022, judge on 2023-2026 (never seen while learning).
1. Every grading point, player pairing and setting factor on its own:
   does it line up with beating the spread, in both periods, the same way?
2. One model using all of them together (ridge regression), scored on the
   unseen seasons by how often its side covered.
Writes results/WHAT_MATTERS.md and data/processed/feature_weights.csv
(used to weight the twin search).
"""
import os, json
import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV
from sklearn.ensemble import HistGradientBoostingRegressor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(ROOT, "data", "processed")
TRAIN = range(2018, 2023)
TEST = range(2023, 2027)

PAIRS = [("WR1_epa_per_target", "CB1_yards_per_target"), ("WR2_epa_per_target", "CB2_yards_per_target"),
         ("WR3_epa_per_target", "CB3_yards_per_target"), ("TE1_epa_per_target", "S1_yards_per_target"),
         ("OT1_unit_pressure_allowed", "EDGE1_pressure_rate"), ("OT2_unit_pressure_allowed", "EDGE2_pressure_rate"),
         ("QB1_under_pressure_epa", "EDGE1_pressure_rate"), ("QB1_deep_epa", "S1_yards_per_target"),
         ("RB1_rush_epa", "DL1_run_stop_tfl"), ("IOL1_unit_run_epa", "DL1_run_stop_tfl"),
         ("RB1_rush_epa", "LB1_tackles"), ("QB1_sack_avoidance", "EDGE1_sack_rate")]
SETTING = ["off_home", "off_zones_travelled", "def_zones_travelled", "off_body_clock_hour", "def_body_clock_hour",
           "rest_diff", "temp_f", "wind_f", "is_dome", "primetime", "week", "days_after_clock_change", "line", "total_line"]


def frame():
    c = pd.read_parquet(os.path.join(PROC, "game_cells.parquet"))
    c = c[c.result_vs_line.notna() & (c.game_type == "REG")].copy()
    c["rest_diff"] = c.off_rest - c.def_rest
    c["is_dome"] = c.roof.isin(["dome", "closed"]).astype(float)
    c["temp_f"] = c.temp.where(c.is_dome == 0, 70).fillna(60)
    c["wind_f"] = c.wind.where(c.is_dome == 0, 0).fillna(5)
    for b in ["off_home", "primetime"]:
        c[b] = c[b].astype(float)
    grades = [x for x in c.columns if (x.startswith("off_") or x.startswith("def_")) and c[x].dtype.kind == "f"
              and x not in SETTING and not x.endswith("_rest") and "points" not in x]
    for o, d in PAIRS:
        c[f"pair_{o}_vs_{d}"] = c[f"off_{o}"] - c[f"def_{d}"]
    feats = grades + [f"pair_{o}_vs_{d}" for o, d in PAIRS] + SETTING
    return c, feats


def main():
    c, feats = frame()
    tr, te = c[c.season.isin(TRAIN)], c[c.season.isin(TEST)]
    y = "result_vs_line"
    rows = []
    for f in feats:
        a = tr[[f, y]].dropna(); b = te[[f, y]].dropna()
        if len(a) < 300 or len(b) < 200:
            continue
        ra = a[f].rank().corr(a[y].rank()); rb = b[f].rank().corr(b[y].rank())
        rm = tr[[f, "result_margin"]].dropna()
        rows.append({"feature": f, "corr_train": round(ra, 3), "corr_test": round(rb, 3),
                     "corr_with_margin": round(rm[f].rank().corr(rm.result_margin.rank()), 3),
                     "n_train": len(a), "n_test": len(b)})
    r = pd.DataFrame(rows)
    r["stable"] = (np.sign(r.corr_train) == np.sign(r.corr_test)) & (r.corr_train.abs() >= 0.03) & (r.corr_test.abs() >= 0.03)
    r = r.sort_values("corr_train", key=abs, ascending=False)
    # Weights for the twin search: how much each point lines up with the final margin (what decides games)
    w = r[["feature", "corr_with_margin", "corr_train"]].copy()
    w["weight"] = w.corr_with_margin.abs() + 2 * w.corr_train.abs()
    w.to_csv(os.path.join(PROC, "feature_weights.csv"), index=False)
    # One model, all features together
    X = lambda d: d[feats].astype(float).fillna(d[feats].astype(float).median())
    med = tr[feats].astype(float).median()
    Xtr, Xte = tr[feats].astype(float).fillna(med), te[feats].astype(float).fillna(med)
    res = {}
    for name, m in [("ridge", RidgeCV(alphas=np.logspace(0, 5, 20))),
                    ("boosted trees", HistGradientBoostingRegressor(max_depth=3, learning_rate=0.03, max_iter=300, l2_regularization=5.0))]:
        m.fit(Xtr, tr[y])
        p = pd.Series(m.predict(Xte), index=te.index)
        # Each game has two rows (one per offense): use the home offense row's prediction minus the away row's
        t2 = te.assign(p=p)
        h = t2[t2.off_home == 1].set_index("game_id"); a = t2[t2.off_home == 0].set_index("game_id")
        a = a[~a.index.duplicated()]; h = h[~h.index.duplicated()]
        g = h[["p", y, "season"]].join(a[["p"]], rsuffix="_away", how="inner")
        g["edge"] = g.p - g.p_away
        g = g[g[y] != 0]
        hit = lambda s: ((s.edge > 0) == (s[y] > 0)).mean()
        top = g[g.edge.abs() >= g.edge.abs().quantile(0.8)]
        res[name] = {"games": len(g), "all": hit(g), "strongest_20pct": hit(top), "strongest_n": len(top),
                     "by_season": {int(s): round(hit(x), 3) for s, x in g.groupby("season")}}
    L = ["# What matters against the line", "",
         f"Learned on {len(tr) // 2} games from 2018-2022, judged on {len(te) // 2} games from 2023-2026 that the "
         "learning never saw. \"Against the line\" = final margin minus the spread, so anything the betting market "
         "already priced counts for nothing here.", "",
         "## One model using everything", "",
         "Needed to profit at standard -110 odds: 52.4%.", "",
         "| Model | Games | Side covered | Strongest 20% of picks | By season |", "| --- | --- | --- | --- | --- |"]
    for k, v in res.items():
        L.append(f"| {k} | {v['games']} | {100 * v['all']:.1f}% | {100 * v['strongest_20pct']:.1f}% ({v['strongest_n']} games) | "
                 + ", ".join(f"{s}: {100 * h:.0f}%" for s, h in v["by_season"].items()) + " |")
    st = r[r.stable]
    L += ["", f"## Grading points that held up in both periods ({len(st)} of {len(r)})", "",
          "Positive = higher for the offense's side goes with beating the spread. Correlations this small are normal "
          "against a betting line; anything above about 0.05 is notable.", "",
          "| Grading point or pairing | 2018-2022 | 2023-2026 | With final margin |", "| --- | --- | --- | --- |"]
    for _, x in st.head(40).iterrows():
        L.append(f"| {x.feature} | {x.corr_train:+.3f} | {x.corr_test:+.3f} | {x.corr_with_margin:+.3f} |")
    L += ["", "## Strongest with the final margin (what decides games, mostly already in the line)", "",
          "| Grading point or pairing | With final margin |", "| --- | --- |"]
    for _, x in r.reindex(r.corr_with_margin.abs().sort_values(ascending=False).index).head(25).iterrows():
        L.append(f"| {x.feature} | {x.corr_with_margin:+.3f} |")
    r.to_csv(os.path.join(ROOT, "results", "what_matters_all.csv"), index=False)
    open(os.path.join(ROOT, "results", "WHAT_MATTERS.md"), "w").write("\n".join(L))
    print(json.dumps(res, indent=1)); print(st.head(25).to_string())


if __name__ == "__main__":
    main()
