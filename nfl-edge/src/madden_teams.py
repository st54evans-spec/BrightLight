"""Team Madden numbers for every team in every edition, then every past game run on them.

No reachable source publishes EA's own team ratings by edition (EA's site and
maddenratings.weebly.com are blocked from here, and no public data set carries
them), so the team numbers are built from that edition's player cards, the same
cards EA builds its team rating from. Each team's preseason Madden roster is
ranked by overall at each spot:
  QB1, RB1, WR1-3, TE1, OL1-5   |   DL1-4, LB1-3, DB1-4   |   K, P
Every slot stays its own number. Unit numbers (QB, RB, WR, TE, OL, DL, LB, DB)
are the slots in that unit; offense = the 11 offensive starters, defense = the
11 defensive starters, team = all 22 plus K and P. Each team and edition is its
own row: nothing is pooled across seasons.

Then every game since 2001 gets both teams' numbers side by side, plus the
head-to-head unit gaps (home QB vs away DB, home OL vs away DL, ...), and:
  1. how often the higher-rated team won, by size of the gap
  2. how often it covered the spread, by size of the gap
  3. a model that learns from 2001-2015 games and is judged on 2016-2025
  4. for every unplayed game, the past games whose two Madden teams look most like it

Writes data/processed/madden_teams.parquet, results/madden_team_games.csv,
results/MADDEN_TEAMS.md and results/madden_team_twins/<game_id>.md.
"""
import os
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(ROOT, "data", "processed")
RES = os.path.join(ROOT, "results")

GROUP = {"quarterback": "QB", "o_rush": "RB", "o_pass": "WR", "o_te": "TE", "o_line": "OL", "d_line": "DL",
         "d_lb": "LB", "d_field": "DB"}
POS = {"QB": "QB", "HB": "RB", "RB": "RB", "FB": "RB", "WR": "WR", "TE": "TE",
       "LT": "OL", "LG": "OL", "C": "OL", "RG": "OL", "RT": "OL", "T": "OL", "G": "OL", "OL": "OL",
       "LEDG": "DL", "REDG": "DL", "DE": "DL", "DT": "DL", "NT": "DL", "DL": "DL",
       "MIKE": "LB", "WILL": "LB", "SAM": "LB", "LB": "LB", "OLB": "LB", "MLB": "LB", "ILB": "LB",
       "CB": "DB", "FS": "DB", "SS": "DB", "S": "DB", "DB": "DB", "K": "K", "P": "P"}
SLOTS = {"QB": 1, "RB": 1, "WR": 3, "TE": 1, "OL": 5, "DL": 4, "LB": 3, "DB": 4, "K": 1, "P": 1}
OFFU, DEFU = ["QB", "RB", "WR", "TE", "OL"], ["DL", "LB", "DB"]
# Madden files use today's franchise codes; the schedule uses the code of the time
SCHED = {"SD": "LAC", "OAK": "LV", "STL": "LAR", "LA": "LAR"}
DUELS = [("QB", "DB"), ("WR", "DB"), ("TE", "LB"), ("OL", "DL"), ("RB", "LB"), ("RB", "DL"), ("QB", "DL")]


def team_numbers():
    m = pd.read_parquet(os.path.join(PROC, "madden_ratings.parquet"))
    m = m[m.m_overall.notna() & m.team.notna()].copy()
    m["team"] = m.team.replace({"LA": "LAR"})
    u = m.position_group.map(GROUP)
    st = m.position.map({"K": "K", "P": "P"})
    m["unit"] = st.fillna(u).fillna(m.position.map(POS))
    m = m[m.unit.notna()].sort_values(["season", "team", "unit", "m_overall"], ascending=[True, True, True, False])
    m["slot"] = m.groupby(["season", "team", "unit"]).cumcount() + 1
    m = m[m.slot <= m.unit.map(SLOTS)]
    rows = []
    for (s, t), x in m.groupby(["season", "team"]):
        r = {"season": s, "madden_edition": s + 1, "team": t}
        for _, p in x.iterrows():
            k = f"{p.unit}{p.slot}" if SLOTS[p.unit] > 1 else p.unit
            r[f"{k}_ovr"] = p.m_overall
            r[f"{k}_name"] = p.fullname
        for un in SLOTS:
            r[f"unit_{un}"] = x[x.unit == un].m_overall.mean()
        r["offense"] = x[x.unit.isin(OFFU)].m_overall.mean()
        r["defense"] = x[x.unit.isin(DEFU)].m_overall.mean()
        r["team_ovr"] = x.m_overall.mean()
        r["starters_rated"] = len(x)
        rows.append(r)
    t = pd.DataFrame(rows)
    # A team with most starter spots unrated is not a real Madden roster (the 2009 source sheet is nearly empty)
    t = t[t.starters_rated >= 20]
    t.to_parquet(os.path.join(PROC, "madden_teams.parquet"), index=False)
    return t


