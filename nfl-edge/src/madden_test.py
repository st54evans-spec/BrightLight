"""Put each player's Madden ratings into every matchup cell, then test them against the line.

For every game and both offenses, each role slot (QB1, RB1, WR1-3, TE1, OT1-2,
IOL1-3 vs EDGE1-2, DL1-2, LB1-2, CB1-3, S1-2) gets that player's ratings from
the Madden edition for that season, attribute by attribute, never blended. Then
head-to-head gaps for the pairings that meet on the field (WR speed vs the CB
across from him, tackle pass block vs the edge rusher's moves, and so on).

Test: the same boosted-tree model as learn_weights.py, trained 2018-2022, judged
on 2023-2025 (launch ratings, nothing known about the season yet). 2026 is shown
apart because the Madden 27 file is the Week 8 update.

Writes data/processed/game_cells_madden.parquet and results/MADDEN.md.
"""
import os, json
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from learn_weights import frame

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(ROOT, "data", "processed")

ROLE_ATTRS = {
    "QB": (1, ["overall", "awareness", "throwpower", "throwaccuracyshort", "throwaccuracymid", "throwaccuracydeep",
               "throwonrun", "throwunderpressure", "playaction", "breaksack", "speed", "injury"]),
    "RB": (1, ["overall", "speed", "acceleration", "agility", "trucking", "bcvision", "carrying", "jukemove",
               "spinmove", "stiffarm", "breaktackle", "catching", "changeofdirection"]),
    "WR": (3, ["overall", "speed", "acceleration", "release", "shortrouterunning", "midrouterunning",
               "deeprouterunning", "catching", "catchintraffic", "spectacularcatch", "jumping"]),
    "TE": (1, ["overall", "speed", "catching", "catchintraffic", "shortrouterunning", "runblock", "passblock"]),
    "OT": (2, ["overall", "passblock", "passblockpower", "passblockfinesse", "runblock", "runblockpower",
               "strength", "awareness"]),
    "IOL": (3, ["overall", "runblock", "runblockpower", "runblockfinesse", "passblock", "strength", "awareness"]),
    "EDGE": (2, ["overall", "speed", "acceleration", "powermoves", "finessemoves", "blockshedding", "strength",
                 "pursuit", "tackle", "playrecognition"]),
    "DL": (2, ["overall", "strength", "powermoves", "finessemoves", "blockshedding", "pursuit", "tackle",
               "playrecognition"]),
    "LB": (2, ["overall", "speed", "pursuit", "tackle", "hitpower", "playrecognition", "zonecoverage",
               "mancoverage", "blockshedding"]),
    "CB": (3, ["overall", "speed", "acceleration", "mancoverage", "zonecoverage", "press", "playrecognition",
               "jumping", "agility"]),
    "S": (2, ["overall", "speed", "zonecoverage", "mancoverage", "playrecognition", "tackle", "hitpower",
              "pursuit"]),
}
OFF_ROLES, DEF_ROLES = ["QB", "RB", "WR", "TE", "OT", "IOL"], ["EDGE", "DL", "LB", "CB", "S"]
# Head-to-head gaps: (offense slot, attribute, defense slot, attribute)
DUELS = ([(f"WR{i}", "speed", f"CB{i}", "speed") for i in (1, 2, 3)] +
         [(f"WR{i}", "release", f"CB{i}", "press") for i in (1, 2, 3)] +
         [(f"WR{i}", "deeprouterunning", f"CB{i}", "mancoverage") for i in (1, 2, 3)] +
         [(f"WR{i}", "shortrouterunning", f"CB{i}", "zonecoverage") for i in (1, 2, 3)] +
         [(f"WR{i}", "catchintraffic", f"CB{i}", "playrecognition") for i in (1, 2, 3)] +
         [("WR1", "speed", "S1", "speed"), ("TE1", "speed", "LB1", "speed"), ("TE1", "catchintraffic", "S1", "zonecoverage"),
          ("OT1", "passblockpower", "EDGE1", "powermoves"), ("OT1", "passblockfinesse", "EDGE1", "finessemoves"),
          ("OT2", "passblockpower", "EDGE2", "powermoves"), ("OT2", "passblockfinesse", "EDGE2", "finessemoves"),
          ("OT1", "passblock", "EDGE1", "speed"), ("OT2", "passblock", "EDGE2", "speed"),
          ("IOL1", "runblockpower", "DL1", "blockshedding"), ("IOL2", "runblockpower", "DL2", "blockshedding"),
          ("IOL1", "passblock", "DL1", "powermoves"), ("IOL2", "passblock", "DL2", "finessemoves"),
          ("RB1", "bcvision", "LB1", "pursuit"), ("RB1", "trucking", "LB1", "hitpower"),
          ("RB1", "jukemove", "S1", "tackle"), ("QB1", "throwunderpressure", "EDGE1", "finessemoves"),
          ("QB1", "throwaccuracydeep", "S1", "zonecoverage"), ("QB1", "awareness", "LB1", "playrecognition")])