def games(t):
    g = pd.read_csv(os.path.join(ROOT, "data", "raw", "games.csv"))
    g = g[g.season >= 2001].copy()
    num = [c for c in t.columns if c.startswith("unit_") or c in ("offense", "defense", "team_ovr")]
    keep = ["season", "team"] + num + ["QB_name"]
    for side in ("home", "away"):
        g[f"_{side}"] = g[f"{side}_team"].replace(SCHED)
        x = t[keep].rename(columns={c: f"{side}_{c}" for c in keep if c not in ("season", "team")})
        g = g.merge(x.rename(columns={"team": f"_{side}"}), on=["season", f"_{side}"], how="left")
    g["gap_team"] = g.home_team_ovr - g.away_team_ovr
    g["gap_offense_vs_defense_home"] = g.home_offense - g.away_defense
    g["gap_offense_vs_defense_away"] = g.away_offense - g.home_defense
    for a, b in DUELS:
        g[f"home_{a}_vs_away_{b}"] = g[f"home_unit_{a}"] - g[f"away_unit_{b}"]
        g[f"away_{a}_vs_home_{b}"] = g[f"away_unit_{a}"] - g[f"home_unit_{b}"]
    g["margin"] = g.home_score - g.away_score
    g["home_vs_line"] = g.margin - g.spread_line          # spread_line = points home expected to win by
    g = g.drop(columns=["_home", "_away"])
    return g


def pct(s):
    return f"{100 * s.mean():.1f}%" if len(s) else "-"