def attach():
    c = pd.read_parquet(os.path.join(PROC, "game_cells.parquet"))
    m = pd.read_parquet(os.path.join(PROC, "madden_ratings.parquet"))
    m = m[m.player_id.notna()].drop_duplicates(["player_id", "season"])
    new = {}
    cover = []
    for side, roles in (("off", OFF_ROLES), ("def", DEF_ROLES)):
        for role in roles:
            n, attrs = ROLE_ATTRS[role]
            attrs = [a for a in attrs if f"m_{a}" in m]
            mm = m[["player_id", "season"] + [f"m_{a}" for a in attrs]]
            for s in range(1, n + 1):
                idc = f"{side}_{role}{s}_player_id"
                if idc not in c:
                    continue
                k = c[[idc, "season"]].rename(columns={idc: "player_id"})
                j = k.merge(mm, on=["player_id", "season"], how="left")
                for a in attrs:
                    new[f"{side}_{role}{s}_m_{a}"] = j[f"m_{a}"].values
                has = j[f"m_{attrs[0]}"].notna()
                for season, h in pd.Series(has.values, index=c.season.values).groupby(level=0):
                    cover.append({"season": season, "slot": f"{role}{s}", "played": int(k.player_id.notna()[c.season == season].sum()),
                                  "with_madden": int(h.sum())})
    md = pd.DataFrame(new, index=c.index)
    for o, oa, d, da in DUELS:
        a, b = f"off_{o}_m_{oa}", f"def_{d}_m_{da}"
        if a in md and b in md:
            md[f"duel_{o}_{oa}_vs_{d}_{da}"] = md[a] - md[b]
    out = pd.concat([c[["game_id", "season", "week", "offense", "defense"]], md], axis=1)
    out.to_parquet(os.path.join(PROC, "game_cells_madden.parquet"), index=False)
    cv = pd.DataFrame(cover).groupby("season")[["played", "with_madden"]].sum().astype(int)
    cv["share"] = (cv.with_madden / cv.played).round(3)
    return out, list(md.columns), cv


def score(tr, te, feats, y="result_vs_line"):
    med = tr[feats].astype(float).median()
    m = HistGradientBoostingRegressor(max_depth=3, learning_rate=0.03, max_iter=300, l2_regularization=5.0, random_state=0)
    m.fit(tr[feats].astype(float).fillna(med), tr[y])
    t2 = te.assign(p=m.predict(te[feats].astype(float).fillna(med)))
    h = t2[t2.off_home == 1].drop_duplicates("game_id").set_index("game_id")
    a = t2[t2.off_home == 0].drop_duplicates("game_id").set_index("game_id")
    g = h[["p", y, "season"]].join(a[["p"]], rsuffix="_away", how="inner")
    g["edge"] = g.p - g.p_away
    g = g[g[y] != 0]
    hit = lambda s: ((s.edge > 0) == (s[y] > 0)).mean() if len(s) else np.nan
    top = g[g.edge.abs() >= g.edge.abs().quantile(0.8)]
    return {"games": len(g), "all": round(100 * hit(g), 1), "top20": round(100 * hit(top), 1), "top_n": len(top),
            "by_season": {int(s): round(100 * hit(x), 1) for s, x in g.groupby("season")}}