def main():
    t = team_numbers()
    g = games(t)
    done = g[g.margin.notna() & g.gap_team.notna()]
    out_cols = ["game_id", "season", "week", "game_type", "gameday", "away_team", "home_team", "away_score", "home_score",
                "spread_line", "home_vs_line", "home_team_ovr", "away_team_ovr", "home_offense", "away_offense",
                "home_defense", "away_defense"] + [c for c in g.columns if c.startswith(("home_unit_", "away_unit_"))] + \
               [c for c in g.columns if "_vs_" in c and c != "home_vs_line"] + ["home_QB_name", "away_QB_name"]
    g[out_cols].to_csv(os.path.join(RES, "madden_team_games.csv"), index=False)

    # 1-2. Higher rated team: won? covered? by size of gap. Seasons with launch ratings only (2001-2025)
    d = done[(done.season <= 2025) & (done.margin != 0)].copy()
    d["fav_is_home"] = d.gap_team > 0
    d["gap"] = d.gap_team.abs()
    d["higher_won"] = (d.margin > 0) == d.fav_is_home
    dl = d[d.spread_line.notna() & (d.home_vs_line != 0)].copy()
    dl["higher_covered"] = (dl.home_vs_line > 0) == dl.fav_is_home
    dl["market_agrees"] = (dl.spread_line > 0) == dl.fav_is_home
    bins = [0, 1, 2, 3, 4, 6, 100]
    d["bucket"] = pd.cut(d.gap, bins, right=False)
    dl["bucket"] = pd.cut(dl.gap, bins, right=False)

    # 3. Model: every team number and unit duel, learn 2001-2015, judge 2016-2025
    feats = [c for c in g.columns if c.startswith(("home_unit_", "away_unit_")) or c in
             ("home_offense", "away_offense", "home_defense", "away_defense", "home_team_ovr", "away_team_ovr", "gap_team",
              "gap_offense_vs_defense_home", "gap_offense_vs_defense_away")] + \
            [c for c in g.columns if "_vs_" in c and c not in ("home_vs_line",) and not c.startswith("gap_")]
    feats_line = feats + ["spread_line"]
    m = done[done.spread_line.notna() & (done.season <= 2025)].copy()
    tr, te = m[m.season <= 2015], m[m.season >= 2016]
    res = {}
    for name, f, y in [("Madden team numbers -> final margin (no line)", feats, "margin"),
                       ("Madden team numbers + line -> margin vs the line", feats_line, "home_vs_line")]:
        med = tr[f].median()
        mdl = HistGradientBoostingRegressor(max_depth=3, learning_rate=0.03, max_iter=300, l2_regularization=5.0, random_state=0)
        mdl.fit(tr[f].fillna(med), tr[y])
        p = pd.Series(mdl.predict(te[f].fillna(med)), index=te.index)
        edge = p - te.spread_line if y == "margin" else p
        e = te.assign(edge=edge)
        e = e[e.home_vs_line != 0]
        hit = lambda s: ((s.edge > 0) == (s.home_vs_line > 0)).mean()
        top = e[e.edge.abs() >= e.edge.abs().quantile(0.8)]
        su = te[te.margin != 0]
        res[name] = {"games": len(e), "ats": hit(e), "top": hit(top), "top_n": len(top),
                     "su": ((p.loc[su.index] > 0) == (su.margin > 0)).mean() if y == "margin" else np.nan,
                     "by_season": {int(s): hit(x) for s, x in e.groupby("season")}}

    L = ["# Team Madden numbers and every past game", "",
         "EA's own team ratings for past editions are not published anywhere we can reach, so these team numbers come "
         "from each edition's player cards: each team's preseason roster ranked by overall at every spot (QB1, RB1, "
         "WR1-3, TE1, OL1-5, DL1-4, LB1-3, DB1-4, K, P). Every slot is kept, the unit numbers are those slots, offense and "
         "defense are the 11 starters each, team = all 24. One row per team per edition "
         "(data/processed/madden_teams.parquet). Every game with both teams' numbers: results/madden_team_games.csv.", "",
         "Editions: Madden 02-26 launch rosters (2001-2025 seasons) and Madden 27 Week 8 update (2026). "
         "Madden 10 (2009 season) is missing in the source, so 2009 games have no numbers.", "",
         "## Teams rated per edition", "", "| Season | Teams | Best team (team number) | Worst |", "| --- | --- | --- | --- |"]
    for s, x in t.groupby("season"):
        b, w = x.loc[x.team_ovr.idxmax()], x.loc[x.team_ovr.idxmin()]
        L.append(f"| {s} | {len(x)} | {b.team} {b.team_ovr:.1f} | {w.team} {w.team_ovr:.1f} |")
    L += ["", f"## 1. Did the higher-rated Madden team win? ({len(d)} games, 2001-2025)", "",
          "Gap = team number difference.", "", "| Gap | Games | Higher-rated team won |", "| --- | --- | --- |"]
    for b, x in d.groupby("bucket", observed=True):
        L.append(f"| {b.left}-{b.right if b.right < 100 else '+'} | {len(x)} | {pct(x.higher_won)} |")
    L += [f"| All | {len(d)} | {pct(d.higher_won)} |", "",
          f"## 2. Did the higher-rated Madden team cover the spread? ({len(dl)} games)", "",
          "Split by whether the betting market also favored that team. Needed to profit at -110: 52.4%.", "",
          "| Gap | Market agrees: games | covered | Market disagrees (Madden's team is the underdog): games | covered |",
          "| --- | --- | --- | --- | --- |"]
    for b, x in dl.groupby("bucket", observed=True):
        a, n = x[x.market_agrees], x[~x.market_agrees]
        L.append(f"| {b.left}-{b.right if b.right < 100 else '+'} | {len(a)} | {pct(a.higher_covered)} | {len(n)} | {pct(n.higher_covered)} |")
    a, n = dl[dl.market_agrees], dl[~dl.market_agrees]
    L += [f"| All | {len(a)} | {pct(a.higher_covered)} | {len(n)} | {pct(n.higher_covered)} |", "",
          "By season, Madden's team as the underdog:", "", "| Season | Games | Covered |", "| --- | --- | --- |"]
    for s, x in n.groupby("season"):
        L.append(f"| {s} | {len(x)} | {pct(x.higher_covered)} |")
    L += ["", "## 3. One model on all team numbers and unit duels (learned 2001-2015, judged 2016-2025)", "",
          "| Model | Games | Covered | Strongest 20% | Picked winner | By season |", "| --- | --- | --- | --- | --- | --- |"]
    for k, v in res.items():
        L.append(f"| {k} | {v['games']} | {100 * v['ats']:.1f}% | {100 * v['top']:.1f}% ({v['top_n']}) | "
                 + (f"{100 * v['su']:.1f}%" if v["su"] == v["su"] else "-") + " | "
                 + ", ".join(f"{s}: {100 * h:.0f}%" for s, h in v["by_season"].items()) + " |")
    L += ["", "## 4. Past games that look like each unplayed game", "",
          "results/madden_team_twins/<game_id>.md: the 15 past games (2001-2025) whose home and away Madden teams are "
          "closest unit by unit (QB, RB, WR, TE, OL, DL, LB, DB for both sides), with how each one finished."]
    open(os.path.join(RES, "MADDEN_TEAMS.md"), "w").write("\n".join(L))

    # 4. Twins for unplayed games
    units = [f"{s}_unit_{u}" for s in ("home", "away") for u in OFFU + DEFU]
    pool = done[done.season <= 2025].dropna(subset=units)
    up = g[g.margin.isna() & g.home_unit_QB.notna()]
    od = os.path.join(RES, "madden_team_twins")
    os.makedirs(od, exist_ok=True)
    for _, r in up.iterrows():
        dist = (pool[units] - r[units].astype(float).values).abs().mean(axis=1)
        tw = pool.assign(_d=dist).nsmallest(15, "_d")
        W = [f"# {r.away_team} at {r.home_team}, {r.gameday} (week {r.week})", "",
             f"Madden 27 numbers: {r.home_team} team {r.home_team_ovr:.1f} (off {r.home_offense:.1f}, def {r.home_defense:.1f}, "
             f"QB {r.home_QB_name} {r.home_unit_QB:.0f}) vs {r.away_team} team {r.away_team_ovr:.1f} "
             f"(off {r.away_offense:.1f}, def {r.away_defense:.1f}, QB {r.away_QB_name} {r.away_unit_QB:.0f}). "
             f"Line: {'home ' + format(-r.spread_line, '+.1f') if r.spread_line == r.spread_line else 'not set yet'}.", "",
             "| Units (home v away) | " + " | ".join(OFFU + DEFU) + " |", "| --- |" + " --- |" * 8,
             f"| {r.home_team} | " + " | ".join(f"{r[f'home_unit_{u}']:.0f}" for u in OFFU + DEFU) + " |",
             f"| {r.away_team} | " + " | ".join(f"{r[f'away_unit_{u}']:.0f}" for u in OFFU + DEFU) + " |", "",
             "| Closeness | Past game | QBs | Score | Home line | Home vs line |", "| --- | --- | --- | --- | --- | --- |"]
        for _, x in tw.iterrows():
            W.append(f"| {max(0, 100 - 10 * x._d):.0f} | {x.gameday} {x.away_team} at {x.home_team} | {x.away_QB_name} v {x.home_QB_name} | "
                     f"{x.away_score:.0f}-{x.home_score:.0f} | "
                     + (f"{-x.spread_line:+.1f} | {x.home_vs_line:+.1f}" if x.spread_line == x.spread_line else "- | -") + " |")
        hw = (tw.margin > 0).mean(); hc = tw[tw.home_vs_line.notna() & (tw.home_vs_line != 0)]
        W += ["", f"Home side won {100 * hw:.0f}% of these {len(tw)}; covered {pct(hc.home_vs_line > 0)} of {len(hc)} with a line."]
        open(os.path.join(od, f"{r.game_id}.md"), "w").write("\n".join(W))
    print("\n".join(L)); print("twins written", len(up))


if __name__ == "__main__":
    main()