def main():
    md, mfeats, cv = attach()
    c, base = frame()
    c = c.merge(md.drop(columns=["season", "week"]), on=["game_id", "offense", "defense"], how="left")
    tr = c[c.season.between(2018, 2022)]
    te = c[c.season.between(2023, 2025)]
    t26 = c[c.season == 2026]
    duels = [f for f in mfeats if f.startswith("duel_")]
    setting = ["off_home", "off_zones_travelled", "def_zones_travelled", "off_body_clock_hour", "def_body_clock_hour",
               "rest_diff", "temp_f", "wind_f", "is_dome", "primetime", "week", "days_after_clock_change", "line", "total_line"]
    runs = {"Our grades only (current model)": base,
            "Madden ratings only (+ setting)": mfeats + setting,
            "Madden duels only (+ setting)": duels + setting,
            "Our grades + Madden ratings": base + mfeats}
    res = {k: {"2023-2025": score(tr, te, f), "2026 (wk 8 ratings)": score(c[c.season.between(2018, 2025)], t26, f)}
           for k, f in runs.items()}
    # Each Madden point on its own, in both periods
    y = "result_vs_line"
    rows = []
    for f in mfeats:
        a, b = tr[[f, y]].dropna(), te[[f, y]].dropna()
        if len(a) < 300 or len(b) < 200:
            continue
        rm = tr[[f, "result_margin"]].dropna()
        rows.append({"feature": f, "corr_train": a[f].rank().corr(a[y].rank()), "corr_test": b[f].rank().corr(b[y].rank()),
                     "corr_with_margin": rm[f].rank().corr(rm.result_margin.rank()), "n_test": len(b)})
    r = pd.DataFrame(rows)
    r["stable"] = (np.sign(r.corr_train) == np.sign(r.corr_test)) & (r.corr_train.abs() >= 0.03) & (r.corr_test.abs() >= 0.03)
    r.round(3).to_csv(os.path.join(ROOT, "results", "madden_points.csv"), index=False)
    mr = pd.read_parquet(os.path.join(PROC, "madden_ratings.parquet"))
    per = mr.groupby("season").agg(players=("fullname", "size"))
    per["attributes_rated"] = [sum(x[col].notna().mean() > 0.5 for col in mr.columns if col.startswith("m_"))
                               for _, x in mr.groupby("season")]
    L = ["# Madden ratings", "",
         "Every player's Madden card for every edition we could reach, each attribute kept on its own "
         "(data/processed/madden_ratings.parquet, one row per player per edition). Season = the NFL season the edition "
         "was played for (Madden 25 = 2024). Ratings are the launch cards for 2001-2025 and the Week 8 update for 2026.", "",
         "## What we have", "",
         "| Season | Madden | Players rated | Attributes rated |", "| --- | --- | --- | --- |"]
    for s, x in per.iterrows():
        L.append(f"| {s} | {str(s + 1)[2:]} | {x.players} | {x.attributes_rated} |")
    L += ["", "Gaps: Madden 03 (2002) sheet has only the overall rating; Madden 10 (2009) sheet is essentially empty in the "
          "source; Madden 05 and 12 sheets carry only part of the attributes. Nothing was filled in by guessing.", "",
          "## How many of our lineup slots have a Madden card", "",
          "| Season | Player slots | With Madden | Share |", "| --- | --- | --- | --- |"]
    for s, x in cv.iterrows():
        L.append(f"| {s} | {x.played} | {x.with_madden} | {100 * x.share:.0f}% |")
    L += ["", "## Do the ratings help against the line?", "",
          "Same boosted-tree model, trained 2018-2022. Needed to profit at -110: 52.4%.", "",
          "| Features | 2023-2025 games | Covered | Strongest 20% | By season | 2026 covered | 2026 strongest 20% |",
          "| --- | --- | --- | --- | --- | --- | --- |"]
    for k, v in res.items():
        a, b = v["2023-2025"], v["2026 (wk 8 ratings)"]
        L.append(f"| {k} | {a['games']} | {a['all']}% | {a['top20']}% ({a['top_n']}) | "
                 + ", ".join(f"{s}: {h}%" for s, h in a["by_season"].items())
                 + f" | {b['all']}% ({b['games']}) | {b['top20']}% ({b['top_n']}) |")
    st = r[r.stable].sort_values("corr_test", key=abs, ascending=False)
    L += ["", f"## Madden points that held up in both periods ({len(st)} of {len(r)})", "",
          "Positive = higher for the offense's side goes with beating the spread.", "",
          "| Rating or duel | 2018-2022 | 2023-2025 | With final margin |", "| --- | --- | --- | --- |"]
    for _, x in st.head(40).iterrows():
        L.append(f"| {x.feature} | {x.corr_train:+.3f} | {x.corr_test:+.3f} | {x.corr_with_margin:+.3f} |")
    L += ["", "## Strongest with the final margin (who wins, mostly already in the line)", "",
          "| Rating or duel | With final margin |", "| --- | --- |"]
    for _, x in r.reindex(r.corr_with_margin.abs().sort_values(ascending=False).index).head(20).iterrows():
        L.append(f"| {x.feature} | {x.corr_with_margin:+.3f} |")
    open(os.path.join(ROOT, "results", "MADDEN.md"), "w").write("\n".join(L))
    print(cv.to_string()); print(json.dumps(res, indent=1)); print(st.head(25).round(3).to_string())


if __name__ == "__main__":
    main()
